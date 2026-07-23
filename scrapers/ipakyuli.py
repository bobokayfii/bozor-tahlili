import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_payment_method,
    extract_percentages,
    extract_section,
    fetch_html,
    has_collateral_requirement,
    html_to_text,
)

_ROW_RE = re.compile(r"(\d+,\d+)%\s*\n(.*?)\n(?:.*\n){0,1}?(\d+)\s*oygacha")
_MIKROQARZ_RATE_TERM_RE = re.compile(r"(\d+,\d+)%\s*\n\s*(\d+)\s*oygacha")
_IKKILAMCHI_RATE_TERM_RE = re.compile(r"(\d+,\d+)%\s*\n(?:[^\n]*\n){1,2}?(\d+)\s*oygacha")
_IKKILAMCHI_DOWN_PAYMENT_RE = re.compile(r"\d+,\d+%\s*\n(\d+)%\s*\n")
_BREND_RATE_RE = re.compile(r"(\d{1,2},\d{1,2})%")
_BREND_TERM_RE = re.compile(r"(\d{1,3})\s*oy(?!dan|gacha)")
_BREND_TIER_RE = re.compile(r"(?<!\d)(\d{2})%(?!\d)")
_MORTGAGE_TERM_RE = re.compile(r"(\d{1,3})\s*oygacha")


class IpakYuliBankScraper(TextSectionScraper):
    """Ipak Yo'li Bank (ipakyulibank.uz) — real, verified data for
    mikroqarz. kredit_karta ("Imkoniyatlar" kartasi) foiz stavkasiz, faqat
    limit+foizsiz davr modeli bilan ishlaydi (aniq foiz ko'rsatilmagan);
    istemol_krediti sahifasida esa aniq summa/stavka umuman yo'q ("dastur
    shartlariga bog'liq" deyilgan, xolos) — ikkalasi ham _build_product
    tomonidan tabiiy ravishda o'tkazib yuboriladi.

    avtokredit sahifasida "Kredit muddati bo'yicha foiz stavkasi" jadvali
    oltita qator (foiz/boshlang'ich badal/muddat kombinatsiyasi) beradi:
    20,90%-24,90% oralig'ida, 12-60 oy muddatda, boshlang'ich badal 25%
    dan boshlab. Eski versiya bu jadvalni umuman o'qimagan edi (CATEGORY_
    HEADINGS "25%"da to'xtab, faqat birinchi qatorning stavkasini —
    20,9% — olar, qolgan besh qatorni ko'rmas edi). Endi run() qayta
    yozilib, har bir qator alohida regex bilan ajratiladi: har bir qator
    "N,NN%\\n<boshlang'ich badal matni>\\n[ixtiyoriy qo'shimcha qator]\\nM
    oygacha" shaklida (faqat birinchi qatorda "Kredit summasi" ham bor,
    qolganlarida yo'q — shu sabab oraliq qatorlar soni {0,1} qilib
    moslashuvchan qilingan).

    Sahifada "Annuitet hamda differentsial to'lov jadvali o'rtasidagi farq
    nima?" degan FAQ bor — bu ikkala usulni umumiy tushuntiruvchi ta'lim
    matni, xolos, aynan SHU mahsulot qaysi usul(lar)ni taklif qilishini
    aytmaydi. Shu sabab to'lov usuli bo'yicha taxmin qilinmadi (None).
    Xuddi shunday sahifada "imtiyozli davr" haqida umuman gap yo'q.

    Boshqa (aloqasiz) mahsulot uchun "garovsiz" so'zi borligi sababli
    to'liq sahifa bo'yicha garov tekshiruvi yolg'on-manfiy beradi (real
    FAQ'da "Garov sifatida ... avtomobil qo'yish mumkin" aniq yozilgan
    bo'lsa ham) — FORCE_COLLATERAL bilan tuzatilgan."""

    bank_name = "Ipak Yo'li Bank"
    url = "https://ipakyulibank.uz/physical/kreditlar"
    CATEGORY_URLS = {
        "avtokredit": "https://ipakyulibank.uz/physical/kreditlar/avtokreditlar/birlamchi-bozor-avtokreditlari",
        "avtokredit_ikkilamchi": (
            "https://ipakyulibank.uz/physical/kreditlar/avtokreditlar/ikkilamchi-bozor-uchun-avtomobil-krediti"
        ),
        "avtokredit_brend_birlamchi": "https://ipakyulibank.uz/physical/kreditlar/avtokreditlar/volkswagen-avtokredit",
        "ipoteka_tijorat": "https://ipakyulibank.uz/physical/kreditlar/ipoteka/ipoteka-24",
        "mikroqarz": "https://ipakyulibank.uz/physical/kreditlar/mikroqarzlar/mikroqarz",
        "kredit_karta": "https://ipakyulibank.uz/physical/kartalar/imkoniyatlar-kredit-kartasi",
        "istemol_krediti": "https://ipakyulibank.uz/physical/kreditlar/istemol-krediti",
    }
    CATEGORY_HEADINGS = {
        "kredit_karta": ("Limit", "Foizsiz davr"),
        "istemol_krediti": ("Kredit muddati", "Kredit qanday qaytariladi"),
    }
    FORCE_COLLATERAL = {
        "avtokredit": True,
        "avtokredit_ikkilamchi": True,
        "mikroqarz": False,
    }
    PRODUCT_NAMES = {
        "avtokredit": "Birlamchi bozor avtokrediti",
        "avtokredit_ikkilamchi": "Ikkilamchi bozor uchun avtomobil krediti",
        "avtokredit_brend_birlamchi": "Volkswagen uchun avtokredit",
        "ipoteka_tijorat": "Ipoteka-24",
        "mikroqarz": "Kafillik asosida mikroqarz",
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
                elif category == "avtokredit_ikkilamchi":
                    product = self._build_avtokredit_ikkilamchi_product(url, now, text)
                elif category == "avtokredit_brend_birlamchi":
                    product = self._build_avtokredit_brend_birlamchi_product(url, now, text)
                elif category == "ipoteka_tijorat":
                    product = self._build_ipoteka_tijorat_product(url, now, text)
                elif category == "mikroqarz":
                    product = self._build_mikroqarz_product(url, now, text)
                else:
                    heading_pair = self.CATEGORY_HEADINGS[category]
                    section = extract_section(text, *heading_pair)
                    product = self._build_product(category, section, url, now, full_text=text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, url, now, text):
        table_section = extract_section(text, "foiz stavkasi\n", "Savollar va javoblar")
        rows = _ROW_RE.findall(table_section)
        rates = [float(rate.replace(",", ".")) for rate, _dp, _term in rows]
        terms = [int(term) for _rate, _dp, term in rows]
        down_payments = []
        for _rate, dp_text, _term in rows:
            pcts = extract_percentages(dp_text)
            if pcts:
                down_payments.append(min(pcts))
        down_payment_pct = min(down_payments) if down_payments else None

        summary_section = extract_section(text, "Birlamchi bozor avtokrediti", "Ariza qoldirish")
        amount = extract_amount_som(summary_section)

        if not rates or not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="avtokredit",
            product_name=self.PRODUCT_NAMES["avtokredit"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=self.FORCE_COLLATERAL["avtokredit"],
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )

    def _build_avtokredit_ikkilamchi_product(self, url, now, text):
        """"Ikkilamchi bozor uchun avtomobil krediti" — "Kredit muddati
        bo'yicha foiz stavkasi" jadvali 6 qatordan iborat: har qatorda
        stavka (vergul-o'nlik, masalan "20,90%"), boshlang'ich to'lov
        ("25%" yoki "25% dan 49,99% gacha" oralig'i — ikkalasi ham "%"
        belgisi bilan), [faqat birinchi qatorda] summa, va muddat ("N
        oygacha"). Boshlang'ich to'lov matni ba'zan ikkinchi "%" (masalan
        "49,99%") ham vergul-o'nlik shaklda bo'lgani uchun oddiy
        extract_percentages bilan ajratib bo'lmaydi — shu sabab maxsus
        regex bilan faqat stavkadan keyin 1-2 qator ichida keladigan "N
        oygacha" bilan juftlashtiriladi (stavka va muddat orasidagi
        boshlang'ich to'lov/summa matni e'tiborga olinmaydi).

        Boshqa avtokredit sahifalari kabi "Annuitet hamda differentsial
        to'lov jadvali o'rtasidagi farq nima?" umumiy FAQ borligi va
        "imtiyozli davr" haqida gap yo'qligi sababli to'lov usuli va
        imtiyozli davr taxmin qilinmaydi (None)."""
        table_section = extract_section(text, "Kredit muddati bo", "Ikkilamchi bozor uchun avtokreditni")
        pairs = _IKKILAMCHI_RATE_TERM_RE.findall(table_section)
        rates = [float(rate.replace(",", ".")) for rate, _term in pairs]
        terms = [int(term) for _rate, term in pairs]

        amount = extract_amount_som(table_section)

        down_payment_match = _IKKILAMCHI_DOWN_PAYMENT_RE.search(table_section)
        down_payment_pct = float(down_payment_match.group(1)) if down_payment_match else None

        if not rates or not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="avtokredit_ikkilamchi",
            product_name=self.PRODUCT_NAMES["avtokredit_ikkilamchi"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=self.FORCE_COLLATERAL["avtokredit_ikkilamchi"],
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )

    def _build_avtokredit_brend_birlamchi_product(self, url, now, text):
        """"Volkswagen uchun avtokredit" — rasmiy dilerdan yangi Volkswagen
        yoki Jetta avtomobili (Passat Pro, Teramont Pro/X, Tiguan L Pro,
        Lavida XR, Tharu XR, Jetta VS5/VS7) uchun. "Foiz stavkasi haqida"
        bo'limida 3 ta mustaqil narx jadvali bor (rasmiy daromadli /
        davlat tashkiloti xodimlari / norasmiy daromadli mijoz toifasi),
        har biri boshlang'ich to'lov ulushi (25%/50%) x muddat (12-60 oy)
        bo'yicha guruhlangan. Ulush yorlig'i har doim 2 xonali butun son
        ("25%"), haqiqiy stavkalar esa har doim vergul-kasr ("20,9%")
        shaklida — shu farq orqali ajratiladi. Muddat "N oygacha" emas,
        yalang' "N oy" ko'rinishida beriladi (bittasida "Muddat" o'rniga
        ruscha "Срок" yozilgan, lekin bu faqat sarlavha, qiymatlarga
        ta'sir qilmaydi).

        Sahifa boshidagi qisqacha xulosa kartochkasi ("Summa\\n800 000 000
        so'mgacha") shu mahsulotning o'zi uchun — pastroqda "Boshqa
        kreditlar" karuselida boshqa mahsulotlar (UzAuto Motors, Voyah)
        bilan bir qatorda takrorlansa ham, extract_section birinchi
        (haqiqiy) uchrashuvni oladi."""
        block = extract_section(text, "Foiz stavkasi haqida", "Savollar va javoblar")
        rates = [float(m.replace(",", ".")) for m in _BREND_RATE_RE.findall(block)]
        terms = [int(m) for m in _BREND_TERM_RE.findall(block)]
        tiers = [int(m) for m in _BREND_TIER_RE.findall(block)]
        down_payment_pct = float(min(tiers)) if tiers else None

        amount_section = extract_section(text, "Summa", "Muddat")
        amount = extract_amount_som(amount_section)

        payment_method_section = extract_section(text, "qaytarish usuli", "Garovni")
        payment_method = extract_payment_method(payment_method_section)

        if not rates or not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="avtokredit_brend_birlamchi",
            product_name=self.PRODUCT_NAMES["avtokredit_brend_birlamchi"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=payment_method,
        )

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """"Ipoteka-24" — bankning o'z mablag'i hisobidan birlamchi va
        ikkilamchi bozordan ko'chmas mulk sotib olish uchun ("Moliya
        vazirligi" kabi davlat manbasiga hech qanday ishora yo'q — bu
        Mikrokreditbank'ning ipoteka mahsulotidan farqli, davlat mablag'i
        emas). "Foiz stavkalari haqida batafsil" jadvali mijoz toifasi
        (rasmiy/norasmiy daromad) x muddat (84/120 oygacha) bo'yicha
        guruhlangan, xuddi "Volkswagen uchun avtokredit" bilan bir xil
        naqsh — comma-kasr stavkalar (22,9% kabi) va 2 xonali butun son
        boshlang'ich badal ulushlari (20%/25%/40%) bir xil regexlar bilan
        ajratiladi. Muddat esa "N oygacha" shaklida (Volkswagen sahifasidagi
        bare "N oy"dan farqli), shu sabab alohida _MORTGAGE_TERM_RE
        ishlatiladi."""
        block = extract_section(text, "Foiz stavkalari haqida batafsil", "Savollar va javoblar")
        rates = [float(m.replace(",", ".")) for m in _BREND_RATE_RE.findall(block)]
        terms = sorted({int(m) for m in _MORTGAGE_TERM_RE.findall(block)})
        tiers = [int(m) for m in _BREND_TIER_RE.findall(block)]
        down_payment_pct = float(min(tiers)) if tiers else None

        amount_section = extract_section(text, "Summa", "Muddat")
        amount = extract_amount_som(amount_section)

        payment_method_section = extract_section(text, "Kreditni qaytarish usuli", "Garovni")
        payment_method = extract_payment_method(payment_method_section)

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
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=payment_method,
        )

    def _build_mikroqarz_product(self, url, now, text):
        """"Kafillik asosidagi mikroqarz" ("Guarantee-based microloan") —
        sahifa faqat bitta joyda "Onlayn kredit arizasi" degan umumiy
        kalkulyator vidjeti sarlavhasini ishlatadi (ko'p sahifalarda
        takrorlanadigan shablon elementi), lekin mahsulotning o'zi
        (sarlavha/breadcrumb) hech qayerda "onlayn" deb atalmagan — shu
        sabab oflayn "mikroqarz" toifasiga kiradi, "mikroqarz_onlayn"ga
        emas.

        Stavka/muddat jadvali "25,9%\\n12 oygacha\\n100 mln
        so'mgacha\\n...\\n26,9%\\n24 oygacha\\n28,9%\\n36 oygacha" shaklida:
        summa faqat birinchi qatorda ko'rsatiladi (qolgan ikkitasiga ham
        tegishli), shuning uchun eng katta qiymat sifatida bir marta
        olinadi.

        FAQ javobida "mulk garovi talab etilmaydi" deb aniq yozilgan (faqat
        kafillik yoki sug'urta polisi talab qilinadi) — "talab etilmaydi"
        umumiy has_collateral_requirement() inkor ro'yxatida yo'q, va
        sahifaning pastki qismidagi aloqasiz "garov bilan qayta
        moliyalashtirish" cross-sell mahsulotlari umumiy "garov" so'zini
        yolg'on ravishda True qilib ko'rsatadi — shu sabab FORCE_COLLATERAL
        orqali aniq False belgilangan."""
        table_section = extract_section(text, "Foiz stavkasi\nMuddati", "Savollar va javoblar")
        pairs = _MIKROQARZ_RATE_TERM_RE.findall(table_section)
        rates = [float(rate.replace(",", ".")) for rate, _term in pairs]
        terms = [int(term) for _rate, term in pairs]

        amount = extract_amount_som(table_section)

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
            requires_collateral=self.FORCE_COLLATERAL["mikroqarz"],
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )
