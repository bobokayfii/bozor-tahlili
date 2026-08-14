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
        "avtokredit_brend_ikkilamchi": "https://mkbank.uz/uz/private/crediting/car-loan-second/",
        "avtokredit_elektro": "https://mkbank.uz/uz/private/crediting/avtokredit-leapmotor/",
        "mikroqarz": "https://mkbank.uz/uz/private/crediting/microloan/",
        "mikroqarz_onlayn": "https://mkbank.uz/uz/private/crediting/microloan/",
        "ipoteka_davlat": "https://mkbank.uz/uz/private/crediting/imkoniyat-ipotekasi-krediti/",
        "ipoteka_tijorat": "https://mkbank.uz/uz/private/crediting/mortgage-loan-secondary-market/",
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
        "avtokredit_brend_ikkilamchi": True,
        "avtokredit_elektro": True,
        "ipoteka_tijorat": True,
    }
    PRODUCT_NAMES = {
        "avtokredit": "Avtokredit UzAuto Motors",
        "avtokredit_ikkilamchi": "Foydalanilgan avtomobillar uchun avtokredit",
        "avtokredit_brend_birlamchi": "Avtokredit ADM GLOBAL",
        "avtokredit_brend_ikkilamchi": "Foydalanilgan avtomobillar uchun avtokredit",
        "avtokredit_elektro": "Avtokredit Leapmotor",
        "mikroqarz": "Mikroqarz",
        "mikroqarz_onlayn": 'Onlayn Mikroqarz "Ommabop"',
        "ipoteka_davlat": "Imkoniyat ipotekasi krediti",
        "ipoteka_tijorat": "Universal ipoteka",
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
                elif category in ("avtokredit_ikkilamchi", "avtokredit_brend_ikkilamchi"):
                    product = self._build_avtokredit_ikkilamchi_product(category, url, now, text)
                elif category == "avtokredit_brend_birlamchi":
                    product = self._build_avtokredit_brend_birlamchi_product(url, now, text)
                elif category == "avtokredit_elektro":
                    product = self._build_avtokredit_elektro_product(url, now, text)
                elif category == "mikroqarz":
                    product = self._build_mikroqarz_product(url, now, text)
                elif category == "mikroqarz_onlayn":
                    product = self._build_mikroqarz_onlayn_product(url, now)
                elif category == "ipoteka_davlat":
                    product = self._build_ipoteka_davlat_product(url, now, text)
                elif category == "ipoteka_tijorat":
                    product = self._build_ipoteka_tijorat_product(url, now, text)
                else:
                    heading_pair = self.CATEGORY_HEADINGS[category]
                    section = extract_section(text, *heading_pair)
                    product = self._build_product(category, section, url, now, full_text=text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """"Universal ipoteka" ("Ikkilamchi bozor uchun ipoteka krediti"
        sahifasi, mortgage-loan-secondary-market/) — bankning o'z mablag'lari
        hisobidan, ikkilamchi bozordan uy-joy sotib olish uchun (ipoteka_davlat
        kategoriyasidagi "Imkoniyat ipotekasi krediti"dan farqli, u aniq
        "Moliya vazirligi mablag'lari" deb yozilgan davlat mahsuloti).

        Sahifa yuqorisida toza statistik kartochka bor: "1 648 000 000
        so'mgacha" (qiymat) -> "kredit miqdori" (kichik harf bilan yorliq,
        QIYMATDAN KEYIN keladi) -> "24%-26%" -> "yillik stavka" -> "20
        yilgacha" -> "kredit muddati". Bu uch band pastroqdagi "Kredit
        shartlari" bo'limida katta harf bilan ("Kredit miqdori" va h.k.)
        TAKRORLANADI (jami 6+ marta) — shu sabab standart extract_section
        katta harfli sarlavhalar bilan ishlatilsa noto'g'ri (keyingi)
        joyga tushib qolardi. Kichik harfli yorliqlar sahifada FAQAT bir
        marta uchraydi, shu sabab ular ustuvor ishlatiladi: "bozoridan
        uy-joy xarid qilish uchun" (tavsif matni, statistik kartochkadan
        oldin, ham bir marta uchraydi) dan "kredit miqdori" gacha bo'lgan
        oraliqda summa, "kredit miqdori" dan "yillik stavka" gacha stavka,
        "yillik stavka" dan "kredit muddati" gacha muddat.

        Muddat "20 yilgacha" (yil, oy emas) — _MORTGAGE_TERM_RE (klass
        darajasida allaqachon mavjud, ipoteka_davlat uchun ham ishlatiladi)
        bilan yil->oy ga aylantiriladi.

        Boshlang'ich badal "Foydalanish shartlari" bo'limida so'z shaklida:
        "Boshlang'ich badalning eng kam miqdori: 25% (uy-joyning oldi-sotdi
        qiymatidan)." — bu ibora sahifada bir marta uchraydi, standart
        extract_percentages bilan olinadi.

        Imtiyozli davr "Kredit shartlari" bo'limida aniq "Imtiyozli davr:
        Yo'q" deb yozilgan (bir marta uchraydi) — bu haqiqiy "yo'q" (0 oy)
        signali, "noma'lum" emas."""
        amount_section = extract_section(text, "bozoridan uy-joy xarid qilish uchun", "kredit miqdori")
        amount = extract_amount_som(amount_section)

        rate_section = extract_section(text, "kredit miqdori", "yillik stavka")
        rates = extract_percentages(rate_section)

        term_section = extract_section(text, "yillik stavka", "kredit muddati")
        term_match = self._MORTGAGE_TERM_RE.search(term_section)
        term = int(term_match.group(1)) * 12 if term_match else None

        down_section = extract_section(text, "Boshlang‘ich badalning eng kam miqdori", "Yillik foiz stavkasi")
        down_rates = extract_percentages(down_section)
        down_payment_pct = min(down_rates) if down_rates else None

        payment_method_section = extract_section(text, "To'lov usuli", "Kreditni rasmiylashtirish usuli")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(text, "Imtiyozli davr", "Kredit ta")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

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
            requires_collateral=self.FORCE_COLLATERAL["ipoteka_tijorat"],
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

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

    def _build_mikroqarz_onlayn_product(self, url, now):
        """"Onlayn Mikroqarz 'Ommabop'" — "mikroqarzlar" hub sahifasidagi
        kartochka Mavrid mobil ilovasini yuklab olishni taklif qiladi,
        lekin hech qanday stavka/muddat/summa raqamini ko'rsatmaydi (avval
        bu yerda "Vaqtincha to'xtatilgan" yozuvi bor edi, 2026-08-12
        holatiga ko'ra u ham yo'qolgan). Foydalanuvchining aniq
        ko'rsatmasiga ko'ra, sayt raqam bermagan hollarda mustaqil
        tasdiqlangan pptx manbasidan olinadi ("Ommabop-2": 26-29%, 24
        oygacha, 50 mln so'mgacha)."""
        return Product(
            bank=self.bank_name,
            category="mikroqarz_onlayn",
            product_name=self.PRODUCT_NAMES["mikroqarz_onlayn"],
            rate_min=26.0,
            rate_max=29.0,
            term_min_months=1,
            term_max_months=24,
            amount_max_som=50_000_000,
            requires_collateral=False,
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
            special_terms="Raqamlar pptx manbasidan — saytda stavka/muddat ko'rsatilmagan",
        )

    def _build_avtokredit_ikkilamchi_product(self, category, url, now, text):
        """"Foydalanilgan avtomobillar uchun avtokredit" — sahifa
        <title>'ida "yo'l bosilgan avtomobillar uchun kredit" deyilgan,
        ya'ni ishlatilgan (ikkilamchi bozor) avtomobillar uchun. Brend
        cheklovi ham yo'q — shu sabab bitta haqiqiy sahifa
        "avtokredit_brend_ikkilamchi" toifasiga ham xaritalanadi (bir xil
        URL, shu metod ikkalasi uchun ham chaqiriladi, faqat `category`
        parametri farq qiladi).

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
            category=category,
            product_name=self.PRODUCT_NAMES[category],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=self.FORCE_COLLATERAL[category],
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

    def _build_avtokredit_elektro_product(self, url, now, text):
        """"Avtokredit Leapmotor" — "Leapmotor" avtomobilini xarid qilish
        uchun avtokredit ("Skyline Global" bilan hamkorlikda). Leapmotor —
        xitoylik elektromobil brendi, "Kredit maqsadi" bandida aniq
        "Leapmotor avtomobilini birlamchi bozordan xarid qilish uchun"
        deyilgan (faqat birlamchi bozor, ikkilamchi haqida gap yo'q).

        ADM GLOBAL sahifasidagi bilan bir xil jadval shabloni: "LEAPMOTOR"
        sarlavhasi ostida boshlang'ich badal ulushi (25%-60%) x muddat
        (12-60 oy) bo'yicha guruhlangan bitta narx jadvali (0,0% dan 16,0%
        gacha). Ulush yorliqlari butun son, haqiqiy stavkalar vergul-kasr
        — shu farq orqali _ADM_RATE_RE/_ADM_TIER_RE bilan ajratiladi (ADM
        GLOBAL bilan bir xil regexlar qayta ishlatiladi, chunki naqsh
        bank-sahifa-xos emas, umumiy shablon)."""
        block = extract_section(text, "LEAPMOTOR", "Kredit oluvchi bankka")
        rates = [float(m.replace(",", ".")) for m in self._ADM_RATE_RE.findall(block)]
        terms = [int(m) for m in self._ADM_TERM_RE.findall(block)]
        tiers = [int(m) for m in self._ADM_TIER_RE.findall(block)]
        down_payment_pct = float(min(tiers)) if tiers else None

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
            category="avtokredit_elektro",
            product_name=self.PRODUCT_NAMES["avtokredit_elektro"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=self.FORCE_COLLATERAL["avtokredit_elektro"],
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
