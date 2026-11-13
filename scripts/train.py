"""Fine-tune Donut on three tasks at once and score it on the held-out test sets.

Tasks (the first decoder token selects one, see invoicedesk/donut.py):
  1. CORD-v2 receipt parsing (public dataset, 800 train / 100 validation / 100 test)
  2. Algerian invoice parsing (generated, invoicedesk/synth.py)
  3. Questions about an Algerian invoice, in French or English

  python scripts/train.py --out build/run            # GPU (Kaggle T4)
  python scripts/train.py --smoke --out build/smoke  # a few steps on CPU/MPS, checks the pipeline

Writes <out>/model (weights + processor), <out>/predictions/*.jsonl, <out>/metrics.json.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from invoicedesk import donut, metrics, qa, synth  # noqa: E402
from invoicedesk.training import next_token_loss  # noqa: E402

BASE = "naver-clova-ix/donut-base"
BASE_REVISION = "a959cf33c20e09215873e338299c900f57047c61"
CORD = "naver-clova-ix/cord-v2"
CORD_REVISION = "7f0115a4b758a71d6473b8d085751692da2fef98"
IMAGE_SIZE = [1280, 960]  # height, width
MAX_LEN = 512
GEN_MAX = MAX_LEN  # the smoke run generates short sequences only


def device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


# ---- data ---------------------------------------------------------------------------------------

def load_cord(split: str, limit: int = 0) -> list[dict[str, Any]]:
    from datasets import load_dataset

    ds = load_dataset(CORD, split=split, revision=CORD_REVISION)
    rows = []
    for i, ex in enumerate(ds):
        if limit and i >= limit:
            break
        gt = json.loads(ex["ground_truth"])["gt_parse"]
        rows.append({"kind": "cord", "id": f"cord-{split}-{i}", "image": ex["image"].convert("RGB"), "label": gt})
    return rows


def invoice_rows(split: str, n: int) -> list[dict[str, Any]]:
    """Lazy rows: the image is rendered from its seed when the loader asks for it."""
    return [{"kind": "invoice", "id": f"{split}-{s}", "seed": s, "split": split}
            for s in synth.split_seeds(split, n)]


def materialise(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return (image, prompt, target) samples for a row. QA rows expand to several questions."""
    if row["kind"] == "cord":
        return [{"image": row["image"], "prompt": donut.TASK_CORD, "target": donut.json2token(row["label"]),
                 "id": row["id"]}]
    img, label, _ = synth.generate(row["seed"], synth.SPLITS[row["split"]][1])
    if row["kind"] == "invoice":
        return [{"image": img, "prompt": donut.TASK_INVOICE, "target": donut.json2token(label), "id": row["id"]}]
    rng = random.Random(row["seed"] * 7 + 1)
    out = []
    for field, question, answer in qa.make_questions(label, rng, row["per_doc"], row["templates"]):
        out.append({"image": img, "prompt": donut.qa_prompt(question), "target": f"{answer}</s_answer>",
                    "id": f"{row['id']}-{field}", "field": field, "question": question, "answer": answer})
    return out


class TrainSet(Dataset):
    def __init__(self, rows: list[dict[str, Any]], processor: Any, seed: int) -> None:
        self.rows, self.processor, self.seed = rows, processor, seed

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int) -> dict[str, torch.Tensor]:
        samples = materialise(self.rows[i])
        s = random.Random(self.seed + i).choice(samples)  # QA rows: one random question per visit
        tok = self.processor.tokenizer
        pixel = self.processor(s["image"], return_tensors="pt").pixel_values[0]
        prompt_ids = tok(s["prompt"], add_special_tokens=False).input_ids
        target_ids = tok(s["target"] + tok.eos_token, add_special_tokens=False).input_ids
        ids = (prompt_ids + target_ids)[:MAX_LEN]
        labels = [-100] * len(prompt_ids) + target_ids  # no loss on the task prompt or the question
        return {"pixel_values": pixel, "ids": torch.tensor(ids), "labels": torch.tensor(labels[:MAX_LEN])}


def collate(batch: list[dict[str, torch.Tensor]], pad_id: int) -> dict[str, torch.Tensor]:
    n = max(len(b["ids"]) for b in batch)
    ids = torch.full((len(batch), n), pad_id)
    labels = torch.full((len(batch), n), -100)
    for k, b in enumerate(batch):
        ids[k, : len(b["ids"])] = b["ids"]
        labels[k, : len(b["labels"])] = b["labels"]
    return {"pixel_values": torch.stack([b["pixel_values"] for b in batch]), "ids": ids, "labels": labels}


# ---- model --------------------------------------------------------------------------------------

def build(smoke: bool) -> tuple[Any, Any]:
    from transformers import DonutProcessor, VisionEncoderDecoderModel

    processor = DonutProcessor.from_pretrained(BASE, revision=BASE_REVISION)
    processor.image_processor.size = {"height": IMAGE_SIZE[0], "width": IMAGE_SIZE[1]}
    processor.image_processor.do_align_long_axis = False
    model = VisionEncoderDecoderModel.from_pretrained(BASE, revision=BASE_REVISION)
    model.config.encoder.image_size = IMAGE_SIZE
    model.config.decoder.max_length = MAX_LEN
    return processor, model


def add_tokens(processor: Any, model: Any, labels: list[Any]) -> int:
    keys: set[str] = set()
    for lab in labels:
        donut.json2token(lab, keys)
    keys |= {donut.TASK_CORD, donut.TASK_INVOICE, donut.TASK_QA, donut.SEP,
             "<s_question>", "</s_question>", "<s_answer>", "</s_answer>"}
    added = processor.tokenizer.add_special_tokens({"additional_special_tokens": sorted(keys)})
    model.decoder.resize_token_embeddings(len(processor.tokenizer))
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.decoder_start_token_id = processor.tokenizer.convert_tokens_to_ids(donut.TASK_INVOICE)
    return added


@torch.no_grad()
def generate(model: Any, processor: Any, image: Any, prompt: str, dev: str) -> tuple[str, float]:
    tok = processor.tokenizer
    pixel = processor(image, return_tensors="pt").pixel_values.to(dev)
    prompt_ids = tok(prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(dev)
    t0 = time.perf_counter()
    with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=dev == "cuda"):
        out = model.generate(
            pixel, decoder_input_ids=prompt_ids, max_length=GEN_MAX, pad_token_id=tok.pad_token_id,
            eos_token_id=tok.eos_token_id, use_cache=True, num_beams=1,
            bad_words_ids=[[tok.unk_token_id]],
        )
    if dev == "cuda":
        torch.cuda.synchronize()
    seconds = time.perf_counter() - t0
    seq = tok.batch_decode(out)[0]
    return seq, seconds


def predict_parse(model: Any, processor: Any, rows: list[dict[str, Any]], dev: str) -> list[dict[str, Any]]:
    model.eval()
    out = []
    tok = processor.tokenizer
    for row in rows:
        s = materialise(row)[0]
        seq, sec = generate(model, processor, s["image"], s["prompt"], dev)
        seq = donut.clean_generated(seq, tok.eos_token, tok.pad_token)
        gold = row["label"] if row["kind"] == "cord" else synth.generate(row["seed"], synth.SPLITS[row["split"]][1])[1]
        out.append({"id": row["id"], "gold": gold, "pred": donut.token2json(seq), "seconds": round(sec, 4)})
    return out


def predict_qa(model: Any, processor: Any, rows: list[dict[str, Any]], dev: str) -> list[dict[str, Any]]:
    model.eval()
    out = []
    for row in rows:
        for s in materialise(row):
            seq, sec = generate(model, processor, s["image"], s["prompt"], dev)
            out.append({"id": s["id"], "field": s["field"], "question": s["question"], "gold": s["answer"],
                        "pred": donut.parse_answer(seq), "seconds": round(sec, 4)})
    return out


def score_parse(preds: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    golds, ps = [p["gold"] for p in preds], [p["pred"] for p in preds]
    res: dict[str, Any] = {"n": len(preds), **metrics.f1_scores(golds, ps, kind)}
    if kind == "invoice":
        res["document_accuracy"] = metrics.document_accuracy(golds, ps)
        res["field_accuracy"] = metrics.field_accuracy(golds, ps, synth.FIELDS)
    secs = sorted(p["seconds"] for p in preds)
    res["seconds_p50"] = secs[len(secs) // 2]
    res["seconds_p95"] = secs[max(0, math.ceil(0.95 * len(secs)) - 1)]
    return res


def score_qa(preds: list[dict[str, Any]]) -> dict[str, Any]:
    res: dict[str, Any] = {"n": len(preds), **metrics.qa_scores([p["gold"] for p in preds], [p["pred"] for p in preds])}
    lang_fr = [p for p in preds if not p["question"].isascii()]
    by_field: dict[str, list[dict[str, Any]]] = {}
    for p in preds:
        by_field.setdefault(p["field"], []).append(p)
    res["by_field_exact_match"] = {
        f: metrics.qa_scores([p["gold"] for p in v], [p["pred"] for p in v])["exact_match"] for f, v in by_field.items()
    }
    res["n_questions_with_accents"] = len(lang_fr)
    return res


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---- main ---------------------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/run")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--accum", type=int, default=4)
    ap.add_argument("--n-invoice", type=int, default=3000, help="generated invoices for training")
    ap.add_argument("--n-qa", type=int, default=3000, help="invoices used for question training")
    ap.add_argument("--n-test", type=int, default=300)
    ap.add_argument("--n-val", type=int, default=60)
    ap.add_argument("--hours", type=float, default=7.0, help="stop training after this long")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        global GEN_MAX
        args.n_invoice, args.n_qa, args.n_test, args.n_val, args.epochs = 4, 4, 2, 2, 1
        args.batch, args.accum = 1, 2
        IMAGE_SIZE[:] = [640, 480]
        GEN_MAX = 48
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    out = Path(args.out)
    dev = device()

    processor, model = build(args.smoke)
    cord_train = load_cord("train", 4 if args.smoke else 0)
    cord_val = load_cord("validation", 2 if args.smoke else 0)
    cord_test = load_cord("test", 2 if args.smoke else 0)
    inv_train = invoice_rows("train", args.n_invoice)
    # QA training uses different invoices from the parsing set (seeds after n_invoice)
    qa_train = [{"kind": "qa", "id": f"qa-train-{s}", "seed": s, "split": "train", "per_doc": 3,
                 "templates": qa.TRAIN_TEMPLATES}
                for s in synth.split_seeds("train", args.n_invoice + args.n_qa)[args.n_invoice:]]
    labels = [r["label"] for r in cord_train + cord_val + cord_test]
    labels += [synth.generate(r["seed"], synth.TRAIN_STYLES)[1] for r in inv_train[:300]]
    added = add_tokens(processor, model, labels)
    model.to(dev)

    train_rows = cord_train + inv_train + qa_train
    ds = TrainSet(train_rows, processor, args.seed)
    pad_id = processor.tokenizer.pad_token_id
    loader = DataLoader(ds, batch_size=args.batch, shuffle=True, num_workers=0 if args.smoke else args.workers,
                        collate_fn=lambda b: collate(b, pad_id), persistent_workers=not args.smoke)
    steps_total = math.ceil(len(loader) * args.epochs / args.accum)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    warm = max(1, int(0.05 * steps_total))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warm) * max(0.0, (steps_total - s) / max(1, steps_total - warm))
    )
    scaler = torch.amp.GradScaler("cuda", enabled=dev == "cuda")
    val_rows = cord_val[: args.n_val] + invoice_rows("validation", args.n_val)

    print(json.dumps({"device": dev, "train_rows": len(train_rows), "cord_train": len(cord_train),
                      "added_tokens": added, "optimizer_steps": steps_total}), flush=True)
    t0, step, history, best = time.time(), 0, [], -1.0
    epoch = 0
    stop = False
    while epoch < math.ceil(args.epochs) and not stop:
        model.train()
        running = 0.0
        for k, batch in enumerate(loader):
            if epoch + k / len(loader) >= args.epochs:
                break
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=dev == "cuda"):
                loss = next_token_loss(model, batch["pixel_values"].to(dev), batch["ids"].to(dev),
                                       batch["labels"].to(dev)) / args.accum
            scaler.scale(loss).backward()
            running += loss.item() * args.accum
            if (k + 1) % args.accum == 0:
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(opt)
                scaler.update()
                opt.zero_grad(set_to_none=True)
                sched.step()
                step += 1
                if step % 50 == 0:
                    print(json.dumps({"step": step, "epoch": round(epoch + k / len(loader), 3),
                                      "loss": round(running / (k + 1), 4),
                                      "minutes": round((time.time() - t0) / 60, 1)}), flush=True)
            if (time.time() - t0) / 3600 > args.hours:
                stop = True
                break
        epoch += 1
        preds = predict_parse(model, processor, val_rows, dev)
        cord_f1 = score_parse([p for p in preds if p["id"].startswith("cord")], "cord")["f1"]
        inv_f1 = score_parse([p for p in preds if not p["id"].startswith("cord")], "invoice")["f1"]
        history.append({"epoch": epoch, "train_loss": round(running / max(1, k + 1), 4),
                        "val_cord_f1": round(cord_f1, 4), "val_invoice_f1": round(inv_f1, 4),
                        "minutes": round((time.time() - t0) / 60, 1)})
        print(json.dumps(history[-1]), flush=True)
        if epoch == 1 and cord_f1 == 0 and inv_f1 == 0 and not args.smoke:
            # a model that learned anything reads at least some fields after one epoch
            raise SystemExit("validation F1 is 0 on both tasks after epoch 1: stopping instead of wasting GPU hours")
        if (cord_f1 + inv_f1) / 2 > best:
            best = (cord_f1 + inv_f1) / 2
            model.save_pretrained(out / "model")
            processor.save_pretrained(out / "model")
    train_minutes = round((time.time() - t0) / 60, 1)

    from transformers import VisionEncoderDecoderModel

    model = VisionEncoderDecoderModel.from_pretrained(out / "model").to(dev)
    results: dict[str, Any] = {"device": dev, "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None,
                               "base_model": BASE, "base_revision": BASE_REVISION, "image_size": IMAGE_SIZE,
                               "args": vars(args), "train_minutes": train_minutes, "history": history}
    tests = {
        "cord_test": (cord_test, "cord"),
        "invoice_test_seen": (invoice_rows("test_seen", args.n_test), "invoice"),
        "invoice_test_heldout": (invoice_rows("test_heldout", args.n_test), "invoice"),
    }
    for name, (rows, kind) in tests.items():
        preds = predict_parse(model, processor, rows, dev)
        write_jsonl(out / "predictions" / f"{name}.jsonl", preds)
        results[name] = score_parse(preds, kind)
        print(name, json.dumps(results[name]), flush=True)
    for split in ("test_seen", "test_heldout"):
        rows = [{"kind": "qa", "id": f"qa-{split}-{s}", "seed": s, "split": split, "per_doc": 1,
                 "templates": qa.TEST_TEMPLATES} for s in synth.split_seeds(split, args.n_test)]
        preds = predict_qa(model, processor, rows, dev)
        write_jsonl(out / "predictions" / f"qa_{split}.jsonl", preds)
        results[f"qa_{split}"] = score_qa(preds)
        print(f"qa_{split}", json.dumps(results[f"qa_{split}"]), flush=True)
    (out / "metrics.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
