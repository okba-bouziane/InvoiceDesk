"""Write web/src/reader/parity.json: inputs and the Python outputs the TypeScript twins must match.

  python scripts/parity_fixture.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from invoicedesk import donut, synth  # noqa: E402
from invoicedesk.normalize import checks, parse_amount, parse_date, tidy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    seqs = [donut.json2token(synth.generate(s, synth.TRAIN_STYLES)[1]) for s in range(5)]
    seqs += [seqs[0][: len(seqs[0]) // 2], "<s_vendor>A</s_vendor><s_vendor>B</s_vendor>", "<s_total_ttc>12 3", ""]
    preds = []
    for split in ("test_seen", "test_heldout"):
        path = ROOT / "results" / "v3" / "predictions" / f"invoice_{split}.jsonl"
        preds += [json.loads(line)["pred"] for line in path.read_text().splitlines()[:60]]
    amounts = ["12 345,00", "12.345,00", "12345,00", "433 318,60 DA", "950,00", "1.234", "abc", "", "-5,00"]
    dates = ["29/12/2024", "29-12-2024", "29.12.2024", "26 janvier 2024", "3 août 2025", "31/02/2024", "hier"]
    fixture = {
        "token2json": [{"in": s, "out": donut.token2json(s)} for s in seqs],
        "tidy_checks": [{"in": p, "tidy": tidy(p), "checks": checks(tidy(p))} for p in preds],
        "amounts": [{"in": a, "out": parse_amount(a)} for a in amounts],
        "dates": [{"in": d, "out": parse_date(d)} for d in dates],
    }
    out = ROOT / "web" / "src" / "reader" / "parity.json"
    out.write_text(json.dumps(fixture, ensure_ascii=False, indent=1))
    print("written", out, {k: len(v) for k, v in fixture.items()})


if __name__ == "__main__":
    main()
