"""Load the fine-tuned model and read invoices: fields as JSON, or the answer to a question."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from PIL import Image

from . import donut

MAX_LEN = 512


class DonutReader:
    def __init__(self, model_dir: str | Path, device: str | None = None) -> None:
        import torch
        from transformers import DonutProcessor, VisionEncoderDecoderModel

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = DonutProcessor.from_pretrained(model_dir)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_dir).to(self.device).eval()
        torch.set_num_threads(max(1, torch.get_num_threads()))

    def _generate(self, image: Image.Image, prompt: str) -> str:
        tok = self.processor.tokenizer
        pixel = self.processor(image.convert("RGB"), return_tensors="pt").pixel_values.to(self.device)
        prompt_ids = tok(prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(self.device)
        with self.torch.inference_mode():
            out = self.model.generate(
                pixel, decoder_input_ids=prompt_ids, max_length=MAX_LEN, pad_token_id=tok.pad_token_id,
                eos_token_id=tok.eos_token_id, use_cache=True, num_beams=1, bad_words_ids=[[tok.unk_token_id]],
            )
        return tok.batch_decode(out)[0]

    def extract(self, image: Image.Image) -> dict[str, Any]:
        tok = self.processor.tokenizer
        seq = donut.clean_generated(self._generate(image, donut.TASK_INVOICE), tok.eos_token, tok.pad_token)
        parsed = donut.token2json(seq)
        return parsed if isinstance(parsed, dict) else {}

    def ask(self, image: Image.Image, question: str) -> str:
        return donut.parse_answer(self._generate(image, donut.qa_prompt(question.strip())))


def timed(fn: Any, *args: Any) -> tuple[Any, float]:
    t0 = time.perf_counter()
    result = fn(*args)
    return result, time.perf_counter() - t0
