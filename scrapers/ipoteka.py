from scrapers.base import TextSectionScraper


class IpotekaBankScraper(TextSectionScraper):
    """Ipoteka Bank (ipotekabank.uz) retail kredit kategoriyalari SQB/NBU kabi
    alohida sahifalarda joylashgan (real saytda tekshirilgan — Task 7
    tadqiqotiga qarang). CATEGORY_HEADINGS kerak emas: har bir fetch qilingan
    sahifa matni bitta kategoriyaga bag'ishlangan deb qabul qilinadi.

    MUHIM: Ipoteka Bank saytida "avtokredit" va "mikroqarz" uchun aniq,
    tasdiqlangan mahsulot sahifalari mavjud (WebFetch orqali jonli tekshirilgan
    va real raqamlar bilan mos keldi). Boshqa ikkita kategoriya uchun esa aniq
    moslik topilmadi:
      - kredit_karta -> Ipoteka Bankda alohida "kredit karta" (credit card)
        krediti yo'q, faqat debet kartalari (UZCARD, VISA Classic, HUMO) bor.
        Shu sababli Overdraft sahifasi eng yaqin funksional analog sifatida
        ishlatilgan (aylanma shaxsiy kredit liniyasi, ish haqi loyihasi
        ishtirokchilariga). BU TAXMIN (best-guess mapping), tasdiqlanmagan —
        NBU'ning kredit_karta->Overdraft yechimidagi bir xil mantiq. Fixture'dagi raqamlar taxminiy va real emas.
      - istemol_krediti -> "consumer" manzili qidiruv natijalarida "Iste'mol
        krediti" sarlavhasi bilan mavjud va URL sifatida real, lekin
        WebFetch orqali sahifa matnini olishga urinishlarda har safar boshqa
        kategoriyalar (ipoteka, avtokredit, mikrokredit) bilan aralashgan
        umumiy "kreditlash" xob kontenti qaytdi (ehtimol /uz/ lokal prefiksi
        301 redirect zanjirida yo'qolib, standart tilga tushib qolgani
        sababli). Demak URL manzili tasdiqlangan, lekin sahifa matni/raqamlari
        TASDIQLANMAGAN — fixture'dagi raqamlar taxminiy va real emas.
    Ushbu ikkala holat ham topshiriq hisobotida aniq bayon qilingan."""

    bank_name = "Ipoteka Bank"
    url = "https://ipotekabank.uz/uz/private/crediting/"
    CATEGORY_URLS = {
        # Tasdiqlangan (real, WebFetch orqali jonli tekshirilgan):
        "avtokredit": "https://ipotekabank.uz/uz/private/crediting/auto/",
        "mikroqarz": "https://www.ipotekabank.uz/private/crediting/micro_new/",
        # Taxminiy (best-guess) — quyidagi sinf docstringiga qarang:
        "kredit_karta": "https://ipotekabank.uz/uz/private/crediting/overdraft/",
        "istemol_krediti": "https://ipotekabank.uz/uz/private/crediting/consumer/",
    }
