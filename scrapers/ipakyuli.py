from scrapers.base import TextSectionScraper


class IpakYuliBankScraper(TextSectionScraper):
    """Ipak Yo'li Bank (ipakyulibank.uz) — real, verified data for
    avtokredit va mikroqarz. kredit_karta ("Imkoniyatlar" kartasi) foiz
    stavkasiz, faqat limit+foizsiz davr modeli bilan ishlaydi (aniq foiz
    ko'rsatilmagan); istemol_krediti sahifasida esa aniq summa/stavka
    umuman yo'q ("dastur shartlariga bog'liq" deyilgan, xolos) — ikkalasi
    ham _build_product tomonidan tabiiy ravishda o'tkazib yuboriladi.

    avtokredit sahifasida boshqa (aloqasiz) mahsulot uchun "garovsiz" so'zi
    borligi sababli to'liq sahifa bo'yicha garov tekshiruvi yolg'on-manfiy
    beradi (real FAQ'da "Garov sifatida ... avtomobil qo'yish mumkin"
    aniq yozilgan bo'lsa ham) — FORCE_COLLATERAL bilan tuzatilgan."""

    bank_name = "Ipak Yo'li Bank"
    url = "https://ipakyulibank.uz/physical/kreditlar"
    CATEGORY_URLS = {
        "avtokredit": "https://ipakyulibank.uz/physical/kreditlar/avtokreditlar/birlamchi-bozor-avtokreditlari",
        "mikroqarz": "https://ipakyulibank.uz/physical/kreditlar/mikroqarzlar/mikroqarz",
        "kredit_karta": "https://ipakyulibank.uz/physical/kartalar/imkoniyatlar-kredit-kartasi",
        "istemol_krediti": "https://ipakyulibank.uz/physical/kreditlar/istemol-krediti",
    }
    CATEGORY_HEADINGS = {
        "avtokredit": ("Birlamchi bozor avtokrediti", "25%"),
        "mikroqarz": ("Foiz stavkasi", "26,9%"),
        "kredit_karta": ("Limit", "Foizsiz davr"),
        "istemol_krediti": ("Kredit muddati", "Kredit qanday qaytariladi"),
    }
    FORCE_COLLATERAL = {
        "avtokredit": True,
    }
