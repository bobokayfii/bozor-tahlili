

from scrapers.base import TextSectionScraper


class AgroBankScraper(TextSectionScraper):
    """AgroBank (agrobank.uz) retail kredit kategoriyalari SQB/NBU/Ipoteka Bank/
    HamkorBank kabi alohida sahifalarda joylashgan. CATEGORY_HEADINGS kerak emas:
    har bir fetch qilingan sahifa matni bitta kategoriyaga bag'ishlangan deb
    qabul qilinadi.

    MUHIM (avvalgi 4 ta bankdan farqli holat): AgroBank saytida barcha 4 ta
    kategoriya uchun HAM nom jihatidan to'g'ridan-to'g'ri mos keladigan real
    mahsulot sahifalari qidiruv orqali topildi (izlash natijalari sarlavhalari
    mos keldi, ya'ni bironta kategoriya uchun ham Overdraft kabi funksional
    analog qidirishga to'g'ri kelmadi). LEKIN agrobank.uz — JavaScript orqali
    render qilinadigan SPA (bir sahifali ilova) sayt: WebFetch orqali barcha
    4 ta sahifani olishga urinishlarda faqat sarlavha/meta matni qaytdi, sahifa
    tanasi (foiz/muddat/summa ko'rsatilgan asosiy matn) hech qachon qaytmadi.
    Shu sababli hech bir kategoriya uchun raqamlar to'g'ridan-to'g'ri
    agrobank.uz'ning o'zidan tasdiqlanmadi. O'rniga uchinchi tomon bank
    taqqoslash agregatorlaridan (bank.uz, depozit.uz, bankxizmatlari.uz) —
    ular aniq Agrobank mahsulotini nom/ID orqali tasdiqlagan holda — raqamlar
    o'zaro solishtirib olindi. Ba'zi agregatorlar bir-biriga zid ma'lumot
    berdi (pastda ko'rsatilgan). Har bir kategoriya uchun holat aniq:

      - avtokredit -> "/person/loans/auto1" — URL VA MAHSULOT NOMI REAL
        (to'g'ridan-to'g'ri moslik, taxmin emas). Foiz (24-27%), muddat
        (48-60 oy) va boshlang'ich badal (25 foiz) bankxizmatlari.uz
        agregatoridan olindi (Agrobank ID 44214 sifatida tasdiqlangan) —
        bular HAQIQIY bozor ma'lumotlari, lekin primary saytdan emas.
        Kredit miqdori (500 mln.so'm) esa TO'LIQ O'YLAB TOPILGAN: manba
        aniq raqam bermay "shartnomaga asosan" deb ko'rsatgan.

      - mikroqarz -> "/person/loans/microloan" — URL VA MAHSULOT NOMI REAL.
        Foiz (25-30%) va kredit miqdori (100 mln.so'm) bank.uz agregatoridan
        olindi — HAQIQIY ma'lumot, lekin primary saytdan emas. Muddatning
        yuqori chegarasi (60 oy = 5 yil) ham shu manbada bor, LEKIN pastki
        chegara (fixture'da 6 oy) manbada yo'q — TO'LIQ O'YLAB TOPILGAN.
        Kredit kafolati tafsilotlari ham manbada ko'rsatilmagan — TO'LIQ
        O'YLAB TOPILGAN.

      - kredit_karta -> "/person/loans/credit-karta" — URL VA MAHSULOT NOMI
        REAL. Ikkita agregator manbasi bir-biriga ZID: depozit.uz joriy
        taklif sifatida 27% / 100 mln.so'm ko'rsatadi, bank.uz esa 27.99% /
        50 mln.so'mni "joriy taklif amal qilmaydi" (eskirgan) deb belgilagan
        holda ko'rsatadi. Fixture'da depozit.uz'ning joriy qiymatlari (27%,
        100 mln.so'm) ishlatildi, lekin bu HAM primary saytdan tasdiqlanmagan
        — faqat ikkilamchi manbadan. Muddat (48 oy = 4 yil) ikkala manbada
        mos keladi. Kredit kafolati tafsilotlari hech bir manbada yo'q —
        TO'LIQ O'YLAB TOPILGAN.

      - istemol_krediti -> "/person/loans/green-energy" ("Yashil energiya"
        iste'mol krediti) — URL REAL, LEKIN MAHSULOT TORAYTIRILGAN: bu
        umumiy maqsadli iste'mol krediti emas, faqat quyosh panellari va
        shunga o'xshash energiya jihozlarini sotib olish uchun maqsadli
        kredit — hozirda topilgan yagona faol "iste'mol krediti" nomli
        mahsulot shu edi (umumiy /page/uz_consumer_loans sahifasi mavjud,
        lekin qidiruv orqali boshqa faol umumiy mahsulot topilmadi). BU
        TORAYTIRILGAN ANALOG sifatida belgilanadi (nomi mos, qamrovi tor).
        Foiz (20%) va kredit miqdori (100 mln.so'm) ikkala manbada mos
        keladi — HAQIQIY, lekin primary saytdan emas. Muddat uchun manbalar
        ZID: biri 3 yil (36 oy), boshqasi 5 yil (60 oy) deydi; fixture'da
        ikkala chegara ham (36-60 oy) kiritildi, lekin bu ANIQ EMAS. Kredit
        kafolati (uchinchi shaxs kafilligi/mol-mulk garovi/sug'urta polisi)
        HAQIQIY ma'lumot, ikkilamchi manbadan.

    XULOSA: barcha 4 ta URL manzili va kategoriya-mahsulot moslashuvi real
    (taxminiy emas), lekin hech bir kategoriyaning raqamli ko'rsatkichlari
    (foiz/muddat/summa/garov) agrobank.uz'ning o'zidan to'g'ridan-to'g'ri
    tasdiqlanmagan — barchasi ikkilamchi agregatorlardan olingan yoki qisman
    o'ylab topilgan. Ishlab chiqarishda (production) bu shuni anglatadiki,
    scraper agrobank.uz'ga jonli murojaat qilganda SPA sahifa tanasi bo'sh
    qaytishi va hech qanday mahsulot topilmasligi mumkin (extract_percentages/
    extract_term_months/extract_amount_som bo'sh natija qaytarsa, parse None
    qaytaradi) — bu Task 10 orchestrator/monitoring bosqichida hisobga
    olinishi kerak."""

    bank_name = "AgroBank"
    url = "https://agrobank.uz/uz/person/loans"
    CATEGORY_URLS = {
        # Barcha URL manzillari real (qidiruv orqali tasdiqlangan), lekin
        # raqamlar primary saytdan emas — yuqoridagi docstringga qarang.
        "avtokredit": "https://agrobank.uz/uz/person/loans/auto1",
        "mikroqarz": "https://agrobank.uz/uz/person/loans/microloan",
        "kredit_karta": "https://agrobank.uz/uz/person/loans/credit-karta",
        # Toraytirilgan analog (faqat "Yashil energiya" maqsadli krediti):
        "istemol_krediti": "https://agrobank.uz/uz/person/loans/green-energy",
    }
