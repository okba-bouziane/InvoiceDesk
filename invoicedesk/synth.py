"""Synthetic Algerian supplier invoices (French), rendered as photographed pages with labels.

There is no public dataset of Algerian invoices, so this module generates them: company names,
wilaya addresses, NIF / NIS / RC / AI identifiers in their usual shapes, line items, TVA at 19% or
9%, an optional stamp-duty line, French number formatting (12 345,00) and several date styles.
The label is the text exactly as printed, so the model learns to read, not to calculate.

Layouts and fonts are split: `TRAIN_STYLES` are used for train / validation / test-seen, and
`HELDOUT_STYLES` (a layout and a font the model never sees in training) only for test-heldout.
Everything is driven by a seeded `random.Random`, so a split is reproducible from its seed.
"""

from __future__ import annotations

import datetime as dt
import io
import os
import random
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FIELDS = [
    "vendor",
    "vendor_address",
    "vendor_nif",
    "vendor_rc",
    "invoice_number",
    "date",
    "client",
    "total_ht",
    "tva_rate",
    "tva",
    "timbre",
    "total_ttc",
]
ITEM_FIELDS = ["name", "qty", "unit_price", "amount"]

FORMS = ["SARL", "EURL", "SPA", "ETS", "SNC"]
NAMES = [
    "El Baraka", "Djurdjura", "Atlas", "Hodna", "Tassili", "Numidia", "Sahel", "El Medina",
    "Ahaggar", "Zibans", "Saoura", "Chelia", "Cirta", "Ifri", "Tafna", "Seybouse", "El Bahdja",
    "Mitidja", "Rym", "Nour El Houda", "Amel", "Ouarsenis", "Tikjda", "El Wiam", "Babors",
    "Soummam", "Dahra", "El Feth", "Ennour", "Belezma", "Tadjenanet", "Ksar", "El Khadra",
]
ACTIVITIES = {
    "Informatique": [
        ("Ordinateur portable 15 pouces", 85000, 160000), ("Écran 24 pouces", 22000, 38000),
        ("Clavier sans fil", 2500, 6500), ("Souris optique", 900, 2800),
        ("Imprimante laser", 28000, 65000), ("Cartouche toner noir", 4500, 12000),
        ("Câble réseau Cat6 (305 m)", 9000, 16000), ("Onduleur 1500 VA", 18000, 32000),
        ("Disque SSD 1 To", 9500, 19000), ("Switch 24 ports", 21000, 45000),
    ],
    "Matériaux de construction": [
        ("Ciment CPJ 42.5 (sac 50 kg)", 750, 1100), ("Rond à béton Ø12 (barre)", 1300, 1900),
        ("Brique 12 trous", 28, 45), ("Sable de carrière (m3)", 2500, 4200),
        ("Plâtre (sac 25 kg)", 450, 700), ("Carrelage 45x45 (m2)", 1200, 2900),
        ("Peinture vinylique 25 kg", 5200, 9800), ("Tube PVC Ø110 (6 m)", 1600, 2700),
    ],
    "Alimentation générale": [
        ("Huile de table 5 L", 620, 780), ("Sucre blanc 1 kg", 90, 120), ("Semoule fine 25 kg", 1100, 1450),
        ("Café moulu 250 g", 350, 520), ("Lait en poudre 500 g", 520, 690), ("Pâtes 500 g", 70, 120),
        ("Concentré de tomate 800 g", 280, 380), ("Eau minérale 1,5 L (pack 6)", 160, 240),
        ("Lentilles 1 kg", 230, 320), ("Thé vert 500 g", 450, 720),
    ],
    "Pièces auto": [
        ("Plaquettes de frein avant", 3200, 7800), ("Filtre à huile", 650, 1500),
        ("Batterie 70 Ah", 14000, 23000), ("Huile moteur 5W30 (5 L)", 4200, 8500),
        ("Courroie de distribution", 4800, 11000), ("Amortisseur arrière", 6500, 14500),
        ("Bougie d'allumage", 450, 1200), ("Filtre à air", 900, 2200),
    ],
    "Fournitures de bureau": [
        ("Rame papier A4 80 g", 650, 950), ("Classeur à levier", 220, 380), ("Stylo bille (boîte 50)", 900, 1600),
        ("Agrafeuse", 450, 1300), ("Chemise cartonnée (lot 100)", 1100, 1900),
        ("Registre 200 pages", 380, 650), ("Calculatrice de bureau", 1200, 3200),
    ],
    "Équipements électriques": [
        ("Disjoncteur 16 A", 450, 950), ("Câble électrique 2,5 mm2 (100 m)", 6500, 11000),
        ("Projecteur LED 100 W", 3800, 7900), ("Tableau électrique 12 modules", 2900, 6200),
        ("Prise murale double", 280, 650), ("Interrupteur va-et-vient", 190, 420),
    ],
}
CITIES = [
    ("16", "Alger", ["Bab Ezzouar", "Hydra", "Rouiba", "Chéraga", "Kouba", "Bir Mourad Raïs", "El Harrach"]),
    ("31", "Oran", ["Es Senia", "Bir El Djir", "Arzew", "Hai Sabah"]),
    ("25", "Constantine", ["El Khroub", "Ali Mendjeli", "Zighoud Youcef"]),
    ("19", "Sétif", ["El Eulma", "Ain Arnat", "Sétif"]),
    ("09", "Blida", ["Boufarik", "Ouled Yaïch", "Blida"]),
    ("23", "Annaba", ["El Bouni", "Sidi Amar", "Annaba"]),
    ("06", "Béjaïa", ["Akbou", "El Kseur", "Béjaïa"]),
    ("13", "Tlemcen", ["Maghnia", "Mansourah", "Tlemcen"]),
    ("05", "Batna", ["Barika", "Batna"]),
    ("15", "Tizi Ouzou", ["Draâ Ben Khedda", "Azazga", "Tizi Ouzou"]),
    ("07", "Biskra", ["Tolga", "Biskra"]),
    ("30", "Ouargla", ["Hassi Messaoud", "Touggourt"]),
]
STREETS = [
    "Cité {n} Logements, Bt {b}", "Zone d'activités, Lot n° {n}", "{n}, Rue Larbi Ben M'hidi",
    "{n}, Boulevard de l'ALN", "Rue des Frères Bouadou, n° {n}", "Lotissement {b}, n° {n}",
    "Zone industrielle, Ilot {b} n° {n}", "{n}, Avenue de l'Indépendance",
]
FIRST = ["Karim", "Sofiane", "Amine", "Yacine", "Nadia", "Samira", "Rachid", "Lamia", "Walid",
         "Mourad", "Imene", "Hichem", "Farid", "Leila", "Nassim", "Khaled", "Djamel", "Sarah"]
LAST = ["Benali", "Haddad", "Mansouri", "Boudiaf", "Cherif", "Belkacem", "Meziane", "Brahimi",
        "Ait Ahmed", "Zerrouki", "Kaci", "Bensalem", "Hamidi", "Rahmani", "Saadi", "Lounis"]
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
          "octobre", "novembre", "décembre"]


# ---- invoice data -------------------------------------------------------------------------------

def fmt_amount(x: float, style: int) -> str:
    """French-style amounts as Algerian invoices print them: 12 345,00 / 12.345,00 / 12345,00."""
    whole, cents = f"{x:.2f}".split(".")
    groups = []
    while whole:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    sep = [" ", ".", ""][style]
    return f"{sep.join(groups)},{cents}"


def fmt_date(d: dt.date, style: int) -> str:
    if style == 0:
        return d.strftime("%d/%m/%Y")
    if style == 1:
        return d.strftime("%d-%m-%Y")
    if style == 2:
        return f"{d.day:02d} {MONTHS[d.month - 1]} {d.year}"
    return d.strftime("%d.%m.%Y")


def digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


def company(rng: random.Random, activity: str) -> str:
    name = rng.choice(NAMES)
    form = rng.choice(FORMS)
    if rng.random() < 0.5:
        return f"{form} {name} {activity.split()[0]}"
    return f"{form} {name}"


def address(rng: random.Random) -> tuple[str, str]:
    code, wilaya, communes = rng.choice(CITIES)
    street = rng.choice(STREETS).format(n=rng.randint(1, 600), b=rng.choice("ABCDEFGH") + str(rng.randint(1, 30)))
    return f"{street}, {rng.choice(communes)}, {wilaya}", code


