import random

from invoicedesk import qa, synth


def test_test_questions_are_worded_differently_from_training():
    train = {q for forms in qa.TRAIN_TEMPLATES.values() for q in forms}
    test = {q for forms in qa.TEST_TEMPLATES.values() for q in forms}
    assert not train & test
    assert qa.TRAIN_TEMPLATES.keys() == qa.TEST_TEMPLATES.keys()


def test_answers_come_from_the_label():
    _, label, _ = synth.generate(11, synth.TRAIN_STYLES)
    triples = qa.make_questions(label, random.Random(0), 20, qa.TRAIN_TEMPLATES)
    assert len({f for f, _, _ in triples}) == len(triples)
    for field, _question, answer in triples:
        if field == "item_amount":
            assert answer in {i["amount"] for i in label["items"]}
        elif field == "item_qty":
            assert answer in {i["qty"] for i in label["items"]}
        else:
            assert answer == label[field]


def test_no_timbre_question_when_the_invoice_has_none():
    for seed in range(30):
        _, label, inv = synth.generate(seed, synth.TRAIN_STYLES)
        fields = {f for f, _, _ in qa.make_questions(label, random.Random(1), 50, qa.TRAIN_TEMPLATES)}
        assert ("timbre" in fields) == bool(inv["timbre"])
