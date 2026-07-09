from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    label_uz: str
    schema: str = "credit"


CATEGORIES: list[Category] = [
    Category(key="avtokredit", label_uz="Avtokredit (birlamchi bozor)"),
    Category(key="avtokredit_ikkilamchi", label_uz="Avtokredit (ikkilamchi bozor)"),
    Category(
        key="avtokredit_brend_birlamchi",
        label_uz="Brendli avtokredit — birlamchi (GM, BYD, KIA, Hyundai, Renault, LADA, Volkswagen, Skoda, Chery)",
    ),
    Category(
        key="avtokredit_brend_ikkilamchi",
        label_uz="Brendli avtokredit — ikkilamchi (GM, BYD, KIA, Hyundai, Renault, LADA, Volkswagen, Skoda, Chery)",
    ),
    Category(key="avtokredit_elektro", label_uz="Elektromobil avtokrediti"),
    Category(key="mikroqarz", label_uz="Mikroqarz (oflayn)"),
    Category(key="mikroqarz_onlayn", label_uz="Mikroqarz (onlayn)"),
    Category(key="kredit_karta", label_uz="Kredit kartalari"),
    Category(key="istemol_krediti", label_uz="Iste'mol krediti"),
    Category(key="ipoteka_tijorat", label_uz="Ipoteka krediti (tijorat)"),
    Category(
        key="ipoteka_davlat",
        label_uz="Ipoteka krediti (Iqtisodiyot va moliya vazirligi mablag'lari hisobidan)",
    ),
]


def category_keys() -> list[str]:
    return [c.key for c in CATEGORIES]
