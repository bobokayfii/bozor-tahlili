import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_payment_method,
    extract_percentages,
    extract_section,
    fetch_html,
    html_to_text,
)

_MIN_TERM_RE = re.compile(r"Minimal muddat\s*\n\s*(\d+)\s*oy")
_MAX_TERM_RE = re.compile(r"Maksimal muddat\s*\n\s*(\d+)\s*oygacha")
_MORTGAGE_RATE_RE = re.compile(r"yillik\s*(\d{1,2}(?:[.,]\d{1,2})?)%")
_MORTGAGE_DOWN_RE = re.compile(r"(\d{1,2})%\s*boshlang")
_MORTGAGE_TERM_RE = re.compile(r"(\d{1,2})\s*yilgacha")


class TengeBankScraper(TextSectionScraper):
    """Tenge Bank (tengebank.uz) "Yangi avtomobil uchun avtokredit" sahifasi
    "Shartlar" bo'limida toza label:qiymat ro'yxati beradi ("Ustama" ->
    "yillik 27,9%", "Maksimal miqdor" -> "500 000 000 so'mgacha", "Muddat"
    -> "4 yilgacha"). "Ustama" so'zi keyinroq kalkulyator natijasi qismida
    ham takrorlanadi ("Ustama" -> hisoblangan summa), lekin bu birinchi
    (haqiqiy shartlar) uchrashuvidan keyin keladi, shuning uchun
    CATEGORY_HEADINGS'ning "Ustama" dan "Qarz oluvchi"gacha bo'lgan
    oralig'i xavfsiz — bu ikkalasi orasida faqat kerakli uchta qiymat bor,
    "Boshlang'ich to'lov" foizlari (26%/35%) "Qarz oluvchi"dan keyin
    kelgani uchun bo'limga kirmaydi.

    Sahifaning yon menyusida boshqa bir mahsulot nomi sifatida "Garovsiz
    onlayn mikroqarz" iborasi bor — bu butun sahifa matnida "garov"
    tekshiruvi uchun umumiy "garovsiz" signali bilan aralashib, yolg'on-
    manfiy beradi, garchi bu avtokredit bilan hech qanday aloqasi yo'q
    boshqa mahsulot nomi bo'lsa ham. Haqiqiy "Kredit ta'minoti" bo'limida
    sotib olinayotgan avtotransport vositasi garovi aniq talab qilinishi
    yozilgan. FORCE_COLLATERAL bilan tuzatilgan.

    Boshlang'ich to'lov "Qarz oluvchi"dan keyin, "Boshlang'ich to'lov"
    bo'limida real "%" belgisi bilan beriladi ("kamida 26%" / bank bilan
    bog'liq shaxslar uchun "kamida 35%") — pastrog'i (26) olinadi. To'lov
    usuli qismidagi "to'lash" so'zidagi "a" harfi sahifada Kirill "а"
    (U+0430) bilan aralashtirib yozilgan (Xalq Banki'dagi "ООО" xatosiga
    o'xshash, lekin harf darajasida) — shu sabab boshlanish sarlavhasi
    sifatida (apostrofsiz, faqat lotin harflaridan iborat) "usuli" so'zi
    ishlatiladi, "to'lash usuli" emas. Sahifada "imtiyozli davr" haqida
    umuman gap yo'q — shu sabab GRACE_PERIOD_HEADINGS berilmagan, standart
    yo'l bilan (butun matnda "imtiyozli" so'zi yo'qligi tufayli) None
    qaytadi."""

    bank_name = "Tenge Bank"
    url = "https://tengebank.uz/credit"
    CATEGORY_URLS = {
        "avtokredit": "https://tengebank.uz/credit/avtokredit-na-novyj-avtomobil",
        "avtokredit_brend_birlamchi": "https://tengebank.uz/credit/avtokredit-na-importnyj-avtomobil",
        "avtokredit_elektro": "https://tengebank.uz/credit/avtokredit-na-elektromobil",
        "ipoteka_tijorat": "https://tengebank.uz/credit/ipoteka-na-novoe-jilyo",
        "mikroqarz_onlayn": "https://tengebank.uz/credit/mikrozajm-onlajn",
    }
    CATEGORY_HEADINGS = {
        "avtokredit": ("Ustama", "Qarz oluvchi"),
        # "Import avtomobil uchun avtokredit" bir xil "Shartlar" shabloniga
        # ega ("Ustama" -> yillik foiz, "Maksimal miqdor", "Muddat", "Qarz
        # oluvchi"gacha) — bir xil sarlavha jufti ishlatiladi.
        "avtokredit_brend_birlamchi": ("Ustama", "Qarz oluvchi"),
        # "Elektromobil uchun avtokredit" sahifasida sarlavha "Ustama"
        # emas, "Boshlang'ich to'lov va ustama" deb birlashtirilgan
        # (boshqa ikkita avtokredit sahifasidan farqli); yagona "Ustama"
        # so'zi bu sahifada faqat bo'sh kalkulyator natijasida uchraydi.
        "avtokredit_elektro": ("Boshlang'ich to'lov va ustama", "Qarz oluvchi"),
    }
    FORCE_COLLATERAL = {
        "avtokredit": True,
        # Xuddi shu "garovsiz onlayn mikroqarz" yon-menyu iborasi bu sahifada
        # ham bor va butun matnda "garov" tekshiruvini yolg'on-manfiy qiladi
        # (haqiqiy "Kredit ta'minoti" bo'limi esa avtotransport vositasi
        # garovini aniq talab qiladi) — shu sabab aniq True belgilangan.
        "avtokredit_brend_birlamchi": True,
        "avtokredit_elektro": True,
    }
    PRODUCT_NAMES = {
        "avtokredit": "Yangi avtomobil uchun avtokredit",
        "avtokredit_brend_birlamchi": "Import avtomobil uchun avtokredit",
        "avtokredit_elektro": "Elektromobil uchun avtokredit",
        "ipoteka_tijorat": "Ipoteka krediti (yangi uy-joy)",
        "mikroqarz_onlayn": "Onlayn mikroqarz",
    }
    DOWN_PAYMENT_HEADINGS = {
        "avtokredit": ("Boshlang'ich to'lov", "Kеchiktirilgаn"),
        "avtokredit_brend_birlamchi": ("Boshlang'ich to'lov", "Kеchiktirilgаn"),
        # "Boshlang'ich to'lov" so'zi bu sahifada birinchi marta
        # "Boshlang'ich to'lov va ustama" birlashtirilgan sarlavhaning bir
        # qismi sifatida (haqiqiy foiz stavkasi bilan birga) uchraydi — shu
        # sabab boshlanish nuqtasi "Qarz oluvchi" qilib olingan, bu orqali
        # stavka (27,9%) badal ro'yxatiga aralashib ketmaydi.
        "avtokredit_elektro": ("Qarz oluvchi", "Kеchiktirilgаn"),
    }
    PAYMENT_METHOD_HEADINGS = {
        "avtokredit": ("usuli", "Zarur hujjatlar"),
        "avtokredit_brend_birlamchi": ("usuli", "Zarur hujjatlar"),
        "avtokredit_elektro": ("usuli", "Zarur hujjatlar"),
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)

                if category == "mikroqarz_onlayn":
                    product = self._build_mikroqarz_onlayn_product(url, now, text)
                elif category == "ipoteka_tijorat":
                    product = self._build_ipoteka_tijorat_product(url, now, text)
                else:
                    heading_pair = self.CATEGORY_HEADINGS.get(category)
                    section = extract_section(text, *heading_pair) if heading_pair else text
                    product = self._build_product(
                        category,
                        section,
                        url,
                        now,
                        full_text=text,
                        down_payment_pct=self._extract_down_payment_pct(category, text),
                        grace_period_months=self._extract_grace_period_months(category, text),
                        payment_method=self._extract_payment_method(category, text),
                    )
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """"Ipoteka krediti (yangi uy-joy)" — davlat/Moliya vazirligi
        mablag'i haqida ishora yo'q, bankning o'z mahsuloti. "Ustama va
        boshlang'ich to'lov" birlashtirilgan sarlavhasi ostida ikkita
        qator beriladi: "25% boshlang'ich to'lov bilan - yillik 24,9%" /
        "50% boshlang'ich to'lov bilan - yillik 23,9%" — bu yerda
        boshlang'ich badal foizi RATE'dan OLDIN keladi (avtokredit
        sahifalaridagidan farqli tartib), shuning uchun oddiy
        extract_percentages ikkalasini aralashtirib yuboradi — "yillik
        N%" va "N% boshlang'ich" naqshlariga alohida mos regexlar
        ishlatiladi.

        Muddat "15 yilgacha" (180 oy) — umumiy extract_term_months'ning
        120 oylik avtokredit-cheklovi bu yerda chetlab o'tiladi, shu
        sabab cheklovsiz maxsus regex ishlatiladi (xuddi boshqa banklardagi
        ipoteka toifalarida qilingani kabi)."""
        section = extract_section(text, "Ustama", "Qarz oluvchi")
        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_RE.findall(section)]
        down_payment_rates = [float(m) for m in _MORTGAGE_DOWN_RE.findall(section)]
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None
        terms = sorted({int(m) * 12 for m in _MORTGAGE_TERM_RE.findall(section)})

        amount_section = extract_section(text, "Maksimal miqdor", "Muddat")
        amount = extract_amount_som(amount_section)

        payment_method = extract_payment_method(text)

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
            requires_collateral=True,
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=payment_method,
        )

    def _build_mikroqarz_onlayn_product(self, url, now, text):
        """"Onlayn mikroqarz" — "bankga tashrif buyurmasdan 24/7
        rasmiylashtirish" deb aniq yozilgan (ofisga bormasdan, 24/7) —
        mikroqarz_onlayn toifasiga kiradi.

        Muddat "Minimal muddat: 6 oy" / "Maksimal muddat: 36 oygacha"
        shaklida beriladi — standart extract_term_months faqat "oygacha"
        (36) ni topadi, "6 oy" esa "oygacha"siz yozilgani uchun bare-fallback
        ishga tushmaydi ("oygacha" allaqachon topilgani sababli). Shu sabab
        ikkala chegara ham alohida, o'z sarlavhasiga qarab regex bilan
        olinadi.

        Ta'minot faqat "Sug'urta polisi" (mulk garovi emas) — shu sabab
        requires_collateral aniq False."""
        section = extract_section(text, "Ustama", "Qarz oluvchi")
        rates = extract_percentages(section)
        min_term_match = _MIN_TERM_RE.search(section)
        max_term_match = _MAX_TERM_RE.search(section)
        amount = extract_amount_som(section)

        payment_method_section = extract_section(text, "lov usuli", "Kredit ta")
        payment_method = extract_payment_method(payment_method_section)

        if not rates or min_term_match is None or max_term_match is None or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="mikroqarz_onlayn",
            product_name=self.PRODUCT_NAMES["mikroqarz_onlayn"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=int(min_term_match.group(1)),
            term_max_months=int(max_term_match.group(1)),
            amount_max_som=amount,
            requires_collateral=False,
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=payment_method,
        )
