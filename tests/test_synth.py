import random

from invoicedesk import synth


def test_same_seed_gives_the_same_invoice():
    a = synth.generate(5, synth.TRAIN_STYLES)
    b = synth.generate(5, synth.TRAIN_STYLES)
    assert a[1] == b[1] and a[0].tobytes() == b[0].tobytes()


def test_totals_add_up_in_the_label():
    from invoicedesk.normalize import parse_amount

    for seed in range(40):
        _, label, inv = synth.generate(seed, synth.TRAIN_STYLES)
        lines = round(sum(parse_amount(i["amount"]) for i in label["items"]), 2)
        assert abs(lines - parse_amount(label["total_ht"])) < 0.011
        ttc = parse_amount(label["total_ht"]) + parse_amount(label["tva"]) + (parse_amount(inv["timbre"]) or 0)
        assert abs(ttc - parse_amount(label["total_ttc"])) < 0.011


def test_identifiers_have_their_usual_shapes():
    import re

    for seed in range(30):
        inv = synth.make_invoice(random.Random(seed))
        assert re.fullmatch(r"\d{15}", inv["vendor_nif"])
        assert re.fullmatch(r"\d{2}/00-\d{7} [AB] \d{2}", inv["vendor_rc"])
        assert inv["tva_rate"] in {"19%", "9%"}


def test_splits_never_share_seeds_and_heldout_uses_unseen_styles():
    seen = [set(synth.split_seeds(s, 5000)) for s in synth.SPLITS]
    for i in range(len(seen)):
        for j in range(i + 1, len(seen)):
            assert not seen[i] & seen[j]
    train_styles = synth.SPLITS["train"][1]
    assert set(synth.FREE_STYLES) <= set(train_styles)
    train_fonts = {s.regular for s in train_styles} | {s.bold for s in train_styles} | {s.layout for s in train_styles}
    for s in synth.HELDOUT_STYLES:
        assert s.regular not in train_fonts and s.bold not in train_fonts and s.layout not in train_fonts


def test_seen_test_and_validation_use_only_the_six_fixed_styles():
    """v2 and v3 are compared on the same test images, so the test splits must not get the free layout."""
    for split in ("validation", "test_seen"):
        assert synth.SPLITS[split][1] == synth.TRAIN_STYLES


def test_french_amount_formats():
    assert synth.fmt_amount(1234567.5, 0) == "1 234 567,50"
    assert synth.fmt_amount(1234567.5, 1) == "1.234.567,50"
    assert synth.fmt_amount(950, 2) == "950,00"
