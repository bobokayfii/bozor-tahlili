import re

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_grace_period_months,
    extract_payment_method,
    extract_section,
)

_DOWN_PAYMENT_RE = re.compile(
    r"Boshlang.ich badal - (\d+) foiz \(Uzautomotors avtomobillari uchun - (\d+) foiz\)"
)
_ISTEMOL_TIER_RE = re.compile(r"(\d)\s*yilga yillik\s*(\d{1,2}(?:\.\d{1,2})?)\s*foiz")
_MORTGAGE_RATE_LINE_RE = re.compile(r"Yillik foiz stavkasi\s*-?\s*(\d{1,2}(?:[.,]\d{1,2})?)%")
_MORTGAGE_DOWN_LINE_RE = re.compile(r"Boshlang.ich to.lov\s*-?\s*(\d{1,2})%")
# extract_term_months caps values at 120 (10 years) — both mortgage terms
# here (180/240 months, i.e. 15/20 years) exceed that, so a dedicated
# cap-free regex is used instead (same fix as bdb.py/nbu.py's ipoteka_davlat).
_MORTGAGE_TERM_RE = re.compile(r"(\d{1,3})\s*oygacha")


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
    qilib belgilanadi.

    "Iste'mol kreditlari" (xb.uz/page/physical-credit-consumption) — sayt
    izlash orqali topildi (pptx'ning "Green iste'mol krediti" nomidagi
    sahifasi endi ishlamaydi/bo'sh qaytadi, bu sahifa haqiqiy va real
    ma'lumot beradi). Kalkulyator vidjetining o'zida faqat bitta yagona
    stavka ("26.99%") ko'rsatiladi, lekin "Iste'mol kreditining qo'shimcha
    ma'lumotlari" bandida to'liq muddat-stavka jadvali bor: "1 yilga
    yillik 23 foiz, 2 yilga yillik 26.99 foiz, 3 yilga yillik 26.99 foiz"
    — shu jadval ustuvor manba (rate_min=23, rate_max=26.99, term 12-36
    oy, yillar oyga ko'paytiriladi). Summa kalkulyatorning o'z chegarasidan
    ("1 000 000 so'm" — "27 000 000 so'm") olinadi. Boshlang'ich to'lov
    slayderi "0%"dan boshlanadi. Ta'minot — "Sug'urta polisi" (mulk/ko'chmas
    mulk garovi emas), shu sabab requires_collateral False."""

    bank_name = "Xalq Banki"
    url = "https://xb.uz/page/kreditlar"
    CATEGORY_URLS = {
        "avtokredit": "https://xb.uz/page/onlayn-avtokredit",
        "mikroqarz_onlayn": "https://xb.uz/page/onlayn-mikroqarz",
        "istemol_krediti": "https://xb.uz/page/physical-credit-consumption",
        "ipoteka_tijorat": "https://xb.uz/page/qulay-ipoteka-krediti",
        "ipoteka_davlat": "https://xb.uz/page/farovon-hayot-ipoteka-kredit",
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
        "istemol_krediti": "Iste'mol krediti",
        "ipoteka_tijorat": '"Qulay" ipoteka krediti',
        "ipoteka_davlat": '"Farovon" ipoteka krediti',
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
        if category == "istemol_krediti":
            return self._build_istemol_krediti_product(source_url, scraped_at, full_text or section)
        if category in ("ipoteka_tijorat", "ipoteka_davlat"):
            return self._build_ipoteka_product(category, source_url, scraped_at, full_text or section)

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

    def _build_istemol_krediti_product(self, url, now, text):
        tiers = _ISTEMOL_TIER_RE.findall(text)
        if not tiers:
            return None
        rates = [float(rate) for _year, rate in tiers]
        terms = [int(year) * 12 for year, _rate in tiers]

        amount_section = extract_section(text, "Kredit summasi", "Muddati")
        amount = extract_amount_som(amount_section)
        if amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="istemol_krediti",
            product_name=self.PRODUCT_NAMES["istemol_krediti"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=False,
            down_payment_pct=0.0,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method="Annuitet, Differensial",
        )

    def _build_ipoteka_product(self, category, url, now, text):
        """""Qulay" ipoteka krediti" (ipoteka_tijorat) — "Bankning o'z
        mablag'lari hisobidan" deb aniq yozilgan, birlamchi VA ikkilamchi
        bozordan uy-joy uchun. ""Farovon" ipoteka krediti" (ipoteka_davlat)
        — aniq quyi (17%) stavkasi va Xalq Banki'ning boshqa "davlat"
        mahsulotlari bilan bir xil 17% qiymati orqali davlat mablag'i
        ekani tasdiqlangan (NBU'ning shunga o'xshash davlat mahsuloti ham
        aynan 17% dan boshlanadi). Ikkala sahifa ham "Kredit shartlari"
        (yoki "...ipoteka kredit shartlari") nomli raqamlangan ro'yxatda
        mijoz segmenti bo'yicha bir necha "Boshlang'ich to'lov - N%
        Yillik foiz stavkasi - M%" qatoridan iborat — shu ikki alohida
        regex bilan ajratiladi (aks holda ikkalasi ham "%" belgili bo'lgani
        uchun extract_percentages ularni ajrata olmas edi)."""
        # "Qulay" heading is standalone "Kredit shartlari" (capital K);
        # "Farovon" heading is the longer '"Farovon" ipoteka kredit
        # shartlari' (lowercase k, part of the quoted product name) —
        # case-sensitive extract_section needs the exact substring for each.
        start_heading = "Kredit shartlari" if category == "ipoteka_tijorat" else "ipoteka kredit shartlari"
        block = extract_section(text, start_heading, "Muhim shartlar")

        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_LINE_RE.findall(block)]
        down_payments = [int(m) for m in _MORTGAGE_DOWN_LINE_RE.findall(block)]

        amount_section = extract_section(block, "Maksimal miqdori", "Kredit muddati")
        amount = extract_amount_som(amount_section)

        term_section = extract_section(block, "Kredit muddati", "Kreditning imtiyozli davri")
        terms = [int(m) for m in _MORTGAGE_TERM_RE.findall(term_section)]

        if not rates or amount is None or not terms:
            return None

        grace_section = extract_section(block, "Kreditning imtiyozli davri", "Kredit")
        grace_period_months = extract_grace_period_months("imtiyozli davri" + grace_section)

        payment_method = extract_payment_method(block)

        return Product(
            bank=self.bank_name,
            category=category,
            product_name=self.PRODUCT_NAMES[category],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            # Ipoteka doim sotib olinayotgan ko'chmas mulk garovi bilan
            # ta'minlanadi (boshqa ipoteka_tijorat/ipoteka_davlat
            # scraperlaridagi bir xil konvensiya) — has_collateral_requirement
            # to'g'ridan-to'g'ri ishlatilmaydi, chunki "Farovon" sahifasida
            # "Kreditning imtiyozli davri: Mavjud emas" iborasi umumiy
            # "mavjud emas" signali bilan aralashib yolg'on-manfiy beradi
            # (avtokredit uchun bu faylda allaqachon hujjatlashtirilgan
            # bir xil muammo).
            requires_collateral=True,
            down_payment_pct=float(min(down_payments)) if down_payments else None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )
