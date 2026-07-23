import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_grace_period_months,
    extract_payment_method,
    extract_section,
    fetch_html,
    html_to_text,
)

_DOWN_PAYMENT_RE = re.compile(r"avtotransport vositasi qiymatining (\d+) foizdan kam")
_MORTGAGE_RATE_RE = re.compile(r"(\d{1,2}(?:[.,]\d{1,2})?)%")
_MORTGAGE_TERM_RE = re.compile(r"Turar joyni sotib olish uchun\s*-\s*(\d+)\s*oygacha")
_MORTGAGE_DOWN_RE = re.compile(r"(\d{1,2})\s*foizidan\s*kam")
_DAVLAT_AMOUNT_RE = re.compile(r"(\d{1,3}(?:,\d{1,2})?)\s*mln\.?\s*so")


class AsakabankScraper(TextSectionScraper):
    """Asakabank (asakabank.uz) "Avtokredit UzAuto Motors" sahifasi
    React/JS orqali client-side render qilinadigan SPA — AgroBank scraper'i
    uchun hujjatlashtirilgan holatning aynan o'zi: oddiy requests-based
    fetch_html bilan olingan HTML tanasi deyarli bo'sh qaytadi (hech qanday
    foiz/muddat/summa matni yo'q), chunki JavaScript hech qachon bajarilmaydi.
    Shu sabab bu fixture requests bilan emas, Playwright orqali (headless
    browser'da sahifa to'liq render qilingandan keyin document.documentElement
    .outerHTML olib) yozib olindi — raqamlar HAQIQIY, jonli sahifadan. LEKIN
    production muhitida scraper hamon oddiy fetch_html (utils.py) orqali
    ishlaydi, JS bajarmaydi — demak bu scraper productionda hech qanday
    mahsulot topmasligi ehtimoli yuqori (AgroBank'dagi bilan bir xil
    cheklov); bu orchestrator/monitoring bosqichida hisobga olinishi kerak.

    Sahifadagi 4 ta statistik karta ("60 oygacha" / "Kredit muddati", "0%
    dan" / "Foiz stavkasi", "25% dan" / "Boshlang'ich to'lov", "80% dan" /
    "Avtomobil summasi uchun") barchasi "%" belgisi bilan yozilgan — agar
    ularning barchasi bitta bo'lim sifatida olinsa, 25%/80% (boshlang'ich
    badal va avtomobil qiymatiga nisbatan ulush, foiz STAVKASI emas)
    rate_max'ni yolg'on ravishda 80% ga ko'tarib yuboradi. Shu sabab standart
    bitta (CATEGORY_HEADINGS) juftlik o'rniga run() qayta yozilgan: foiz
    stavkasi faqat "Kredit muddati" -> "Foiz stavkasi" oralig'idan (bu yerda
    boshqa % yo'q, faqat "0% dan" statistik qiymati) olinadi; muddat va aniq
    kredit summasi esa "Shart va talablar" bo'limidagi nasrdan ("uzaytirish
    huquqisiz 60 oygacha" ... "kredit miqdori 1 (bir) mlrd. so'mdan
    oshmagan miqdorda") olinadi. Bu ikkinchi qismda ham "80%dan" (avtomobil
    qiymatiga nisbatan ulush, foiz stavkasi emas) uchraydi — bitta umumiy
    section'ga qo'shilgandan keyin extract_percentages buni ham hisoblab,
    rate_max'ni yolg'on ravishda 80% ga ko'tarib yuborishi mumkin edi, shu
    sabab bu ikkinchi qismdagi barcha "%" belgilari birlashtirishdan oldin
    olib tashlanadi (extract_term_months/extract_amount_som "%" belgisiga
    umuman e'tibor bermagani uchun bu xavfsiz)."""

    bank_name = "Asakabank"
    url = "https://asakabank.uz/uz/physical-persons/credits"
    CATEGORY_URLS = {
        "avtokredit": "https://asakabank.uz/uz/physical-persons/credits/avtokredit-uzauto-motors",
        # "ADM Global I" — ADM Jizzakh zavodida ishlab chiqarilgan KIA
        # avtomobillari (Sonet, Carens, Bongo, Carnival PE, K8 PE) uchun,
        # xuddi shu "Kredit haqida" -> "Shart va talablar" shabloni bilan.
        "avtokredit_brend_birlamchi": "https://asakabank.uz/uz/physical-persons/credits/adm-global-i",
        # "Ipoteka Universal 2.0" — bir sahifada har ikkala tab
        # ("Kredit haqida"/"Shart va talablar") mazmuni allaqachon DOMda
        # mavjud (ADM Global'dan farqli, tab bosishni talab qilmaydi).
        "ipoteka_tijorat": "https://asakabank.uz/uz/physical-persons/credits/ipoteka-universal",
        "ipoteka_davlat": "https://asakabank.uz/uz/physical-persons/credits/ipoteka",
    }
    PRODUCT_NAMES = {
        "avtokredit": "Avtokredit UzAuto Motors",
        "avtokredit_brend_birlamchi": "ADM Global I",
        "ipoteka_tijorat": "Ipoteka Universal 2.0",
        "ipoteka_davlat": "Qulay Makon",
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
            text = html_to_text(html)

            if category == "ipoteka_tijorat":
                product = self._build_ipoteka_tijorat_product(url, now, text)
                if product is not None:
                    products.append(product)
                continue

            if category == "ipoteka_davlat":
                product = self._build_ipoteka_davlat_product(url, now, text)
                if product is not None:
                    products.append(product)
                continue

            rate_section = extract_section(text, "Kredit muddati", "Foiz stavkasi")
            detail_section = extract_section(text, "uzaytirish huquqisiz", "Boshlang")
            # detail_section contains "80%dan" (loan-to-vehicle-value share,
            # not an interest rate) — stripped so it can't contaminate
            # rate_max once concatenated with rate_section. term/amount
            # regexes never key on "%", so this is safe for their purposes.
            section = f"{rate_section}\n{detail_section.replace('%', '')}"

            # Boshlang'ich badal so'z shaklida ("25 foizdan kam bo'lmagan")
            # berilgan, "%" belgisisiz — alohida regex bilan olinadi.
            down_payment_match = _DOWN_PAYMENT_RE.search(text)
            down_payment_pct = float(down_payment_match.group(1)) if down_payment_match else None

            # To'lov usuli faqat kalkulyator tugmalarida ko'rsatilgan
            # ("Kredit turi: Annuitet / Differensial" tanlovi).
            payment_method_section = extract_section(text, "Kredit turi", "Daromad turi")
            payment_method = extract_payment_method(payment_method_section)

            # "Imtiyozli davr - ko'zda tutilmagan."
            grace_section = extract_section(text, "Imtiyozli davr", "Kredit soni")
            grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

            product = self._build_product(
                category,
                section,
                url,
                now,
                full_text=text,
                down_payment_pct=down_payment_pct,
                grace_period_months=grace_period_months,
                payment_method=payment_method,
            )
            if product is not None:
                products.append(product)
        return products

    def _build_ipoteka_davlat_product(self, url, now, text):
        """"Qulay Makon" — sahifada aniq "Moliya vazirligi" so'zi yo'q,
        lekin ikkita mustaqil signal buni davlat mablag'i bilan
        moliyalashtirilgan mahsulot ekanini tasdiqlaydi: (1) kredit
        summasi chegaralari ("Toshkent — 480,0 mln so'mgacha",
        "Qoraqalpog'iston/viloyatlar — 380,0 mln so'mgacha") boshqa olti
        bankda (SQB, HamkorBank, Ipoteka Bank, Aloqabank) "Moliya
        vazirligi" deb aniq yozilgan xuddi shu davlat ipoteka dasturining
        chegaralari bilan bir xil; (2) hujjatlar ro'yxatida "Subsidiya
        xabarnomasi (mavjud bo'lsa)" tilga olinadi — bu shu davlat
        subsidiyasi dasturiga xos hujjat. "Ipoteka Universal 2.0"
        (ipoteka_tijorat, bankning o'z mablag'i) da bunday chegara yoki
        subsidiya hujjati yo'q.

        "Kredit summasi" bo'limidagi qiymatlar vergul-o'nlik ("480,0
        mln so'mgacha") formatida — umumiy extract_amount_som bunga mos
        kelmagani uchun (SQB/Aloqabank'da ham uchragan xuddi shu
        muammo) maxsus regex bilan ikkalasi ham olinib, kattasi
        ishlatiladi.

        Sahifada "garov" so'zi umuman yo'q (faqat "Ta'minot bilan
        bog'liq hujjatlar" degan umumiy ibora bor) — ipoteka ta'rifiga
        ko'ra doim ko'chmas mulk garovi bilan ta'minlangani uchun
        requires_collateral qattiq True belgilangan (boshqa banklardagi
        FORCE_COLLATERAL konventsiyasi bilan bir xil)."""
        block = extract_section(text, "Kredit summasi", "Kimlar uchun")
        stavka_idx = block.find("Foiz stavkasi")
        amount_section = block[:stavka_idx] if stavka_idx != -1 else block
        amounts = [round(float(m.replace(",", ".")) * 1_000_000) for m in _DAVLAT_AMOUNT_RE.findall(amount_section)]
        amount = max(amounts) if amounts else None

        rate_section = extract_section(block, "Foiz stavkasi", "Boshlang")
        rate_match = re.search(r"(\d{1,2})%", rate_section)
        rates = [float(rate_match.group(1))] if rate_match else []

        down_section = extract_section(block, "Boshlang", "Kredit muddati")
        down_payment_rates = [float(m) for m in re.findall(r"(\d{1,2})%", down_section)]
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        term_section = extract_section(block, "Kredit muddati", None)
        term_match = re.search(r"(\d{1,2})\s*yilgacha", term_section)
        term = int(term_match.group(1)) * 12 if term_match else None

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
            requires_collateral=True,
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=payment_method,
        )

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """"Ipoteka Universal 2.0" — davlat/Moliya vazirligi mablag'i
        haqida hech qanday ishora yo'q, bankning o'z mahsuloti;
        birlamchi va ikkilamchi bozordan uy-joy xaridi uchun. Ikkita
        stavka beriladi (21,99% asosiy, 20,99% ish haqi loyihasi
        ishtirokchilari uchun) — "Foiz stavkasi:" dan "Boshlang'ich
        to'lov"gacha bo'lgan tor blokdan olinadi (avtokredit sahifalaridagi
        kabi "80%" turdagi aloqasiz ulush contaminatsiyasi bu yerda yo'q).

        Muddat "Turar joyni sotib olish uchun - 240 oygacha" shaklida —
        aniq shu iboraga bog'langan regex bilan olinadi (sahifada "Kredit
        muddati" statistik kartasi ham bor, lekin u faqat bitta qiymat
        beradi va aynan shu naqsh bilan ustuvor).

        Boshlang'ich badal "%" belgisisiz, so'z shaklida ("25
        foizidan\\xa0kam bo'lmagan") — uzilmaydigan probel (\\xa0) tufayli
        oddiy bo'sh joy o'rniga \\s* ishlatiladi."""
        rate_section = extract_section(text, "Foiz stavkasi:", "Boshlang")
        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_RE.findall(rate_section)]

        term_match = _MORTGAGE_TERM_RE.search(text)
        term = int(term_match.group(1)) if term_match else None

        amount_section = extract_section(text, "Kredit miqdori:\n", "Kredit foiz stavkasi")
        amount = extract_amount_som(amount_section)

        down_match = _MORTGAGE_DOWN_RE.search(text)
        down_payment_pct = float(down_match.group(1)) if down_match else None

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
            requires_collateral=True,
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=payment_method,
        )
