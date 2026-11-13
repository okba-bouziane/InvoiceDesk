from invoicedesk import metrics


def test_field_f1_counts_header_fields_and_line_items():
    gold = {"vendor": "SARL Atlas", "total_ttc": "1 190,00", "items": [{"name": "A", "amount": "1 000,00"}]}
    pred = {"vendor": "SARL  atlas", "total_ttc": "1 190,01", "items": [{"name": "A", "amount": "1 000,00"}]}
    s = metrics.f1_scores([gold], [pred])
    assert s["precision"] == s["recall"] == 0.75  # vendor matches after normalisation, total does not


def test_missing_prediction_scores_zero_recall():
    s = metrics.f1_scores([{"vendor": "X"}], [{}])
    assert s == {"precision": 0.0, "recall": 0.0, "f1": 0.0}


def test_document_accuracy_needs_every_fact():
    g = {"a": "1", "items": [{"n": "x"}]}
    assert metrics.document_accuracy([g, g], [g, {"a": "1"}]) == 0.5


def test_field_accuracy_treats_missing_as_wrong():
    acc = metrics.field_accuracy([{"vendor": "X", "date": "1"}], [{"vendor": "X"}], ["vendor", "date"])
    assert acc == {"vendor": 1.0, "date": 0.0}


def test_anls_rewards_near_misses_only_above_threshold():
    assert metrics.anls("123456789012345", "123456789012345") == 1.0
    assert 0.9 < metrics.anls("123456789012345", "123456789012346") < 1.0
    assert metrics.anls("SARL Atlas", "19%") == 0.0


def test_cord_labels_are_compared_as_paths():
    gold = {"menu": [{"nm": "Tea", "price": "10"}], "total": {"total_price": "10"}}
    pred = {"menu": [{"nm": "Tea", "price": "12"}], "total": {"total_price": "10"}}
    assert round(metrics.f1_scores([gold], [pred], "cord")["f1"], 3) == 0.667
