"""Questions about an invoice, in French and English, with the answer taken from its label.

Training uses `TRAIN_TEMPLATES`; the test questions use different wordings (`TEST_TEMPLATES`) so the
score measures understanding of the question, not memorised phrasing.
"""

from __future__ import annotations

import random
from typing import Any

TRAIN_TEMPLATES: dict[str, list[str]] = {
    "vendor": [
        "Quel est le fournisseur ?", "Who issued this invoice?", "Nom de la société émettrice ?",
        "Qui est le vendeur ?", "Quel est le nom du fournisseur ?", "Which supplier sent this invoice?",
        "Who is the supplier?", "Name of the vendor?", "De quelle société vient cette facture ?",
        "Raison sociale du fournisseur ?",
    ],
    "vendor_nif": [
        "Quel est le NIF du fournisseur ?", "What is the supplier's tax number (NIF)?",
        "Numéro d'identification fiscale du fournisseur ?", "NIF du vendeur ?", "Supplier NIF?",
        "What NIF is printed for the supplier?", "Donne le NIF.", "Tax identification number of the supplier?",
        "Quel NIF figure sur la facture ?", "Le numéro NIF ?",
    ],
    "vendor_rc": [
        "Quel est le numéro du registre de commerce ?", "What is the RC number?", "Numéro RC du fournisseur ?",
        "Registre de commerce ?", "Trade register number?", "What is the supplier's commercial register?",
        "Quel est le RC ?", "RC number of the vendor?", "N° de registre du commerce du vendeur ?",
        "Give me the trade register number.",
    ],
    "invoice_number": [
        "Quel est le numéro de la facture ?", "What is the invoice number?", "Numéro de la facture ?",
        "Référence de la facture ?", "Invoice reference?", "Which number does this invoice have?",
        "Quelle est la référence ?", "Invoice no.?", "N° de facture ?", "Give me the invoice number.",
    ],
    "date": [
        "Quelle est la date de la facture ?", "When was this invoice issued?", "Date de la facture ?",
        "De quand date la facture ?", "Invoice date?", "On what date was it issued?",
        "Quand a-t-elle été émise ?", "What is the date?", "Date d'émission de la facture ?",
        "Which day is on the invoice?",
    ],
    "client": [
        "Qui est le client ?", "Who is the invoice addressed to?", "Nom du client ?", "Pour qui est la facture ?",
        "Who is the buyer?", "Customer name?", "Qui doit payer cette facture ?", "Who was billed?",
        "Quel est le destinataire ?", "Billed to whom?",
    ],
    "total_ht": [
        "Quel est le total hors taxes ?", "What is the total before tax?", "Total HT ?", "Montant hors taxe ?",
        "Net amount before VAT?", "What is the subtotal excluding tax?", "Combien fait le total HT ?",
        "Amount without VAT?", "Sous-total HT ?", "Total net of tax?",
    ],
    "tva": [
        "Quel est le montant de la TVA ?", "How much VAT is charged?", "Montant TVA ?", "Combien de taxe ?",
        "VAT charged?", "What is the tax amount?", "Combien la TVA coûte-t-elle ?", "Amount of VAT?",
        "Valeur de la TVA ?", "How much is the VAT in dinars?",
    ],
    "tva_rate": [
        "Quel est le taux de TVA ?", "What VAT rate applies?", "Taux de TVA appliqué ?", "TVA à combien ?",
        "VAT rate?", "Which VAT percentage?", "Quel pourcentage de TVA ?", "What is the tax rate?",
        "Taux de taxe ?", "Percentage of VAT applied?",
    ],
    "total_ttc": [
        "Quel est le montant TTC ?", "What is the total amount to pay?", "Combien faut-il payer au total ?",
        "Total TTC ?", "Combien reste à payer ?", "Total including VAT?", "How much is due?",
        "Montant total à régler ?",
        "Grand total?", "What do I pay in total?",
    ],
    "timbre": [
        "Quel est le montant du droit de timbre ?", "How much is the stamp duty?", "Droit de timbre ?",
        "Combien de timbre ?", "Stamp tax amount?", "Montant du timbre fiscal ?", "What is the stamp duty?",
        "Timbre à payer ?", "Fiscal stamp amount?", "Combien coûte le timbre ?",
    ],
    "item_amount": [
        "Quel est le montant de la ligne « {item} » ?", "What is the amount for {item}?", "Montant pour {item} ?",
        "Combien pour {item} ?", "Line amount of {item}?", "How much do the {item} cost in total?",
        "Total de la ligne {item} ?", "Price of the {item} line?", "Montant HT de {item} ?", "{item}: amount?",
    ],
    "item_qty": [
        "Quelle quantité de « {item} » ?", "How many {item} were bought?", "Quantité de {item} ?",
        "Combien de {item} ?", "Qty of {item}?", "Number of {item}?", "Combien d'articles {item} ?",
        "How many units of {item}?", "Nombre de {item} commandés ?", "{item}: quantity?",
    ],
}
TEST_TEMPLATES: dict[str, list[str]] = {
    "vendor": ["Quelle entreprise a établi cette facture ?", "Which company is the seller?"],
    "vendor_nif": ["Donne-moi le numéro d'identification fiscale du vendeur.", "Seller NIF?"],
    "vendor_rc": ["RC du vendeur ?", "Commercial register number of the seller?"],
    "invoice_number": ["Numéro de facture ?", "Which invoice number is this?"],
    "date": ["Date d'émission ?", "What date is on the invoice?"],
    "client": ["À qui la facture est-elle adressée ?", "Who is the customer?"],
    "total_ht": ["Montant HT ?", "Total excluding VAT?"],
    "tva": ["Combien de TVA ?", "VAT amount?"],
    "tva_rate": ["TVA à quel taux ?", "Which VAT percentage is used?"],
    "total_ttc": ["Net à payer ?", "Grand total including tax?"],
    "timbre": ["Timbre fiscal ?", "Stamp duty amount?"],
    "item_amount": ["Combien coûte la ligne {item} au total ?", "Line total for {item}?"],
    "item_qty": ["Combien d'unités de {item} ?", "Quantity of {item}?"],
}


def make_questions(
    label: dict[str, Any], rng: random.Random, n: int, templates: dict[str, list[str]]
) -> list[tuple[str, str, str]]:
    """Up to `n` (field, question, answer) triples, each on a different field."""
    candidates: list[tuple[str, str, str]] = []
    for field, forms in templates.items():
        if field.startswith("item_"):
            items = label.get("items") or []
            if not items:
                continue
            it = rng.choice(items)
            key = "amount" if field == "item_amount" else "qty"
            candidates.append((field, rng.choice(forms).format(item=it["name"]), it[key]))
        elif label.get(field):
            candidates.append((field, rng.choice(forms), label[field]))
    rng.shuffle(candidates)
    return candidates[:n]
