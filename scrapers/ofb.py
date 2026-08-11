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
    html_to_text,
)

# Stavka jadvalining har bir qatorida IKKITA foiz bor — boshlang'ich badal
# ulushi (25/30/40/50%) VA shu ulushga mos haqiqiy stavka (masalan,
# "25% dan — yillik 24,5%") — oddiy extract_percentages ikkalasini ham
# aralashtirib yuborardi. Faqat "dan —" dan KEYIN keladigan raqam olinadi.
# "Oson avtokredit" sahifasida stavka so'zi "yillik" bilan, "Avtokredit
# BYD" sahifasida "yillik"siz yoziladi — shu farqni `(?:yillik\s*)?`
# ixtiyoriy guruhi qamrab oladi, regex ikkala sahifada ham ishlaydi.
_RATE_TIER_RE = re.compile(r"dan\s*—\s*\n?\s*(?:yillik\s*)?(\d{1,2}(?:,\d{1,2})?)%")
# "Avtokredit BYD" sahifasida muddat "36 yoki 60 oyga" shaklida beriladi
# ("oygacha" so'zisiz) — standart extract_term_months buni tanimaydi
# (u faqat "N oygacha"/"N oydan M oygacha" naqshlarini kutadi). Ikkinchi
# guruh ixtiyoriy, chunki ba'zan faqat bitta muddat ko'rsatilishi mumkin.
_TERM_PAIR_RE = re.compile(r"(\d{1,3})\s*(?:yoki\s*(\d{1,3})\s*)?oyga\b")
# "Foydali ipoteka" (ipoteka_davlat) sahifasida muddat "240 oygacha" (20
# yil) — standart extract_term_months'ning 120 oylik qattiq chegarasidan
# oshib ketadi va shu sabab standart funksiya bu qiymatni butunlay
# CHIQARIB TASHLAYDI (bo'sh ro'yxat qaytaradi). Boshqa banklardagi >120
# oylik ipoteka muddatlari bilan bir xil yechim — to'g'ridan-to'g'ri
# regex (masalan scrapers/bdb.py'dagi _YEAR_TERM_RE, scrapers/aab.py).
_IPOTEKA_DAVLAT_TERM_RE = re.compile(r"(\d{1,3})\s*oygacha")


