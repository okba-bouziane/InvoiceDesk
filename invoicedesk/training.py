"""Training pieces kept apart from the script so they can be tested without a GPU or a download."""

from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F


def next_token_loss(model: Any, pixel_values: torch.Tensor, ids: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    """Cross-entropy of predicting token i+1 from tokens 0..i (teacher forcing).

    The loss is computed here instead of passing `labels` to the model: with transformers 4.57,
    `VisionEncoderDecoderModel` falls back to `ForCausalLMLoss`, which shifts the labels by one
    position itself. Shifting them here as well trained the first Kaggle run to predict the token
    two steps ahead: the training loss went down normally and every prediction was garbage.
    """
    logits = model(pixel_values=pixel_values, decoder_input_ids=ids[:, :-1]).logits
    targets = labels[:, 1:]
    return F.cross_entropy(logits.reshape(-1, logits.size(-1)).float(), targets.reshape(-1), ignore_index=-100)
