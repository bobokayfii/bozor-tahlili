import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
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

    Har ikkala sahifada ham pastroqda "payment_type"/"grace_period" kabi
    inglizcha placeholder so'zlar bilan generik kredit atamalari jadvali
    bor (barcha OFB mahsulot sahifalarida takrorlanadigan umumiy shablon,
    "annuitet"/"differensial"/"imtiyozli" so'zlarini o'z ichiga oladi,
    lekin mahsulotga xos aniq qiymat bermaydi) — shu sabab payment_method
    va grace_period_months ikkala kategoriyada ham None qoladi.

    "mikroqarz" ("Ishonch mikroqarz") va "mikroqarz_onlayn" ("Onlayn
    mikroqarz") — ikkalasi ham https://ofb.uz/kreditlar/mikroqarzlar hub
    (ro'yxat) sahifasidagi kartochkalardan olinadi, bu sahifa run()da
    BITTA marta fetch qilinib ikkalasiga ham beriladi (pastga qarang).
    mikroqarz_onlayn uchun esa muddat hub sahifasida umuman yo'q, shu
    sabab qo'shimcha ravishda o'zining alohida sahifasi ham
    (https://ofb.uz/kreditlar/onlayn-mikroqarz) fetch qilinadi."""

    bank_name = "OFB"
    url = "https://ofb.uz/kreditlar"
    CATEGORY_URLS = {
        "avtokredit": "https://ofb.uz/kreditlar/oson-avtokredit",
        "avtokredit_elektro": "https://ofb.uz/kreditlar/avtokredit-byd",
        # "mikroqarz" va "mikroqarz_onlayn" ikkalasi ham shu hub/ro'yxat
        # sahifasidagi kartochkalardan summasi+stavkasini oladi — run()da bu
        # sahifa BITTA marta fetch qilinadi va ikkala kategoriyaga ham
        # beriladi (pastdagi izohga qarang). source_url sifatida esa har biri
        # o'zining eng mos, mustaqil sahifasini ko'rsatadi.
        "mikroqarz": "https://ofb.uz/kreditlar/mikroqarzlar",
        "mikroqarz_onlayn": "https://ofb.uz/kreditlar/onlayn-mikroqarz",
    }
    PRODUCT_NAMES = {
        "avtokredit": "Oson avtokredit",
        "avtokredit_elektro": "Avtokredit BYD",
        # Brifda "Ishonch mikroqarzi" (grammatik egalik shakli) taklif
        # qilingan edi, lekin na hub sahifada, na mahsulotning o'z alohida
        # sahifasida (https://ofb.uz/kreditlar/ishonch-mikroqarz, faqat
        # tekshirish uchun fetch qilingan, run()da ishlatilmaydi) bu shakl
        # uchramaydi — sayt hamma joyda "Ishonch mikroqarz" deb yozadi
        # (<title>ning o'zida ham xuddi shunday), shu haqiqiy shakl
        # ishlatilgan.
        "mikroqarz": "Ishonch mikroqarz",
        "mikroqarz_onlayn": "Onlayn mikroqarz",
    }
    # Ikkalasi ham avtokredit — sotib olinayotgan avtomobilning o'zi garov
    # bo'lib xizmat qiladi (boshqa banklardagi avtokredit konvensiyasi
    # bilan bir xil), sahifa matnida buni aniq "garov" so'zi bilan
    # yozilmasa ham.
    FORCE_COLLATERAL = {
        "avtokredit": True,
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
                elif category == "avtokredit_elektro":
                    text = html_to_text(fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT))
                    product = self._build_avtokredit_elektro_product(url, now, text)
                elif category == "mikroqarz":
                    if hub_text is None:
                        continue
                    product = self._build_mikroqarz_product(url, now, hub_text)
                else:  # mikroqarz_onlayn
                    if hub_text is None:
                        continue
                    onlayn_text = html_to_text(fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT))
                    product = self._build_mikroqarz_onlayn_product(url, now, hub_text, onlayn_text)
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
        ga toraytiradi."""
        amount_section = extract_section(text, "Avtokreditning maksimal miqdori", "Kredit qancha muddatga")
        amount = extract_amount_som(amount_section)

        term_section = extract_section(text, "Kredit qancha muddatga beriladi?", "Foiz stavkasi qancha?")
        terms = extract_term_months(term_section)

        rate_section = extract_section(text, "Foiz stavkasi qancha?", "Minimal boshlang")
        rates = [float(m.replace(",", ".")) for m in _RATE_TIER_RE.findall(rate_section)]

        down_payment_section = extract_section(text, "Minimal boshlang", "Qaysi avtomobillarni")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

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
        noyob ibora talab qilinadi."""
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
            grace_period_months=None,
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
        birga end_heading qo'shilishi bo'limni yanada toraytiradi)."""
        amount_rate_section = extract_section(hub_text, "Onlayn mikroqarz", "Ishonch")
        amount = extract_amount_som(amount_rate_section)
        rates = extract_percentages(amount_rate_section)

        term_section = extract_section(onlayn_text, "Mikroqarz muddati", "Foiz stavkasi")
        terms = extract_term_months(term_section)

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
            grace_period_months=None,
            payment_method=None,
        )
