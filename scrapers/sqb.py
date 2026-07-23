import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_grace_period_months,
    extract_payment_method,
    extract_percentages,
    extract_section,
    fetch_html,
    has_collateral_requirement,
    html_to_text,
)

_YIL_RATE_RE = re.compile(r"(\d)\s*yil\s*.\s*(\d+,\d+)%")
_MORTGAGE_TERM_YEAR_RE = re.compile(r"(\d{1,2})\s*yilgacha")
_MORTGAGE_RATE_RE = re.compile(r"yillik\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*%", re.IGNORECASE)
_MORTGAGE_AMOUNT_RE = re.compile(r"([\d\s\xa0]{5,})\s*so.mgacha")


class SQBScraper(TextSectionScraper):
    """SQB retail kredit kategoriyalari bitta sahifada emas, balki har biri
    o'zining alohida mahsulot sahifasida joylashgan (real saytda tekshirilgan
    — Task 5 hisobotidagi tadqiqotga qarang). Shuning uchun CATEGORY_URLS
    ishlatiladi: har bir kategoriya o'z URL'idan alohida fetch qilinadi.

    avtokredit sahifasida ("«Avto imkon» avtokrediti") CATEGORY_HEADINGS
    yetarli emas — sahifada bir nechta ALOHIDA label:qiymat blok bor
    ("Batafsil shartlar" -> "Asosiy ma'lumotlar" ro'yxati) va ular orasida
    "Boshlang'ich badal: kamida 25%" ham bor. Agar butun blok bitta bo'lim
    sifatida olinsa, bu 25% "Foiz stavkalari" jadvalidagi 20-22% qatoriga
    aralashib, rate_max'ni yolg'on ravishda 25%ga ko'tarib yuboradi (yoki
    hatto battarroq — sahifa oxiridagi "qarz yuki 50%", "LTV 75%" va
    ipoteka cross-sell "17%" banneri bilan ham). Shu sabab avtokredit uchun
    run() qayta yozilib, har bir maydon ALOHIDA, tor oraliqdan olinadi:
      - foiz stavkasi: "Foiz stavkalari" -> "Qo'shimcha shartlar" (20%, 21%,
        22% — muddatiga qarab uchta variant, boshqa banklardagi kabi
        rate_min/rate_max butun jadval bo'yicha hisoblanadi)
      - muddat va kredit miqdori: "Kredit muddati:" -> "badal" (60 oygacha,
        800 million so'mgacha — "badal" so'zi ASCII-xavfsiz belgi sifatida
        ishlatiladi, chunki "Boshlang'ich badal" iborasidagi apostrof
        sahifada boshqa joylardagidan farqli Unicode belgi bilan yozilgan)
      - boshlang'ich badal: "badal:" -> "To'lov jadvali" (kamida 25%)
      - to'lov usuli: "To'lov jadvali:" -> "Kredit ta" (annuitet / differensial)
      - imtiyozli davr: "Imtiyozli davr:" -> "Kredit miqdori" (3 oy, faqat
        differensial to'lov jadvali bo'yicha)
    Boshqa 3 kategoriya (mikroqarz, kredit_karta, istemol_krediti) eski,
    tekshirilgan mantiqda qoladi — CATEGORY_HEADINGS orqali (yoki, agar
    yo'q bo'lsa, butun sahifa matni bo'yicha)."""

    bank_name = "SQB"
    url = "https://sqb.uz/uz/individuals/credits/"
    CATEGORY_URLS = {
        "avtokredit": "https://sqb.uz/uz/individuals/autoloans/avtokredit-imkon-uz/",
        "ipoteka_tijorat": "https://sqb.uz/uz/individuals/ipoteka/ishonchli-ipoteka-uz/",
        "ipoteka_davlat": "https://sqb.uz/uz/individuals/ipoteka/exclusive-ipoteka-uz/",
        "mikroqarz": "https://sqb.uz/uz/individuals/credits/mikrokredit-uz/",
        "kredit_karta": "https://sqb.uz/uz/individuals/credits/credit-card-new-uz/",
        "istemol_krediti": "https://sqb.uz/uz/individuals/credits/consumer-credit-new-uz/",
    }
    # consumer-credit-new-uz sahifasida "Foiz stavkasi:" jadvalidan tashqarida
    # ham boshqa % belgilar bor (masalan, "Qarz yuki ko'rsatkichi 50% dan
    # oshmasligi" talabi va ipoteka mahsulotiga cross-sell banneri "yillik
    # 17%"). CATEGORY_HEADINGS bo'lmasa butun sahifa matni bitta bo'lim
    # sifatida olinadi va shu begona foizlar rate_min/rate_max'ni buzadi.
    # Shuning uchun bu yerda faqat haqiqiy stavka jadvali bilan chegaralanadi.
    CATEGORY_HEADINGS = {
        "istemol_krediti": ("Kredit miqdori:", "Imtiyozli davr"),
    }
    PRODUCT_NAMES = {
        "avtokredit": "«Avto imkon» avtokrediti",
        "ipoteka_tijorat": "Ishonchli ipoteka krediti",
        "ipoteka_davlat": "Exclusive ipoteka",
        "mikroqarz": "Mikrokredit",
    }
    FORCE_COLLATERAL = {
        "avtokredit": True,
        # Ipoteka doim sotib olinayotgan ko'chmas mulk garovi bilan
        # ta'minlanadi; sahifadagi umumiy garov tekshiruvi boshqa
        # aloqasiz "garovsiz" iborasi tufayli yolg'on-manfiy berishi
        # mumkin bo'lgani uchun aniq True belgilangan.
        "ipoteka_tijorat": True,
        # Xuddi shu sababga ko'ra — ipoteka doim ko'chmas mulk garovi bilan
        # ta'minlanadi.
        "ipoteka_davlat": True,
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)

                if category == "avtokredit":
                    product = self._build_avtokredit_product(url, now, text)
                elif category == "ipoteka_tijorat":
                    product = self._build_ipoteka_tijorat_product(url, now, text)
                elif category == "ipoteka_davlat":
                    product = self._build_ipoteka_davlat_product(url, now, text)
                elif category == "mikroqarz":
                    product = self._build_mikroqarz_product(url, now, text)
                else:
                    heading_pair = self.CATEGORY_HEADINGS.get(category)
                    section = extract_section(text, *heading_pair) if heading_pair is not None else text
                    product = self._build_product(category, section, url, now, full_text=text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, url, now, text):
        rate_section = extract_section(text, "Foiz stavkalari", "Qo'shimcha shartlar")
        term_amount_section = extract_section(text, "Kredit muddati:", "badal")
        section = f"{rate_section}\n{term_amount_section}"

        down_payment_section = extract_section(text, "badal:", "To'lov jadvali")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        payment_method_section = extract_section(text, "To'lov jadvali:", "Kredit ta")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(text, "Imtiyozli davr:", "Kredit miqdori")
        grace_period_months = extract_grace_period_months("Imtiyozli davr:" + grace_section)

        return self._build_product(
            "avtokredit",
            section,
            url,
            now,
            full_text=text,
            down_payment_pct=down_payment_pct,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """"Ishonchli ipoteka krediti" — bankning o'z (tijorat) mablag'lari
        hisobidan birlamchi va ikkilamchi bozorlardan uy-joy sotib olish
        uchun. "Kredit foiz stavkasi" bo'limi mijoz toifasi bo'yicha 3 ta
        alohida qatordan iborat (23,5% / 24% / 24,5%), har biri o'z
        "Kredit muddati: N yilgacha" qiymatiga ega (15/10/15 yil). Muddat
        180 oygacha chiqadi — umumiy extract_term_months'ning avtokredit
        uchun mo'ljallangan 120 oylik qattiq chegarasi bu yerda ishlatilmaydi
        (aks holda 15 yillik variant, 180 oy, chetlab o'tilardi), o'rniga
        cheklovsiz "N yilgacha" regexi ishlatiladi.

        Sahifada apostrof — boshqa ko'plab SQB sahifalaridan farqli —
        Unicode o'ng qo'shtirnoq (‘) bilan yozilgan ("Boshlang‘ich badal:",
        "To‘lov usuli:"), oddiy ASCII (') emas — shu sabab boshlanish
        sarlavhalari shu maxsus belgi bilan mos kelishi kerak."""
        rate_section = extract_section(text, "Kredit foiz stavkasi", "Qo")
        rates = extract_percentages(rate_section)
        terms = sorted({int(m) * 12 for m in _MORTGAGE_TERM_YEAR_RE.findall(rate_section)})

        amount_section = extract_section(text, "Kredit maksimal miqdori", "Imtiyozli davr")
        amount = extract_amount_som(amount_section)

        down_payment_section = extract_section(text, "Boshlang‘ich badal:", "To‘lov usuli")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        payment_method_section = extract_section(text, "To‘lov usuli:", "Kredit ajratish shakli")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(text, "Imtiyozli davr:", "Boshlang")
        grace_period_months = extract_grace_period_months("Imtiyozli davr:" + grace_section)

        if not rates or not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="ipoteka_tijorat",
            product_name=self.PRODUCT_NAMES["ipoteka_tijorat"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=self.FORCE_COLLATERAL["ipoteka_tijorat"],
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_ipoteka_davlat_product(self, url, now, text):
        """"Exclusive ipoteka" — sahifada aniq yozilgan: "Yangi tartib
        doirasida Iqtisodiyot va moliya vazirligi mablag'lari hamda
        Bankning o'z mablag'lari hisobidan moliyalashtiriladigan ipoteka
        krediti" — davlat (Moliya vazirligi) mablag'lari + bankning o'z
        mablag'lari aralash moliyalashtirilgan mahsulot; "Ishonchli
        ipoteka"dagi 100% bankning o'z mablag'idan farqli. Faqat birlamchi
        bozordagi (foydalanishga topshirilgan) xonadon xaridi uchun. SQB
        saytida shunga o'xshash yana 3 ta "hamkor" nomli sahifa bor
        ("Hamkor ipoteka", "Ipoteka Universal hamkor", "Yangi Toshkent"),
        lekin ular ko'p xonadonli qurilishda ULUSH KIRITISH (qurilish
        bosqichidagi obyektga pul kiritish) uchun mo'ljallangan, tugallangan
        uy-joy sotib olish uchun emas — shu sabab ular chetlab o'tilgan.

        "Kreditning eng ko'p miqdori" bo'limida UCHTA raqam bor: umumiy
        chegara ("1 000 000 000 so'mgacha", aniq guruhlangan son) va ikkita
        Moliya vazirligi mablag'i sub-chegarasi ("380 mln so'mgacha",
        "480 mln so'mgacha"). Umumiy extract_amount_som mln-formatidagi
        qiymatlar mavjud bo'lganda guruhlangan-aniq-son fallback'ini
        umuman ishlatmaydi, shuning uchun natija noto'g'ri ravishda eng
        kichik sub-chegara (480 mln)ga tushib qolardi — maxsus regex bilan
        "mln" so'zisiz, to'g'ridan-to'g'ri "so'mgacha"ga ulangan birinchi
        guruhlangan sonni ("1 000 000 000") olib, umumiy chegara
        ishlatiladi.

        "Boshlang'ich badal" sarlavhasi sahifada IKKI marta uchraydi
        (yuqoridagi bo'sh kalkulyator vidjeti va haqiqiy "Batafsil
        shartlar" ro'yxati) — shu sabab avval butun "Kredit maqsadi" ->
        "Hujjatlar" detallashtirilgan bloki ajratib olinadi (bu blokda har
        bir sarlavha faqat bir marta uchraydi), so'ng barcha maydonlar shu
        BLOK ICHIDA qidiriladi.

        Stavka "Yillik 18% dan" — bitta boshlang'ich (min) qiymat, aniq
        yuqori chegara berilmagan, shuning uchun rate_min=rate_max=18.0."""
        block = extract_section(text, "Kredit maqsadi", "Hujjatlar")

        amount_section = extract_section(block, "Kreditning eng ko", "Boshlang")
        amount_match = _MORTGAGE_AMOUNT_RE.search(amount_section)
        amount = int(amount_match.group(1).replace(" ", "").replace("\xa0", "")) if amount_match else None

        down_payment_section = extract_section(block, "Boshlang", "Kredit muddati")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        term_section = extract_section(block, "Kredit muddati", "To")
        term_match = _MORTGAGE_TERM_YEAR_RE.search(term_section)
        term = int(term_match.group(1)) * 12 if term_match else None

        payment_method_section = extract_section(block, "To‘lov usuli", "Imtiyozli davr")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(block, "Imtiyozli davr", "Foiz stavkasi")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        rate_section = extract_section(block, "Foiz stavkasi", "Ta")
        rate_match = _MORTGAGE_RATE_RE.search(rate_section)
        rates = [float(rate_match.group(1).replace(",", "."))] if rate_match else []

        if not rates or term is None or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="ipoteka_davlat",
            product_name=self.PRODUCT_NAMES["ipoteka_davlat"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=term,
            term_max_months=term,
            amount_max_som=amount,
            requires_collateral=self.FORCE_COLLATERAL["ipoteka_davlat"],
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_mikroqarz_product(self, url, now, text):
        """SQB'ning "Mikrokredit" sahifasi (sarlavhada "onlayn" so'zi yo'q —
        faqat mobil ilova orqali kredit olish haqidagi umumiy maslahat
        bandida "onlayn" so'zi tasodifan uchraydi, mahsulot nomining o'zi
        emas) — shu sabab bu "mikroqarz" (oflayn) toifasiga tegishli.
        "Foiz stavkasi:" jadvali muddatga qarab uchta qiymat beradi (3
        yil-26,9%, 4 yil-27,9%, 5 yil-28,9%)."""
        rate_section = extract_section(text, "Foiz stavkasi:", "To'lov davriyligi")
        pairs = _YIL_RATE_RE.findall(rate_section)
        rates = [float(rate.replace(",", ".")) for _yil, rate in pairs]
        terms = [int(yil) * 12 for yil, _rate in pairs]

        amount_section = extract_section(text, "Mikroqarz miqdori:", "Mikroqarz muddati")
        amount = extract_amount_som(amount_section)

        payment_method_section = extract_section(text, "To'lov usuli:", "Bank bo")
        payment_method = extract_payment_method(payment_method_section)

        if not rates or not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="mikroqarz",
            product_name=self.PRODUCT_NAMES["mikroqarz"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=payment_method,
        )
