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

_RATE_TIER_RE = re.compile(r"(\d+)%\s*[–-]\s*(\d+)%\s*yil")
_BREND_TIER_BLOCK_RE = re.compile(r"(\d{2})%\s*\n((?:\d{1,2}(?:[.,]\d{1,2})?%\s*\n?){6})")
_BREND_TERM_HEADER_RE = re.compile(r"(\d{1,3})\s*oy(?!dan|gacha)")
_MORTGAGE_RATE_RE = re.compile(r"yillik\s*(\d{1,2}(?:[.,]\d{1,2})?)%")
_MORTGAGE_DOWN_RE = re.compile(r"badalning\s*(\d{1,2})%")
_MORTGAGE_TERM_RE = re.compile(r"(\d{1,2})\s*yil\s*\((\d+)\s*oy\)")
_MORTGAGE_GRACE_RE = re.compile(r"(\d+)\s*oylik imtiyozli davr")


class NBUScraper(TextSectionScraper):
    """NBU (O'zmilliybank) retail kredit kategoriyalari SQB kabi alohida
    sahifalarda joylashgan (nbu.uz/jismoniy-shaxslarga-kreditlar/... — real
    saytda tekshirilgan, Task 6 tadqiqotiga qarang).

    avtokredit uchun URL foydalanuvchi so'ragan aniq mahsulot sahifasiga
    ("yangi-avtomobillar-uchun-avtokredit") almashtirildi (avvalgi umumiy
    "/avtokreditlar" hub-sahifasi o'rniga). Bu sahifada "Foiz stavkasi"
    bo'limi bitta son emas, balki boshlang'ich badal ulushiga qarab
    guruhlangan jadval: "20% – 21% yillik" / "30% – 20% yillik" (rasmiy
    daromadli mijozlar uchun) va "30% - 22% yilik" (o'zini-o'zi band
    qilganlar uchun, ba'zan ajratuvchi sifatida en-dash "–" o'rniga oddiy
    "-" ishlatilgan va "yillik" so'zi "yilik" deb xato yozilgan — regex
    ikkalasiga ham mos keladi). Har bir juftlikning BIRINCHI raqami
    boshlang'ich badal ulushi, IKKINCHISI esa haqiqiy stavka — agar bular
    ajratilmasdan extract_percentages bilan olinsa, ikkalasi bir xil
    diapazonda (20-30%) bo'lgani uchun qaysi biri stavka, qaysi biri badal
    ekanini farqlab bo'lmas edi. Shu sabab maxsus regex bilan juft-juft
    ajratiladi.

    Sahifada "Kredit muddati", "Imtiyozli davr" kabi sarlavhalar UCH marta
    takrorlanadi (yuqoridagi statistik xulosa, interaktiv kalkulyator
    maydon nomlari, va pastdagi toza "Batafsil" ro'yxati) — birinchi
    ikkitasida haqiqiy qiymat yo'q (kalkulyator maydonlari bo'sh). Shu
    sabab avval yagona "Kredit maqsadi" (faqat bir marta uchraydi) bilan
    butun "Batafsil" blokini ajratib olinadi, so'ng har bir maydon shu
    bloknign ICHIDA qidiriladi — bu orqali bo'sh kalkulyator maydonlariga
    tushib qolish oldi olinadi."""

    bank_name = "NBU"
    url = "https://nbu.uz/jismoniy-shaxslarga-kreditlar"
    CATEGORY_URLS = {
        "avtokredit": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/yangi-avtomobillar-uchun-avtokredit",
        "avtokredit_ikkilamchi": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/ikkilamchi-bozor-uchun-avtokredit",
        "avtokredit_brend_birlamchi": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/avtokredit-kia-haval-chery",
        "avtokredit_elektro": (
            "https://nbu.uz/jismoniy-shaxslarga-kreditlar/elektromobillar-va-gibridlar-uchun-avtokredit"
        ),
        # Bank "Mikroqarzlar" xob-sahifasida ikkita alohida mahsulot bor
        # ("Mikroqarz" va "Onlayn mikroqarz") — har birining o'z sahifasi.
        "mikroqarz": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/mikroqarz",
        "mikroqarz_onlayn": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/onlayn-mikroqarz",
        # Taxminiy (best-guess):
        "kredit_karta": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/overdraft",
        "ipoteka_davlat": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/standard-ipoteka-krediti",
    }
    PRODUCT_NAMES = {
        "avtokredit": "Yangi avtomobillar uchun avtokredit",
        "avtokredit_ikkilamchi": "Ikkilamchi bozor uchun avtokredit",
        "avtokredit_brend_birlamchi": "Avtokredit KIA, Chery",
        "avtokredit_elektro": "Elektromobillar va gibridlar uchun avtokredit",
        "mikroqarz": "Mikroqarz",
        "mikroqarz_onlayn": "Onlayn mikroqarz",
        "ipoteka_davlat": "Standard ipoteka krediti",
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)

                if category in ("avtokredit", "avtokredit_elektro"):
                    product = self._build_avtokredit_product(category, url, now, text)
                elif category == "avtokredit_ikkilamchi":
                    product = self._build_avtokredit_ikkilamchi_product(url, now, text)
                elif category == "avtokredit_brend_birlamchi":
                    product = self._build_avtokredit_brend_birlamchi_product(url, now, text)
                elif category == "ipoteka_davlat":
                    product = self._build_ipoteka_davlat_product(url, now, text)
                elif category == "mikroqarz":
                    product = self._build_mikroqarz_product(url, now, text)
                elif category == "mikroqarz_onlayn":
                    product = self._build_mikroqarz_onlayn_product(url, now, text)
                else:
                    product = self._build_product(category, text, url, now, full_text=text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, category, url, now, text):
        """"avtokredit" va "avtokredit_elektro" ("Elektromobillar va
        gibridlar uchun avtokredit") bir xil sahifa shabloniga ega:
        "Kredit maqsadi" bilan boshlanadigan bo'lim, tierli stavka
        jadvali ("30% – 22% yillik" kabi juftliklar). "avtokredit_elektro"
        sahifasida "Kredit xavfsizligi" sarlavhasi umuman yo'q — bu holda
        extract_section matn oxirigacha davom etadi, lekin _RATE_TIER_RE
        yetarlicha o'ziga xos (faqat "N% - M% yil" naqshiga mos keladi)
        bo'lgani uchun bu xavfsiz, boshqa aloqasiz % qiymatlari bilan
        aralashib ketmaydi."""
        block = extract_section(text, "Kredit maqsadi", "Kredit xavfsizligi")

        term_section = extract_section(block, "Kredit muddati", "Imtiyozli davr")
        terms = extract_term_months(term_section)

        amount_section = extract_section(block, "Kredit miqdori", "Kredit muddati")
        amount = extract_amount_som(amount_section)

        grace_section = extract_section(block, "Imtiyozli davr", "Foiz stavkasi")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        rate_section = extract_section(block, "Foiz stavkasi", None)
        tier_pairs = _RATE_TIER_RE.findall(rate_section)
        down_payments = [float(down) for down, _rate in tier_pairs]
        rates = [float(rate) for _down, rate in tier_pairs]
        down_payment_pct = min(down_payments) if down_payments else None

        payment_method = extract_payment_method(text)

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
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_avtokredit_ikkilamchi_product(self, url, now, text):
        """"Ikkilamchi bozor uchun avtokredit" — nomining o'zi ikkilamchi
        bozor uchun ekanini tasdiqlaydi. Xuddi birlamchi bozor avtokrediti
        kabi, "Foiz stavkasi" bo'limi boshlang'ich badal ulushiga qarab
        guruhlangan jadval ("20% – 22% yillik" / "30% – 21% yillik" /
        "30% - 23% yilik") — shu sabab bir xil _RATE_TIER_RE ishlatiladi
        (birinchi raqam badal, ikkinchisi haqiqiy stavka).

        "Kreditni ta'minlash: Kredit mablag'lari hisobiga sotib olinadigan
        transport vositasi" — "garov" so'zi ishlatilmagan, shu sabab
        has_collateral_requirement yolg'on-manfiy beradi; avtokredit doim
        sotib olinayotgan avtomobil bilan ta'minlangani uchun bu yerda
        to'g'ridan-to'g'ri True beriladi (boshqa banklardagi bir xil
        yechim).

        To'lov usuli axborot varaqasida "variable" (JS orqali to'ldiriladi,
        statik HTML'da yo'q) — shu sabab taxmin qilinmaydi (None)."""
        block = extract_section(text, "Kredit shartlari", "Kredit 18 yoshdan")

        term_section = extract_section(block, "Kredit muddati", "Imtiyozli davr")
        terms = extract_term_months(term_section)

        amount_section = extract_section(block, "Kredit miqdori", "Kredit muddati")
        amount = extract_amount_som(amount_section)

        grace_section = extract_section(block, "Imtiyozli davr", "Foiz stavkasi")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        rate_section = extract_section(block, "Foiz stavkasi", "Kreditni ta")
        tier_pairs = _RATE_TIER_RE.findall(rate_section)
        down_payments = [float(down) for down, _rate in tier_pairs]
        rates = [float(rate) for _down, rate in tier_pairs]
        down_payment_pct = min(down_payments) if down_payments else None

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
            requires_collateral=True,
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=None,
        )

    def _build_avtokredit_brend_birlamchi_product(self, url, now, text):
        """"Avtokredit KIA, Chery" — birlamchi bozordan KIA (Carens, K9,
        Sportage, K5C, EV6) va Chery avtomobillari uchun. Sahifada "Kredit
        shartlari" tab-bo'limi ichida 6 ta mustaqil narx jadvali bor (model
        guruhi x mijoz toifasi bo'yicha), har biri boshlang'ich to'lov
        ulushi (30%/40%/50%) x muddat (12-60 oy) bo'yicha guruhlangan.
        Ulush yorlig'i har doim 2 xonali butun son bo'lib, undan keyin
        aynan 6 ta stavka qiymati keladi (12/18/24/36/48/60 oy ustunlari) —
        shu qat'iy struktura orqali ulush va stavkalar ajratiladi (stavka
        qiymatlari orasida ham butun sonlar bor, shu sabab faqat vergul-
        kasr belgisiga tayanib bo'lmaydi).

        "Imtiyozli davr: 6 oygacha" jumlasi ham "N oygacha" shakliga mos
        kelgani uchun umumiy extract_term_months uni asosiy muddat bilan
        aralashtirib yuboradi (6 ni noto'g'ri minimal muddat sifatida olib
        qo'yadi) — shu sabab muddat alohida, faqat jadval ustunlaridagi
        yalang' "N oy" (dan/gacha qo'shimchasisiz) ko'rinishlaridan
        olinadi."""
        block = extract_section(text, "Kredit shartlari", "Kredit ta")

        tier_blocks = _BREND_TIER_BLOCK_RE.findall(block)
        tiers = [int(tier) for tier, _rates in tier_blocks]
        rates: list[float] = []
        for _tier, rate_str in tier_blocks:
            rates.extend(float(v.replace(",", ".")) for v in re.findall(r"(\d{1,2}(?:[.,]\d{1,2})?)%", rate_str))
        down_payment_pct = float(min(tiers)) if tiers else None

        terms = [int(m) for m in _BREND_TERM_HEADER_RE.findall(block)]

        amount = extract_amount_som(block)

        grace_section = extract_section(block, "Imtiyozli davr", "KIA")
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
            requires_collateral=True,
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=None,
        )

    def _build_ipoteka_davlat_product(self, url, now, text):
        """"Standard ipoteka krediti" — "Kreditlash manbai: O'zbekiston
        Respublikasi Iqtisodiyot va moliya vazirligi mablag'lari" deb
        aniq yozilgan — davlat (byudjet) mablag'i, bankning o'z tijorat
        mahsuloti emas (bank yana "ikkilamchi-bozor-uchun-ipoteka-krediti"
        degan alohida sahifada "Bankning o'z mablag'lari hisobidan" deb
        aytadigan tijorat mahsulotiga ham ega — bu boshqa sahifa).

        Stavka mijoz toifasi x boshlang'ich badal ulushiga qarab beriladi
        ("Dastlabki badalning 15% to'langanda - yillik 17%" kabi) —
        "yillik N%" va "badalning N%" uchun alohida regexlar ishlatiladi,
        chunki ular bir xil jumlada aralash keladi. Muddat "20 yil (240
        oy), 6 oylik imtiyozli davr bilan" — ikkalasi ham o'z regexi bilan
        ajratiladi."""
        block = extract_section(text, "Kredit maqsadi", "Muhim")

        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_RE.findall(block)]
        down_payments = [int(m) for m in _MORTGAGE_DOWN_RE.findall(block)]
        down_payment_pct = float(min(down_payments)) if down_payments else None

        term_match = _MORTGAGE_TERM_RE.search(block)
        term = int(term_match.group(2)) if term_match else None

        grace_match = _MORTGAGE_GRACE_RE.search(block)
        grace_period_months = int(grace_match.group(1)) if grace_match else None

        amount_section = extract_section(block, "Kredit summasi", "Ta")
        amount = extract_amount_som(amount_section)

        payment_method = extract_payment_method(block)

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
        """"Mikroqarz" — axborot varaqasida "1. Kreditning turi: Mikroqarz"
        deb aniq yozilgan ("Onlayn" prefiksisiz), rasmiylashtirish naqd pul
        yoki bank kartasiga o'tkazish orqali — oflayn "mikroqarz" toifasi
        (garchi ariza topshirish bosqichi ba'zi mijoz toifalari uchun
        "onlayn mavjud" bo'lsa ham, bu faqat qisman va rasmiy nom "Onlayn"
        emas).

        Sahifada "Kredit muddati" sarlavhasi 4 marta takrorlanadi (bo'sh
        kalkulyator maydonlari + haqiqiy "Kredit shartlari" ro'yxati) — end_
        heading "Kredit ajratish tartibi" bilan chegaralab, faqat oxirgi
        haqiqiy qiymatlar oralig'i olinadi (oraliqda qolgan bo'sh
        kalkulyator maydonlari va sonlar rate/term/amount natijasiga hech
        qanday ta'sir qilmaydi, chunki ular "%" yoki "oygacha" formatida
        yozilmagan)."""
        section = extract_section(text, "Kredit muddati", "Kredit ajratish tartibi")
        rates = extract_percentages(section)
        terms = extract_term_months(section)
        amount = extract_amount_som(section)

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
            requires_collateral=has_collateral_requirement(section),
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )

    def _build_mikroqarz_onlayn_product(self, url, now, text):
        """"Onlayn mikroqarz" — sahifa sarlavhasi "Onlayn mikrozaym — NBU",
        axborot varaqasida "1. Kreditning turi: Onlayn mikroqarz" va
        "Onlayn rasmiylashtirish: Ofisga bormasdan va qog'ozbozliksiz
        kreditni rasmiylashtiring" deb aniq yozilgan — mikroqarz_onlayn
        toifasiga kiradi.

        Bu safar "Kredit shartlari" -> "Onlayn mikrokredit qulay
        shartlari" tor oralig'i yetarli (faqat bitta "Kredit muddati"
        sarlavhasi shu ikki nuqta orasida joylashgan).

        Ta'minot faqat "Kreditni qaytarmaslik xavfidan sug'urta polisi"
        (mulk garovi emas, sug'urta) — shu sabab FORCE_COLLATERAL orqali
        aniq False belgilangan (oflayn "Mikroqarz"dan farqli, u yerda
        "Mol-mulk garovi" ham muqobil variant sifatida bor)."""
        section = extract_section(text, "Kredit shartlari", "Onlayn mikrokredit qulay shartlari")
        rates = extract_percentages(section)
        terms = extract_term_months(section)
        amount = extract_amount_som(section)

        if not rates or not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="mikroqarz_onlayn",
            product_name=self.PRODUCT_NAMES["mikroqarz_onlayn"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=False,
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )
