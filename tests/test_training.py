import torch
import torch.nn.functional as F
from transformers import (
    DonutSwinConfig,
    MBartConfig,
    VisionEncoderDecoderConfig,
    VisionEncoderDecoderModel,
)

from invoicedesk.training import next_token_loss


def tiny_donut() -> VisionEncoderDecoderModel:
    """A random Donut-shaped model small enough for CPU, built without any download."""
    enc = DonutSwinConfig(
        image_size=[64, 64], patch_size=4, embed_dim=16, depths=[1, 1], num_heads=[2, 2], window_size=4
    )
    dec = MBartConfig(vocab_size=50, d_model=16, decoder_layers=1, decoder_attention_heads=2, decoder_ffn_dim=32,
                      encoder_layers=1, encoder_attention_heads=2, encoder_ffn_dim=32, max_position_embeddings=64,
                      is_decoder=True, add_cross_attention=True)
    torch.manual_seed(0)
    return VisionEncoderDecoderModel(config=VisionEncoderDecoderConfig.from_encoder_decoder_configs(enc, dec)).eval()


def test_loss_scores_the_next_token_not_the_one_after():
    model = tiny_donut()
    pixels = torch.randn(1, 3, 64, 64)
    ids = torch.randint(3, 50, (1, 10))
    labels = ids.clone()
    labels[:, :2] = -100  # the task prompt is not scored
    with torch.no_grad():
        loss = next_token_loss(model, pixels, ids, labels)
        logits = model(pixel_values=pixels, decoder_input_ids=ids[:, :-1]).logits
    expected = F.cross_entropy(logits[0], labels[0, 1:], ignore_index=-100)
    two_ahead = F.cross_entropy(logits[0, :-1], labels[0, 2:], ignore_index=-100)
    assert torch.isclose(loss, expected)
    assert not torch.isclose(loss, two_ahead)


def test_a_few_steps_teach_the_tiny_model_a_fixed_sequence():
    """The objective and teacher forcing fit together: greedy decoding reproduces what was trained."""
    model = tiny_donut().train()
    pixels = torch.randn(1, 3, 64, 64)
    ids = torch.tensor([[5, 11, 23, 7, 31, 2]])  # prompt 5, then the target ending with eos 2
    labels = ids.clone()
    labels[:, :1] = -100
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    for _ in range(150):
        opt.zero_grad()
        next_token_loss(model, pixels, ids, labels).backward()
        opt.step()
    model.eval()
    out = ids[:, :1]
    with torch.no_grad():
        for _ in range(5):
            logits = model(pixel_values=pixels, decoder_input_ids=out).logits
            out = torch.cat([out, logits[:, -1:].argmax(-1)], dim=1)
    assert out.tolist() == ids.tolist()
