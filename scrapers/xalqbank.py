import re

from scrapers.base import TextSectionScraper

_DOWN_PAYMENT_RE = re.compile(
    r"Boshlang.ich badal - (\d+) foiz \(Uzautomotors avtomobillari uchun - (\d+) foiz\)"
)


class XalqBankScraper(TextSectionScraper):
    """Xalq Banki (xb.uz) "Onlayn-Avtokredit" sahifasi (dilerlardan/
    avtosalonlardan yangi mashina sotib olish uchun) ikkita bir xil qisqa
    xulosa vidjetini ketma-ket ikki marta chiqaradi ("Kredit foizi: 23%",
    "Kredit Muddati: 60 oy", "Maksimal miqdori ... 600 ... so'm"); pastroqdagi
    "Avto kredit shartlari" ro'yxati esa xuddi shu ma'lumotni "foiz" so'zi
    bilan beradi ("23 foiz"), "%" belgisisiz — extract_percentages faqat "%"
    belgisini tanigani uchun o'sha blok ishlatilmaydi. Shu sabab
    CATEGORY_HEADINGS birinchi vidjetni ("Kredit foizi:" dan ikkinchi
    "Onlayn-Avtokredit" nomi takrorlanishigacha) ajratib oladi.

    Saytning o'zida "Maksimal miqdori" qiymati "600 ООО ООО so'mgacha" deb
    yozilgan — raqamli nolning o'rniga xato bilan Kirill "О" harfi (U+041E)
    terilgan (uch-uchtadan guruhlangan, "000 000" o'rniga). Bu
    extract_amount_som'ning \\d{1,5} naqshiga umuman mos kelmaydi, shuning
    uchun _build_product'ga uzatishdan oldin faqat shu bank uchun "ООО" ->
    "000" almashtiriladi (global emas — boshqa banklar sahifalaridagi
    qonuniy Kirill matnni, masalan "ООО" tashkiliy-huquqiy shakl
    qisqartmasini, buzib qo'ymaslik uchun scrapers/utils.py o'zgartirilmadi).

    "Imtiyozli davri: Mavjud emas" iborasi butun sahifa matnida "garov"
    tekshiruvi uchun umumiy "mavjud emas" signali bilan aralashib, yolg'on-
    manfiy beradi — holbuki "Kredit ta'minoti" bo'limida sotib olinayotgan
    avtomashina aniq garovga olinishi yozilgan (InfinBank/IpotekaBank
    scraperlaridagi xuddi shu turdagi yechimga qarang). FORCE_COLLATERAL
    bilan tuzatilgan.

    Boshlang'ich badal ham "35 foiz (Uzautomotors avtomobillari uchun - 25
    foiz)" so'z shaklida berilgan — umumiy DOWN_PAYMENT_HEADINGS mexanizmi
    "%" belgisiga tayanadi, shu sabab bu yerda alohida regex bilan aniq
    ikkala qiymatdan (35, 25) pastrog'i olinadi.

    "Onlayn mikroqarz" (xb.uz/page/onlayn-mikroqarz) — nomining o'zi
    "onlayn" so'zini aniq ishlatadi, mahsulot tavsifi ham "Xazna" mobil
    ilovasi orqali, hujjatsiz, avtomatlashtirilgan skoring orqali
    beriladi deydi — shu sabab "mikroqarz_onlayn" toifasiga tegishli, oflayn
    "mikroqarz"ga emas. "Onlayn-mikroqarz krediti shartlari" bo'limida ikki
    xil mijoz toifasi uchun alohida stavka/muddat jadvali bor (ish haqi
    loyihasi ishtirokchilari: 24-27%, doimiy daromadli: 25-29%) — barchasi
    standart CATEGORY_HEADINGS oralig'ida, kontaminatsiyasiz. Boshlang'ich
    badal esa "Dastlabki to'lov: 0" deb bir necha marta aniq takrorlangan
    (foiz belgisisiz, "%" yo'q joyda), shu sabab _build_product'da bu
    kategoriya uchun to'g'ridan-to'g'ri 0 sifatida belgilanadi. Sahifada
    "imtiyozli davr" so'zi faqat umumiy "Ko'p so'raladigan savollar"
    ro'yxatidagi "Kredit bo'yicha imtiyozli davr bu nima?" degan FAQ
    savolida uchraydi — bu SHU mahsulot uchun aniq bir davr borligini
    bildirmaydi, shuning uchun standart (scoping'siz) qidiruv butun sahifa
    matnidan tasodifiy son topib, yolg'on natija berardi; shu sabab bu
    kategoriya uchun grace_period_months ham to'g'ridan-to'g'ri None
    qilib belgilanadi."""

    bank_name = "Xalq Banki"
    url = "https://xb.uz/page/kreditlar"
    CATEGORY_URLS = {
        "avtokredit": "https://xb.uz/page/onlayn-avtokredit",
        "mikroqarz_onlayn": "https://xb.uz/page/onlayn-mikroqarz",
    }
    CATEGORY_HEADINGS = {
        "avtokredit": ("Kredit foizi:", "Onlayn-Avtokredit"),
        "mikroqarz_onlayn": ("Onlayn-mikroqarz krediti shartlari", "Muhim shartlar"),
    }
    FORCE_COLLATERAL = {
        "avtokredit": True,
    }
    PRODUCT_NAMES = {
        "avtokredit": "Onlayn-Avtokredit",
        "mikroqarz_onlayn": "Onlayn mikroqarz",
    }
    PAYMENT_METHOD_HEADINGS = {
        "avtokredit": ("Kreditning to'lov grafigi", "Muhim shartlar"),
        "mikroqarz_onlayn": ("Muhim shartlar", "Onlayn mikroqarz: doimiy"),
    }
    GRACE_PERIOD_HEADINGS = {
        "avtokredit": ("Imtiyozli davri", "Umumiy tartib"),
    }

    def _build_product(
        self,
        category,
        section,
        source_url,
        scraped_at,
        full_text=None,
        down_payment_pct=None,
        grace_period_months=None,
        **kwargs,
    ):
        section = section.replace("ООО", "000")
        if category == "avtokredit" and down_payment_pct is None and full_text is not None:
            match = _DOWN_PAYMENT_RE.search(full_text)
            if match:
                down_payment_pct = min(float(match.group(1)), float(match.group(2)))
        elif category == "mikroqarz_onlayn":
            down_payment_pct = 0.0
            grace_period_months = None
        return super()._build_product(
            category,
            section,
            source_url,
            scraped_at,
            full_text,
            down_payment_pct=down_payment_pct,
            grace_period_months=grace_period_months,
            **kwargs,
        )
