"""Scores for extraction and question answering. Same code for the model and the baseline.

- Field F1: every (field, value) pair, plus every line item's (index, field, value), counts as one
  fact. A predicted fact is correct when the value matches exactly after whitespace normalisation.
  Precision = correct / predicted facts, recall = correct / gold facts.
- Per-field accuracy: share of documents where that header field is exactly right (missing = wrong).
- Document accuracy: share of documents where every header field and every line is right.
- QA: exact match and ANLS (average normalised Levenshtein similarity, threshold 0.5, as in DocVQA).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def norm(v: Any) -> str:
    return " ".join(str(v).split()).strip().lower()


def facts(doc: dict[str, Any] | Any) -> set[tuple[str, ...]]:
    out: set[tuple[str, ...]] = set()
    if not isinstance(doc, dict):
        return out
    for k, v in doc.items():
        if k == "items" and isinstance(v, list):
            for i, it in enumerate(v):
                if isinstance(it, dict):
                    out.update((f"items.{i}", ik, norm(iv)) for ik, iv in it.items())
        elif isinstance(v, str | int | float):
            out.add((k, norm(v)))
    return out


def _flatten_cord(doc: Any, prefix: str = "") -> set[tuple[str, ...]]:
    """CORD labels are nested (menu lists, sub_total, total); compare them as path/value facts."""
    out: set[tuple[str, ...]] = set()
    if isinstance(doc, dict):
        for k, v in doc.items():
            out |= _flatten_cord(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            out |= _flatten_cord(v, f"{prefix}[{i}]")
    else:
        out.add((prefix, norm(doc)))
    return out


def f1_scores(golds: list[Any], preds: list[Any], kind: str = "invoice") -> dict[str, float]:
    get = facts if kind == "invoice" else _flatten_cord
    tp = n_pred = n_gold = 0
    for g, p in zip(golds, preds, strict=True):
        gf, pf = get(g), get(p)
        tp += len(gf & pf)
        n_pred += len(pf)
        n_gold += len(gf)
    precision = tp / n_pred if n_pred else 0.0
    recall = tp / n_gold if n_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def field_accuracy(golds: list[dict[str, Any]], preds: list[Any], fields: list[str]) -> dict[str, float]:
    hits: dict[str, list[bool]] = defaultdict(list)
    for g, p in zip(golds, preds, strict=True):
        p = p if isinstance(p, dict) else {}
        for f in fields:
            if f in g:
                hits[f].append(norm(p.get(f, "")) == norm(g[f]))
        if g.get("items"):
            hits["items (all lines)"].append(facts({"items": g["items"]}) == facts({"items": p.get("items", [])}))
    return {f: sum(v) / len(v) for f, v in hits.items()}


def document_accuracy(golds: list[Any], preds: list[Any]) -> float:
    return sum(facts(g) == facts(p) for g, p in zip(golds, preds, strict=True)) / len(golds)


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def anls(gold: str, pred: str, threshold: float = 0.5) -> float:
    g, p = norm(gold), norm(pred)
    if not g and not p:
        return 1.0
    sim = 1 - levenshtein(g, p) / max(len(g), len(p))
    return sim if sim >= threshold else 0.0


def qa_scores(golds: list[str], preds: list[str]) -> dict[str, float]:
    n = len(golds)
    return {
        "exact_match": sum(norm(g) == norm(p) for g, p in zip(golds, preds, strict=True)) / n,
        "anls": sum(anls(g, p) for g, p in zip(golds, preds, strict=True)) / n,
    }
