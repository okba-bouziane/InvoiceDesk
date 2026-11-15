"""8-bit ONNX copy of the model for the in-browser demo (transformers.js), and its score.

  optimum-cli export onnx --model models/invoicedesk --task image-to-text-with-past build/onnx
  python scripts/export_onnx.py quantize          # -> build/onnx/onnx/*_quantized.onnx
  python scripts/export_onnx.py evaluate --n 100  # -> results/int8/metrics.json

`evaluate` runs the 8-bit model with ONNX Runtime on the first N images of each test set and
scores it with the same code as the PyTorch model; the v3 numbers on the same N images are
recomputed from results/v3/predictions so the two are compared on identical inputs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from invoicedesk import donut, metrics, qa, synth  # noqa: E402
from invoicedesk.normalize import tidy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# INT8_DIR: a folder with the processor files and onnx/*_quantized.onnx (a snapshot of the Hub repo works)
ONNX = Path(os.environ.get("INT8_DIR", ROOT / "build" / "onnx"))
PARTS = ("encoder_model", "decoder_model_merged")
# INT8_ENCODER: which encoder file to run; onnx/encoder_model.onnx keeps the image encoder at full precision
ENCODER = os.environ.get("INT8_ENCODER", "encoder_model_quantized.onnx")


HEAD = "/decoder/lm_head/MatMul"  # the output layer, one score per vocabulary token (57k), in both If branches


def quantize(parts: tuple[str, ...] = PARTS, per_channel: bool = False, keep_head: bool = False) -> None:
    """8-bit weights for each part. --per-channel gives every output channel its own scale;
    --keep-head leaves the decoder's output layer at full precision."""
    from onnxruntime.quantization import QuantType, quantize_dynamic

    out = ONNX / "onnx"
    out.mkdir(exist_ok=True)
    for part in parts:
        t0 = time.time()
        # the merged decoder keeps its weights inside an If subgraph, skipped unless EnableSubgraph is set
        quantize_dynamic(
            ONNX / f"{part}.onnx",
            out / f"{part}_quantized.onnx",
            weight_type=QuantType.QUInt8,
            per_channel=per_channel,
            nodes_to_exclude=[HEAD] if keep_head and part.startswith("decoder") else [],
            extra_options={"EnableSubgraph": True},
        )
        before = (ONNX / f"{part}.onnx").stat().st_size / 1e6
        after = (out / f"{part}_quantized.onnx").stat().st_size / 1e6
        print(f"{part}: {before:.0f} MB -> {after:.0f} MB in {time.time() - t0:.0f} s", flush=True)


class Int8Reader:
    """Greedy decoding with ONNX Runtime on the two 8-bit files, the same loop transformers.js runs:
    encoder once, then the merged decoder (first call without cache, then one token at a time)."""

    def __init__(self) -> None:
        import onnxruntime as ort
        from transformers import DonutProcessor

        self.enc = ort.InferenceSession(str(ONNX / "onnx" / ENCODER))
        self.dec = ort.InferenceSession(str(ONNX / "onnx" / "decoder_model_merged_quantized.onnx"))
        self.past = [i.name for i in self.dec.get_inputs() if i.name.startswith("past_key_values")]
        self.outputs = [o.name for o in self.dec.get_outputs()]
        self.heads = self.dec.get_inputs()[2].shape[1]
        self.processor = DonutProcessor.from_pretrained(ONNX)
        self.tok = self.processor.tokenizer

    def __call__(self, image, prompt: str, max_length: int = 512) -> tuple[str, float]:
        import numpy as np

        pixels = self.processor(image, return_tensors="np").pixel_values.astype(np.float32)
        ids = self.tok(prompt, add_special_tokens=False, return_tensors="np").input_ids.astype(np.int64)
        t0 = time.perf_counter()
        hidden = self.enc.run(None, {"pixel_values": pixels})[0]
        past = {n: np.zeros((1, self.heads, 0, 64), dtype=np.float32) for n in self.past}
        step_ids, first, out = ids, True, list(ids[0])
        while len(out) < max_length:
            feeds = {
                "input_ids": step_ids,
                "encoder_hidden_states": hidden,
                **past,
                "use_cache_branch": np.array([not first]),
            }
            res = dict(zip(self.outputs, self.dec.run(None, feeds), strict=True))
            logits = res["logits"][0, -1]
            logits[self.tok.unk_token_id] = -np.inf
            nxt = int(logits.argmax())
            out.append(nxt)
            if nxt == self.tok.eos_token_id:
                break
            # decoder keys/values grow every step; the encoder ones are computed on the first call only
            past = {
                n: res[n.replace("past_key_values", "present")] if (first or ".decoder." in n) else past[n]
                for n in self.past
            }
            step_ids, first = np.array([[nxt]], dtype=np.int64), False
        return self.tok.decode(out), time.perf_counter() - t0


def published(split: str, kind: str, n: int) -> list[dict]:
    path = ROOT / "results" / "v3" / "predictions" / f"{kind}_{split}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()][:n]


def evaluate(n: int, variant: str = "") -> None:
    reader = Int8Reader()
    tok = reader.tok
    encoder = "8-bit" if "quantized" in ENCODER else "full-precision"
    runtime = f"onnxruntime CPU, 8-bit decoder, {encoder} encoder"
    sizes = {f: (ONNX / "onnx" / f).stat().st_size for f in (ENCODER, "decoder_model_merged_quantized.onnx")}
    out: dict = {"n_per_set": n, "runtime": runtime, "variant": variant, "file_bytes": sizes, "sets": {}}
    for split in ("test_seen", "test_heldout"):
        golds, preds, secs, q_gold, q_pred = [], [], [], [], []
        for s in synth.split_seeds(split, n):
            img, label, _ = synth.generate(s, synth.SPLITS[split][1])
            seq, sec = reader(img, donut.TASK_INVOICE)
            golds.append(label)
            preds.append(tidy(donut.token2json(donut.clean_generated(seq, tok.eos_token, tok.pad_token))))
            secs.append(sec)
            field, question, answer = qa.make_questions(
                label, __import__("random").Random(s * 7 + 1), 1, qa.TEST_TEMPLATES
            )[0]
            seq, _ = reader(img, donut.qa_prompt(question))
            q_gold.append(answer)
            q_pred.append(donut.parse_answer(seq))
        ref = published(split, "invoice", n)
        ref_q = published(split, "qa", n)
        assert [r["gold"] for r in ref] == golds, "the published predictions are for different images"
        out["sets"][split] = {
            "int8_field_f1": metrics.f1_scores(golds, preds)["f1"],
            "v3_field_f1_same_images": metrics.f1_scores(golds, [tidy(r["pred"]) for r in ref])["f1"],
            "int8_qa_exact": metrics.qa_scores(q_gold, q_pred)["exact_match"],
            "v3_qa_exact_same_images": metrics.qa_scores([r["gold"] for r in ref_q], [r["pred"] for r in ref_q])[
                "exact_match"
            ],
            "int8_seconds_p50": sorted(secs)[len(secs) // 2],
        }
        print(split, json.dumps(out["sets"][split]), flush=True)
    path = Path(os.environ.get("INT8_OUT", ROOT / "results" / "int8")) / "metrics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["quantize", "evaluate"])
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--parts", nargs="+", default=list(PARTS))
    ap.add_argument("--per-channel", action="store_true")
    ap.add_argument("--keep-head", action="store_true")
    ap.add_argument("--variant", default="", help="a label saved with the evaluation")
    args = ap.parse_args()
    if args.step == "quantize":
        quantize(tuple(args.parts), args.per_channel, args.keep_head)
    else:
        evaluate(args.n, args.variant)


if __name__ == "__main__":
    main()
