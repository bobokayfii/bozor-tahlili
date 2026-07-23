import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_grace_period_months,
    extract_payment_method,
    extract_section,
    fetch_html,
    has_collateral_requirement,
    html_to_text,
)

_YIL_RATE_RE = re.compile(r"(\d)\s*yil\s*-\s*(\d+)%")
_PROMO_RATE_RE = re.compile(r"yillik\s+(\d+)%\s+stavkada")
_PROMO_TERM_RE = re.compile(r"(\d+)\s*oyga(?!cha)")
_DOWN_PAYMENT_RE = re.compile(r"to['ʻ’]lovi?\s*\n?\s*(\d+)%")
_MORTGAGE_RATE_RE = re.compile(r"yillik foiz stavkasi\s*(\d{1,2}(?:[.,]\d{1,2})?)%")
_MORTGAGE_TERM_RE = re.compile(r"Kredit muddati:\s*(\d{1,2})\s*yil\b")
_MORTGAGE_AMOUNT_RE = re.compile(r"([\d\xa0]+)\s*с[уy]м\s*gacha")
_KREDIT_KARTA_TERM_RE = re.compile(r"Kredit muddati:\s*\n?\s*(\d{1,2})\s*yil")
_KREDIT_KARTA_RATE_RE = re.compile(r"(\d{1,2})%\s*\(")
_KREDIT_KARTA_AMOUNT_RE = re.compile(r"([\d\s]{5,})\s*\([^)]*\)\s*so.mgacha")


class AgroBankScraper(TextSectionScraper):
    """AgroBank (agrobank.uz) — React/JS orqali client-side render qilinadigan
    SPA (boshqa scraperlarda ham uchragan holat — Asakabank'ga qarang):
    oddiy requests-based fetch_html bilan sahifa tanasi bo'sh qaytadi. Bu
    fixture Playwright orqali (headless brauzerda sahifani to'liq render
    qilib, "Avtokredit berish shartlari" yorlig'ini bosib ochib, keyin
    document.documentElement.outerHTML olib) yozib olindi — barcha
    raqamlar HAQIQIY, birlamchi manbadan (ikkilamchi agregatorlardan emas).

    ESKI VERSIYADAGI MUHIM FARQ: avvalgi versiya agrobank.uz'dan hech qanday
    matn ololmagani uchun barcha raqamlarni uchinchi tomon agregatorlardan
    (bank.uz, depozit.uz, bankxizmatlari.uz) olgan va hatto kredit miqdorini
    "TO'LIQ O'YLAB TOPGAN" edi (500 mln so'm, hech qanday manbasiz). Endi
    Playwright orqali birlamchi sahifaning o'zidan haqiqiy ma'lumot olinadi,
    shu sabab bu taxminlar butunlay olib tashlandi.

    Sahifada ikki xil narx rejimi bor: (1) ayrim modellar (Chevrolet Onix,
    Tracker) uchun "yillik 0% stavkada" aksiya, muddat/boshlang'ich badal
    juftliklari bilan (24-60 oy, 25-60% badal); (2) qolgan barcha modellar
    uchun oddiy stavka jadvali: rasmiy daromadli mijozlar uchun 4 yil-24%/
    5 yil-25%, rasmiy daromadsiz mijozlar uchun 4 yil-26%/5 yil-27%,
    boshlang'ich badal 25%. Haqiqiy rate_min/rate_max ikkala rejimni ham
    qamrab oladi (0%-27%), xuddi shunday term_min/term_max ham (24-60 oy) —
    aksiya modellaridagi qisqaroq muddatlar (24 oy) ham hisobga olinadi.

    Muhim: sahifa matni "\\xa0" (uzilmaydigan probel) bilan so'z-so'z
    ("5<nbsp>yil<nbsp>gacha" kabi) ajratilgan — bu umumiy extract_term_months
    naqshining "yilgacha"/"oygacha"ni BITTA so'z sifatida talab qilishini
    buzadi, shu sabab muddat/summa alohida maxsus regexlar bilan olinadi
    (extract_term_months/extract_percentages'ga tayanmasdan). Valyuta so'zi
    ham lotin "so'm" o'rniga Kirill "сум" bilan yozilgan (Xalq Banki'dagi
    "ООО" xatosiga o'xshash, lekin butun so'z darajasida) — kalkulyator
    bo'limida shu sabab alohida almashtiriladi.

    Sahifada garov "garov" so'zi bilan emas, "ta'minot" so'zi bilan
    ta'riflangan ("Kredit ta'minoti: ... Avtokredit hisobiga sotib olingan
    avtomashina") — has_collateral_requirement faqat "garov" so'zini
    tanigani uchun bu yerda haqiqiy ijobiy holatni topa olmaydi (oldingi
    banklardagi "yolg'on-manfiy" holatlaridan farqli, bu "sinonim
    tanilmasligi" holati). FORCE_COLLATERAL bilan to'g'ri qiymat
    belgilangan."""

    bank_name = "AgroBank"
    url = "https://agrobank.uz/uz/person/loans"
    CATEGORY_URLS = {
        "avtokredit": "https://agrobank.uz/uz/person/loans/auto1",
        # "mikroqarz" hali qayta tekshirilmagan (eski, ikkilamchi
        # agregatorlardan olingan ma'lumotlarga asoslangan holicha qoladi):
        "mikroqarz": "https://agrobank.uz/uz/person/loans/microloan",
        "kredit_karta": "https://agrobank.uz/uz/person/loans/credit-karta",
        "ipoteka_tijorat": "https://agrobank.uz/uz/person/loans/mortgage-bank",
        "ipoteka_davlat": "https://agrobank.uz/uz/person/loans/ijtimoiy-komak-ipoteka",
    }
    FORCE_COLLATERAL = {
        "avtokredit": True,
    }
    PRODUCT_NAMES = {
        "avtokredit": "Avtokredit (birlamchi bozor uchun)",
        "ipoteka_tijorat": '"Bizdan uy" ipoteka krediti',
        "ipoteka_davlat": '"Ijtimoiy ko\'mak" ipoteka krediti',
        "kredit_karta": "Kredit karta",
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
                elif category == "kredit_karta":
                    product = self._build_kredit_karta_product(url, now, text)
                else:
                    product = self._build_product(category, text, url, now, full_text=text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, url, now, text):
        yil_rate_pairs = _YIL_RATE_RE.findall(text)
        rates = [float(rate) for _yil, rate in yil_rate_pairs]
        promo_rate_match = _PROMO_RATE_RE.search(text)
        if promo_rate_match:
            rates.append(float(promo_rate_match.group(1)))

        terms = [int(yil) * 12 for yil, _rate in yil_rate_pairs]
        terms.extend(int(m) for m in _PROMO_TERM_RE.findall(text))

        down_payment_matches = _DOWN_PAYMENT_RE.findall(text)
        down_payments = [float(m) for m in down_payment_matches]
        down_payment_pct = min(down_payments) if down_payments else None

        normalized = text.replace("\xa0", " ").replace("сум", "so'm")
        amount_section = extract_section(normalized, "Miqdori", "Kredit muddati")
        amount = extract_amount_som(amount_section)

        payment_method_section = extract_section(text, "lov grafigi", "Birgalikda")
        payment_method = extract_payment_method(payment_method_section)

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
            payment_method=payment_method,
        )

    def _build_kredit_karta_product(self, url, now, text):
        """"Kredit karta" — revolver (aylanma) tarzda ajratiladigan kredit
        karta. "Kredit miqdori" -> "Kredit ta'minoti" bloki ichida
        "oxirgi 6 oy ichida barqaror daromad" degan talab ham bor — bu
        "6 oy" umumiy extract_term_months orqali olinsa, haqiqiy "4 yil
        (48 oy)" muddatidan oldin yolg'on ravishda term_min sifatida
        olinardi. Shu sabab muddat faqat "Kredit muddati:" sarlavhasiga
        bog'langan maxsus regex bilan olinadi.

        Foiz stavkasi ikkita mijoz toifasi uchun beriladi ("27% (Ish haqi
        loyihasidagi ...)" / "30% (Doimiy daromad ...)") — "N% (" naqshiga
        mos regex bilan ajratiladi.

        Kredit miqdori "100 000 000 (yuz million) so'mgacha" — grouped son
        va "so'mgacha" orasida qavscha ichidagi so'z bilan yozilgan raqam
        bor; umumiy extract_amount_som bu holatni qamrab olmagani uchun
        maxsus regex ishlatiladi.

        "Kredit ta'minoti: ... Likvidlik garovi" — "garov" so'zi mavjud,
        shuning uchun has_collateral_requirement to'g'ri True qaytaradi."""
        block = extract_section(text, "Kredit miqdori:", "Kredit ta")

        amount_section = extract_section(block, "", "Kredit muddati")
        amount_match = _KREDIT_KARTA_AMOUNT_RE.search(amount_section)
        amount = int(amount_match.group(1).replace(" ", "")) if amount_match else None

        term_match = _KREDIT_KARTA_TERM_RE.search(block)
        term = int(term_match.group(1)) * 12 if term_match else None

        rate_section = extract_section(block, "Kredit foiz stavkasi", None)
        rates = [float(m) for m in _KREDIT_KARTA_RATE_RE.findall(rate_section)]

        if not rates or term is None or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="kredit_karta",
            product_name=self.PRODUCT_NAMES["kredit_karta"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=term,
            term_max_months=term,
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )

    def _build_ipoteka_davlat_product(self, url, now, text):
        """""Ijtimoiy ko'mak" ipoteka krediti — mahsulot nomining o'zi
        (ijtimoiy yordam) davlat dasturi ekanini bildiradi; "Subsidiya"
        bo'limida aniq yozilgan: kredit miqdorining 15 foizi subsidiya
        sifatida ajratiladi, shuningdek dastlabki 5 yil davomida foiz
        stavkasining 12%dan oshgan qismi davlat tomonidan qoplab beriladi
        — bu "Bizdan uy" (ipoteka_tijorat, bankning o'z mablag'i) dan
        farqli, davlat subsidiyasi bilan ta'minlangan mahsulot. Boshqa
        banklardagi tayyor kvartira xarididan farqli, bu mahsulot yakka
        tartibdagi uy-joy QURISH/rekonstruksiya/ta'mirlash uchun.

        Boshqa AgroBank sahifalaridan farqli, bu sahifada "\\xa0" bilan
        so'z-so'z ajratish yo'q — oddiy bo'sh joy bilan yozilgan, shuning
        uchun umumiy extract_percentages/extract_amount_som funksiyalari
        bu yerda to'g'ri ishlaydi (avtokredit sahifasidagi maxsus \\xa0
        almashtirish kerak emas).

        Sahifa "Kredit ta'minoti" o'rniga "Garov ta'minoti" so'zini
        ishlatadi (avtokredit/ipoteka_tijoratdagi "ta'minot"dan farqli,
        bu yerda "garov" so'zi bor) — shuning uchun has_collateral_
        requirement to'g'ri ravishda True qaytaradi, FORCE_COLLATERAL
        kerak emas."""
        block = extract_section(text, "Kredit maqsadi", "Subsidiya")

        amount_section = extract_section(block, "Kredit miqdori", "Kredit foizi")
        amount = extract_amount_som(amount_section)

        rate_section = extract_section(block, "Kredit foizi", "Kredit muddati")
        rate_match = re.search(r"(\d{1,2}(?:[.,]\d{1,2})?)%", rate_section)
        rates = [float(rate_match.group(1).replace(",", "."))] if rate_match else []

        term_section = extract_section(block, "Kredit muddati", "Kredit to")
        term_match = re.search(r"(\d{1,2})\s*yil", term_section)
        term = int(term_match.group(1)) * 12 if term_match else None

        payment_method_section = extract_section(block, "Kredit to", "Boshlang")
        payment_method = extract_payment_method(payment_method_section)

        down_section = extract_section(block, "Boshlang", None)
        down_match = re.search(r"(\d{1,2})%", down_section)
        down_payment_pct = float(down_match.group(1)) if down_match else None

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
            grace_period_months=None,
            payment_method=payment_method,
        )

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """""Bizdan uy" ipoteka krediti — "O'z mablag'lari hisobidan
        ipoteka krediti" (bank's own funds, not a state/Ministry of
        Finance program); birlamchi va ikkilamchi bozordan uy-joy uchun.
        Rate/down-payment tiers are given inline ("boshlang'ich badal 40%
        - yillik foiz stavkasi 23,99%") — a dedicated "yillik foiz
        stavkasi N%" regex isolates the real rate from the down-payment
        percentage on the same line.

        No absolute "Kredit summasi" is stated in the static list (only
        "sotib olinayotgan uy summasi miqdorida" — tied to the house
        price); the interactive calculator's own slider ceiling ("900 000
        000 сум gacha") is used instead, same convention as other banks'
        BHM/relative-ceiling pages. That figure uses Cyrillic "сум" (not
        "so'm") and \xa0 digit grouping — dedicated regex, since
        extract_amount_som only recognizes the Latin spelling."""
        rate_section = extract_section(text, "Foiz stavkasi:", "Kredit muddati")
        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_RE.findall(rate_section)]

        term_match = _MORTGAGE_TERM_RE.search(text)
        term = int(term_match.group(1)) * 12 if term_match else None

        amount_match = _MORTGAGE_AMOUNT_RE.search(text)
        amount = int(amount_match.group(1).replace("\xa0", "")) if amount_match else None

        down_payments = [int(m) for m in re.findall(r"boshlang.ich badal\s*(\d{1,2})%", rate_section)]
        down_payment_pct = float(min(down_payments)) if down_payments else None

        grace_section = extract_section(text, "Imtiyozli davr:", "Kredit summasi")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        payment_method = extract_payment_method(text)

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
