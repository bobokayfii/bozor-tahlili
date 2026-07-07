from scrapers.base import TextSectionScraper


class SQBScraper(TextSectionScraper):
    bank_name = "SQB"
    url = "https://sqb.uz/uz/individuals/credits/"
    CATEGORY_HEADINGS = {
        "avtokredit": ("Avtokredit", "Mikroqarz"),
        "mikroqarz": ("Mikroqarz", "Kredit karta"),
        "kredit_karta": ("Kredit karta", "Iste'mol krediti"),
        "istemol_krediti": ("Iste'mol krediti", None),
    }
