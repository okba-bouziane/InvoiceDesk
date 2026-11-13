from scripts.baseline_ocr import extract

OCR_TEXT = """SARL Tassili Informatique
12, Rue Larbi Ben M'hidi, Hydra, Alger
RC : 16/00-1234567 B 19
NIF : 001216012345678
FACTURE
N° : FA24/0042
Date : 03/04/2024
Client :
EURL Numidia
Total HT : 10 000,00 DA
TVA 19% : 1 900,00
Total TTC : 11 900,00 DA
"""


def test_rules_read_header_and_totals_from_ocr_text():
    out = extract(OCR_TEXT)
    assert out["vendor"] == "SARL Tassili Informatique"
    assert out["vendor_address"].startswith("12, Rue Larbi")
    assert out["vendor_nif"] == "001216012345678"
    assert out["vendor_rc"] == "16/00-1234567 B 19"
    assert out["invoice_number"] == "FA24/0042"
    assert out["date"] == "03/04/2024"
    assert out["client"] == "EURL Numidia"
    totals = (out["total_ht"], out["tva_rate"], out["tva"], out["total_ttc"])
    assert totals == ("10 000,00", "19%", "1 900,00", "11 900,00")
