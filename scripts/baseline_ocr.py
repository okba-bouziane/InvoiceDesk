"""Baseline: Tesseract OCR (French) + hand-written rules, on the same invoice test sets.

This is the usual way invoices are digitised without a trained model. The rules read the header
fields and totals; they do not attempt the line items, so the item facts count as missed.

  python scripts/baseline_ocr.py --out build/run   # needs tesseract-ocr + tesseract-ocr-fra
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from invoicedesk import metrics, synth  # noqa: E402

AMOUNT = r"(\d{1,3}(?:[ .]\d{3})*(?:,\d{2})|\d+,\d{2})"
FORMS = r"(?:SARL|EURL|SPA|ETS|SNC)"


def _first(pattern: str, text: str, flags: int = 0) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def extract(text: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: dict[str, Any] = {}
    client_idx = next((i for i, ln in enumerate(lines) if ln.lower().startswith("client")), None)
    vendor = next((ln for i, ln in enumerate(lines)
                   if re.match(FORMS, ln) and (client_idx is None or i < client_idx)), None)
    if vendor:
        out["vendor"] = re.split(r"\s{2,}|FACTURE", vendor)[0].strip()
    if client_idx is not None and client_idx + 1 < len(lines):
        out["client"] = lines[client_idx + 1]
    fields = {
        "vendor_nif": r"NIF\s*:?\s*(\d{15})",
        "vendor_rc": r"RC\s*:?\s*(\d{2}/\d{2}-\d{7} [AB] \d{2})",
        "invoice_number": r"(?:N°|Numéro)\s*:?\s*((?:FA|F-|N° )?[\w/\-]+(?:/\d{2,4})?)",
        "date": r"(?:Date(?: de facturation)?|Le)\s*:\s*(\d{2}[/\-.]\d{2}[/\-.]\d{4}|\d{2} [a-zéû]+ \d{4})",
        "total_ht": rf"Total HT\s*:?\s*{AMOUNT}",
        "tva_rate": r"TVA\s*(\d{1,2}%)",
        "tva": rf"TVA\s*\d{{1,2}}%\s*:?\s*{AMOUNT}",
        "timbre": rf"timbre\s*:?\s*{AMOUNT}",
        "total_ttc": rf"(?:Total TTC|Net à payer TTC)\s*:?\s*{AMOUNT}",
    }
    for key, pattern in fields.items():
        value = _first(pattern, text, re.IGNORECASE)
        if value:
            out[key] = value
    if "invoice_number" in out:
        out["invoice_number"] = out["invoice_number"].removeprefix("N° ").strip()
    addr = None
    if vendor:
        i = lines.index(vendor)
        if i + 1 < len(lines) and not lines[i + 1].startswith(("Tél", "RC", "NIF")):
            addr = lines[i + 1]
    if addr:
        out["vendor_address"] = addr
    return out


def main() -> None:
    import pytesseract

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/run")
    ap.add_argument("--n-test", type=int, default=300)
    args = ap.parse_args()
    out = Path(args.out)
    results: dict[str, Any] = {"system": "tesseract-fra + rules", "tesseract": str(pytesseract.get_tesseract_version())}
    for split in ("test_seen", "test_heldout"):
        preds = []
        for s in synth.split_seeds(split, args.n_test):
            img, label, _ = synth.generate(s, synth.SPLITS[split][1])
            t0 = time.perf_counter()
            text = pytesseract.image_to_string(img, lang="fra")
            sec = time.perf_counter() - t0
            preds.append({"id": f"{split}-{s}", "gold": label, "pred": extract(text), "seconds": round(sec, 4)})
        golds, ps = [p["gold"] for p in preds], [p["pred"] for p in preds]
        header_golds = [{k: v for k, v in g.items() if k != "items"} for g in golds]
        res = {
            "n": len(preds),
            **metrics.f1_scores(golds, ps),
            "header_only": metrics.f1_scores(header_golds, ps),
            "document_accuracy": metrics.document_accuracy(golds, ps),
            "field_accuracy": metrics.field_accuracy(golds, ps, synth.FIELDS),
        }
        secs = sorted(p["seconds"] for p in preds)
        res["seconds_p50"] = secs[len(secs) // 2]
        results[f"invoice_{split}"] = res
        (out / "predictions").mkdir(parents=True, exist_ok=True)
        with (out / "predictions" / f"baseline_{split}.jsonl").open("w") as f:
            for p in preds:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(split, json.dumps(res, ensure_ascii=False), flush=True)
    (out / "baseline_metrics.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