def make_invoice(rng: random.Random) -> dict[str, Any]:
    """Labelled content of one invoice; every value is a string exactly as it will be printed."""
    activity = rng.choice(list(ACTIVITIES))
    vendor = company(rng, activity)
    vendor_address, code = address(rng)
    amount_style = rng.choice([0, 0, 1, 2])
    tva_rate = rng.choice([19, 19, 19, 9])
    n_items = rng.randint(1, 5)
    items, total = [], 0.0
    for name, lo, hi in rng.sample(ACTIVITIES[activity], k=min(n_items, len(ACTIVITIES[activity]))):
        qty = rng.choice([1, 1, 2, 3, 4, 5, 6, 10, 12, 20, 24, 50, 100]) if hi < 5000 else rng.randint(1, 4)
        price = round(rng.uniform(lo, hi) / 10) * 10 if hi > 2000 else round(rng.uniform(lo, hi), 2)
        amount = round(qty * price, 2)
        total += amount
        items.append({"name": name, "qty": str(qty), "unit_price": fmt_amount(price, amount_style),
                      "amount": fmt_amount(amount, amount_style)})
    total_ht = round(total, 2)
    tva = round(total_ht * tva_rate / 100, 2)
    cash = rng.random() < 0.35
    timbre = round(min(max((total_ht + tva) * 0.01, 5), 10000), 2) if cash else 0.0
    ttc = round(total_ht + tva + timbre, 2)
    day = dt.date(2024, 1, 1) + dt.timedelta(days=rng.randint(0, 1050))
    client_is_company = rng.random() < 0.7
    client_activity = rng.choice(list(ACTIVITIES))
    client = company(rng, client_activity) if client_is_company else f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    year = str(day.year)
    number = rng.choice([
        f"FA{year[2:]}/{rng.randint(1, 9999):04d}", f"{rng.randint(1, 999):03d}/{year}",
        f"F-{year}-{rng.randint(1, 99999):05d}", f"N° {rng.randint(100, 9999)}/{year[2:]}",
    ])
    rc_letter = rng.choice(["B", "B", "A"])
    return {
        "vendor": vendor,
        "vendor_address": vendor_address,
        "vendor_nif": digits(rng, 15),
        "vendor_nis": digits(rng, 15),
        "vendor_rc": f"{code}/00-{digits(rng, 7)} {rc_letter} {rng.randint(98, 124) % 100:02d}",
        "vendor_ai": digits(rng, 11),
        "vendor_phone": f"0{rng.choice('2345')}{rng.randint(1, 9)} {digits(rng, 2)} {digits(rng, 2)} {digits(rng, 2)}",
        "invoice_number": number,
        "date": fmt_date(day, rng.choice([0, 0, 1, 2, 3])),
        "client": client,
        "client_address": address(rng)[0],
        "items": items,
        "total_ht": fmt_amount(total_ht, amount_style),
        "tva_rate": f"{tva_rate}%",
        "tva": fmt_amount(tva, amount_style),
        "timbre": fmt_amount(timbre, amount_style) if cash else "",
        "total_ttc": fmt_amount(ttc, amount_style),
        "payment": "Espèces" if cash else rng.choice(["Chèque", "Virement bancaire", "À terme 30 jours"]),
    }


def label(inv: dict[str, Any]) -> dict[str, Any]:
    """The target the model is trained to produce (the fields a bookkeeper types in)."""
    out: dict[str, Any] = {k: inv[k] for k in FIELDS if inv.get(k)}
    out["items"] = [{k: it[k] for k in ITEM_FIELDS} for it in inv["items"]]
    return out


# ---- rendering ----------------------------------------------------------------------------------

def _font_dir() -> str:
    import matplotlib

    return os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")


@dataclass(frozen=True)
class Style:
    name: str
    regular: str
    bold: str
    layout: str  # "classic" | "banner" | "compact" | "boxed"


TRAIN_STYLES = [
    Style("sans-classic", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "classic"),
    Style("serif-classic", "DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "classic"),
    Style("sans-banner", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "banner"),
    Style("stix-banner", "STIXGeneral.ttf", "STIXGeneralBol.ttf", "banner"),
    Style("serif-compact", "DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "compact"),
    Style("stix-compact", "STIXGeneral.ttf", "STIXGeneralBol.ttf", "compact"),
]
# Training only (added for v3): one "free" layout whose blocks, table style, labels and spacing
# are drawn at random per invoice, in fonts and slants the six fixed styles do not use.
# None of it touches the held-out signature below: no monospace font, no right-aligned supplier
# block, no boxed metadata or totals, no outlined item table.
FREE_STYLES = [
    Style("sans-free", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "free"),
    Style("serif-free", "DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "free"),
    Style("stix-free", "STIXGeneral.ttf", "STIXGeneralBol.ttf", "free"),
    Style("oblique-free", "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf", "free"),
    Style("italic-free", "DejaVuSerif-Italic.ttf", "DejaVuSerif-Bold.ttf", "free"),
    Style("stixitalic-free", "STIXGeneralItalic.ttf", "STIXGeneralBol.ttf", "free"),
]
# A layout and a font family that never appear in training.
HELDOUT_STYLES = [
    Style("mono-boxed", "DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf", "boxed"),
]


class Canvas:
    def __init__(self, style: Style, rng: random.Random, width: int = 1240, height: int = 1754) -> None:
        self.img = Image.new("RGB", (width, height), (255, 255, 255))
        self.d = ImageDraw.Draw(self.img)
        self.style, self.rng = style, rng
        self.w, self.h = width, height
        self.margin = rng.randint(70, 110)
        self.size = rng.randint(22, 26)
        self._fonts: dict[tuple[bool, int], ImageFont.FreeTypeFont] = {}
        self.ink = (rng.randint(10, 40),) * 3

    def font(self, bold: bool = False, delta: int = 0) -> ImageFont.FreeTypeFont:
        key = (bold, self.size + delta)
        if key not in self._fonts:
            name = self.style.bold if bold else self.style.regular
            self._fonts[key] = ImageFont.truetype(os.path.join(_font_dir(), name), key[1])
        return self._fonts[key]

    def text(self, x: float, y: float, s: str, bold: bool = False, delta: int = 0, anchor: str = "la") -> int:
        f = self.font(bold, delta)
        self.d.text((x, y), s, font=f, fill=self.ink, anchor=anchor)
        box = self.d.textbbox((x, y), s, font=f, anchor=anchor)
        return box[3] - box[1]

    def width(self, s: str, bold: bool = False, delta: int = 0) -> float:
        return self.d.textlength(s, font=self.font(bold, delta))

    def wrap(self, s: str, max_w: float, bold: bool = False, delta: int = 0) -> list[str]:
        words, lines, cur = s.split(), [], ""
        for w in words:
            nxt = f"{cur} {w}".strip()
            if self.width(nxt, bold, delta) <= max_w or not cur:
                cur = nxt
            else:
                lines.append(cur)
                cur = w
        return lines + ([cur] if cur else [])

    def line(self, y: float, x0: float | None = None, x1: float | None = None, width: int = 2) -> None:
        self.d.line([(x0 or self.margin, y), (x1 or self.w - self.margin, y)], fill=(90, 90, 90), width=width)


def _vendor_block(c: Canvas, inv: dict[str, Any], x: float, y: float, align: str = "la") -> float:
    gap = int(c.size * 1.45)
    max_w = c.w / 2 - c.margin - 40
    for ln in c.wrap(inv["vendor"], max_w, bold=True, delta=14):
        y += c.text(x, y, ln, bold=True, delta=14, anchor=align) + 10
    y += 4
    for ln in c.wrap(inv["vendor_address"], max_w):
        c.text(x, y, ln, anchor=align)
        y += gap
    for lab, key in [("Tél", "vendor_phone"), ("RC", "vendor_rc"), ("NIF", "vendor_nif"),
                     ("NIS", "vendor_nis"), ("AI", "vendor_ai")]:
        c.text(x, y, f"{lab} : {inv[key]}", delta=-4, anchor=align)
        y += int(gap * 0.85)
    return y


def _client_block(c: Canvas, inv: dict[str, Any], x: float, y: float) -> float:
    gap = int(c.size * 1.45)
    c.text(x, y, "Client :", bold=True)
    y += gap
    c.text(x, y, inv["client"])
    y += gap
    for ln in c.wrap(inv["client_address"], c.w / 2 - c.margin):
        c.text(x, y, ln, delta=-4)
        y += int(gap * 0.85)
    return y


def _meta_block(c: Canvas, inv: dict[str, Any], x: float, y: float) -> float:
    gap = int(c.size * 1.5)
    title = c.rng.choice(["FACTURE", "Facture", "FACTURE N°"])
    if title == "FACTURE N°":
        c.text(x, y, f"FACTURE N° {inv['invoice_number']}", bold=True, delta=6)
    else:
        c.text(x, y, title, bold=True, delta=14)
        y += int(gap * 1.3)
        c.text(x, y, f"N° : {inv['invoice_number']}", bold=True)
    y += int(gap * 1.2)
    c.text(x, y, f"{c.rng.choice(['Date', 'Date de facturation', 'Le'])} : {inv['date']}")
    y += gap
    c.text(x, y, f"Mode de paiement : {inv['payment']}", delta=-4)
    return y + gap


def _items_table(c: Canvas, inv: dict[str, Any], y: float, boxed: bool = False) -> float:
    x0, x1 = c.margin, c.w - c.margin
    cols = [("Désignation", 0.0), ("Qté", 0.52), ("P.U. HT", 0.63), ("Montant HT", 0.82)]
    span = x1 - x0
    row_h = int(c.size * 1.9)
    if boxed:
        c.d.rectangle([x0, y, x1, y + row_h], fill=(225, 225, 225))
    else:
        c.line(y, width=3)
    for name, frac in cols:
        c.text(x0 + 10 + frac * span, y + row_h * 0.25, name, bold=True, delta=-2)
    y += row_h
    if not boxed:
        c.line(y)
    for it in inv["items"]:
        names = c.wrap(it["name"], span * 0.5 - 20, delta=-2)
        for k, ln in enumerate(names):
            c.text(x0 + 10, y + row_h * 0.25 + k * c.size, ln, delta=-2)
        c.text(x0 + 10 + 0.52 * span, y + row_h * 0.25, it["qty"], delta=-2)
        c.text(x1 - 10 - 0.18 * span - 10, y + row_h * 0.25, it["unit_price"], delta=-2, anchor="ra")
        c.text(x1 - 10, y + row_h * 0.25, it["amount"], delta=-2, anchor="ra")
        y += row_h + (len(names) - 1) * c.size
        if boxed:
            c.line(y, width=1)
    c.line(y, width=3 if not boxed else 1)
    if boxed:
        c.d.rectangle([x0, y - row_h * (len(inv["items"]) + 1) - 20, x1, y], outline=(60, 60, 60), width=2)
    return y + 30


def _totals(c: Canvas, inv: dict[str, Any], y: float, boxed: bool = False) -> float:
    rows = [("Total HT", inv["total_ht"]), (f"TVA {inv['tva_rate']}", inv["tva"])]
    if inv["timbre"]:
        rows.append(("Droit de timbre", inv["timbre"]))
    rows.append(("Total TTC" if c.rng.random() < 0.8 else "Net à payer TTC", inv["total_ttc"]))
    x1 = c.w - c.margin
    x_lab = x1 - c.rng.randint(420, 520)
    gap = int(c.size * 1.6)
    if boxed:
        c.d.rectangle([x_lab - 20, y - 10, x1, y + gap * len(rows)], outline=(40, 40, 40), width=2)
    for k, (lab, val) in enumerate(rows):
        last = k == len(rows) - 1
        c.text(x_lab, y, lab + " :", bold=last)
        c.text(x1 - 10, y, f"{val} DA" if c.rng.random() < 0.5 or last else val, bold=last, anchor="ra")
        y += gap
    return y


def _footer(c: Canvas, inv: dict[str, Any], y: float) -> None:
    words = c.rng.choice([
        "Arrêtée la présente facture à la somme indiquée ci-dessus.",
        "Merci pour votre confiance.",
        "Marchandise vendue ni reprise ni échangée.",
    ])
    c.text(c.margin, max(y + 30, c.h - c.margin - 160), words, delta=-4)
    c.text(c.w - c.margin, c.h - c.margin - 80, "Cachet et signature", delta=-4, anchor="ra")


def render_page(inv: dict[str, Any], style: Style, rng: random.Random) -> Image.Image:
    c = Canvas(style, rng)
    m = c.margin
    if style.layout == "classic":
        y = _vendor_block(c, inv, m, m)
        _meta_block(c, inv, c.w / 2 + 60, m + 10)
        y = _client_block(c, inv, c.w / 2 + 60, max(y, m + 230) + 20)
        y = _items_table(c, inv, y + 40)
        y = _totals(c, inv, y)
    elif style.layout == "banner":
        c.d.rectangle([0, 0, c.w, m + 30], fill=(235, 235, 235))
        c.text(c.w / 2, m / 2, inv["vendor"], bold=True, delta=14, anchor="ma")
        c.line(m + 30, 0, c.w, 3)
        y = m + 60
        info = [inv["vendor_address"], f"RC : {inv['vendor_rc']}   NIF : {inv['vendor_nif']}",
                f"NIS : {inv['vendor_nis']}   AI : {inv['vendor_ai']}   Tél : {inv['vendor_phone']}"]
        for ln in info:
            c.text(c.w / 2, y, ln, delta=-4, anchor="ma")
            y += int(c.size * 1.3)
        y += 30
        y2 = _meta_block(c, inv, m, y)
        y = max(y2, _client_block(c, inv, c.w / 2 + 60, y))
        y = _items_table(c, inv, y + 30)
        y = _totals(c, inv, y)
    elif style.layout == "compact":
        c.text(m, m, "FACTURE", bold=True, delta=14)
        c.text(c.w - m, m, inv["invoice_number"], bold=True, anchor="ra")
        c.text(c.w - m, m + 40, inv["date"], anchor="ra")
        y = _vendor_block(c, inv, m, m + 80)
        y = _client_block(c, inv, m, y + 20)
        c.text(m, y + 10, f"Paiement : {inv['payment']}", delta=-4)
        y = _items_table(c, inv, y + 60)
        y = _totals(c, inv, y)
    elif style.layout == "free":
        render_free(inv, c)
        return c.img
    else:  # boxed: held-out layout, vendor on the right, everything boxed
        y = _vendor_block(c, inv, c.w - m, m, align="ra")
        c.d.rectangle([m, m, c.w / 2 - 20, m + 220], outline=(40, 40, 40), width=2)
        c.text(m + 20, m + 20, "FACTURE", bold=True, delta=6)
        c.text(m + 20, m + 80, f"Numéro : {inv['invoice_number']}")
        c.text(m + 20, m + 120, f"Date : {inv['date']}")
        c.text(m + 20, m + 160, f"Règlement : {inv['payment']}", delta=-4)
        y = _client_block(c, inv, m, max(y, m + 240) + 30)
        y = _items_table(c, inv, y + 40, boxed=True)
        y = _totals(c, inv, y + 10, boxed=True)
    _footer(c, inv, y)
    return c.img


FREE_LABELS = {
    "item": ["Désignation", "Article", "Produit", "Description"],
    "qty": ["Qté", "Quantité", "Qte"],
    "unit": ["P.U. HT", "Prix unitaire", "PU HT", "Prix U."],
    "amount": ["Montant HT", "Total HT", "Montant"],
    "ht": ["Total HT", "Montant HT", "Total hors taxes", "Sous-total HT"],
    "tva": ["TVA {rate}", "T.V.A. {rate}", "TVA ({rate})"],
    "timbre": ["Droit de timbre", "Timbre fiscal", "Timbre"],
    "ttc": ["Total TTC", "Net à payer", "Montant TTC", "Net à payer TTC"],
    "number": ["N° : {n}", "Facture n° {n}", "Réf. : {n}", "N° facture : {n}"],
    "date": ["Date : {d}", "Le {d}", "Date de facture : {d}", "Émise le {d}"],
    "client": ["Client :", "Doit :", "Facturé à :", "Destinataire :"],
}


def _free_label(c: Canvas, key: str, **kw: str) -> str:
    return c.rng.choice(FREE_LABELS[key]).format(**kw)


def render_free(inv: dict[str, Any], c: Canvas) -> None:
    """A layout drawn at random: header position, block order, table style and wording vary."""
    rng, m, gap = c.rng, c.margin, int(c.size * 1.45)
    y = m
    centered = rng.random() < 0.35
    if centered:
        for ln in c.wrap(inv["vendor"], c.w - 2 * m, bold=True, delta=14):
            y += c.text(c.w / 2, y, ln, bold=True, delta=14, anchor="ma") + 10
        for ln in [
            inv["vendor_address"],
            f"Tél : {inv['vendor_phone']}",
            f"RC : {inv['vendor_rc']}   NIF : {inv['vendor_nif']}",
            f"NIS : {inv['vendor_nis']}   AI : {inv['vendor_ai']}",
        ]:
            c.text(c.w / 2, y, ln, delta=-4, anchor="ma")
            y += int(gap * 0.85)
        if rng.random() < 0.5:
            c.line(y + 6, width=2)
        y += 30
    else:
        y = _vendor_block(c, inv, m, y) + 20
    meta_x = m if centered or rng.random() < 0.5 else c.w / 2 + rng.randint(20, 80)
    meta_y = y if meta_x == m else m + rng.randint(0, 40)
    title = rng.choice(["FACTURE", "Facture", "FACTURE COMMERCIALE", "Facture de vente"])
    c.text(meta_x, meta_y, title, bold=True, delta=rng.choice([6, 10, 14]))
    my = meta_y + int(gap * 1.5)
    c.text(meta_x, my, _free_label(c, "number", n=inv["invoice_number"]), bold=rng.random() < 0.5)
    my += gap
    c.text(meta_x, my, _free_label(c, "date", d=inv["date"]))
    my += gap
    if rng.random() < 0.7:
        c.text(meta_x, my, f"Paiement : {inv['payment']}", delta=-4)
        my += gap
    y = max(y, my) + 20
    cx = m if rng.random() < 0.6 else c.w / 2 + rng.randint(0, 60)
    c.text(cx, y, _free_label(c, "client"), bold=True)
    c.text(cx, y + gap, inv["client"])
    yy = y + 2 * gap
    for ln in c.wrap(inv["client_address"], c.w / 2 - m, delta=-4):
        c.text(cx, yy, ln, delta=-4)
        yy += int(gap * 0.85)
    y = yy + rng.randint(30, 60)

    # items: ruled, striped or plain (never the outlined table of the held-out layout)
    style = rng.choice(["ruled", "striped", "plain"])
    x0, x1 = m, c.w - m
    span = x1 - x0
    row_h = int(c.size * rng.uniform(1.6, 2.1))
    q_at = rng.uniform(0.48, 0.56)
    heads = [(_free_label(c, "item"), 0.0, "la"), (_free_label(c, "qty"), q_at, "la"),
             (_free_label(c, "unit"), 0.80 - 0.0, "ra"), (_free_label(c, "amount"), 1.0, "ra")]
    if style == "striped":
        c.d.rectangle([x0, y, x1, y + row_h], fill=(215, 215, 215))
    else:
        c.line(y, width=rng.choice([1, 2, 3]))
    for name, frac, anchor in heads:
        x = x0 + 10 + frac * span if anchor == "la" else x0 + frac * span - 10
        c.text(x, y + row_h * 0.25, name, bold=True, delta=-2, anchor=anchor)
    y += row_h
    if style != "striped":
        c.line(y, width=1)
    for k, it in enumerate(inv["items"]):
        names = c.wrap(it["name"], span * (q_at - 0.04), delta=-2)
        h = row_h + (len(names) - 1) * c.size
        if style == "striped" and k % 2 == 1:
            c.d.rectangle([x0, y, x1, y + h], fill=(240, 240, 240))
        for j, ln in enumerate(names):
            c.text(x0 + 10, y + row_h * 0.25 + j * c.size, ln, delta=-2)
        c.text(x0 + 10 + q_at * span, y + row_h * 0.25, it["qty"], delta=-2)
        c.text(x0 + 0.80 * span - 10, y + row_h * 0.25, it["unit_price"], delta=-2, anchor="ra")
        c.text(x1 - 10, y + row_h * 0.25, it["amount"], delta=-2, anchor="ra")
        y += h
        if style == "ruled":
            c.line(y, width=1)
    if style != "ruled":
        c.line(y, width=2)
    y += 30

    rows = [(_free_label(c, "ht"), inv["total_ht"]), (_free_label(c, "tva", rate=inv["tva_rate"]), inv["tva"])]
    if inv["timbre"]:
        rows.append((_free_label(c, "timbre"), inv["timbre"]))
    rows.append((_free_label(c, "ttc"), inv["total_ttc"]))
    left_totals = rng.random() < 0.25
    x_lab = m if left_totals else x1 - rng.randint(400, 540)
    x_val = x_lab + rng.randint(330, 400) if left_totals else x1 - 10
    sep = rng.choice([" :", "", " :"])
    for k, (lab, val) in enumerate(rows):
        last = k == len(rows) - 1
        if last and rng.random() < 0.5:
            c.line(y - 6, x_lab, x_val + 10, 2)
        c.text(x_lab, y, lab + sep, bold=last)
        c.text(x_val, y, f"{val} DA" if last or rng.random() < 0.5 else val, bold=last, anchor="ra")
        y += int(c.size * 1.6)
    _footer(c, inv, y)


def photograph(img: Image.Image, rng: random.Random) -> Image.Image:
    """Make a clean render look like a phone photo or a scan: tilt, blur, light, JPEG."""
    bg = tuple(rng.randint(120, 200) for _ in range(3))
    angle = rng.uniform(-2.5, 2.5)
    img = img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=bg)
    pad = rng.randint(0, 60)
    if pad:
        canvas = Image.new("RGB", (img.width + 2 * pad, img.height + 2 * pad), bg)
        canvas.paste(img, (pad + rng.randint(-pad // 2, pad // 2), pad + rng.randint(-pad // 2, pad // 2)))
        img = canvas
    img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.8, 1.1))
    img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.8, 1.15))
    if rng.random() < 0.6:
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.2, 1.1)))
    scale = rng.uniform(0.6, 1.0)
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=rng.randint(55, 90))
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def generate(seed: int, styles: list[Style]) -> tuple[Image.Image, dict[str, Any], dict[str, Any]]:
    """One sample: (image, label, full invoice data including fields not in the label)."""
    rng = random.Random(seed)
    inv = make_invoice(rng)
    style = rng.choice(styles)
    img = photograph(render_page(inv, style, rng), rng)
    if style.layout == "free":  # stronger capture variation, training only (after the shared steps)
        img = phone_capture(img, rng)
    return img, label(inv), inv | {"style": style.name}


