import pytest

from invoicedesk.normalize import checks, parse_amount, parse_date


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("12 345,00", 12345.0),
        ("12.345,00", 12345.0),
        ("12345,00", 12345.0),
        ("433 318,60 DA", 433318.6),
        ("950,00", 950.0),
        ("", None),
        (None, None),
        ("abc", None),
    ],
)
def test_amounts(text, value):
    assert parse_amount(text) == value


@pytest.mark.parametrize(
    ("text", "iso"),
    [
        ("29/12/2024", "2024-12-29"),
        ("29-12-2024", "2024-12-29"),
        ("29.12.2024", "2024-12-29"),
        ("26 janvier 2024", "2024-01-26"),
        ("3 août 2025", "2025-08-03"),
        ("31/02/2024", None),
        ("hier", None),
    ],
)
def test_dates(text, iso):
    assert parse_date(text) == iso


def test_checks_flag_a_total_that_does_not_add_up():
    fields = {
        "total_ht": "1 000,00",
        "tva_rate": "19%",
        "tva": "190,00",
        "total_ttc": "1 200,00",
        "items": [{"amount": "1 000,00"}],
        "vendor_nif": "12345",
        "date": "01/01/2025",
    }
    result = {c["name"]: c["ok"] for c in checks(fields)}
    assert result == {
        "HT + TVA + timbre = TTC": False,
        "TVA = 19% of HT": True,
        "sum of lines = HT": True,
        "NIF has 15 digits": False,
        "date is valid": True,
    }


def test_checks_include_the_stamp_duty():
    fields = {"total_ht": "1 000,00", "tva": "190,00", "timbre": "11,90", "total_ttc": "1 201,90"}
    assert checks(fields)[0]["ok"]


def test_checks_survive_odd_model_output():
    """The model can repeat a field (a list) or emit an object; the API must not crash on it."""
    fields = {
        "total_ht": ["1 000,00", "1 000,00"],
        "tva": {},
        "total_ttc": "1 190,00",
        "tva_rate": ["19%"],
        "vendor_nif": ["1"],
        "date": ["01/01/2025"],
        "items": "oops",
    }
    assert checks(fields) == []
    assert parse_amount(["1,00"]) is None and parse_date({"d": 1}) is None


def test_tidy_gives_raw_output_the_documented_shape():
    from invoicedesk.normalize import tidy

    raw = {
        "vendor": ["SARL Atlas", "SARL Atlas"],
        "tva": {},
        "total_ttc": " 1 190,00 ",
        "client": "",
        "items": {"name": "Ciment", "amount": ["900,00"], "qty": {}},
    }
    assert tidy(raw) == {
        "vendor": "SARL Atlas",
        "total_ttc": "1 190,00",
        "items": [{"name": "Ciment", "amount": "900,00"}],
    }
    assert tidy("not json") == {}
