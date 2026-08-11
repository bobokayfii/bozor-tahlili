from scrapers.base import TextSectionScraper


class TrastBankScraper(TextSectionScraper):
    """TrastBank (trustbank.uz).

    "Mikroqarzlar" sahifasida (https://trustbank.uz/uz/private/crediting/
    microloans/) UCHTA mijoz-toifasi ketma-ket keladi, har biri o'z stavka/
    muddat/summa jadvaliga ega:
      1. "Doimiy daromadga ega bo'lgan mijozlar uchun" — 100 mln so'mgacha,
         12/36/60 oygacha, ikkita stavka jadvali: kafillik/sug'urta asosida
         28%/29%/30%, so'ng avtotransport/ko'chmas mulk garovi asosida
         29%/30%/31,9%.
      2. "O'zini-o'zi band qilgan shaxslarga" — 50,0 mln so'mgacha, 12/24/36
         oy (bu yerda "oygacha"siz, yalang' "N oy" shaklida — standart
         extract_term_months bu qiymatlarni faqat "oygacha" ibora hech
         qayerda topilmasa oladi, shu sabab quyida tushuntirilganidek bu
         qiymatlar birlashtirilgan bo'lakda amalda e'tiborga olinmaydi).
      3. "...ish haqi loyihasi... Ta'lim va sog'liqni saqlash tizimlarida
         ishlovchi xodimlar uchun" — 100 mln so'mgacha, 12/36/60 oygacha,
         ikkita stavka jadvali: kafillik/sug'urta asosida 24%/25%/26%, so'ng
         garov asosida 25%/26,5%/27,9%.

    Uchala toifa ALOHIDA-ALOHIDA emas, BITTA umumiy bo'lak sifatida olinadi
    ("Doimiy daromadga ega bo" dan — apostrof ASCII-xavfsiz kesilgan,
    haqiqiy belgi U+2018 '‘' — "Mikroqarz rasmiylashtirishda" gacha, bu
    ikkinchisi sahifada FAQAT bir marta uchraydi va uchala toifadan keyin,
    hujjatlar ro'yxati boshida keladi), so'ng shu bo'lak ustida standart
    extract_percentages/extract_term_months/extract_amount_som ishlatiladi
    (CATEGORY_HEADINGS orqali, umumiy TextSectionScraper.run()ning standart
    yo'li bilan — bu kategoriya uchun maxsus run()/_build_* metodi shart
    emas, chunki barcha maydonlar bitta oddiy bo'lak ustida standart
    funksiyalar bilan to'g'ri chiqadi):
      - rates: {28,29,30,31.9,24,25,26,26.5,27.9} -> min=24.0, max=31.9
        (barcha besh stavka jadvalidan, uchala toifaning haqiqiysi).
      - terms: standart extract_term_months avval "N oydan M oygacha" range
        naqshini qidiradi (topilmaydi), so'ng "N oygacha" ibora to'plamiga
        tushadi — bu FAQAT 1- va 3-toifaning {12,36,60} qiymatlarini oladi
        (ikkalasida ham bir xil, "oygacha" bilan yozilgan). 2-toifaning
        yalang' "12 oy"/"24 oy"/"36 oy" (oygachasiz) qiymatlari bu yo'lda
        chiqarib tashlanadi, chunki "N oygacha" to'plami bo'sh emasligi
        sababli funksiya yalang' "N oy" fallback shoxobchasiga umuman
        o'tmaydi — lekin bu natijaga ta'sir qilmaydi: {12,36,60} allaqachon
        min=12/max=60 ni beradi, 2-toifaning eng kattasi (36) bu oraliqdan
        oshib ketmaydi.
      - amount: "100 mln so'mgacha" ikki marta (1- va 3-toifa) va "50,0 mln
        so'mgacha" (2-toifa, VERGUL bilan yozilgan — standart mln regex
        vergul-o'nlik qismini tanimaydi, shu sabab bu son mos kelmaydi va
        e'tiborga olinmaydi, lekin baribir muhim emas, chunki u 100 mlndan
        kichik) -> max = 100_000_000.

    Bu tasodifiy emas — barcha uch toifaning haqiqiy, jonli saytda e'lon
    qilingan stavka/muddat qiymatlari, faqat birlashtirilgan holda.

    Imtiyozli davr: sahifa muqaddimasida (birinchi jadvaldan OLDIN) aniq
    "Mikroqarzning imtiyozli davri: mavjud emas" deb yozilgan — bu real
    "yo'q" signali (0 oy), "noma'lum" emas. GRACE_PERIOD_HEADINGS orqali
    "Mikroqarzning imtiyozli davri" dan "Doimiy daromadga ega bo" gacha
    (bu ikkinchi sarlavha darhol undan keyin kelmaydi, lekin oralig'idagi
    bo'sh matnda "imtiyozli" so'zi boshqa hech qayerda uchramaydi, shu sabab
    bu tor chegara xavfsiz) chegaralanadi.

    down_payment_pct va payment_method: sahifaning bu bo'limida umuman
    tilga olinmagan (jonli sahifada "Boshlang'ich"/"Jadval turi"/
    "annuitet"/"differen" so'zlarining birortasi ham uchramasligi
    tasdiqlangan) — DOWN_PAYMENT_HEADINGS/PAYMENT_METHOD_HEADINGS
    belgilanmagani uchun ikkalasi ham tabiiy ravishda None qoladi.

    requires_collateral: FORCE_COLLATERAL orqali qat'iy True belgilangan —
    barcha uch toifa ham kafillik/sug'urta/garov turlaridan birortasini
    talab qiladi, hech qanday "garovsiz" variant yo'q. DIQQAT: umumiy
    has_collateral_requirement bu sahifada ishonchsiz bo'lardi — sahifa
    muqaddimasidagi "imtiyozli davri: mavjud emas" jumlasi tufayli butun
    sahifa matnida "mavjud emas" so'z birikmasi bor, bu esa
    has_collateral_requirement'ning yolg'on-manfiy shoxobchasini
    ("mavjud emas" bo'lsa False qaytarish) ishga tushirib, haqiqatda
    garov/kafillik/sug'urta talab qilinishiga qaramay False qaytarardi
    (tekshirilgan) — shu sabab bu yerda aniq force qilish ayniqsa muhim.

    ipoteka_tijorat va ipoteka_davlat — TrastBank uchun boshqa, alohida
    topshiriqlar doirasida keyinroq shu faylga qo'shiladi; bu yerda ular
    uchun joy egallovchi (placeholder) yozuv YO'Q."""

    bank_name = "TrastBank"
    url = "https://trustbank.uz/uz/private/crediting/microloans/"
    CATEGORY_URLS = {
        "mikroqarz": "https://trustbank.uz/uz/private/crediting/microloans/",
    }
    CATEGORY_HEADINGS = {
        "mikroqarz": ("Doimiy daromadga ega bo", "Mikroqarz rasmiylashtirishda"),
    }
    GRACE_PERIOD_HEADINGS = {
        "mikroqarz": ("Mikroqarzning imtiyozli davri", "Doimiy daromadga ega bo"),
    }
    PRODUCT_NAMES = {
        "mikroqarz": "Mikroqarz",
    }
    FORCE_COLLATERAL = {
        "mikroqarz": True,
    }