def phone_capture(img: Image.Image, rng: random.Random) -> Image.Image:
    """A slanted phone shot: perspective, uneven light, a soft shadow band, random crop margin."""
    w, h = img.size
    d = [rng.uniform(-0.04, 0.04) * v for v in (w, h, w, h, w, h, w, h)]
    quad = (d[0], d[1], d[2], h + d[3], w + d[4], h + d[5], w + d[6], d[7])
    img = img.transform((w, h), Image.Transform.QUAD, quad, Image.Resampling.BICUBIC, fillcolor=(150, 150, 150))
    if rng.random() < 0.5:
        shade = Image.new("L", (w, h), 255)
        band = ImageDraw.Draw(shade)
        top = rng.randint(0, h)
        band.rectangle([0, top, w, top + rng.randint(h // 8, h // 3)], fill=rng.randint(170, 220))
        shade = shade.filter(ImageFilter.GaussianBlur(40))
        img = Image.composite(img, Image.new("RGB", (w, h), (0, 0, 0)), shade)
    return ImageEnhance.Brightness(img).enhance(rng.uniform(0.85, 1.1))


# Seeds never overlap between splits.
SPLITS = {
    "train": (0, TRAIN_STYLES + FREE_STYLES),  # v3: + the free layout (v2 trained on TRAIN_STYLES only)
    "validation": (1_000_000, TRAIN_STYLES),
    "test_seen": (2_000_000, TRAIN_STYLES),
    "test_heldout": (3_000_000, HELDOUT_STYLES),
}


def split_seeds(split: str, n: int) -> list[int]:
    base, _ = SPLITS[split]
    return [base + i for i in range(n)]
