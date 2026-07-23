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

_RATE_RANGE_RE = re.compile(r"(\d+(?:,\d+)?)\s*-\s*(\d+(?:,\d+)?)%")
_MORTGAGE_RATE_RE = re.compile(r"yillik\s*(\d{1,2}(?:[.,]\d{1,2})?)%")
_MORTGAGE_TERM_YEAR_RE = re.compile(r"(\d{1,2})\s*yilgacha")


class IpotekaBankScraper(TextSectionScraper):
    """Ipoteka Bank (ipotekabank.uz) retail kredit kategoriyalari SQB/NBU kabi
    alohida sahifalarda joylashgan (real saytda tekshirilgan — Task 7
    tadqiqotiga qarang). mikroqarz/istemol_krediti eski, tekshirilgan
    mantiqda qoladi.

    "kredit_karta" (avvalgi "overdraft/" URL) olib tashlandi: sahifa
    endi butunlay boshqa mahsulotga (Rus tilidagi Onlayn Mikrozaym
    sahifasiga) yo'naltiradi — saytda hech qanday kredit karta (overdraft)
    mahsuloti umuman topilmadi (faqat oddiy plastik/debit kartalar bor).

    avtokredit uchun URL foydalanuvchi so'ragan aniq mahsulot sahifasiga
    ("crediting/autocredit/cobalt-special/") almashtirildi (avvalgi umumiy
    "/crediting/autocredit/" o'rniga). Bu sahifada "Kreditlash shartlari"
    bo'limi toza label:qiymat ro'yxati beradi (Miqdori/Boshlang'ich
    to'lov/Foiz stavkasi yillik/Muddati), lekin "Foiz stavkasi yillik"
    qiymati "0-18%" formatida — extract_percentages faqat "%" belgisi
    OLDIDAGI raqamni oladi ("18" ni topadi, lekin chiziqning boshidagi "0"
    "%" bilan tugamagani uchun mos kelmaydi). Shu sabab maxsus regex bilan
    ikkala uchi ham ("0" va "18") birga olinadi. Boshlang'ich to'lov ("25%
    dan boshlab") xuddi shu bo'limdan oldin joylashgani uchun alohida
    tor oraliqda ("Miqdori" -> "Foiz stavkasi yillik") olinadi — aks holda
    ikkalasi birga extract_percentages'ga tushib, rate_max'ni yolg'on
    ravishda 25%ga ko'tarib yuboradi.

    Axborot varaqasi uslubidagi raqamlangan ro'yxatda "6.Kreditning
    imtiyozli davri ... imtiyozli davrsiz" deb aniq yozilgan — "davrsiz"
    ("-siz" inkor qo'shimchasi) avvalgi GRACE_PERIOD inkor ro'yxatiga
    qo'shildi (scrapers/utils.py'ga qarang). Xuddi shu ro'yxatda to'lov
    usuli "(differentsial usulida)" deb — "differensial"dan farqli, "t"
    harfi bilan — yozilgan; extract_payment_method endi ikkala imloni ham
    taniydi.

    Sahifaning boshqa joyida (aloqasiz) "O'zini o'zi band qilganlar uchun
    garovsiz mikrokredit" iborasi bor — bu butun sahifa matnida "garov"
    tekshiruvi uchun umumiy "garovsiz" signali bilan aralashib, yolg'on-
    manfiy beradi. Avtokredit ta'rifiga ko'ra doim sotib olinayotgan
    avtomobilning o'zi bilan ta'minlanadi, shuning uchun FORCE_COLLATERAL
    orqali aniq True belgilangan (eski versiyadagi bilan bir xil yechim).

    Eski "mikroqarz" kaliti "mikroqarz_onlayn"ga o'zgartirildi: sahifaning
    o'zi (<title> va "Kredit mablag'larini olish: Onlayn, Ipoteka Mobile
    ilovasidagi joriy hisobraqamga") mahsulotni aniq "Onlayn Mikroqarz"
    deb ataydi — oflayn "mikroqarz" toifasi emas. Bu safar sahifada
    mustaqil "Ta'minot"/garov bo'limi umuman yo'q (faqat ixtiyoriy
    sug'urta tilga olingan) — shuning uchun FORCE_COLLATERAL kerak emas,
    has_collateral_requirement'ning "False" natijasi bu safar to'g'ri
    (yolg'on-manfiy emas)."""

    bank_name = "Ipoteka Bank"
    url = "https://ipotekabank.uz/uz/private/crediting/"
    CATEGORY_URLS = {
        "avtokredit": "https://www.ipotekabank.uz/crediting/autocredit/cobalt-special/",
        "avtokredit_ikkilamchi": "https://www.ipotekabank.uz/crediting/autocredit/avtokredit-r1/",
        "avtokredit_brend_birlamchi": "https://www.ipotekabank.uz/crediting/autocredit/avtokredit-hyundai/",
        "avtokredit_elektro": "https://www.ipotekabank.uz/crediting/autocredit/avtokredit-super-byd/",
        "ipoteka_tijorat": "https://www.ipotekabank.uz/crediting/mortgage/tijorat/",
        "ipoteka_davlat": "https://www.ipotekabank.uz/crediting/mortgage/oson/",
        "mikroqarz_onlayn": "https://www.ipotekabank.uz/private/crediting/micro_new/",
        "istemol_krediti": "https://ipotekabank.uz/uz/private/crediting/consumer/",
    }
    FORCE_COLLATERAL = {
        "avtokredit": True,
        "avtokredit_ikkilamchi": True,
        "avtokredit_brend_birlamchi": True,
        "avtokredit_elektro": True,
        # Ipoteka (uy-joy garovi) ta'rifiga ko'ra doim sotib olinayotgan
        # ko'chmas mulk bilan ta'minlanadi; sahifada aloqasiz "garovsiz
        # mikrokredit" iborasi borligi sababli umumiy tekshiruv yolg'on-
        # manfiy berardi.
        "ipoteka_tijorat": True,
        # Xuddi shu sababga ko'ra ("garovsiz mikrokredit" iborasi bilan
        # aralashib ketishi) — ipoteka doim ko'chmas mulk garovi bilan
        # ta'minlanadi.
        "ipoteka_davlat": True,
    }
    PRODUCT_NAMES = {
        "avtokredit": "Avtokredit Cobalt Special",
        "avtokredit_ikkilamchi": "Avtokredit R1",
        "avtokredit_brend_birlamchi": "Avtokredit Hyundai",
        "avtokredit_elektro": "Avtokredit Super BYD",
        "ipoteka_tijorat": "Tijorat ipotekasi",
        "ipoteka_davlat": '"Oson" ipotekasi',
        "mikroqarz_onlayn": "Onlayn Mikroqarz",
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
                elif category == "avtokredit_elektro":
                    product = self._build_avtokredit_elektro_product(url, now, text)
                elif category == "ipoteka_tijorat":
                    product = self._build_ipoteka_tijorat_product(url, now, text)
                elif category == "ipoteka_davlat":
                    product = self._build_ipoteka_davlat_product(url, now, text)
                elif category == "mikroqarz_onlayn":
                    product = self._build_mikroqarz_onlayn_product(url, now, text)
                else:
                    product = self._build_product(category, text, url, now, full_text=text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_mikroqarz_onlayn_product(self, url, now, text):
        section = extract_section(text, "Miqdori", "Kredit mablag")
        rates = extract_percentages(section)
        terms = extract_term_months(section)
        amount = extract_amount_som(section)

        grace_section = extract_section(text, "imtiyozli davri", "8.")
        grace_period_months = extract_grace_period_months("imtiyozli davri" + grace_section)

        payment_method_section = extract_section(text, "ndirish usuli", "10.")
        payment_method = extract_payment_method(payment_method_section)

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
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_avtokredit_product(self, url, now, text):
        amount_section = extract_section(text, "Miqdori", "Boshlang")
        amount = extract_amount_som(amount_section)

        down_payment_section = extract_section(text, "Miqdori", "Foiz stavkasi yillik")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        rate_section = extract_section(text, "Foiz stavkasi yillik", "Muddati")
        rate_match = _RATE_RANGE_RE.search(rate_section)
        rates = (
            [float(rate_match.group(1).replace(",", ".")), float(rate_match.group(2).replace(",", "."))]
            if rate_match
            else []
        )

        term_section = extract_section(text, "Muddati", "Talablar")
        terms = extract_term_months(term_section)

        grace_section = extract_section(text, "imtiyozli davri", "Kreditni so")
        grace_period_months = extract_grace_period_months("imtiyozli davri" + grace_section)

        payment_method_section = extract_section(text, "ndirish usuli", "Toʻlovlarning")
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
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_avtokredit_ikkilamchi_product(self, url, now, text):
        """"Avtokredit R1" — sahifa sarlavhasi "Avtokredit R1 yangi yoki
        ishlatilgan avtomobil uchun" deb aniq yozilgan, ya'ni yangi VA
        ishlatilgan (ikkilamchi bozor) avtomobillarni ham qamrab oladi.

        "Foiz stavkasi" sarlavhasi sahifada 2 marta uchraydi: birinchisi
        yuqoridagi bo'sh kalkulyator vidjeti ("Foiz stavkasi: %"), ikkinchisi
        haqiqiy "Kreditlash shartlari" ro'yxatida. Shu sabab avval butun
        "Miqdori" -> "Talablar" bloki ajratib olinadi (bu oraliqda "Foiz
        stavkasi" faqat bitta marta uchraydi), so'ng barcha qo'shimcha
        maydonlar (boshlang'ich to'lov, stavka, muddat) shu tor blok
        ICHIDA qidiriladi — aks holda noto'g'ri (bo'sh) vidjet qiymatiga
        tushib qolinardi."""
        block = extract_section(text, "Miqdori", "Talablar")
        amount_section = extract_section(block, "", "Boshlang")
        amount = extract_amount_som(amount_section)

        down_payment_section = extract_section(block, "Boshlang", "Foiz stavkasi")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        rate_section = extract_section(block, "Foiz stavkasi", "Muddati")
        rates = extract_percentages(rate_section)

        term_section = extract_section(block, "Muddati", None)
        terms = extract_term_months(term_section)

        grace_section = extract_section(text, "imtiyozli davri", "To‘lovlarning davriyligi")
        grace_period_months = extract_grace_period_months("imtiyozli davri" + grace_section)

        payment_method_section = extract_section(text, "differentsial usulida)", "9.")
        payment_method = extract_payment_method(payment_method_section)

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

    def _build_avtokredit_elektro_product(self, url, now, text):
        """"Avtokredit Super BYD" — Song Plus DM-i/Pro DM-i, e2, Chazor,
        Song Plus EV (plug-in gibrid va elektromobil) modellari uchun,
        "Avtokredit Hyundai" bilan bir xil "Miqdori" -> "Talablar" shabloni.
        Farqi: boshlang'ich badal qatoridan keyin darhol footnote matni
        keladi ("* agar 2024-yil 1-iyuldan keyin ... 15% ... 20%"), va bu
        footnote'dagi "15%"/"20%" ham "%" belgili raqamlar bo'lgani uchun
        oddiy extract_percentages ularni ham "boshlang'ich badal" sifatida
        olib, min() natijasini yolg'on ravishda 15% ga tushirib yuboradi —
        shu sabab down-payment bo'limi footnote boshlanishi ("* agar")dan
        oldin to'xtatiladi, Hyundai'dagi umumiy "Foiz stavkasi" chegarasi
        o'rniga."""
        block = extract_section(text, "Miqdori", "Talablar")
        amount_section = extract_section(block, "", "Boshlang")
        amount = extract_amount_som(amount_section)

        down_payment_section = extract_section(block, "Boshlang", "* agar")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        rate_section = extract_section(block, "Foiz stavkasi", "Muddati")
        rate_match = _RATE_RANGE_RE.search(rate_section)
        rates = (
            [float(rate_match.group(1).replace(",", ".")), float(rate_match.group(2).replace(",", "."))]
            if rate_match
            else []
        )

        term_section = extract_section(block, "Muddati", None)
        terms = extract_term_months(term_section)

        grace_section = extract_section(text, "imtiyozli davri", "To‘lovlarning davriyligi")
        grace_period_months = extract_grace_period_months("imtiyozli davri" + grace_section)

        payment_method_section = extract_section(text, "differentsial usulida)", "9.")
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
            requires_collateral=self.FORCE_COLLATERAL["avtokredit_elektro"],
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """"Tijorat ipotekasi" — davlat mablag'lari emas, bankning o'z
        (tijorat) mablag'lari hisobidan birlamchi yoki ikkilamchi bozordan
        uy-joy sotib olish uchun. Stavka mijoz toifasi (rasmiy daromadli /
        o'zini o'zi band qilgan hamqarz bilan yoki hamqarzsiz) x muddat
        (10 yil / 20 yil) bo'yicha guruhlangan uchta blok sifatida beriladi
        ("10 yilgacha (120 oy) — yillik 22.5%%" kabi) — umumiy
        extract_percentages o'rniga "yillik N%" naqshiga qat'iy mos
        keladigan maxsus regex ishlatiladi, aks holda boshlang'ich badal
        ulushlari (20%/30%/40%/50%) ham stavka sifatida hisoblanib ketardi.

        Muddat "10 yilgacha"/"20 yilgacha" ko'rinishida — umumiy
        extract_term_months bu qiymatlarni oyga aylantirsa ham, natijada
        120 oydan katta har qanday qiymatni (masalan 20 yil = 240 oy)
        avtomatik chetlab o'tadi (bu cheklov avtokredit kontekstida
        mantiqiy, lekin ipoteka uchun noto'g'ri — shuning uchun bu yerda
        alohida, cheklovsiz regex bilan yil->oy konversiyasi qilinadi).

        Sahifada aloqasiz "garovsiz mikrokredit" iborasi borligi sababli
        umumiy garov tekshiruvi yolg'on-manfiy beradi — ipoteka ta'rifiga
        ko'ra doim ko'chmas mulk garovi bilan ta'minlangani uchun
        FORCE_COLLATERAL orqali aniq True belgilangan."""
        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_RE.findall(text)]

        term_block_start = text.find("Rasmiy daromad bilan:")
        term_block_end = text.find("Hamqarzlar", term_block_start) if term_block_start != -1 else -1
        term_block = text[term_block_start:term_block_end] if term_block_start != -1 and term_block_end != -1 else ""
        terms = sorted({int(m) * 12 for m in _MORTGAGE_TERM_YEAR_RE.findall(term_block)})

        down_payment_section = extract_section(text, "Rasmiy daromad bilan — ", "O")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        amount_section = extract_section(text, "To‘lov muddati", "Ipoteka bo")
        amount = extract_amount_som(amount_section)

        grace_section = extract_section(text, "Imtiyozli davr", "Hamqarzlar")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

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
            requires_collateral=self.FORCE_COLLATERAL["ipoteka_tijorat"],
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_ipoteka_davlat_product(self, url, now, text):
        """""Oson" ipotekasi — sahifa title'ida aniq yozilgan: "Moliya
        vazirligi subsidiyasi bilan" — davlat (byudjet) mablag'i, "Tijorat
        ipotekasi"dagi bankning o'z mablag'idan farqli. Faqat birlamchi
        bozordagi yangi qurilgan uy-joy (novostroyka) xaridi uchun.

        Barcha maydonlar sayt FAQ (Tez-tez beriladigan savollar) bo'limidagi
        savol-javob juftliklaridan olinadi — har biri o'z sarlavhasi orqali
        ajratiladi, chunki umumiy "Miqdori"/"Foiz stavkasi" kabi label:qiymat
        ro'yxati bu sahifada yo'q.

        Stavka BITTA qat'iy (fixed) qiymat — "Foiz stavkasi — yillik
        16,99% (qat'iy)" — min/max teng. "Maksimal kredit miqdori qancha?"
        savoli sahifada IKKI marta uchraydi (umumiy javob va keyinroq
        hudud bo'yicha taqsimot); birinchi (umumiy, 480 mln so'm) javobi
        ishlatiladi — extract_section keyingi "Dastur qaysi hududlarda"
        sarlavhasigacha to'xtatiladi, shuning uchun ikkinchi takror bilan
        aralashmaydi.

        Boshlang'ich to'lov rasmiy daromadli mijozlar uchun "15%dan
        boshlab", o'zini o'zi band qilganlar uchun "30%dan 50%gacha" —
        eng past (15%) qiymat olinadi (avvalgi ipoteka_tijorat/mikrokredit-
        bank ipoteka_davlat konvensiyasi bilan bir xil).

        Sahifada aloqasiz "garovsiz mikrokredit" iborasi borligi sababli
        has_collateral_requirement umumiy tekshiruvda yolg'on-manfiy
        ("Sotib olinadigan uy-joy garov sifatida qo'yiladi" degan aniq
        matn borligiga qaramay False) beradi — shu sabab ipoteka_tijorat
        bilan bir xil FORCE_COLLATERAL orqali True belgilangan."""
        rate_term_block = extract_section(text, "Foiz stavkasi va kredit muddati", "Minimal boshlang")
        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_RE.findall(rate_term_block)]

        term_match = re.search(r"muddati\s*—\s*(\d{1,3})\s*oygacha", rate_term_block)
        term = int(term_match.group(1)) if term_match else None

        amount_section = extract_section(text, "Maksimal kredit miqdori qancha?", "Dastur qaysi hududlarda")
        amount = extract_amount_som(amount_section)

        down_payment_section = extract_section(text, "Minimal boshlang", "Ariza topshirish uchun")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        grace_section = extract_section(text, "Imtiyozli davr", "Minimal boshlang")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        payment_section = extract_section(text, "Qoplash tartibi", "To‘lov sanasi")
        payment_method = extract_payment_method(payment_section)

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

    def _build_avtokredit_brend_birlamchi_product(self, url, now, text):
        """"Avtokredit Hyundai" — brend-maxsus (Hyundai) birlamchi bozor
        avtokrediti, "Avtokredit R1" bilan bir xil sahifa shabloniga ega
        (xuddi shu "Miqdori" -> "Talablar" bloki, xuddi shu axborot
        varaqasi tuzilishi). Stavka "0 - 19,9%" formatida (vergul-o'nlik
        yuqori chegara bilan) — shu sabab _RATE_RANGE_RE endi vergul-o'nlik
        raqamlarni ham qabul qiladi (ikkala uchini, "0" va "19,9", birga
        oladi)."""
        block = extract_section(text, "Miqdori", "Talablar")
        amount_section = extract_section(block, "", "Boshlang")
        amount = extract_amount_som(amount_section)

        down_payment_section = extract_section(block, "Boshlang", "Foiz stavkasi")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        rate_section = extract_section(block, "Foiz stavkasi", "Muddati")
        rate_match = _RATE_RANGE_RE.search(rate_section)
        rates = (
            [float(rate_match.group(1).replace(",", ".")), float(rate_match.group(2).replace(",", "."))]
            if rate_match
            else []
        )

        term_section = extract_section(block, "Muddati", None)
        terms = extract_term_months(term_section)

        grace_section = extract_section(text, "imtiyozli davri", "To‘lovlarning davriyligi")
        grace_period_months = extract_grace_period_months("imtiyozli davri" + grace_section)

        payment_method_section = extract_section(text, "differentsial usulida)", "9.")
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
            requires_collateral=self.FORCE_COLLATERAL["avtokredit_brend_birlamchi"],
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )
