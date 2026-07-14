from scrapers.base import TextSectionScraper


class MikrokreditBankScraper(TextSectionScraper):
    """Mikrokreditbank (mkbank.uz) retail kredit kategoriyalari SQB kabi
    alohida sahifalarda joylashgan. Har bir mahsulot sahifasi standart shablon
    bo'yicha "Kredit muddati / Valyuta / Stavka foizi / Kredit miqdori / ..."
    ketma-ketligida bir xil tuzilgan — shu bois barcha 4 kategoriya uchun bir
    xil CATEGORY_HEADINGS ("Kredit muddati" -> "Qarz oluvchi") ishlatiladi.

    Saytda mustaqil "kredit karta" mahsuloti yo'q (faqat debet kartalari bor),
    shuning uchun IpotekaBank/NBU'dagi kabi "Qulay Overdraft" mahsuloti eng
    yaqin funksional analog sifatida ishlatilgan — bu TAXMIN (best-guess
    mapping), boshqa kategoriyalardan farqli ravishda.

    Har bir sahifada "Kredit muddati" satri ikki xil holatda uchraydi: sahifa
    boshidagi kichik xulosa kartochkasida kichik harf bilan ("kredit
    muddati"), pastroqdagi to'liq jadvalda esa katta harf bilan ("Kredit
    muddati"). extract_section case-sensitive qidiruv olib boradi, shuning
    uchun katta harfli variant birinchi haqiqiy jadvalni to'g'ri topadi —
    kichik harfli xulosa kartochkasi chalg'itmaydi."""

    bank_name = "Mikrokreditbank"
    url = "https://mkbank.uz/uz/private/crediting/"
    CATEGORY_URLS = {
        "avtokredit": "https://mkbank.uz/uz/private/crediting/car-loan/",
        "mikroqarz": "https://mkbank.uz/uz/private/crediting/microloan/",
        # Taxminiy (best-guess) — sinf docstringiga qarang.
        "kredit_karta": "https://mkbank.uz/uz/private/crediting/qulay-overdraft/",
        "istemol_krediti": "https://mkbank.uz/uz/private/crediting/consumer-loan/",
    }
    CATEGORY_HEADINGS = {
        "avtokredit": ("Kredit muddati", "Qarz oluvchi"),
        "mikroqarz": ("Kredit muddati", "Qarz oluvchi"),
        "kredit_karta": ("Kredit muddati", "Qarz oluvchi"),
        "istemol_krediti": ("Kredit muddati", "Qarz oluvchi"),
    }
