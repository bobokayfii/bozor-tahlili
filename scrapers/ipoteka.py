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
      - avtokredit -> eski "/uz/private/crediting/auto/" manzili sayt qayta
        qurilgandan keyin "/ru/crediting/autocredit/" (rus tilidagi) sahifaga
        301 redirect qiladi — natijada o'zbekcha regex naqshlari ("oygacha",
        "so'm") mos kelmay, mahsulot butunlay tushib qolardi. To'g'ri, hozirgi
        manzil "https://www.ipotekabank.uz/crediting/autocredit/" bo'lib,
        o'zbekcha kontentni to'g'ridan-to'g'ri (redirectsiz) qaytaradi. Bu
        sahifada bitta umumiy stavka o'rniga har bir avtomobil brendi/dilер
        uchun alohida shartnoma kartochkasi bor (~12 xil stavka, 0%–29.99%
        oralig'ida) — bu KONTAMINATSIYA emas, balki turli brendlar uchun
        haqiqiy turlicha shartlar, shuning uchun rate_min/rate_max butun
        sahifa bo'ylab hisoblanadi. Muddat esa "oy" emas, "5 yilgacha" (yil)
        shaklida berilgan — scrapers/utils.py'dagi extract_term_months endi
        "N yilgacha" naqshini ham oyga aylantirib tushunadi. Garov (kafolat)
        talabi haqida sahifada aniq "garov" so'zi yo'q — sahifada boshqa bir
        mahsulot uchun "garovsiz mikrokredit" iborasi bor bo'lib, bu butun
        sahifa bo'yicha yolg'on-manfiy (false negative) beradi. Avtokredit esa
        ta'rifiga ko'ra doim sotib olinayotgan avtomobilning o'zi bilan
        ta'minlanadi (umumbank amaliyoti, alohida yozilmasa ham) — shu sababli
        FORCE_COLLATERAL orqali aniq True belgilangan.
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
        "avtokredit": "https://www.ipotekabank.uz/crediting/autocredit/",
        "mikroqarz": "https://www.ipotekabank.uz/private/crediting/micro_new/",
        # Taxminiy (best-guess) — quyidagi sinf docstringiga qarang:
        "kredit_karta": "https://ipotekabank.uz/uz/private/crediting/overdraft/",
        "istemol_krediti": "https://ipotekabank.uz/uz/private/crediting/consumer/",
    }
    FORCE_COLLATERAL = {
        "avtokredit": True,
    }
