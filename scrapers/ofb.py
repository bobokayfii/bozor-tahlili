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
    va grace_period_months ikkala kategoriyada ham None qoladi."""

    bank_name = "OFB"
    url = "https://ofb.uz/kreditlar"
    CATEGORY_URLS = {
        "avtokredit": "https://ofb.uz/kreditlar/oson-avtokredit",
        "avtokredit_elektro": "https://ofb.uz/kreditlar/avtokredit-byd",
    }
    PRODUCT_NAMES = {
        "avtokredit": "Oson avtokredit",
        "avtokredit_elektro": "Avtokredit BYD",
    }
    # Ikkalasi ham avtokredit — sotib olinayotgan avtomobilning o'zi garov
    # bo'lib xizmat qiladi (boshqa banklardagi avtokredit konvensiyasi
    # bilan bir xil), sahifa matnida buni aniq "garov" so'zi bilan
    # yozilmasa ham.
    FORCE_COLLATERAL = {
        "avtokredit": True,
        "avtokredit_elektro": True,
    }

    def run(self) -> list[Product]:
        now = datetime.now(timezone.utc)
        products: list[Product] = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)
                if category == "avtokredit":
                    product = self._build_avtokredit_product(url, now, text)
                else:
                    product = self._build_avtokredit_elektro_product(url, now, text)
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
