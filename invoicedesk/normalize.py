"""Turn printed values into typed ones and check that an invoice adds up."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
         "octobre", "novembre", "décembre"]
    )
}


def parse_amount(text: object) -> float | None:
    """'12 345,00' / '12.345,00' / '12345,00' / '12 345,00 DA' -> 12345.0. Anything else -> None."""
    if not text or not isinstance(text, str):  # the model can return a list when it repeats a field
        return None
    s = re.sub(r"[^\d,.\-]", "", text.replace(" ", " "))
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1 or re.search(r"\.\d{3}$", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_date(text: object) -> str | None:
    """'29/12/2024', '29-12-2024', '29.12.2024', '29 décembre 2024' -> '2024-12-29'."""
    if not text or not isinstance(text, str):
        return None
    t = text.strip().lower()
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", t)
    if m:
        d, mo, y = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{1,2})\s+([a-zéû]+)\s+(\d{4})", t)
        if not m or m.group(2) not in MONTHS:
            return None
        d, mo, y = int(m.group(1)), MONTHS[m.group(2)], int(m.group(3))
    try:
        return dt.date(y, mo, d).isoformat()
    except ValueError:
        return None


def checks(fields: dict[str, Any]) -> list[dict[str, Any]]:
    """Consistency checks a bookkeeper would do by hand. Each: {name, ok, detail}."""
    out: list[dict[str, Any]] = []
    ht, tva, ttc = (parse_amount(fields.get(k)) for k in ("total_ht", "tva", "total_ttc"))
    timbre = parse_amount(fields.get("timbre")) or 0.0
    if ht is not None and tva is not None and ttc is not None:
        expected = round(ht + tva + timbre, 2)
        out.append({"name": "HT + TVA + timbre = TTC", "ok": abs(expected - ttc) <= 0.02,
                    "detail": f"{expected:.2f} vs {ttc:.2f}"})
    rate = fields.get("tva_rate")
    if ht is not None and tva is not None and isinstance(rate, str) and rate:
        r = parse_amount(rate.replace("%", ""))
        if r is not None:
            want = round(ht * r / 100, 2)
            out.append({"name": f"TVA = {rate} of HT", "ok": abs(want - tva) <= 0.02,
                        "detail": f"{want:.2f} vs {tva:.2f}"})
    items = fields.get("items") or []
    amounts = [parse_amount(i.get("amount")) for i in items if isinstance(i, dict)]
    if ht is not None and amounts and all(a is not None for a in amounts):
        s = round(sum(a for a in amounts if a is not None), 2)
        out.append({"name": "sum of lines = HT", "ok": abs(s - ht) <= 0.02, "detail": f"{s:.2f} vs {ht:.2f}"})
    nif = fields.get("vendor_nif")
    if isinstance(nif, str) and nif:
        out.append({"name": "NIF has 15 digits", "ok": bool(re.fullmatch(r"\d{15}", nif)), "detail": nif})
    if isinstance(fields.get("date"), str) and fields["date"]:
        out.append({"name": "date is valid", "ok": parse_date(fields["date"]) is not None,
                    "detail": fields["date"]})
    return out


def tidy(fields: object) -> dict[str, Any]:
    """Give raw model output the documented shape: header fields are strings, `items` a list of
    objects with string values. A repeated field keeps its first value; anything else is dropped."""
    if not isinstance(fields, dict):
        return {}

    def text(v: object) -> str | None:
        if isinstance(v, list):
            v = next((x for x in v if isinstance(x, str) and x.strip()), None)
        return v.strip() if isinstance(v, str) and v.strip() else None

    out: dict[str, Any] = {}
    for k, v in fields.items():
        if k == "items":
            rows = v if isinstance(v, list) else [v]
            items = [
                {ik: t for ik, iv in r.items() if (t := text(iv)) is not None} for r in rows if isinstance(r, dict)
            ]
            if items := [i for i in items if i]:
                out["items"] = items
        elif (t := text(v)) is not None:
            out[k] = t
    return out
