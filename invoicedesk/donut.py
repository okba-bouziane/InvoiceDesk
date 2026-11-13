"""Turning labels into Donut target sequences and generated sequences back into JSON.

Donut is an encoder-decoder: a Swin image encoder and a BART-style text decoder. It reads the page
pixels directly (no OCR step) and writes a sequence such as
`<s_vendor>SARL Atlas</s_vendor><s_items><s_name>Ciment</s_name>...<sep/>...</s_items>`. The
first token says which task to do:

- `<s_cord-v2>`: parse a CORD receipt (public dataset)
- `<s_dzinv>`: parse an Algerian invoice into the fields in `invoicedesk.synth.FIELDS`
- `<s_docvqa><s_question>...</s_question><s_answer>`: answer a question about the page
"""

from __future__ import annotations

import re
from typing import Any

TASK_CORD = "<s_cord-v2>"
TASK_INVOICE = "<s_dzinv>"
TASK_QA = "<s_docvqa>"
SEP = "<sep/>"


def json2token(obj: Any, keys: set[str] | None = None, sort_keys: bool = True) -> str:
    """Serialise a label. `keys`, if given, collects every field name (they become new tokens)."""
    if isinstance(obj, dict):
        if len(obj) == 1 and "text_sequence" in obj:
            return str(obj["text_sequence"])
        out = ""
        for k in sorted(obj) if sort_keys else obj:
            if keys is not None:
                keys.update({f"<s_{k}>", f"</s_{k}>"})
            out += f"<s_{k}>" + json2token(obj[k], keys, sort_keys) + f"</s_{k}>"
        return out
    if isinstance(obj, list):
        return SEP.join(json2token(v, keys, sort_keys) for v in obj)
    return str(obj)


def token2json(seq: str) -> dict[str, Any] | list[Any] | str:
    """Parse a generated sequence back into JSON; tolerant of a truncated or malformed tail."""
    out: dict[str, Any] = {}
    seq = seq.strip()
    while seq:
        start = re.search(r"<s_(.*?)>", seq)
        if start is None:
            break
        key = start.group(1)
        end = re.search(rf"</s_{re.escape(key)}>", seq)
        if end is None:  # unclosed: drop this opening tag and keep going
            seq = seq.replace(start.group(), "", 1)
            continue
        inner = seq[start.end() : end.start()]
        if re.search(r"<s_.*?>", inner):  # nested object or list of objects
            parts = [token2json(p) for p in inner.split(SEP)]
            parts = [p for p in parts if p]
            value: Any = parts if len(parts) > 1 or key == "items" else (parts[0] if parts else {})
        else:
            items = [p.strip() for p in inner.split(SEP)]
            value = items if len(items) > 1 else items[0]
        if key in out:  # repeated key: keep both
            out[key] = (out[key] if isinstance(out[key], list) else [out[key]]) + (
                value if isinstance(value, list) else [value]
            )
        else:
            out[key] = value
        seq = seq[end.end() :].strip()
    return out


def qa_prompt(question: str) -> str:
    return f"{TASK_QA}<s_question>{question}</s_question><s_answer>"


def qa_target(question: str, answer: str) -> str:
    return f"{qa_prompt(question)}{answer}</s_answer>"


def parse_answer(seq: str) -> str:
    m = re.search(r"<s_answer>(.*?)(?:</s_answer>|$)", seq, re.DOTALL)
    return (m.group(1) if m else "").strip()


def clean_generated(seq: str, eos: str, pad: str) -> str:
    """Drop special tokens added by generation and the leading task token."""
    seq = seq.replace(eos, "").replace(pad, "")
    return re.sub(r"^\s*<s_(cord-v2|dzinv)>", "", seq, count=1).strip()
