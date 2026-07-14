from scrapers.base import TextSectionScraper


class InfinBankScraper(TextSectionScraper):
    """InfinBank (infinbank.com) retail kredit kategoriyalari SQB kabi
    alohida sahifalarda joylashgan. Saytning TLS sertifikati oraliq
    (intermediate) CA'siz yuboriladi — EXTRA_CA_CERT shu bo'shliqni
    to'ldiradi (scrapers/utils.py va scrapers/certs/ ga qarang).

    Har bir sahifada "Axborot varaqasi" uslubidagi aniq label:qiymat
    bloki bor, lekin ikkita kategoriya uchun bu blok to'liq mahsulot
    yaratish uchun yetarli emas:
      - avtokredit: sahifada 6 xil variant (birlamchi/ikkilamchi bozor,
        turli boshlang'ich to'lov foizlari) bor, lekin birortasida ham
        aniq "N mln so'm" shaklida kredit miqdori ko'rsatilmagan — barchasi
        "Аvtotransport vositasining qiymatiga qarab" (avtomobil narxiga
        bog'liq) deb yozilgan. amount_max_som topilmagani uchun
        _build_product bu kategoriyani o'tkazib yuboradi — bu XATO EMAS,
        sahifada haqiqatan ham son ko'rinishidagi chegara yo'q.
      - kredit_karta (InfinBLACK): aylanma kredit liniyasi mahsuloti,
        muddat o'rniga "5 yil" (limit amal qilish muddati) faqat sahifaning
        boshqa, interaktiv kalkulyator qismida ko'rsatilgan — u yerda esa
        foiz stavkasi kalkulyator slayder qiymatlari va naqd pul/o'tkazma
        komissiya foizlari bilan aralashib ketadi (kontaminatsiya). Shuning
        uchun CATEGORY_HEADINGS faqat toza tarif jadvalini (limit, stavka
        oralig'i) qamrab oladi — natijada rate/amount to'g'ri, lekin term
        topilmaydi va _build_product bu kategoriyani ham o'tkazib yuboradi.

    Garov (kafolat) tekshiruvi har doim TO'LIQ sahifa matnida o'tkaziladi
    (narrowed section'da emas — bazaviy klass dizayni shunday, chunki garov
    ma'lumoti ko'pincha stavka jadvalidan tashqarida joylashadi). Bu InfinBank
    sahifalarida yolg'on-manfiy (false negative) beradi: mikroqarz va
    istemol_krediti sahifalarida boshqa bir bo'lim ("qo'shimcha to'lovlar")
    uchun "Mavjud emas" deb yozilgan bo'lib, has_collateral_requirement buni
    umumiy "mavjud emas" signali sifatida noto'g'ri o'qib, garov YO'Q deb
    xulosa chiqaradi — holbuki ikkala mahsulotning o'z "Ta'minot" bo'limida
    aniq "garov" talab qilinishi yozilgan (narrowed section'ni qo'lda
    tekshirganda tasdiqlangan). FORCE_COLLATERAL shu ikkala kategoriya uchun
    to'g'ri qiymatni aniq belgilaydi — IpotekaBank scraper'idagi xuddi shu
    turdagi yechimga qarang.
    """

    bank_name = "InfinBank"
    url = "https://infinbank.com/uz/private/credits/"
    EXTRA_CA_CERT = "infinbank_intermediate.pem"
    CATEGORY_URLS = {
        "avtokredit": "https://infinbank.com/uz/private/credits/avto_credit/",
        "mikroqarz": "https://infinbank.com/uz/private/credits/microloans/",
        "kredit_karta": "https://infinbank.com/uz/private/credits/overdraft/",
        "istemol_krediti": "https://infinbank.com/uz/private/credits/consumer/",
    }
    CATEGORY_HEADINGS = {
        # Sahifada 4 xil avtokredit varianti ketma-ket takrorlanadi; faqat
        # birinchisi ("Axborot varaqasi" -> ikkinchi "Kredit maqsadi"
        # takrorlanishigacha) olinadi — real, boshqalaridan farqli birinchi
        # variantning to'liq shartlari.
        "avtokredit": ("Axborot varaqasi", "Potensial qarz oluvchiga talablar"),
        "mikroqarz": ("Kredit muddati", "Potensial qarz oluvchiga talablar"),
        "kredit_karta": ("Maksimal kredit limiti", "Minimal toʻlov"),
        # "Potentsial" (t harfi bilan) — mikroqarz sahifasidagi
        # "Potensial"dan farqli imlo, sahifada shunday yozilgan.
        "istemol_krediti": ("Kredit muddati", "Potentsial qarz oluvchiga talablar"),
    }
    FORCE_COLLATERAL = {
        "mikroqarz": True,
        "istemol_krediti": True,
    }
