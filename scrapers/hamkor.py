import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_grace_period_months,
    extract_percentages,
    extract_section,
    extract_term_months,
    fetch_html,
    has_collateral_requirement,
    html_to_text,
)

_RATE_TERM_PAIR_RE = re.compile(r"(\d+)\s*oy\s*(?:\s*\n)*\s*([\d,]+)\s*%")
_MIKROQARZ_RATE_RE = re.compile(r"(\d+)\s*oygacha\D+?(\d+,\d+)%")
_MIKROQARZ_ONLAYN_TERM_RE = re.compile(r"(\d{1,3})\s*oydan\s*(\d{1,2})\s*yilgacha")
_IKKILAMCHI_RATE_RE = re.compile(r"(\d+(?:,\d+)?)%(?!\s*\n?\s*dan boshlab)")
_MORTGAGE_RATE_RE = re.compile(r"yillik\s*(\d{1,2}(?:[.,]\d{1,2})?)%")
_MORTGAGE_TERM_YEAR_RE = re.compile(r"(\d{1,2})\s*yilgacha")
_DAVLAT_RATE_RE = re.compile(r"(\d{1,2}(?:,\d{1,2})?)%\s*-\s*\d{1,2}%?\s*dan")
_DAVLAT_DOWN_RE = re.compile(r"(\d{1,2})%\s*dan\s*(?:\d{1,2}%\s*gacha|yuqori)")


class HamkorBankScraper(TextSectionScraper):
    """HamkorBank (hamkorbank.uz) retail kredit kategoriyalari SQB/NBU/Ipoteka
    Bank kabi alohida sahifalarda joylashgan. CATEGORY_HEADINGS kerak emas:
    har bir fetch qilingan sahifa matni bitta kategoriyaga bag'ishlangan deb
    qabul qilinadi — mikroqarz/kredit_karta/istemol_krediti uchun bu hamon
    to'g'ri.

    avtokredit uchun URL "Auto DAMAS" sahifasiga ("https://hamkorbank.uz/
    physical/credits/auto-damas/") almashtirildi (foydalanuvchi so'ragan
    aniq manzil — avvalgi "Auto Light" emas). Bu sahifa (uz/ prefiksisiz
    so'ralsa Rus tiliga qaytadi — shuning uchun URL uz/ prefiksi bilan
    yozilgan) o'ta murakkab tuzilishga ega: yuqoridagi qisqa xulosa
    kartochkasi ("0% dan boshlab" / "25% dan boshlab") ostida ikkita to'liq
    stavka matritsasi bor (rasmiy daromadsiz va rasmiy daromadli shaxslar
    uchun, har biri boshlang'ich badal ulushi (25-70%) x muddat (13-60 oy)
    bo'yicha guruhlangan). Bu matritsada "Kamida 30%" kabi boshlang'ich
    badal ulushi ham "%" belgisi bilan yozilgan — agar butun matritsa
    extract_percentages bilan olinsa, bu ulush foizlari haqiqiy stavkalar
    (0%-19%) bilan aralashib, rate_max'ni yolg'on ravishda 70%ga ko'tarib
    yuboradi (SQB/HamkorBank'da avval kuzatilgan xuddi shu 70-75%
    kontaminatsiya sinfi). Shu sabab maxsus regex ishlatiladi: faqat "N
    oy" dan keyin darhol keladigan "X%" juftliklari olinadi (masalan "13
    oy\\n0,0%"), "Kamida N%" kabi mustaqil foiz yozuvlari bu naqshga mos
    kelmaydi va tabiiy ravishda chetlab o'tiladi.

    Muddat esa faqat qisqa xulosa kartochkasidan ("5 yilgacha" -> 60 oy)
    olinadi — matritsadagi qisqaroq muddatlar (13 oy dan boshlab) mavjud,
    lekin boshqa banklardagi "yagona shift" konventsiyasiga muvofiq faqat
    yakuniy chegara (60 oy) term_min/term_max sifatida ishlatiladi.

    Sahifaning yon menyusida boshqa (aloqasiz) "Uy-joy ta'miri uchun
    kredit" mahsuloti "Imtiyozli shartlar asosida" deb tavsiflangan — bu
    butun sahifa matnida "imtiyozli davr" tekshiruvi uchun yolg'on signal
    beradi (mavjud emas iborasi boshqa joyda tasodifan topilib, 0 oy
    natija berardi). Shu sabab imtiyozli davr faqat "Kredit maqsadi" ->
    "Garov" oralig'idan qidiriladi — bu yerda "imtiyozli" so'zi umuman
    yo'q, shuning uchun to'g'ri ravishda None (haqiqatan ham aytilmagan)
    qaytadi. To'lov usuli (Annuitet/Differensial) ham sahifada butunlay
    tilga olinmagan — shu sabab u ham None qoladi."""

    bank_name = "HamkorBank"
    url = "https://hamkorbank.uz/uz/physical/credits/"
    CATEGORY_URLS = {
        "avtokredit": "https://hamkorbank.uz/uz/physical/credits/auto-damas/",
        "avtokredit_ikkilamchi": "https://hamkorbank.uz/uz/physical/credits/autolight/",
        "avtokredit_brend_birlamchi": "https://hamkorbank.uz/uz/physical/credits/auto-kia-sonet/",
        "ipoteka_tijorat": "https://hamkorbank.uz/uz/physical/mortgage/bank-mortgage/",
        "ipoteka_davlat": "https://hamkorbank.uz/uz/physical/mortgage/mortgage-new-build/",
        "mikroqarz": "https://hamkorbank.uz/uz/physical/credits/microcredit-plus/",
        "mikroqarz_onlayn": "https://hamkorbank.uz/uz/physical/credits/online-credit/",
        "kredit_karta": "https://hamkorbank.uz/uz/physical/credit-card/",
        "istemol_krediti": "https://hamkorbank.uz/uz/physical/credits/personal-loan/",
    }
    FORCE_COLLATERAL = {
        "avtokredit_ikkilamchi": True,
    }
    PRODUCT_NAMES = {
        "avtokredit": "Auto DAMAS",
        "avtokredit_ikkilamchi": "Auto light avtokrediti",
        "avtokredit_brend_birlamchi": "Auto KIA Sonet",
        "ipoteka_tijorat": "Bank ipotekasi",
        "ipoteka_davlat": "Yangi qurilgan uy-joy uchun ipoteka",
        "mikroqarz": "Mikrokredit Plus",
        "mikroqarz_onlayn": "Onlayn kredit",
        "istemol_krediti": "Iste'mol krediti",
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)

                if category in ("avtokredit", "avtokredit_brend_birlamchi"):
                    product = self._build_avtokredit_product(category, url, now, text)
                elif category == "avtokredit_ikkilamchi":
                    product = self._build_avtokredit_ikkilamchi_product(url, now, text)
                elif category == "mikroqarz":
                    product = self._build_mikroqarz_product(url, now, text)
                elif category == "mikroqarz_onlayn":
                    product = self._build_mikroqarz_onlayn_product(url, now, text)
                elif category == "ipoteka_tijorat":
                    product = self._build_ipoteka_tijorat_product(url, now, text)
                elif category == "ipoteka_davlat":
                    product = self._build_ipoteka_davlat_product(url, now, text)
                elif category == "istemol_krediti":
                    product = self._build_istemol_krediti_product(url, now, text)
                else:
                    product = self._build_product(category, text, url, now, full_text=text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, category, url, now, text):
        """"Auto DAMAS" (birlamchi) va "Auto KIA Sonet" (brend-maxsus
        birlamchi) bir xil sahifa shabloniga ega — ikkalasi ham shu bitta
        metod orqali ishlanadi (category parametri bilan)."""
        rate_matrix_section = extract_section(text, "boshlang", "Garov ta")
        rate_pairs = _RATE_TERM_PAIR_RE.findall(rate_matrix_section)
        rates = [float(rate.replace(",", ".")) for _, rate in rate_pairs]

        term_section = extract_section(text, "Kredit miqdori", "Foydali taklif")
        terms = extract_term_months(term_section)

        amount_section = extract_section(text, "Ariza qoldirish", "Kredit miqdori")
        amount = extract_amount_som(amount_section)

        down_payment_section = extract_section(text, "Foiz stavkasi", "Foydali taklif")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        grace_section = extract_section(text, "Kredit maqsadi", "Garov")
        grace_period_months = extract_grace_period_months(grace_section)

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
            payment_method=None,
        )

    def _build_avtokredit_ikkilamchi_product(self, url, now, text):
        """"Auto light avtokrediti" — "Kredit maqsadi: Transport
        vositalarini birlamchi va ikkilamchi bozordan sotib olish uchun
        avtokredit" deb aniq yozilgan, ya'ni bitta mahsulot ikkala bozorni
        ham qamrab oladi — shu sabab "avtokredit_ikkilamchi" toifasiga
        xaritalanadi.

        Stavka jadvali ikkita mijoz toifasiga (rasmiy daromadli / rasmiy
        daromadsiz) bo'linib, har birida bir nechta "N yilgacha — X%" qatori
        bor. Boshlang'ich badal ro'yxati ham "%" belgisi bilan, lekin har
        doim "... dan boshlab" iborasi bilan tugaydi — shu farq orqali
        haqiqiy stavkalar undan ajratiladi (negative lookahead: "% dan
        boshlab" bilan tugamaydigan foizlar).

        "Ariza bank ofisida to'ldiriladi" — ofisga borish talab qilingani
        uchun bu mahsulotning o'zi (garchi "ikkilamchi bozor" nomi bo'lsa
        ham) onlayn emas. To'lov usuli (Annuitet/Differensial) va imtiyozli
        davr sahifada aniq tilga olinmagan — ikkalasi ham None qoladi."""
        block = extract_section(text, "Kredit maqsadi", "Garov ta")
        rates = [float(r.replace(",", ".")) for r in _IKKILAMCHI_RATE_RE.findall(block)]

        amount_section = extract_section(block, "Kredit miqdori", "Foiz stavkasi")
        amount = extract_amount_som(amount_section)

        term_section = extract_section(block, "Kredit muddati", None)
        terms = extract_term_months(term_section)

        down_payment_section = extract_section(block, "Boshlang", "Kredit muddati")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

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

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """"Bank ipotekasi" — davlat mablag'lari emas, bankning o'z
        mablag'lari hisobidan uy-joy sotib olish YOKI ta'mirlash uchun
        (ikkalasi ham shu bitta sahifada, "Kredit maqsadi" -> "Kafillik
        yoki garov" oralig'ida). "Foiz stavkasi" bo'limida stavka va
        boshlang'ich badal ulushi bir qatorda aralash beriladi ("yillik
        26% - boshlang'ich to'lov 25% dan 30% gacha") — shu sabab faqat
        "yillik N%" naqshiga mos keladigan maxsus regex bilan haqiqiy
        stavkalar ajratiladi, aks holda badal ulushlari (25/30/40%) ham
        stavka sifatida hisoblanib, rate_max'ni yolg'on ravishda
        ko'tarib yuborardi.

        Muddat "10 yilgacha" (sotib olish) / "6 yilgacha" (ta'mirlash)
        shaklida — umumiy extract_term_months 120 oydan katta bo'lmagan
        qiymatlarni chetlab o'tmaydi bu safar (10 yil=120 oy chegarada),
        lekin izchillik uchun boshqa ipoteka toifalari bilan bir xil
        cheklovsiz yil->oy regexi ishlatiladi.

        Sahifaning yon menyusida "Imtiyozli shartlar asosida" tavsiflangan
        aloqasiz "Uy-joy ta'miri" mahsuloti borligi sababli butun sahifa
        bo'yicha imtiyozli davr tekshiruvi yolg'on-ijobiy (0 oy) berardi —
        shu sabab faqat "Kredit maqsadi" -> "Kafillik yoki garov" tor
        blokidan tekshiriladi, bu yerda "imtiyozli" so'zi umuman yo'q va
        to'g'ri ravishda None qaytadi. To'lov usuli ham sahifada
        tilga olinmagan — None qoladi."""
        block = extract_section(text, "Kredit maqsadi", "Kafillik")

        amount_section = extract_section(block, "Kredit miqdori", "Foiz stavkasi")
        amount = extract_amount_som(amount_section)

        rate_section = extract_section(block, "Foiz stavkasi", "Kredit muddati")
        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_RE.findall(rate_section)]

        term_section = extract_section(block, "Kredit muddati", "Boshlang‘ich to‘lov")
        terms = sorted({int(m) * 12 for m in _MORTGAGE_TERM_YEAR_RE.findall(term_section)})

        down_payment_section = extract_section(block, "Boshlang‘ich to‘lov", None)
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        grace_period_months = extract_grace_period_months(block)

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
            grace_period_months=grace_period_months,
            payment_method=None,
        )

    def _build_ipoteka_davlat_product(self, url, now, text):
        """""Yangi qurilgan uy-joy uchun ipoteka" ("mortgage-new-build") —
        sahifada aniq yozilgan: "O'zbekiston Respublikasi Iqtisodiyot va
        moliya vazirligi va bank o'z mablag'lari hisobidan birlamchi
        uy-joy bozoridan kvartira sotib olish uchun ipoteka krediti" —
        davlat (Moliya vazirligi) va bankning o'z mablag'lari aralash
        moliyalashtirilgan, "Bank ipotekasi"dagi 100% bank mablag'idan
        farqli.

        "Foiz stavkasi" bo'limida stavka va boshlang'ich badal oralig'i
        bir qatorda beriladi ("17,5% - 15% dan 30% gacha boshlang'ich
        to'lov bilan"): stavka har doim "% -" bilan tugaydigan birinchi
        raqam, boshlang'ich badal esa "% dan N% gacha"/"% dan yuqori"
        naqshiga mos keladigan ikkinchi raqam(lar) — ikkalasi uchun
        alohida regex ishlatiladi, aks holda oddiy extract_percentages
        ularni birlashtirib, rate_max'ni yolg'on ravishda 40%ga ko'tarib
        yuborardi.

        "Kredit muddati" ikki xil qiymat beradi: "20 yilgacha - Vazirlik
        mablag'lari hisobidan" va "10 yilgacha — Bank o'z mablag'lari
        hisobidan" — ikkalasi ham term_min/term_max sifatida saqlanadi
        (120/240 oy), boshqa banklardagi bir xil naqshga o'xshab.

        Sahifada aniq "Imtiyozli davr" yoki "Annuitet/Differensial"
        so'zlari umuman tilga olinmagan — ikkalasi ham None qoladi
        (taxmin qilinmaydi)."""
        block = extract_section(text, "Kredit maqsadi", "Hujjatlar")

        amount_section = extract_section(block, "Kredit miqdori", "Foiz stavkasi")
        amount = extract_amount_som(amount_section)

        rate_section = extract_section(block, "Foiz stavkasi", "Kredit muddati")
        rates = [float(m.replace(",", ".")) for m in _DAVLAT_RATE_RE.findall(rate_section)]
        down_payment_rates = [float(m) for m in _DAVLAT_DOWN_RE.findall(rate_section)]
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        term_section = extract_section(block, "Kredit muddati", "Ta")
        terms = sorted({int(m) * 12 for m in _MORTGAGE_TERM_YEAR_RE.findall(term_section)})

        if not rates or not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="ipoteka_davlat",
            product_name=self.PRODUCT_NAMES["ipoteka_davlat"],
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
            payment_method=None,
        )

    def _build_istemol_krediti_product(self, url, now, text):
        """"Iste'mol krediti" ("personal-loan") — "Kredit miqdori"
        sarlavhasi sahifada IKKI marta uchraydi: birinchisi yuqoridagi
        qisqa xulosa kartochkasida ("36 oygacha" / "26% dan boshlab"),
        ikkinchisi "Kredit haqida batafsil" bo'limidagi haqiqiy
        "Kredit shartlari" jadvalida (200 mln so'mgacha / 26-30% / 12-36
        oy). Shu sabab qidiruv "Kredit haqida batafsil" iborasidan
        keyingi matnga chegaralanadi — aks holda birinchi (noto'liq)
        uchrashuv olinib, undan keyin "Qarz yuki 50%" (daromadga nisbat
        talabi, stavka emas) ham bir bo'lakka tushib, rate_max'ni yolg'on
        ravishda 50%ga ko'tarib yuborardi.

        Stavka "12 oygacha — 26%" kabi muddat-stavka juftliklarida
        beriladi — "—" belgisidan keyingi raqam olinadi.

        "Garov ta'minoti: Kafillik yoki garov" — "garov" so'zi mavjud,
        lekin sahifaning yuqorisidagi reklama blokida "Garovsiz — 50 mln
        so'mgacha bo'lgan kreditlar uchun" iborasi bor va "Qarz oluvchiga
        talablar" bo'limida ham aloqasiz "qarzdorlik mavjud emasligi"
        iborasi bor — ikkalasi ham has_collateral_requirement'ning butun
        sahifa yoki hatto "batafsil" tail bo'yicha tekshiruvini yolg'on-
        manfiy qilib yuborardi. Shu sabab tekshiruv faqat "Garov
        ta'minoti" -> "Hujjatlar" tor blokida o'tkaziladi. "Imtiyozli
        davr: Imtiyozli davr mavjud emas" — 0 oy."""
        tail = text[text.find("Kredit haqida batafsil"):]
        block = extract_section(tail, "Kredit miqdori", "Qarz yuki")

        amount_section = extract_section(block, "", "Foiz stavkasi")
        amount = extract_amount_som(amount_section)

        rate_section = extract_section(block, "Foiz stavkasi", "Kredit muddati")
        rates = [float(m) for m in re.findall(r"—\s*(\d{1,2})%", rate_section)]

        term_section = extract_section(block, "Kredit muddati", None)
        terms = [int(m) for m in re.findall(r"(\d{1,2})\s*oy\b", term_section)]

        grace_section = extract_section(tail, "Imtiyozli davr", "Qarz oluvchi va")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        collateral_section = extract_section(tail, "Garov ta", "Hujjatlar")

        if not rates or not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="istemol_krediti",
            product_name=self.PRODUCT_NAMES["istemol_krediti"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(collateral_section),
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=None,
        )

    def _build_mikroqarz_product(self, url, now, text):
        """"Mikrokredit Plus" — "O'zini o'zi band qilganlarga garov evaziga
        ajratiladi" (avtomobil/ko'chmas mulk garovi bilan), ariza bank
        ofisida to'ldiriladi — oflayn "mikroqarz" toifasi. Stavka jadvali
        qarz yuki va garov (avtomobil yoshi) toifalariga qarab 4 xil
        qatorda beriladi, har qatorda "12 oygacha X%" / "60 oygacha Y%"
        juftligi bor. Qator boshidagi "Qarz yuki 50% gacha ..." izohi ham
        "%" bilan yozilgan — shu sabab faqat "N oygacha" dan KEYIN
        keladigan foizlar olinadi, mustaqil "50%" izohi mos kelmaydi.
        To'lov usuli va imtiyozli davr sahifada umuman tilga olinmagan."""
        rate_section = extract_section(text, "Qarz yuki 50", "Kredit muddati\n\n\n\n\n\n\n\n5")
        pairs = _MIKROQARZ_RATE_RE.findall(rate_section)
        rates = [float(rate.replace(",", ".")) for _term, rate in pairs]

        summary_section = extract_section(text, "Ariza qoldirish", "Foiz stavkasi")
        terms = extract_term_months(summary_section)

        amount_section = extract_section(text, "20,6", "Foiz stavkasi")
        amount = extract_amount_som(amount_section)

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
            payment_method=None,
        )

    def _build_mikroqarz_onlayn_product(self, url, now, text):
        """"Onlayn kredit" — sahifa sarlavhasida "garovsiz" (mulk garovi
        talab qilinmaydi, faqat pasport kerak) va "Ariza berish joyi:
        Hamkor ilovasida" deb aniq yozilgan (mobil ilova orqali, ofisga
        bormasdan) — mikroqarz_onlayn toifasiga kiradi. Sahifa sarlavhasi
        (<title>) hattoki "Bir necha daqiqa ichida kartaga mikroqarz" deydi.

        Muddat "6 oydan 3 yilgacha" — aralash birlik oralig'i (oy dan
        yilgacha), standart _TERM_RANGE_RE ("N oydan M oygacha") yoki
        _TERM_YEAR_RANGE_RE ("N yildan M yilgacha") ikkalasi ham mos
        kelmaydi — shu sabab maxsus regex ishlatiladi.

        Kalkulyatorda "Teng qismlarda"/"Kamayish bo'yicha" (aslida
        Annuitet/Differensial) tanlovi bor, lekin bu so'zlarning o'zi
        (Annuitet/Differensial) sahifada hech qayerda tilga olinmagan —
        shu sabab to'lov usuli taxmin qilinmaydi, None qoladi. Xuddi
        shunday "imtiyozli davr" haqida ham gap yo'q."""
        section = extract_section(text, "Onlayn kredit miqdori", "Ajratish shakli")
        rates = extract_percentages(section)
        term_match = _MIKROQARZ_ONLAYN_TERM_RE.search(section)
        amount = extract_amount_som(section)

        if not rates or term_match is None or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="mikroqarz_onlayn",
            product_name=self.PRODUCT_NAMES["mikroqarz_onlayn"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=int(term_match.group(1)),
            term_max_months=int(term_match.group(2)) * 12,
            amount_max_som=amount,
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )
