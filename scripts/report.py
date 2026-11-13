"""Print the README tables from results/<run>/ (metrics written by the Kaggle job, plus the predictions).

python scripts/report.py            # v3 (published) against v2 and the OCR baseline
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from invoicedesk.metrics import norm  # noqa: E402
from invoicedesk.normalize import checks, tidy  # noqa: E402

RES = Path(__file__).resolve().parents[1] / "results"


def load(run: str) -> tuple[dict, dict]:
    return json.loads((RES / run / "metrics.json").read_text()), json.loads(
        (RES / run / "baseline_metrics.json").read_text()
    )


def f(x: float) -> str:
    return f"{x:.3f}"


CHECKED = ("total_ht", "tva", "tva_rate", "timbre", "total_ttc", "vendor_nif", "date")


def check_catch_rate(run: str, split: str) -> dict[str, int]:
    """Do the arithmetic checks flag the invoices where a checked value was misread?

    An invoice counts as misread when any value the checks look at (amounts, TVA rate, line
    amounts, NIF, date) differs from the label. `false_alarms` counts flags on invoices whose
    checked values are all right; by construction a check can only fail on inconsistent values.
    """
    path = RES / run / "predictions" / f"invoice_{split}.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    out = {"misread": 0, "caught": 0, "read_right": 0, "false_alarms": 0}
    for r in rows:
        gold, pred = r["gold"], tidy(r["pred"])
        same = all(norm(pred.get(k, "")) == norm(gold.get(k, "")) for k in CHECKED if gold.get(k))
        same &= [norm(i.get("amount", "")) for i in gold.get("items", [])] == [
            norm(i.get("amount", "")) for i in pred.get("items", [])
        ]
        fails = [c for c in checks(pred) if not c["ok"]]
        flagged = bool(fails) or not pred.get("total_ttc")  # a missing total is shown as missing, too
        key = ("read_right", "false_alarms") if same else ("misread", "caught")
        out[key[0]] += 1
        out[key[1]] += flagged
    return out


def main() -> None:
    v3, base = load("v3")
    v2, _ = load("v2")
    print("Field F1 (every header field and every line-item value counts as one fact)\n")
    print("| Test set | Tesseract + rules | v2 | v3 (published) |")
    print("| --- | --- | --- | --- |")
    for split, label in (
        ("test_seen", "Invoices, the 6 training layouts (300)"),
        ("test_heldout", "Invoices, unseen layout and font (300)"),
    ):
        b = base[f"invoice_{split}"]
        print(f"| {label} | {f(b['f1'])} | {f(v2[f'invoice_{split}']['f1'])} | **{f(v3[f'invoice_{split}']['f1'])}** |")
    cord2, cord3 = f(v2["cord_test"]["f1"]), f(v3["cord_test"]["f1"])
    print(f"| CORD-v2 test, real receipt photos (100) | n/a | {cord2} | **{cord3}** |")

    print("\nQuestions (worded differently from every training question), exact match / ANLS\n")
    print("| Test set | v2 | v3 (published) |")
    print("| --- | --- | --- |")
    for split, label in (("test_seen", "Training layouts (300)"), ("test_heldout", "Unseen layout (300)")):
        a, b = v2[f"qa_{split}"], v3[f"qa_{split}"]
        print(f"| {label} | {f(a['exact_match'])} / {f(a['anls'])} | **{f(b['exact_match'])} / {f(b['anls'])}** |")

    print("\nPer field, v3, share of invoices where the field is exactly right\n")
    seen, held = v3["invoice_test_seen"]["field_accuracy"], v3["invoice_test_heldout"]["field_accuracy"]
    bs, bh = base["invoice_test_seen"]["field_accuracy"], base["invoice_test_heldout"]["field_accuracy"]
    print("| Field | v3, training layouts | v3, unseen layout | OCR, training layouts | OCR, unseen layout |")
    print("| --- | --- | --- | --- | --- |")
    for k in seen:
        print(f"| {k} | {f(seen[k])} | {f(held.get(k, 0))} | {f(bs.get(k, 0))} | {f(bh.get(k, 0))} |")

    print("\nDocuments fully right (every field and every line)")
    for split in ("test_seen", "test_heldout"):
        print(
            f"  {split}: v3 {f(v3[f'invoice_{split}']['document_accuracy'])}, "
            f"OCR {f(base[f'invoice_{split}']['document_accuracy'])}"
        )

    print("\nChecks on v3's output (HT + TVA + timbre = TTC, TVA rate, sum of lines, NIF length, date)")
    for split in ("test_seen", "test_heldout"):
        print(f"  {split}: {check_catch_rate('v3', split)}")

    print("\nSpeed, one invoice, p50 / p95 seconds")
    print(f"  v3 on a Kaggle T4: {v3['invoice_test_seen']['seconds_p50']} / {v3['invoice_test_seen']['seconds_p95']}")
    print(f"  OCR baseline (Kaggle CPU): {base['invoice_test_seen']['seconds_p50']}")
    print(
        f"\nTraining: {v3['train_minutes']} min on a {v3['gpu']}, {v3['args']['epochs']:.0f} epochs, "
        f"image {v3['image_size'][0]}x{v3['image_size'][1]}"
    )


if __name__ == "__main__":
    main()
