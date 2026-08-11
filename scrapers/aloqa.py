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

_YILLIK_RATE_RE = re.compile(r"Yillik\s*(\d{1,2}(?:,\d{1,2})?)%")
_TIER_RE = re.compile(r"Kamida\s*(\d{1,2})%")
_TERM_RE = re.compile(r"(\d{1,3})\s*oy")
_MORTGAGE_DOWN_RE = re.compile(r"(\d{1,2})\s*\([^)]*\)\s*foiz")
_MORTGAGE_TERM_RE = re.compile(r"(\d{1,2})\s*yilgacha")
_DAVLAT_DOWN_RE = re.compile(r"(\d{1,2})\s*foiz")
_DAVLAT_AMOUNT_RE = re.compile(r"(\d{1,3}(?:,\d{1,2})?)\s*mln\.?\s*so")
_DAVLAT_TERM_RE = re.compile(r"(\d{1,2})\s*yild")
_DAVLAT_GRACE_RE = re.compile(r"(\d{1,2})\s*oygacha imtiyozli")
_ELEKTRO_RATE_RE = re.compile(r"(\d{1,2},\d)%")
_ELEKTRO_DOWN_RE = re.compile(r"(\d{1,2})%\**\s*dan boshlab")
_ELEKTRO_TERM_RE = re.compile(r"(\d{1,2})\s*\n\s*yoki\n\s*(\d{1,2})\s*\n\s*oy")
_ELEKTRO_AMOUNT_RE = re.compile(r"(\d+(?:,\d+)?)\s*milliard\s*so.mgacha")
_IKKILAMCHI_SLIDER_PCT_RE = re.compile(r"(\d{1,2}(?:\.\d{1,2})?)\s*%dan\s*\n+\s*(\d{1,2}(?:\.\d{1,2})?)\s*%gacha")
_IKKILAMCHI_SLIDER_TERM_RE = re.compile(r"(\d{1,3})\s*oydan boshlab\s*\n+\s*(\d{1,3})\s*oygacha")
_IKKILAMCHI_SLIDER_AMOUNT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*million\s*so.mgacha")


class AloqabankScraper(TextSectionScraper):
    """Aloqabank (aloqabank.uz) avtokredit sahifasi ("Avtokredit - birlamchi
    bozor uchun") boshqa banklardagi kabi "Kredit shartlari" nomli bo'lim
    ostida stavka/muddat/summa jadvalini beradi, lekin bu sarlavha matni
    sahifada IKKI marta uchraydi: birinchi marta yon menyu havolasida
    (<a>...Kredit shartlari</a>), ikkinchi marta esa haqiqiy bo'lim
    sarlavhasida (<h2>). extract_section birinchi uchrashuvni oladi, shu
    sabab CATEGORY_HEADINGS boshlanish nuqtasi sifatida "Kredit shartlari"
    o'rniga "Yillik foiz stavkasi" ishlatiladi — bu ham sahifada ikki marta
    uchraydi (avval kalkulyator natijasi qatorida, keyin haqiqiy shartlar
    jadvalida), lekin ikkalasi orasida boshqa foiz/raqam yo'q, shuning uchun
    birinchi uchrashuvdan boshlab olingan bo'lim baribir to'g'ri, yagona
    stavka qiymatigacha (jadvaldagi haqiqiy "23% dan") yetib boradi.

    Sahifada "Kreditning maksimal summasi" uchun aniq son ko'rsatilmagan —
    "cheklanmagan" (garov mulki qiymatining 75-90 foizigacha) deb yozilgan.
    amount_max_som shu sababli topilmaydi va _build_product bu kategoriyani
    o'tkazib yuboradi — bu XATO EMAS, InfinBank avtokredit sahifasidagi xuddi
    shu holatga o'xshash (scrapers/infinbank.py'ga qarang): sahifada
    haqiqatan ham son ko'rinishidagi chegara yo'q."""

    bank_name = "Aloqabank"
    url = "https://aloqabank.uz/uz/private/crediting/"
    CATEGORY_URLS = {
        "avtokredit": "https://aloqabank.uz/uz/private/crediting/avtokredit-birlamchi-bozor-uchun/",
        "avtokredit_ikkilamchi": "https://aloqabank.uz/uz/private/crediting/avtokredit-ikkilamchi-bozor-uchun4940/",
        "avtokredit_brend_birlamchi": "https://aloqabank.uz/uz/private/crediting/avtokredit-import-/",
        "ipoteka_tijorat": "https://aloqabank.uz/uz/private/crediting/ipoteka-secondary/",
        "ipoteka_davlat": "https://aloqabank.uz/uz/private/crediting/primary-mortgage/",
        "avtokredit_elektro": "https://aloqabank.uz/uz/private/crediting/avtokredit-byd-avto-/",
    }
    CATEGORY_HEADINGS = {
        "avtokredit": ("Yillik foiz stavkasi", "Kredit maqsadi"),
    }
    PRODUCT_NAMES = {
        "avtokredit": "Avtokredit - birlamchi bozor uchun",
        "avtokredit_ikkilamchi": 'Avtokredit - "ikkilamchi bozor uchun"',
        "avtokredit_brend_birlamchi": "Avtokredit import",
        "ipoteka_tijorat": "Ipoteka (ikkilamchi bozor)",
        "ipoteka_davlat": "Ipoteka krediti - Iqtisodiyot va moliya vazirligi mablag'lari hisobidan",
        "avtokredit_elektro": "Avtokredit BYD Avto",
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)

                if category == "avtokredit_brend_birlamchi":
                    product = self._build_avtokredit_brend_birlamchi_product(url, now, text)
                elif category == "avtokredit_ikkilamchi":
                    product = self._build_avtokredit_ikkilamchi_product(url, now, text)
                elif category == "ipoteka_tijorat":
                    product = self._build_ipoteka_tijorat_product(url, now, text)
                elif category == "ipoteka_davlat":
                    product = self._build_ipoteka_davlat_product(url, now, text)
                elif category == "avtokredit_elektro":
                    product = self._build_avtokredit_elektro_product(url, now, text)
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

    def _build_avtokredit_brend_birlamchi_product(self, url, now, text):
        """"Avtokredit import" — "Birlamchi bozordan chet elda ishlab
        chiqarilgan yengil avtotransport vositalarini sotib olish uchun"
        (any foreign-made vehicle, not one specific brand — unlike
        Aloqabank's other dedicated dealer pages such as "avtokredit-byd-
        avto-" or "avtokredit-haval"). Rate table is grouped by down-
        payment tier for two customer classes (official-income /
        self-employed): "Kamida 30%" -> "Yillik 23,5%", "Kamida 40%" ->
        "Yillik 23%" (income) and "Kamida 30%" -> "Yillik 24%", "Kamida
        40%" -> "Yillik 23,5%" (self-employed). "Kamida" tier labels and
        "Yillik" rate labels are extracted with separate anchored regexes
        so the down-payment percentages never leak into rate_min/rate_max."""
        block = extract_section(text, "boshlang‘ich badal miqdori va foizi", "Kredit miqdori")
        rates = [float(m.replace(",", ".")) for m in _YILLIK_RATE_RE.findall(block)]
        tiers = [int(m) for m in _TIER_RE.findall(block)]
        terms = [int(m) for m in _TERM_RE.findall(block)]
        down_payment_pct = float(min(tiers)) if tiers else None

        amount_section = extract_section(text, "Kredit miqdori", "Ajratish shakli")
        amount = extract_amount_som(amount_section)

        grace_period_months = extract_grace_period_months("imtiyozli " + block)

        payment_method_section = extract_section(text, "Qaytarish usuli", "Kredit ta")
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
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_avtokredit_ikkilamchi_product(self, url, now, text):
        """"Avtokredit - "ikkilamchi bozor uchun"" — "Kredit maqsadi" bandida
        aniq yozilgan: "Ishlab chiqarilganiga 5 yildan oshmagan, ya'ni
        2022-yil va undan keyingi yillarda 'UzAuto Motors' AJ tomonidan
        ishlab chiqarilgan yengil avtotransport vositasini ikkilamchi
        bozordan sotib olish uchun" — ya'ni FAQAT UzAuto Motors (mahalliy)
        brendiga cheklangan, boshqa Aloqabank ikkilamchi-emas sahifalaridan
        farqli (masalan "avtokredit-import-", "avtokredit-byd-avto-") bu
        brend-cheklovsiz EMAS — shu sabab "avtokredit_ikkilamchi" (umumiy,
        mahalliy brend) toifasiga tegishli, "avtokredit_brend_ikkilamchi"ga
        (GM/BYD/KIA/... import brendlar) EMAS.

        Sahifada "Kredit shartlari" nomli aniq bo'lim ("Yillik foiz
        stavkasi" -> "23% dan") faqat pastki chegarani beradi. Undan oldin
        esa alohida interaktiv slayder-vidjet bor — bu yerda "Foiz
        stavkasi" ("23 %dan" -> "25,5 %gacha"), "Boshlang'ich badal
        miqdori" ("15 %dan" -> "85 %gacha"), "Kredit summasi" ("500 ming
        so'mdan" -> "300 million so'mgacha") va "Kredit muddati" ("3
        oydan boshlab" -> "60 oygacha") — TO'LIQ diapazon sifatida
        beriladi (bitta standart qiymat emas, chinakam min-max chegara),
        va bu qiymatlar pptx-da mustaqil tasdiqlangan raqamlar bilan aynan
        mos keladi. Shu sabab aynan shu slayder-vidjet — pastroqdagi
        "Kredit shartlari"ning yagona "23% dan" qiymatidan farqli — asosiy
        manba sifatida ishlatiladi. "%dan...%gacha" naqshi sahifada FAQAT
        ikki marta uchraydi (stavka, keyin boshlang'ich badal) — shu sabab
        findall natijasidagi birinchi juftlik stavka, ikkinchisi badal."""
        pct_pairs = _IKKILAMCHI_SLIDER_PCT_RE.findall(text)
        if len(pct_pairs) < 2:
            return None
        rate_min, rate_max = (float(v) for v in pct_pairs[0])
        down_payment_pct = float(pct_pairs[1][0])

        term_match = _IKKILAMCHI_SLIDER_TERM_RE.search(text)
        if not term_match:
            return None
        term_min, term_max = int(term_match.group(1)), int(term_match.group(2))

        amount_match = _IKKILAMCHI_SLIDER_AMOUNT_RE.search(text)
        amount = round(float(amount_match.group(1).replace(",", ".")) * 1_000_000) if amount_match else None
        if amount is None:
            return None

        payment_method_section = extract_section(text, "Toʻlov usuli", "Rasmiylashtirish usuli")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(text, "Rasmiylashtirish usuli", "Axborot varaqasi")
        grace_period_months = extract_grace_period_months("imtiyozli" + grace_section)

        return Product(
            bank=self.bank_name,
            category="avtokredit_ikkilamchi",
            product_name=self.PRODUCT_NAMES["avtokredit_ikkilamchi"],
            rate_min=rate_min,
            rate_max=rate_max,
            term_min_months=term_min,
            term_max_months=term_max,
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_ipoteka_davlat_product(self, url, now, text):
        """"Ipoteka krediti - Iqtisodiyot va moliya vazirligi mablag'lari
        hisobidan" — yon menyudagi nomida aniq yozilgan, alohida sahifa
        ("primary-mortgage") "Ipoteka (ikkilamchi bozor)" (bankning o'z
        mablag'i, ipoteka_tijorat) dan farqli. Faqat birlamchi bozordagi
        ko'p kvartirali uy-joy xaridi uchun.

        Boshlang'ich badal "%" belgisisiz so'z shaklida ("15 foizidan kam
        bo'lmagan") — ipoteka_tijoratdagi "N (so'z) foiz" naqshidan farqli
        (bu yerda qavscha yo'q), shuning uchun oddiyroq "\\d foiz" regexi
        ishlatiladi.

        Kredit miqdori "380,0 mln. so'mdan" / "480,0 mln. so'mgacha" —
        vergul-o'nlik ("380,0") va nuqta bilan qisqartirilgan "mln."
        birligi umumiy extract_amount_som'ning regexiga mos kelmaydi
        (u faqat butun son + "mln" (nuqtasiz yoki "so'm" so'zidan oldin
        boshqa nuqta bo'lmasligi) kutadi) — shu sabab maxsus regex bilan
        ikkala qiymat ham olinib, eng kattasi (Toshkent, 480 mln)
        ishlatiladi.

        Sahifadagi rasmiy "Qaytarish usuli: Annuutet yoki Differensial"
        qatorida "Annuitet" so'zi TIPO bilan ("Annuutet", "i" harfisiz)
        yozilgan — lekin pastroqdagi kalkulyator vidjetida to'g'ri
        yozilgan "Annuitet" so'zi ham bor, shuning uchun butun sahifa
        matni bo'yicha tekshirilsa (tor bo'lim o'rniga) to'g'ri natija
        ("Annuitet, Differensial") olinadi."""
        block = extract_section(text, "Kredit maqsadi", "Ajratiish shakli")

        rate_section = extract_section(block, "Kredit foizi", "Boshlang")
        rates = extract_percentages(rate_section)

        term_section = extract_section(block, "Kredit muddati", "Kredit foizi")
        term_match = _DAVLAT_TERM_RE.search(term_section)
        term = int(term_match.group(1)) * 12 if term_match else None
        grace_match = _DAVLAT_GRACE_RE.search(term_section)
        grace_period_months = int(grace_match.group(1)) if grace_match else None

        down_section = extract_section(block, "Boshlang", "Kredit miqdori")
        down_payment_rates = [float(m) for m in _DAVLAT_DOWN_RE.findall(down_section)]
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        amount_section = extract_section(block, "Kredit miqdori", "Ajratiish")
        amounts = [round(float(m.replace(",", ".")) * 1_000_000) for m in _DAVLAT_AMOUNT_RE.findall(amount_section)]
        amount = max(amounts) if amounts else None

        payment_method = extract_payment_method(text)

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
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_avtokredit_elektro_product(self, url, now, text):
        """"Avtokredit BYD Avto" — "Kredit maqsadi" bo'limida aniq
        yozilgan: "Song Plus Champion Hybrid, Song Plus Champion EV, Song
        Pro, Chazor markadagi avtomobillar uchun amal qiladi" — bu
        modellar elektromobil/gibrid, shuning uchun avtokredit_elektro
        toifasiga to'g'ri keladi (boshqa Aloqabank avtokredit sahifalari
        istalgan brend/model uchun, faqat shu sahifa BYD elektro/gibrid
        modellariga xos).

        Stavka jadvalida ("21,9%"/"20,9%"/"19,9%"/"18,9%") barcha qiymatlar
        vergul-kasr bilan yozilgan, boshlang'ich badal ulushlari esa
        ("20%"/"30%"/"40%"/"50%") butun son — shu farq orqali ikkalasi
        ajratiladi (vergul-kasrli regex faqat stavkalarni oladi).

        Muddat "36 yoki 60 oy" — ikkita aniq qiymat (oraliq emas),
        term_min=36, term_max=60.

        "Kreditning eng ko'p miqdori" bo'limida faqat garov qiymatiga
        nisbat (75-90%) ko'rsatilgan, aniq so'm yo'q — shu sabab sahifa
        pastidagi interaktiv kalkulyatorning o'z chegarasi ("1 milliard
        so'mgacha") ishlatiladi (Turonbank/boshqa banklardagi BHM/nisbat-
        asosli chegara konvensiyasi bilan bir xil).

        Boshlang'ich badalning "**" izohida shart bajarilmasa 25% dan kam
        bo'lmasligi kerakligi aytiladi, lekin shu izohning o'zida hozirgi
        Nizom bo'yicha garov nisbati 90%gacha ruxsat etilishi ham
        ta'kidlangan (ya'ni 75% shart amalda kamdan-kam ishlaydi) — shu
        sabab jadvalda aniq ko'rsatilgan boshlang'ich (20%) qiymat
        ishlatiladi, shartli 25% emas."""
        block = extract_section(text, "Kredit maqsadi", "Ajratish shakli")
        rates = [float(m.replace(",", ".")) for m in _ELEKTRO_RATE_RE.findall(block)]
        down_payment_rates = [float(m) for m in _ELEKTRO_DOWN_RE.findall(block)]
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        term_match = _ELEKTRO_TERM_RE.search(block)
        terms = [int(term_match.group(1)), int(term_match.group(2))] if term_match else []

        amount_match = _ELEKTRO_AMOUNT_RE.search(text)
        amount = round(float(amount_match.group(1).replace(",", ".")) * 1_000_000_000) if amount_match else None

        grace_period_months = extract_grace_period_months("imtiyozli " + block)

        payment_method_section = extract_section(text, "Qaytarish usuli", "Kredit ta")
        payment_method = extract_payment_method(payment_method_section)

        if not rates or not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="avtokredit_elektro",
            product_name=self.PRODUCT_NAMES["avtokredit_elektro"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """"Ipoteka (ikkilamchi bozor)" — davlat/Moliya vazirligi mablag'i
        haqida ishora yo'q, bankning o'z mahsuloti; "Birlamchi va
        ikkilamchi uy-joy bozorida ... kvartiralarni yoki yakka tartibdagi
        uy-joylarni sotib olish uchun" (aslida ikkalasini ham qamrab
        oladi, faqat URL nomi "secondary" bo'lsa ham). "Kredit shartlari"
        ro'yxatida barcha maydonlar toza yagona qiymatlar: 24% stavka,
        800 mln so'm, 20 yilgacha muddat.

        Boshlang'ich badal "%" belgisisiz, so'z shaklida berilgan
        ("uy-joy qiymatining 20 (yigirma) foizidan kam bo'lmagan") — shu
        sabab maxsus regex (\\d (so'z) foiz) ishlatiladi, oddiy
        extract_percentages "%" belgisi yo'qligi sababli hech narsa
        topmaydi. Muddat "20 yilgacha" (240 oy) — umumiy
        extract_term_months'ning 120 oylik cheklovi bu yerda chetlab
        o'tiladi."""
        rate_section = extract_section(text, "Yillik foiz stavkasi", "Kreditning maksimal summasi")
        rates = extract_percentages(rate_section)

        term_match = _MORTGAGE_TERM_RE.search(text)
        term = int(term_match.group(1)) * 12 if term_match else None

        amount_section = extract_section(text, "Kreditning maksimal summasi", "Kredit muddati")
        amount = extract_amount_som(amount_section)

        down_match = _MORTGAGE_DOWN_RE.search(text)
        down_payment_pct = float(down_match.group(1)) if down_match else None

        grace_section = extract_section(text, "Imtiyozli davr", "Axborot varaqasi")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        payment_method_section = extract_section(text, "Toʻlov usuli", "Rasmiylashtirish usuli")
        payment_method = extract_payment_method(payment_method_section)

        if not rates or term is None or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="ipoteka_tijorat",
            product_name=self.PRODUCT_NAMES["ipoteka_tijorat"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=term,
            term_max_months=term,
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )
