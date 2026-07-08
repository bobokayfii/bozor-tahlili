from scrapers.base import TextSectionScraper


class HamkorBankScraper(TextSectionScraper):
    """HamkorBank (hamkorbank.uz) retail kredit kategoriyalari SQB/NBU/Ipoteka
    Bank kabi alohida sahifalarda joylashgan. CATEGORY_HEADINGS kerak emas:
    har bir fetch qilingan sahifa matni bitta kategoriyaga bag'ishlangan deb
    qabul qilinadi.

    MUHIM: HamkorBank saytida barcha 4 ta kategoriya uchun aniq, TO'LIQ
    TASDIQLANGAN mahsulot sahifalari topildi — barcha to'rttala URL ham
    WebFetch orqali jonli tekshirilgan va sahifa mazmuni tegishli kategoriya
    bilan aniq mos keldi (avvalgi banklardan farqli o'laroq, taxminiy/analog
    xaritalash kerak bo'lmadi):
      - avtokredit -> "Auto Light avtokrediti" sahifasi. Nomida "avtokredit"
        so'zi bevosita mavjud, to'g'ridan-to'g'ri moslik.
      - mikroqarz -> "Mikrokredit Plus" sahifasi. Sahifa nomi "mikroqarz"
        emas, "mikrokredit" deb ataladi, lekin bu xuddi shu tushuncha uchun
        HamkorBank ishlatadigan brend nomi — jismoniy shaxslarga mo'ljallangan
        kichik hajmdagi kredit mahsuloti, funksional analog emas, to'g'ridan-
        to'g'ri moslik.
      - kredit_karta -> "Kredit karta" sahifasi. To'g'ridan-to'g'ri moslik.
      - istemol_krediti -> "Iste'mol krediti" sahifasi. To'g'ridan-to'g'ri
        moslik.
    Fixture'lardagi barcha raqamlar (foiz stavkalari, muddatlar, summalar,
    garov shartlari) WebFetch orqali jonli sahifalardan olingan HAQIQIY
    ma'lumotlarga asoslangan (hech biri o'ylab topilmagan/invented emas);
    fixture matni faqat sinov uchun ixcham HTML shaklida qayta yozilgan,
    lekin son ko'rsatkichlari real sahifa mazmuniga mos keladi. Tadqiqot
    tafsilotlari Task 8 hisobotida keltirilgan."""

    bank_name = "HamkorBank"
    url = "https://hamkorbank.uz/uz/physical/credits/"
    CATEGORY_URLS = {
        # Barchasi tasdiqlangan (real, WebFetch orqali jonli tekshirilgan):
        "avtokredit": "https://hamkorbank.uz/uz/physical/credits/autolight/",
        "mikroqarz": "https://hamkorbank.uz/uz/physical/credits/microcredit-plus/",
        "kredit_karta": "https://hamkorbank.uz/uz/physical/credit-card/",
        "istemol_krediti": "https://hamkorbank.uz/uz/physical/credits/personal-loan/",
    }
