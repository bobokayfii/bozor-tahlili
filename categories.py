from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    label_uz: str
    schema: str = "credit"


CATEGORIES: list[Category] = [
    Category(key="avtokredit", label_uz="Avtokredit (birlamchi bozor)", schema="credit_down_payment"),
    Category(
        key="avtokredit_ikkilamchi",
        label_uz="Avtokredit (ikkilamchi bozor)",
        schema="credit_down_payment",
    ),
    Category(
        key="avtokredit_brend_birlamchi",
        label_uz="Brendli avtokredit — birlamchi (GM, BYD, KIA, Hyundai, Renault, LADA, Volkswagen, Skoda, Chery)",
        schema="credit_down_payment",
    ),
    Category(
        key="avtokredit_brend_ikkilamchi",
        label_uz="Brendli avtokredit — ikkilamchi (GM, BYD, KIA, Hyundai, Renault, LADA, Volkswagen, Skoda, Chery)",
        schema="credit_down_payment",
    ),
    Category(key="avtokredit_elektro", label_uz="Elektromobil avtokrediti", schema="credit_down_payment"),
    Category(key="mikroqarz", label_uz="Mikroqarz (oflayn)", schema="credit_special_terms"),
    Category(key="mikroqarz_onlayn", label_uz="Mikroqarz (onlayn)", schema="credit_special_terms"),
    Category(key="kredit_karta", label_uz="Kredit kartalari", schema="credit_special_terms"),
    Category(key="istemol_krediti", label_uz="Iste'mol krediti", schema="credit_special_terms"),
    Category(key="ipoteka_tijorat", label_uz="Ipoteka krediti (tijorat)", schema="credit_down_payment"),
    Category(
        key="ipoteka_davlat",
        label_uz="Ipoteka krediti (Iqtisodiyot va moliya vazirligi mablag'lari hisobidan)",
        schema="credit_down_payment",
    ),
]


def category_keys() -> list[str]:
    return [c.key for c in CATEGORIES]
