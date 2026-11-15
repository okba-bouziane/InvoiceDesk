"""Build a Kaggle job that scores the 8-bit ONNX model (the one the browser demo runs) on CPU.

It downloads the model from the Hugging Face Hub, regenerates the test invoices from their seeds,
and compares with the published v3 predictions on the same images.

  python kaggle/build_eval_kernel.py --user <kaggle-username>
  # full-precision encoder: add --encoder encoder_model.onnx --slug invoicedesk-eval-fp32enc
  kaggle kernels push -p build/kaggle-eval
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNNER = r"""
import base64, io, os, subprocess, tarfile
os.chdir("/kaggle/working")
tarfile.open(fileobj=io.BytesIO(base64.b64decode(BUNDLE))).extractall(".")

def run(cmd):
    print("$", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)

run('pip install -q "transformers>=4.45,<5" "sentencepiece>=0.2" onnx onnxruntime huggingface_hub')
run("nproc")
from huggingface_hub import snapshot_download
decoder = "decoder_model_merged.onnx" if QUANTIZE else "decoder_model_merged_quantized.onnx"
files = ["*.json", "*.model", "onnx/" + ENCODER, "onnx/" + decoder]
path = snapshot_download(REPO, allow_patterns=files)
if QUANTIZE:
    # quantize the full-precision decoder here, then evaluate the new file
    run(f"mkdir -p work/onnx && cp -L {path}/*.json {path}/*.model work/ && cp -L {path}/onnx/{ENCODER} work/onnx/")
    run(f"cp -L {path}/onnx/{decoder} work/")
    path = "/kaggle/working/work"
    os.environ["INT8_DIR"] = path
    run(f"python scripts/export_onnx.py quantize --parts decoder_model_merged {QUANTIZE}")
    run(f"rm work/{decoder}")
os.environ["INT8_DIR"] = path
os.environ["INT8_ENCODER"] = ENCODER
os.environ["INT8_OUT"] = "/kaggle/working/int8"
run(f"python scripts/export_onnx.py evaluate --n {N} --variant '{SLUG}'")
if QUANTIZE:
    run("mkdir -p out && mv work/onnx/decoder_model_merged_quantized.onnx out/ && rm -rf work")
"""


def bundle() -> str:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in sorted((ROOT / "invoicedesk").rglob("*.py")) + [ROOT / "scripts" / "export_onnx.py"]:
            tar.add(f, arcname=str(f.relative_to(ROOT)))
        for f in sorted((ROOT / "results" / "v3" / "predictions").glob("*.jsonl")):
            tar.add(f, arcname=str(f.relative_to(ROOT)))
    return base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--slug", default="invoicedesk-eval-int8")
    ap.add_argument("--repo", default="okba-bouziane/invoicedesk-donut")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--encoder", default="encoder_model_quantized.onnx", help="or encoder_model.onnx (full precision)")
    ap.add_argument("--quantize", default="", help='re-quantize the decoder first, e.g. "--per-channel --keep-head"')
    ap.add_argument("--out", default="build/kaggle-eval")
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    head = f"BUNDLE = {bundle()!r}\nREPO = {args.repo!r}\nN = {args.n}\nENCODER = {args.encoder!r}\n"
    head += f"QUANTIZE = {args.quantize!r}\nSLUG = {args.slug!r}\n"
    (out / "run.py").write_text(head + RUNNER)
    (out / "kernel-metadata.json").write_text(
        json.dumps(
            {
                "id": f"{args.user}/{args.slug}",
                "title": args.slug,
                "code_file": "run.py",
                "language": "python",
                "kernel_type": "script",
                "is_private": True,
                "enable_gpu": False,
                "enable_internet": True,
                "dataset_sources": [],
                "competition_sources": [],
                "kernel_sources": [],
            },
            indent=2,
        )
    )
    print(f"kernel written to {out}")


if __name__ == "__main__":
    main()
