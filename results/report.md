Field F1 (every header field and every line-item value counts as one fact)

| Test set | Tesseract + rules | v2 | v3 (published) |
| --- | --- | --- | --- |
| Invoices, the 6 training layouts (300) | 0.428 | 0.971 | **0.968** |
| Invoices, unseen layout and font (300) | 0.477 | 0.593 | **0.698** |
| CORD-v2 test, real receipt photos (100) | n/a | 0.612 | **0.592** |

Questions (worded differently from every training question), exact match / ANLS

| Test set | v2 | v3 (published) |
| --- | --- | --- |
| Training layouts (300) | 0.427 / 0.470 | **0.777 / 0.846** |
| Unseen layout (300) | 0.410 / 0.477 | **0.737 / 0.796** |

Per field, v3, share of invoices where the field is exactly right

| Field | v3, training layouts | v3, unseen layout | OCR, training layouts | OCR, unseen layout |
| --- | --- | --- | --- | --- |
| vendor | 1.000 | 0.437 | 0.663 | 0.117 |
| vendor_address | 0.957 | 0.000 | 0.303 | 0.000 |
| vendor_nif | 0.617 | 0.220 | 0.827 | 0.927 |
| vendor_rc | 0.807 | 0.267 | 0.633 | 0.577 |
| invoice_number | 0.993 | 0.663 | 0.250 | 0.553 |
| date | 0.990 | 0.770 | 0.647 | 0.940 |
| client | 0.990 | 0.893 | 0.663 | 0.987 |
| total_ht | 0.997 | 0.707 | 0.623 | 0.770 |
| tva_rate | 1.000 | 0.733 | 0.740 | 0.937 |
| tva | 0.983 | 0.717 | 0.620 | 0.783 |
| total_ttc | 0.987 | 0.710 | 0.603 | 0.773 |
| items (all lines) | 0.943 | 0.387 | 0.000 | 0.000 |
| timbre | 0.990 | 0.730 | 0.710 | 0.829 |

Documents fully right (every field and every line)
  test_seen: v3 0.497, OCR 0.000
  test_heldout: v3 0.000, OCR 0.000

Checks on v3's output (HT + TVA + timbre = TTC, TVA rate, sum of lines, NIF length, date)
  test_seen: {'misread': 130, 'caught': 88, 'read_right': 170, 'false_alarms': 0}
  test_heldout: {'misread': 263, 'caught': 193, 'read_right': 37, 'false_alarms': 0}

Speed, one invoice, p50 / p95 seconds
  v3 on a Kaggle T4: 0.9414 / 1.2253
  OCR baseline (Kaggle CPU): 0.6891

Training: 135.5 min on a Tesla T4, 3 epochs, image 1280x960