class OFBScraper(TextSectionScraper):
    """OFB (Orient Finans Bank, ofb.uz) — "Oson avtokredit" va "Avtokredit
    BYD" (elektromobil) sahifalari AYNAN bir xil FAQ shabloniga ega
    ("Kredit qancha muddatga beriladi?", "Foiz stavkasi qancha?" va h.k.
    sarlavhalari bilan), faqat raqamlar farq qiladi — BYD elektromobil
    uchun stavkalar pastroq (rag'batlantirish siyosati bo'lishi mumkin) va
    muddat "N oygacha" o'rniga "36 yoki 60 oyga" (ikkita aniq variant)
    shaklida beriladi. Har ikkala kategoriya ham CATEGORY_URLS orqali o'z
    alohida sahifasidan olinadi.

    Ikkala metod ham self._build_product()ga emas, balki Product(...)ga
    to'g'ridan-to'g'ri qurilgan (scrapers/sqb.py'dagi
    _build_ipoteka_davlat_product uslubiga o'xshab) — chunki summa, muddat
    va stavka sahifaning turli, bir-biridan uzoq bo'laklaridan yig'iladi va
    ular orasida (ayniqsa "None" end_heading bilan sahifa oxirigacha
    cho'ziladigan bo'limlarda) begona foiz/raqamlar bor, bitta umumiy
    kengroq section'ga sig'dirib bo'lmaydi.

    Har ikkala sahifada ham pastroqda "Kreditlash shartlari" umumiy
    shablon jadvali bor — "Jadval turi" (to'lov usuli) qatori bu ikkala
    avtokredit sahifasida yo'q (shu sabab payment_method None qoladi), lekin
    "Imtiyoz davrining muddati" qatori BOR va aniq "ko'zda tutilmagan" deb
    yozilgan — bu real, mahsulotga xos "imtiyozli davr yo'q" signali (0 oy),
    "noma'lum" emas, shu sabab grace_period_months ikkalasida ham 0 qilib
    to'ldiriladi (pastga qarang).

    "mikroqarz" ("Ishonch mikroqarz") va "mikroqarz_onlayn" ("Onlayn
    mikroqarz") — ikkalasi ham https://ofb.uz/kreditlar/mikroqarzlar hub
    (ro'yxat) sahifasidagi kartochkalardan olinadi, bu sahifa run()da
    BITTA marta fetch qilinib ikkalasiga ham beriladi (pastga qarang).
    mikroqarz_onlayn uchun esa muddat hub sahifasida umuman yo'q, shu
    sabab qo'shimcha ravishda o'zining alohida sahifasi ham
    (https://ofb.uz/kreditlar/onlayn-mikroqarz) fetch qilinadi.

    "kredit_karta" ("Kredit karta Niyat") boshqa barcha kategoriyalardan
    farqli o'laroq `/kreditlar/` emas, `/kartalar/` yo'lida joylashgan
    (https://ofb.uz/kartalar/niyat-kredit-kartasi). Bu sahifada boshqa
    kategoriyalardagi kabi tarqoq FAQ bo'limlari emas, balki ozoda
    "Parametr / Shart" jadvali bor — har bir sarlavha ("Amal qilish
    muddati", "Imtiyozli muddat", "Maksimal summa", "Foiz stavkasi")
    sahifada FAQAT bir marta uchraydi, shu sabab boshqa kategoriyalardagi
    kabi bir necha bosqichli toraytirish yoki maxsus regexlar kerak
    emas — har bir maydon o'zining ikki qo'shni sarlavhasi orasidan
    to'g'ridan-to'g'ri olinadi."""

    bank_name = "OFB"
    url = "https://ofb.uz/kreditlar"
    CATEGORY_URLS = {
        "avtokredit": "https://ofb.uz/kreditlar/oson-avtokredit",
        "avtokredit_ikkilamchi": "https://ofb.uz/kreditlar/ikkilamchi-bozor-uchun-avtokredit",
        "avtokredit_elektro": "https://ofb.uz/kreditlar/avtokredit-byd",
        # "mikroqarz" va "mikroqarz_onlayn" ikkalasi ham shu hub/ro'yxat
        # sahifasidagi kartochkalardan summasi+stavkasini oladi — run()da bu
        # sahifa BITTA marta fetch qilinadi va ikkala kategoriyaga ham
        # beriladi (pastdagi izohga qarang). source_url sifatida esa har biri
        # o'zining eng mos, mustaqil sahifasini ko'rsatadi.
        "mikroqarz": "https://ofb.uz/kreditlar/mikroqarzlar",
        "mikroqarz_onlayn": "https://ofb.uz/kreditlar/onlayn-mikroqarz",
        "ipoteka_davlat": "https://ofb.uz/kreditlar/foydali-ipoteka",
        # DIQQAT: bu boshqa barcha OFB kategoriyalaridan farqli `/kartalar/`
        # yo'lida joylashgan, `/kreditlar/`da EMAS — sahifa haqiqatan ham
        # shu manzilda joylashgani jonli saytdan tasdiqlangan.
        "kredit_karta": "https://ofb.uz/kartalar/niyat-kredit-kartasi",
    }
    PRODUCT_NAMES = {
        "avtokredit": "Oson avtokredit",
        "avtokredit_ikkilamchi": "Ikkilamchi bozor uchun avtokredit",
        "avtokredit_elektro": "Avtokredit BYD",
        # Sahifa sarlavhasi (<title>) va "Foydali ipoteka" H1/breadcrumb
        # ikkalasi ham aynan shu shaklda, brifdagi taklif tasdiqlandi.
        "ipoteka_davlat": "Foydali ipoteka",
        # Brifda "Ishonch mikroqarzi" (grammatik egalik shakli) taklif
        # qilingan edi, lekin na hub sahifada, na mahsulotning o'z alohida
        # sahifasida (https://ofb.uz/kreditlar/ishonch-mikroqarz, faqat
        # tekshirish uchun fetch qilingan, run()da ishlatilmaydi) bu shakl
        # uchramaydi — sayt hamma joyda "Ishonch mikroqarz" deb yozadi
        # (<title>ning o'zida ham xuddi shunday), shu haqiqiy shakl
        # ishlatilgan.
        "mikroqarz": "Ishonch mikroqarz",
        "mikroqarz_onlayn": "Onlayn mikroqarz",
        # Sahifaning H1 sarlavhasi aslida teskari so'z tartibida ("Niyat
        # kredit kartasi") — bu shakl esa navigatsiya menyusidagi havola
        # matnida ikki marta aynan shu ko'rinishda uchraydi, jonli
        # sahifadan tasdiqlangan.
        "kredit_karta": "Kredit karta Niyat",
    }
    # Ikkalasi ham avtokredit — sotib olinayotgan avtomobilning o'zi garov
    # bo'lib xizmat qiladi (boshqa banklardagi avtokredit konvensiyasi
    # bilan bir xil), sahifa matnida buni aniq "garov" so'zi bilan
    # yozilmasa ham.
    FORCE_COLLATERAL = {
        "avtokredit": True,
        "avtokredit_ikkilamchi": True,
        "avtokredit_elektro": True,
        # Hub sahifasida ("mikroqarzlar") "Ishonch" kartochkasi uchun garov
        # haqida umuman gap yo'q (has_collateral_requirement standart
        # bo'yicha ham False qaytaradi). DIQQAT: mahsulotning o'z alohida
        # sahifasi (ishonch-mikroqarz, run()da FETCH QILINMAYDI, faqat shu
        # topilmani hujjatlash uchun tekshirilgan) aslida buni murakkabroq
        # tasvirlaydi — "Ta'minot" bandida "Jismoniy shaxslarning
        # kafilligi... YOKI Bank talablarini qondiradigan BOSHQA GAROV
        # ta'minoti (ko'char mulk yoki, rasmiy daromadi yo'q mijozlar uchun,
        # ko'chmas mulk garovi)" deyilgan — ya'ni ba'zi mijoz toifalari uchun
        # haqiqiy mulk garovi talab qilinishi mumkin. Task 2 doirasi faqat
        # hub sahifasidan foydalanishni belgilaganligi sababli va u yerda
        # bu haqda aniq gap bo'lmagani uchun, brifning "aniq bo'lmasa False"
        # ko'rsatmasiga muvofiq False qoldirilgan — bu soddalashtirish
        # sifatida hisobotda alohida qayd etilgan.
        "mikroqarz": False,
        # Mahsulotning o'z alohida sahifasida ("onlayn-mikroqarz", term
        # uchun run()da fetch qilinadi) "Ta'minot" bandi ANIQ va shartsiz:
        # "Kreditni qaytarmaslik xavfiga qarshi sug'urta polisi. Sug'urta
        # mukofoti bank tomonidan to'lanadi." va "Ta'minot miqdori:
        # Mikroqarz summasining kamida 125%" — mulk garovi emas, faqat
        # sug'urta polisi (SQB'ning xuddi shu nomdagi "mikroqarz_onlayn"
        # kategoriyasidagi bilan bir xil konvensiya).
        "mikroqarz_onlayn": False,
        # Ipoteka har doim ko'chmas mulk garovi bilan ta'minlanadi (boshqa
        # banklardagi ipoteka_davlat konvensiyasi bilan bir xil, masalan
        # scrapers/sqb.py, scrapers/aab.py, scrapers/ipoteka.py) — sahifaning
        # o'zida ham "Ta'minot: Sotib olinadigan xonadon va bank
        # talablariga muvofiq boshqa ta'minot" deyilgan, garchi "garov"
        # so'zining o'zi ishlatilmasa ham (has_collateral_requirement bu
        # holatda False qaytargan bo'lardi).
        "ipoteka_davlat": True,
        # Kredit karta — ipoteka/avtokredit kabi jismoniy garov talab
        # qilmaydi (boshqa banklardagi kredit_karta konvensiyasi bilan bir
        # xil, masalan scrapers/sqb.py'ning "credit-card-new-uz" sahifasida
        # ham FORCE_COLLATERAL orqali forceanmagan — sababi sodda: sahifada
        # "garov" so'zi umuman uchramaydi). Jonli "niyat-kredit-kartasi"
        # sahifasida ham "garov" so'zi bir marta ham uchramagani
        # tasdiqlandi, shu sabab bu yerda ham aniq False belgilangan
        # (standart has_collateral_requirement bu holatda baribir False
        # qaytargan bo'lardi, lekin boshqa kategoriyalar kabi izchillik
        # uchun aniq belgilash afzal ko'rildi).
        "kredit_karta": False,
    }

    def run(self) -> list[Product]:
        now = datetime.now(timezone.utc)
        products: list[Product] = []

        # "mikroqarz" va "mikroqarz_onlayn" ikkalasi ham shu hub sahifasidan
        # (kartochkalar ro'yxati) summasi+stavkasini o'qiydi — ikki marta
        # fetch qilib yubormaslik uchun bu yerda BITTA marta, oldindan
        # olinadi va pastdagi tsiklda ikkala mos build metodiga ham
        # o'zgarmas argument sifatida uzatiladi. Hub o'zi ham
        # CATEGORY_URLS["mikroqarz"] orqali olinadi (bu shu bilan birga
        # "mikroqarz" kategoriyasining o'z source_url'i ham).
        try:
            hub_html = fetch_html(self.CATEGORY_URLS["mikroqarz"], extra_ca_cert=self.EXTRA_CA_CERT)
            hub_text = html_to_text(hub_html)
        except Exception:
            hub_text = None

        for category, url in self.CATEGORY_URLS.items():
            try:
                if category == "avtokredit":
                    text = html_to_text(fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT))
                    product = self._build_avtokredit_product(url, now, text)
                elif category == "avtokredit_ikkilamchi":
                    text = html_to_text(fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT))
                    product = self._build_avtokredit_ikkilamchi_product(url, now, text)
                elif category == "avtokredit_elektro":
                    text = html_to_text(fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT))
                    product = self._build_avtokredit_elektro_product(url, now, text)
                elif category == "mikroqarz":
                    if hub_text is None:
                        continue
                    product = self._build_mikroqarz_product(url, now, hub_text)
                elif category == "mikroqarz_onlayn":
                    if hub_text is None:
                        continue
                    onlayn_text = html_to_text(fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT))
                    product = self._build_mikroqarz_onlayn_product(url, now, hub_text, onlayn_text)
                elif category == "ipoteka_davlat":
                    text = html_to_text(fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT))
                    product = self._build_ipoteka_davlat_product(url, now, text)
                else:  # kredit_karta
                    text = html_to_text(fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT))
                    product = self._build_kredit_karta_product(url, now, text)
            except Exception:
                continue
            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, url, now, text):
        """"Oson avtokredit" — summa "Avtokreditning maksimal miqdori" ->
        "Kredit qancha muddatga" tor oralig'ida ("— 800 mln so'mgacha"),
        muddat "Kredit qancha muddatga beriladi?" -> "Foiz stavkasi
        qancha?" oralig'ida ("60 oygacha" — standart extract_term_months
        bilan muammosiz o'qiladi).

        Boshlang'ich badal bo'limi uchun brifda taklif qilingan yakuniy
        sarlavha ("Boshlang'ich to'lov qancha yuqori") sahifada ASCII
        apostrof bilan yozilgan edi, lekin haqiqiy sahifada bu ibora
        Unicode chap qo'shtirnoq (U+2018 '‘') bilan yozilgan — ASCII bilan
        mos kelmagani uchun extract_section end_heading topolmay qolib,
        bo'lim sahifa oxirigacha cho'zilib ketardi va tasodifan yana bitta
        begona 30% ni ham qamrab olardi (min() bilan baribir to'g'ri 25.0
        chiqadi, lekin bu ishonchsiz edi). Shu sabab o'rniga keyingi
        HAQIQIY sarlavha — "Qaysi avtomobillarni kreditga olish mumkin?"
        — end_heading sifatida ishlatiladi, bu bo'limni bitta aniq "25%"
        ga toraytiradi.

        "Imtiyoz davrining muddati" -> "Pasport" (hujjatlar ro'yxatidagi
        keyingi band, sahifada FAQAT bir marta uchraydi) oralig'ida aniq
        "ko'zda tutilmagan" deb yozilgan — standart extract_grace_period_months
        "imtiyozli" so'zi borligini talab qilgani uchun (sarlavhaning o'zida
        yo'q, "imtiyoz" xolos) bu so'z qo'lda prefiks sifatida qo'shiladi."""
        amount_section = extract_section(text, "Avtokreditning maksimal miqdori", "Kredit qancha muddatga")
        amount = extract_amount_som(amount_section)

        term_section = extract_section(text, "Kredit qancha muddatga beriladi?", "Foiz stavkasi qancha?")
        terms = extract_term_months(term_section)

        rate_section = extract_section(text, "Foiz stavkasi qancha?", "Minimal boshlang")
        rates = [float(m.replace(",", ".")) for m in _RATE_TIER_RE.findall(rate_section)]

        down_payment_section = extract_section(text, "Minimal boshlang", "Qaysi avtomobillarni")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        grace_section = extract_section(text, "Imtiyoz davrining muddati", "Pasport")
        grace_period_months = extract_grace_period_months("imtiyozli" + grace_section)

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
            payment_method=None,
        )

    def _build_avtokredit_ikkilamchi_product(self, url, now, text):
        """"Ikkilamchi bozor uchun avtokredit" — "Oson avtokredit" bilan
        bir xil FAQ shabloniga ega ("Avtokreditning maksimal miqdori" ->
        "800 mln so'mgacha", "Kredit qancha muddatga beriladi?" -> "48
        oygacha"), lekin stavka jadvali boshqacha shaklda: "Foiz stavkasi
        qancha?" javobida ikkita alohida gap bor — "boshlang'ich to'lov
        kamida 30% bo'lsa — yillik 26,9%" va "40% dan yuqori bo'lsa —
        yillik 24,9%" — bu yerda tier ulushi HAM "yillik" so'zidan OLDIN,
        HAM undan keyin foiz belgisi bilan yozilgan bo'lishi mumkin
        ("Oson avtokredit"dagi "dan —" naqshiga mos kelmaydi), shu sabab
        _RATE_TIER_RE o'rniga to'g'ridan-to'g'ri "yillik N%" iboralari
        qidiriladi — ikkala qatorda ham faqat shu so'zdan keyin keladigan
        raqam haqiqiy stavka, tier ulushlari (30%/40%) "yillik" so'zisiz
        yoziladi, shu sabab aralashmaydi.

        "Imtiyoz davrining muddati" -> "Pasport" oralig'ida aniq "ko'zda
        tutilmagan" — "Oson avtokredit"dagi bilan bir xil naqsh, 0 oy."""
        amount_section = extract_section(text, "Avtokreditning maksimal miqdori", "Kredit qancha muddatga")
        amount = extract_amount_som(amount_section)

        term_section = extract_section(text, "Kredit qancha muddatga beriladi?", "Foiz stavkasi qancha?")
        terms = extract_term_months(term_section)

        rate_section = extract_section(text, "Foiz stavkasi qancha?", "Boshlang")
        rates = [float(m.replace(",", ".")) for m in re.findall(r"yillik\s*(\d{1,2}(?:,\d{1,2})?)%", rate_section)]

        down_payment_section = extract_section(text, "Minimal boshlang", "Boshlang")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        grace_section = extract_section(text, "Imtiyoz davrining muddati", "Pasport")
        grace_period_months = extract_grace_period_months("imtiyozli" + grace_section)

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
            payment_method=None,
        )

    def _build_avtokredit_elektro_product(self, url, now, text):
        """"Avtokredit BYD" — "Oson avtokredit" bilan bir xil FAQ
        shabloniga ega, faqat raqamlar farq qiladi. Muddat "36 yoki 60
        oyga" shaklida ("oygacha"siz) beriladi — _TERM_PAIR_RE ikkala
        aniq qiymatni bitta moslikdan ("36" va "60" guruhlari) oladi.

        Boshlang'ich badal sarlavhasi ("Boshlang‘ich badal avtomobil
        qiymatining kamida") to'g'ridan-to'g'ri Unicode chap qo'shtirnoq
        (U+2018) bilan yozilgan — bu yerda "Boshlang" kabi qisqartirilgan
        ASCII-xavfsiz anchor ishlatib bo'lmaydi, chunki sahifada yuqorida
        alohida umumiy kredit kalkulyatori vidjeti bor va "Boshlang" so'zi
        o'sha yerda ham bir necha marta takrorlanadi — shu sabab to'liq,
        noyob ibora talab qilinadi.

        "Imtiyoz davrining muddati" -> "Pasport" oralig'ida aniq "ko'zda
        tutilmagan" deb yozilgan, xuddi "Oson avtokredit" sahifasidagi
        bilan bir xil ("imtiyozli" so'zi qo'lda prefiks sifatida
        qo'shiladi, chunki sarlavhaning o'zida "imtiyoz" bor, "imtiyozli"
        emas)."""
        amount_section = extract_section(text, "Avtokredit miqdori", "Kredit qancha muddatga")
        amount = extract_amount_som(amount_section)

        term_section = extract_section(text, "Kredit qancha muddatga beriladi?", "Foiz stavkasi qancha?")
        term_match = _TERM_PAIR_RE.search(term_section)
        terms = [int(g) for g in term_match.groups() if g] if term_match else []

        rate_section = extract_section(text, "Foiz stavkasi qancha?", "Boshlang")
        rates = [float(m.replace(",", ".")) for m in _RATE_TIER_RE.findall(rate_section)]

        down_payment_section = extract_section(
            text, "Boshlang‘ich badal avtomobil qiymatining kamida", "Rasmiy daromadi"
        )
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        grace_section = extract_section(text, "Imtiyoz davrining muddati", "Pasport")
        grace_period_months = extract_grace_period_months("imtiyozli" + grace_section)

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
            payment_method=None,
        )

    def _build_mikroqarz_product(self, url, now, hub_text):
        """"Ishonch mikroqarz" — mikroqarzlar hub sahifasidagi ikkinchi
        kartochka ("Onlayn mikroqarz"dan keyin keladi). Kartochka sarlavhasi
        o'zi bitta so'z, "Ishonch" — lekin bu so'z sahifa yuqorisidagi
        navigatsiya/dropdown menyusida ("OFB Ishonch" — omonat mahsuloti,
        "OFB Ishonchli" — biznes krediti) ANCHA OLDINROQ ham uchraydi, shu
        sabab extract_section(hub_text, "Ishonch", ...) to'g'ridan-to'g'ri
        BUTUN hub_text'ga qo'llansa, noto'g'ri, juda erta joydan boshlab
        ketardi. Shu sabab avval "Onlayn mikroqarz" (hub sahifada FAQAT bir
        marta, aynan shu kartochka sarlavhasi sifatida uchraydi) dan
        keyingi qoldiq matn ajratib olinadi — navigatsiya menyusi undan
        oldin joylashgani uchun bu qoldiqda "Ishonch" birinchi marta aynan
        kerakli kartochka sarlavhasi sifatida uchraydi.

        Bo'lim ichida: "Miqdor\\n100\\nmln so'mgacha\\nMuddat\\n36\\noygacha\\n
        Stavka\\n24\\n% dan" — bo'lim "Kreditni hisoblash" tugmasi
        matnigacha (shu kartochkaning o'zidagi, keyingi "Corporate Plus"
        kartochkasiga o'tmasdan) toraytirilgan, shuning uchun boshqa begona
        % yo'q."""
        after_onlayn_card = extract_section(hub_text, "Onlayn mikroqarz", None)
        section = extract_section(after_onlayn_card, "Ishonch", "Kreditni hisoblash")

        amount = extract_amount_som(section)
        terms = extract_term_months(section)
        rates = extract_percentages(section)

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

    def _build_mikroqarz_onlayn_product(self, url, now, hub_text, onlayn_text):
        """"Onlayn mikroqarz" — summa va stavka hub sahifasidagi BIRINCHI
        kartochkadan ("Onlayn mikroqarz" -> keyingi "Ishonch" kartochkasi
        sarlavhasigacha, bu yerda "Ishonch" end_heading sifatida xavfsiz —
        extract_section uning navigatsiyadagi oldingi uchrashlarini emas,
        start_idx'dan KEYINGI birinchisini qidiradi, bu esa to'g'ridan-to'g'ri
        haqiqiy kartochka sarlavhasi): "Summa\\n50\\nmln so'mgacha\\nStavka\\n
        30\\n%".

        Muddat esa hub sahifasida umuman ko'rsatilmagan — faqat mahsulotning
        o'z alohida sahifasida ("onlayn-mikroqarz", run() bu yerga qo'shimcha
        fetch qiladi, chunki hub bitta o'zi yetarli emas): "Mikroqarz
        muddati\\n24 oygacha." bo'limi "Foiz stavkasi" sarlavhasigacha
        toraytirilgan (bu sahifada pastroqda 125%/50% kabi begona foizlar
        bor, lekin ular term emas, rate maydoniga aloqasi yo'q, shu bilan
        birga end_heading qo'shilishi bo'limni yanada toraytiradi).

        to'lov usuli va imtiyozli davr onlayn-mikroqarz'ning o'z sahifasida
        (hub'da emas) bor: "Jadval turi" -> "Arizani ko" oralig'ida aniq
        "Annuitet yoki differensial." (bu sarlavha sahifada FAQAT bir marta
        uchraydi), "Imtiyoz davrining muddati" -> "Pasport" oralig'ida esa
        "ko'zda tutilmagan" (boshqa OFB avtokredit sahifalaridagi bilan bir
        xil naqsh) — ikkalasi ham qo'shimcha fetch talab qilmaydi, chunki
        onlayn_text muddat uchun allaqachon xotirada."""
        amount_rate_section = extract_section(hub_text, "Onlayn mikroqarz", "Ishonch")
        amount = extract_amount_som(amount_rate_section)
        rates = extract_percentages(amount_rate_section)

        term_section = extract_section(onlayn_text, "Mikroqarz muddati", "Foiz stavkasi")
        terms = extract_term_months(term_section)

        payment_method_section = extract_section(onlayn_text, "Jadval turi", "Arizani ko")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(onlayn_text, "Imtiyoz davrining muddati", "Pasport")
        grace_period_months = extract_grace_period_months("imtiyozli" + grace_section)

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
            requires_collateral=self.FORCE_COLLATERAL["mikroqarz_onlayn"],
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_ipoteka_davlat_product(self, url, now, text):
        """"Foydali ipoteka" — davlat dasturi (Iqtisodiyot va moliya
        vazirligi mablag'lari) va bank o'z mablag'i aralash moliyalashadigan
        ipoteka. Sahifada raqamlangan qisqa xulosa bor: "01. Kredit
        summasi" -> "02. Kredit muddati" -> "03. Foiz stavkasi".

        Summa bo'limida UCHTA raqam bor: "1,06 mlrd so'mgacha —
        Toshkentda\\n(480 mln so'mgacha davlat dasturi bo'yicha, qolgan
        summa — bank hisobidan)\\n960 mln so'mgacha — hududlarda\\n(380
        mln so'mgacha davlat dasturi bo'yicha...)" — bular umumiy
        Toshkent chegarasi (1,06 mlrd) va ikkita kichikroq davlat-dasturi
        sub-limiti (480 mln, 380 mln) va hududiy umumiy chegara (960
        mln). Platformaning sxemasi bitta amount_max_som talab qiladi —
        mijoz olishi mumkin bo'lgan ENG KATTA umumiy summa, ya'ni 1,06
        mlrd (Toshkent). extract_amount_som allaqachon barcha topilgan
        summalar orasidan max() ni oladi, shu sabab qo'shimcha maxsus
        regexsiz ham to'g'ri (1 060 000 000) natija beradi — mln
        naqshlari (480/960/380 mln) hammasi 1,06 mlrddan kichik.

        Muddat "240 oygacha" (20 yil) — standart extract_term_months
        buni 120 oylik qattiq chegarasi tufayli CHIQARIB TASHLAYDI (bo'sh
        ro'yxat), shu sabab _IPOTEKA_DAVLAT_TERM_RE orqali to'g'ridan-to'g'ri
        regex bilan olinadi (boshqa >120 oylik ipoteka mahsulotlari bilan
        bir xil yechim, masalan scrapers/bdb.py).

        Stavka bo'limi "03. Foiz stavkasi" dan sahifadagi KEYINGI "Kredit
        summasi" uchrashigacha (kalkulyator vidjetining "Kredit summasi"
        yorlig'i) toraytirilgan — bu juda tor oraliq bo'lib, faqat "Davlat
        qismi bo'yicha — yiliga 17%\\nBank tomonidan beriladigan qism
        bo'yicha — yiliga 25%" ni o'z ichiga oladi, begona foizlar yo'q.

        Boshlang'ich badal, imtiyozli davr va to'lov usuli qisqa "01/02/03"
        xulosada YO'Q, lekin sahifa pastroqda "Kreditlash shartlari"
        yorlig'ida BATAFSILROQ jadval bor ("Kredit summasi", "Muddati",
        "Foiz stavkasi", "Boshlang'ich badal" — "25% dan", "To'lov" —
        "Oylik", "Jadval" — "annuitet yoki differensial", "Ta'minot",
        "Imtiyoz davrining muddati" — "6 oy"). Bu uchala qiymat ham aniq
        va bor, brifning "aniq bo'lmasa None" faraz qilingan holatidan
        farqli o'laroq — implementer sahifani mustaqil tekshirib topdi.

        DIQQAT — noyob so'z "Boshlang'ich badal" sahifada BIR NECHA marta
        uchraydi: birinchi marta "Daromad talablari" bo'limidagi butunlay
        boshqa ma'noli jumlada ("Boshlang'ich badal 35% dan bo'lsa,
        daromadni tasdiqlash talab etilmaydi" — bu daromad tasdiqlashni
        talab qilmaydigan CHEGARA, eng kam boshlang'ich badal emas!),
        keyin BATAFSIL jadvaldagi haqiqiy sarlavha ("25% dan"), so'ngra
        FAQ bo'limida yana bir necha marta. Shu sabab avval "Kredit
        obyekti" (sahifada FAQAT bir marta, batafsil jadval boshida
        uchraydi) dan keyingi qoldiq olinadi, so'ngra o'sha qoldiq ichida
        "Kredit summasi" (batafsil jadvalning o'z sarlavhasi, endi
        noyob) dan keyingi qism ajratiladi — shu ikki bosqichli
        toraytirish noto'g'ri, oldinroq joylashgan "35% dan" jumlasini
        chetlab o'tadi va faqat haqiqiy "Boshlang'ich badal" sarlavhasiga
        (qiymati "25% dan") yetib boradi.

        Imtiyozli davr uchun standart extract_grace_period_months
        ishlatilmaydi — u faqat matnda "imtiyozli" so'zi (oxirida "li"
        bilan) borligini tekshiradi, lekin bu sahifadagi haqiqiy sarlavha
        "Imtiyoz davrining muddati" ("li"siz) — shu sabab extract_term_months
        to'g'ridan-to'g'ri "6 oy" (yalang' oy, "gacha"siz) dan 6 ni oladi
        (funksiyaning yalang' "N oy" fallback shoxobchasi orqali)."""
        amount_section = extract_section(text, "01. Kredit summasi", "02. Kredit muddati")
        amount = extract_amount_som(amount_section)

        term_section = extract_section(text, "02. Kredit muddati", "03. Foiz stavkasi")
        term_match = _IPOTEKA_DAVLAT_TERM_RE.search(term_section)
        term = int(term_match.group(1)) if term_match else None

        rate_section = extract_section(text, "03. Foiz stavkasi", "Kredit summasi")
        rates = extract_percentages(rate_section)

        if amount is None or term is None or not rates:
            return None

        after_kredit_obyekti = extract_section(text, "Kredit obyekti", None)
        detail_section = extract_section(after_kredit_obyekti, "Kredit summasi", None)

        down_section = extract_section(detail_section, "Boshlang", "To‘lov")
        down_rates = extract_percentages(down_section)
        down_payment_pct = min(down_rates) if down_rates else None

        payment_section = extract_section(detail_section, "Jadval", "Ta’minot")
        payment_method = extract_payment_method(payment_section)

        grace_section = extract_section(
            detail_section, "Imtiyoz davrining muddati", "zbekiston Respublikasi fuqarosining pasporti"
        )
        grace_months = extract_term_months(grace_section)
        grace_period_months = grace_months[0] if grace_months else None

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

    def _build_kredit_karta_product(self, url, now, text):
        """"Kredit karta Niyat" — boshqa OFB kategoriyalaridan farqli, bu
        sahifada tarqoq FAQ matni o'rniga ozoda "Parametr / Shart" jadvali
        bor: "Karta turi" -> "Amal qilish muddati" (3 yil) -> "OFB mobil
        ilovasida chiqarish narxi" -> "Imtiyozli muddat" (45 kungacha) ->
        "Maksimal summa" (50 million so'mgacha, qayta tiklanadigan) ->
        "Foiz stavkasi" (34%) -> "Mahsulot va xizmatlar uchun to'lov
        komissiyalari". Har bir sarlavha jonli sahifada FAQAT bir marta
        uchraydi (tekshirilgan), shu sabab bu yerda ham boshqa
        kategoriyalardagi kabi ko'p bosqichli toraytirish yoki maxsus
        regex kerak emas — har bir maydon shu jadvaldagi ikki qo'shni
        sarlavha orasidan to'g'ridan-to'g'ri olinadi.

        "million so'm" iborasi sahifada IKKI marta uchraydi — jadvaldagi
        "Maksimal summa" qatorida va pastroqdagi "Qanday kredit limiti
        mavjud?" FAQ javobida ("Karta bo'yicha maksimal limit 50 million
        so'mgacha") — lekin ikkalasi ham AYNAN BIR XIL qiymatni (50
        million) bildiradi, shu sabab bu decoy emas, shunchaki
        takrorlanish; "Maksimal summa" -> "Foiz stavkasi" tor oralig'i
        baribir faqat birinchisini qamrab oladi va natija to'g'ri chiqadi.

        Stavka bo'limi ("Foiz stavkasi" -> "Mahsulot va xizmatlar")
        atayin tor tutilgan — agar end_heading berilmasa (yoki juda
        keng bo'lsa), bo'lim pastroqdagi "0%" (mamlakat ichidagi
        komissiya) va "0,5 foizi" (mamlakat tashqarisidagi komissiya)
        kabi butunlay boshqa ma'noli foizlarni ham qamrab olib,
        rate_max'ni yolg'on ravishda pasaytirib yuborardi (min() 0%'ni
        olardi). Tor oraliq bilan bo'limda faqat "34%" qoladi — bitta
        aniq qiymat, oraliq emas (rate_min == rate_max == 34.0).

        Muddat "3 yil" (yalang', "yilgacha"/"yildan" qo'shimchasisiz)
        standart extract_term_months'ning yalang' "N yil" fallback
        shoxobchasi orqali muammosiz o'qiladi (12 oy * 3 = 36 oy) —
        maxsus regex shart emas.

        Imtiyozli (foizsiz) davr — sahifada "45 kungacha foizsiz" bir
        necha marta takrorlanadi, shu jumladan jadvalning o'zida ham
        aniq "Imtiyozli muddat: 45 kungacha" shaklida. LEKIN bu loyihada
        `Product.grace_period_months` maydoni OYLARDA ifodalanadi, sahifa
        esa muddatni faqat KUNLARDA beradi (45 kun) — bu ikkisi orasida
        yo'qotishsiz, aniq konvertatsiya yo'q: 45 // 30 = 1 oy desak,
        haqiqiy 1,5 oylik imtiyozni KAMSITIB ko'rsatamiz (foydalanuvchiga
        haqiqatdan kamroq imtiyoz bergandek tuyuladi); yaxlitlab 2 ga
        chiqarsak, ORTIQCHA ko'rsatamiz. Bu aynan shu muammo tufayli
        Apex Bank'ning kredit_karta sahifasida ("imtiyozli davr faqat
        KUNLARDA berilgan, sxema esa OYLARNI talab qiladi") butun
        kategoriya E'TIBORGA OLINMAGAN edi (scrapers/apex.py'da
        "kredit_karta" CATEGORY_URLS'da umuman yo'q — tekshirilgan).

        Bu yerda esa xuddi shu kunlik-vs-oylik muammo bo'lsa-da,
        kategoriyaning o'zi TO'LIQ chiqarib tashlanmadi — chunki qolgan
        to'rtta maydon (limit, stavka, muddat, mahsulot nomi) aniq va
        foydali, ular haqiqatan mavjud bo'lgan aniq raqamlarga
        asoslangan. Faqat noaniq/lossy bo'lgan bitta maydon —
        grace_period_months — None qoldirilgan, negaki noto'g'ri
        (yaxlitlangan) qiymatni schema birligiga (oy) zo'rlab kiritish
        "Octobank saboq"iga to'g'ridan-to'g'ri zid keladi: aniq raqam
        topa olmasang, uni O'YLAB TOPMA — shunchaki None qoldir. Bu yerda
        "topa olmaslik" emas, balki "topilgan qiymat boshqa birlikda va
        uni yo'qotishsiz o'girib bo'lmaydi" holati, lekin natija bir xil:
        None ancha ishonchli, chunki 1 yoki 2 oy — ikkalasi ham
        haqiqatga teng darajada yaqin/uzoq bo'lardi."""
        term_section = extract_section(text, "Amal qilish muddati", "OFB mobil ilovasida")
        terms = extract_term_months(term_section)

        amount_section = extract_section(text, "Maksimal summa", "Foiz stavkasi")
        amount = extract_amount_som(amount_section)

        rate_section = extract_section(text, "Foiz stavkasi", "Mahsulot va xizmatlar")
        rates = extract_percentages(rate_section)

        if not rates or not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="kredit_karta",
            product_name=self.PRODUCT_NAMES["kredit_karta"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=self.FORCE_COLLATERAL["kredit_karta"],
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )
