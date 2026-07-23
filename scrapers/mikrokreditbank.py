import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_grace_period_months,
    extract_payment_method,
    extract_percentages,
    extract_section,
    extract_term_months,
    fetch_html,
    has_collateral_requirement,
    html_to_text,
)


class MikrokreditBankScraper(TextSectionScraper):
    """Mikrokreditbank (mkbank.uz) retail kredit kategoriyalari SQB kabi
    alohida sahifalarda joylashgan. mikroqarz/kredit_karta/istemol_krediti
    eski, tekshirilgan "Kredit muddati" -> "Qarz oluvchi" shabloni bilan
    qoladi.

    avtokredit uchun URL foydalanuvchi so'ragan aniq mahsulot sahifasiga
    ("avtokredit-uzauto-motors1933/") almashtirildi (avvalgi umumiy
    "car-loan/" o'rniga). Bu "UzAuto Motors" 0% aksiyasi sahifasi: pastroqda
    boshlang'ich badal ulushi (25%/30%/40%/50%/60%) bo'yicha guruhlangan
    matritsa bor, lekin barcha katakchalarda "Kredit foizi" "0,0%" — shuning
    uchun eski umumiy CATEGORY_HEADINGS shablonidan farqli, alohida run()
    orqali: stavka toza xulosa kartochkasidan ("0%"), boshlang'ich badal esa
    matritsaning eng past ulushidan (25%) olinadi — ikkalasi bir xil
    section'da bo'lmagani uchun aralashib ketmaydi."""

    bank_name = "Mikrokreditbank"
    url = "https://mkbank.uz/uz/private/crediting/"
    CATEGORY_URLS = {
        "avtokredit": "https://mkbank.uz/uz/private/crediting/avtokredit-uzauto-motors1933/",
        "avtokredit_ikkilamchi": "https://mkbank.uz/uz/private/crediting/car-loan-second/",
        "avtokredit_brend_birlamchi": "https://mkbank.uz/uz/private/crediting/avtokrediti-adm-global-/",
        "mikroqarz": "https://mkbank.uz/uz/private/crediting/microloan/",
        "ipoteka_davlat": "https://mkbank.uz/uz/private/crediting/imkoniyat-ipotekasi-krediti/",
        # Taxminiy (best-guess) — sinf docstringiga qarang.
        "kredit_karta": "https://mkbank.uz/uz/private/crediting/qulay-overdraft/",
        "istemol_krediti": "https://mkbank.uz/uz/private/crediting/consumer-loan/",
    }
    CATEGORY_HEADINGS = {
        "kredit_karta": ("Kredit muddati", "Qarz oluvchi"),
        "istemol_krediti": ("Kredit muddati", "Qarz oluvchi"),
    }
    FORCE_COLLATERAL = {
        "avtokredit_ikkilamchi": True,
        "avtokredit_brend_birlamchi": True,
    }
    PRODUCT_NAMES = {
        "avtokredit": "Avtokredit UzAuto Motors",
        "avtokredit_ikkilamchi": "Foydalanilgan avtomobillar uchun avtokredit",
        "avtokredit_brend_birlamchi": "Avtokredit ADM GLOBAL",
        "mikroqarz": "Mikroqarz",
        "ipoteka_davlat": "Imkoniyat ipotekasi krediti",
    }

    _ADM_RATE_RE = re.compile(r"(\d{1,2},\d{1,2})%")
    _ADM_TERM_RE = re.compile(r"(\d{1,3})\s*oy(?!dan|gacha)")
    _ADM_TIER_RE = re.compile(r"(?<!\d)(\d{2})%(?!\d)")
    _MORTGAGE_TERM_RE = re.compile(r"(\d{1,2})\s*yilgacha")

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
                elif category == "mikroqarz":
                    product = self._build_mikroqarz_product(url, now, text)
                elif category == "ipoteka_davlat":
                    product = self._build_ipoteka_davlat_product(url, now, text)
                else:
                    heading_pair = self.CATEGORY_HEADINGS[category]
                    section = extract_section(text, *heading_pair)
                    product = self._build_product(category, section, url, now, full_text=text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_ipoteka_davlat_product(self, url, now, text):
        """"Imkoniyat ipotekasi krediti" — "Mahalla yettiligi" tavsiyasi
        asosida Kambag'allikdan chiqarish dasturiga kiritilgan fuqarolar
        uchun; alohida joyda (hujjatlar bo'limida) "Moliya vazirligi
        mablag'lari hisobidan ajratiladigan ipoteka krediti" deb aniq
        yozilgan — davlat (byudjet) mablag'i, bankning o'z tijorat
        mahsuloti emas.

        Muddat "20 yilgacha" (240 oy) — umumiy extract_term_months'ning
        120 oylik cheklovi bu yerda chetlab o'tiladi. Stavka bitta yagona
        qiymat ("Stavka foizi: 18%"), matritsa yo'q. Boshlang'ich badal
        "%" belgisi bilan ("15 % dan kam bo'lmagan"), lekin ushbu ibora
        pastroqda takrorlanadigan "Foiz stavkasi" (Markaziy bank stavkasi
        haqida umumiy izoh) sarlavhasi bilan tor chegaralanadi, aks holda
        sahifa oxiridagi aloqasiz boshqa mahsulotlar % qiymatlari bilan
        aralashib ketardi."""
        block = extract_section(text, "Kredit muddati", "Kredit ta")

        term_match = self._MORTGAGE_TERM_RE.search(block)
        term = int(term_match.group(1)) * 12 if term_match else None

        rate_section = extract_section(block, "Stavka foizi", "Kredit miqdori")
        rates = extract_percentages(rate_section)

        amount_section = extract_section(block, "Kredit miqdori", "To'lov usuli")
        amount = extract_amount_som(amount_section)

        payment_method_section = extract_section(block, "To'lov usuli", "Kreditni rasmiylashtirish")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(block, "Imtiyozli davr", None)
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        down_payment_section = extract_section(
            text, "Boshlang‘ich badalning eng kam miqdori", "Foiz stavkasi"
        )
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

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

    def _build_mikroqarz_product(self, url, now, text):
        """"Mikroqarz" — "Kreditni rasmiylashtirish usuli: Bank ofisi"
        (branch visit, not app-based) — oflayn "mikroqarz" toifasi.
        Stavka/muddat jadvali toza "N oygacha" / "X%" ro'yxatlari sifatida
        beriladi ("Mikrokreditbank ATB tizimida" bilan tugaydigan bo'limda),
        shuning uchun umumiy extract_percentages/extract_term_months
        yetarli — kontaminatsiya xavfi yo'q.

        Miqdor bo'limi ("Kredit ajratishning eng yuqori miqdori") end_heading
        sifatida None qabul qilinsa sahifaning oxirigacha davom etadi va
        uzoqdagi aloqasiz "824 mln" (avtokredit mahsulotining chegarasi)
        eng katta qiymat sifatida noto'g'ri tanlanadi — shuning uchun tor
        "Muammoli kreditlar" bilan chegaralangan."""
        rate_term_section = extract_section(text, "Kredit muddati: ", "Mikrokreditbank ATB tizimida")
        rates = extract_percentages(rate_term_section)
        terms = extract_term_months(rate_term_section)

        amount_section = extract_section(text, "Kredit ajratishning eng yuqori miqdori", "Muammoli kreditlar")
        amount = extract_amount_som(amount_section)

        payment_method_section = extract_section(text, "lov usuli", "Kreditni rasmiylashtirish")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(text, "Imtiyozli davr", "Kredit ta")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

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
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_avtokredit_ikkilamchi_product(self, url, now, text):
        """"Foydalanilgan avtomobillar uchun avtokredit" — sahifa
        <title>'ida "yo'l bosilgan avtomobillar uchun kredit" deyilgan,
        ya'ni ishlatilgan (ikkilamchi bozor) avtomobillar uchun.

        "60 oygacha" muddat qisqacha xulosa kartochkasida BIR marta va
        "Qo'shimcha shartlar" jadvalida yana bir marta (headers keyin
        values tartibida: Muddati/Boshlang'ich badal/Yillik foiz stavkasi
        -> 60 oygacha/40%/24%) uchraydi — shu sabab faqat "shimcha
        shartlar" (Qo'shimcha shartlar, apostrofsiz ASCII-xavfsiz anker)
        dan "Bankda hisobvarag'i" gacha bo'lgan tor blokdan olinadi, aks
        holda muddat/foiz noto'g'ri (bo'sh yoki boshqa) qiymatga
        tushib qolardi."""
        block = extract_section(text, "shimcha shartlar", "Bankda hisobvarag")
        terms = extract_term_months(block)
        percentages = extract_percentages(block)
        down_payment_pct = percentages[0] if percentages else None
        rates = percentages[1:] if len(percentages) > 1 else []

        amount_section = extract_section(text, "Kredit miqdori", "Kredit maqsadi")
        amount = extract_amount_som(amount_section)

        payment_method_section = extract_section(text, "lov usuli", "Kreditni rasmiylashtirish")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(text, "Imtiyozli davr", "Kredit ta")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

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
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_avtokredit_brend_birlamchi_product(self, url, now, text):
        """"Avtokredit ADM GLOBAL" — KIA, Chery, Haval va Changan
        avtomobillari uchun (birlamchi bozor). Sahifada 3 ta mustaqil narx
        jadvali bor (asosiy "KREDIT", "ROODELL I", "ROODELL II"), har biri
        boshlang'ich badal ulushi (25%-60%) x muddat (12-60 oy) bo'yicha
        guruhlangan. Ulush yorliqlari ("25%" kabi) har doim butun son,
        haqiqiy stavkalar esa har doim vergul-kasr ("0,0%", "4,5%" kabi)
        shaklida yozilgan — shu farq orqali ikkisi aralashmasdan alohida
        regexlar bilan ajratiladi. Barcha 3 jadval bo'yicha eng past/eng
        yuqori stavka, 12-60 oy oralig'i va eng past boshlang'ich badal
        ulushi olinadi."""
        block = extract_section(text, "KREDIT", "Kredit oluvchi bankka")
        rates = [float(m.replace(",", ".")) for m in self._ADM_RATE_RE.findall(block)]
        terms = [int(m) for m in self._ADM_TERM_RE.findall(block)]
        tiers = [int(m) for m in self._ADM_TIER_RE.findall(block)]
        down_payment_pct = float(min(tiers)) if tiers else None

        amount_section = extract_section(text, "xarid qilish uchun", "yillik stavka")
        amount = extract_amount_som(amount_section)

        payment_method_section = extract_section(text, "lov usuli", "Kreditni rasmiylashtirish")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(text, "Imtiyozli davr", "Kredit ta")
        grace_period_months = extract_grace_period_months("imtiyozli " + grace_section)

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
            requires_collateral=self.FORCE_COLLATERAL["avtokredit_brend_birlamchi"],
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_avtokredit_product(self, url, now, text):
        rate_section = extract_section(text, "kredit miqdori", "kredit muddati")
        rates = extract_percentages(rate_section)

        term_section = extract_section(text, "yillik stavka", "Kredit haqida")
        terms = extract_term_months(term_section)

        amount_section = extract_section(text, "xarid qilish uchun", "kredit miqdori")
        amount = extract_amount_som(amount_section)

        down_payment_section = extract_section(text, "Boshlang", "Kredit foizi")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        payment_method_section = extract_section(text, "To'lov usuli", "Kreditni rasmiylashtirish")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(text, "Imtiyozli davr", "Kredit ta")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

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
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )
