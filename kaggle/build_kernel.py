"""Build a self-contained Kaggle kernel that fine-tunes and evaluates the model on a GPU.

The kernel is one script: it unpacks this repo's `invoicedesk/` and `scripts/` (embedded as base64),
installs Tesseract for the baseline, trains, evaluates, and leaves the model, predictions and
metrics in /kaggle/working for `kaggle kernels output`.

  python kaggle/build_kernel.py --user <kaggle-username>
  kaggle kernels push -p build/kaggle-kernel
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNNER = r'''
import base64, io, os, subprocess, tarfile, time
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.chdir("/kaggle/working")
tarfile.open(fileobj=io.BytesIO(base64.b64decode(BUNDLE))).extractall(".")

def run(cmd, check=True):
    print("$", cmd, flush=True); t0 = time.time()
    subprocess.run(cmd, shell=True, check=check)
    print(f"done in {(time.time() - t0) / 60:.1f} min", flush=True)

run('pip install -q "transformers>=4.45,<5" "sentencepiece>=0.2" "datasets>=3.0" pytesseract')
run("nvidia-smi --query-gpu=name,memory.total --format=csv")
run("apt-get install -y -q tesseract-ocr tesseract-ocr-fra > /dev/null", check=False)
run("python scripts/baseline_ocr.py --out run", check=False)
run(f"python scripts/train.py --out run {TRAIN_ARGS}")
'''


def bundle() -> str:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for folder in ("invoicedesk", "scripts"):
            for f in sorted((ROOT / folder).rglob("*.py")):
                tar.add(f, arcname=str(f.relative_to(ROOT)))
    return base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--slug", default="invoicedesk-train")
    ap.add_argument("--out", default="build/kaggle-kernel")
    ap.add_argument("--train-args", default="", help="extra arguments for scripts/train.py")
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "run.py").write_text(f"BUNDLE = {bundle()!r}\nTRAIN_ARGS = {args.train_args!r}\n{RUNNER}")
    (out / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{args.user}/{args.slug}",
        "title": args.slug,
        "code_file": "run.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "dataset_sources": [], "competition_sources": [], "kernel_sources": [],
    }, indent=2))
    print(f"kernel written to {out}")


if __name__ == "__main__":
    main()
