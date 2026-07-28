import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_section,
    extract_term_months,
    fetch_html,
    html_to_text,
)

_RATE_RE = re.compile(r"yillik\s*(\d+(?:,\d+)?)%\s*dan\s*(\d+(?:,\d+)?)%\s*gacha")
_DOWN_PAYMENT_RE = re.compile(r"kamida\s*(\d+(?:,\d+)?)%")


class TBCBankScraper(TextSectionScraper):
    """TBC Bank (tbcbank.uz) — "TBC Avtokredit" sahifasi jadval emas, balki
    "Ko'p beriladigan savollar" (FAQ) matnida yozilgan: rasmiy dilerlar
    orqali KO'P turli brend (BMW, BYD, Changan, Chery, Chevrolet, Haval,
    Hyundai, KIA, Toyota, Zeekr va boshqalar) uchun FAQAT YANGI avtomobil
    sotib olishga mo'ljallangan — bitta brendga cheklanmagan (masalan,
    Ipoteka Bank'ning "Avtokredit Hyundai"sidan farqli), lekin baribir
    "avtokredit_brend_birlamchi" toifasiga to'g'ri keladi: chunki bu ham
    NBU'ning "Avtokredit KIA, Chery" (bir nechta brend birlashgan)
    mahsuloti kabi, oddiy "avtokredit" (odatda mahalliy ishlab chiqarilgan
    UzAuto/Chevrolet modellari) dan farqli o'laroq, chet el brendlari
    uchun alohida shartnoma sifatida taqdim etiladi.

    Sahifaning o'zida (kalkulyator vidjeti ustida) aniq stavka/summa
    ko'rsatilmagan — "Avtomobilning aniq narxi va kredit foiz stavkasini
    TBC UZ ilovasida bilib olishingiz mumkin" deyilgan. Shuningdek, sahifa
    pastida "Kreditning asosiy shartlari to'g'risida axborot varaqasi"
    degan rasmiy shakl bor, lekin u "Mikroqarz" / "Shaxsiy ehtiyojlar
    uchun" nomli, avtokreditga umuman aloqasi yo'q boshqa mahsulot uchun
    to'ldirilgan (kalkulyator demo namunasi, ehtimol butun saytda bir xil
    shablon ishlatilgani sabab) — shu sababli bu bo'lim butunlay e'tiborga
    olinmaydi.

    Haqiqiy raqamlar FAQ javoblarida keladi: "TBC Bank avtokreditining
    shartlari qanday?" savoliga javoban "Avtokreditni 12 oydan 60 oygacha
    bo'lgan muddatga, 1 mlrd so'mgacha yillik 0% dan 29,5% gacha bo'lgan
    stavka bilan rasmiylashtirsa bo'ladi" deyilgan — bu yerda aniq quyi
    (0%) va yuqori (29,5%) chegara bor. Pastroqdagi qisqa marketing
    ro'yxati ("foiz stavkasi — yillik 29,5% gacha") faqat yuqori chegarani
    takrorlaydi, quyi chegarasiz — shu sabab FAQ javobi ustuvor manba
    sifatida ishlatiladi. Boshlang'ich to'lov alohida savolda ("Boshlang'ich
    to'lov kerakmi?") "kamida 25%" deb aniq yozilgan.

    To'lov usuli (Annuitet/Differensial) va imtiyozli davr haqida
    avtokredit uchun hech qanday aniq gap yo'q (yagona "Annuitet" so'zi
    yuqoridagi aloqasiz Mikroqarz namunasida uchraydi) — shu sabab
    ikkalasi ham None qoldiriladi.

    Garov: FAQ'da "Kredit to'liq yopilguncha avtomobil bankda garovda
    turadi" deb aniq yozilgan, lekin sahifaning boshqa joyida (aloqasiz
    Mikroqarz namunasidagi "Qo'shimcha xarajatlar: Mavjud emas" kabi)
    "mavjud emas" so'zi ham bor — umumiy has_collateral_requirement()
    "mavjud emas" ni butun sahifa bo'yicha yolg'on-manfiy signal sifatida
    o'qiydi. Shu sabab garov FORCE_COLLATERAL orqali aniq True qilib
    belgilangan, matndan taxmin qilinmaydi."""

    bank_name = "TBC Bank"
    url = "https://tbcbank.uz/product/avtokredit/"
    CATEGORY_URLS = {
        "avtokredit_brend_birlamchi": "https://tbcbank.uz/product/avtokredit/",
    }
    FORCE_COLLATERAL = {
        "avtokredit_brend_birlamchi": True,
    }
    PRODUCT_NAMES = {
        "avtokredit_brend_birlamchi": "TBC Avtokredit",
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)
                product = self._build_avtokredit_brend_birlamchi_product(url, now, text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_brend_birlamchi_product(self, url, now, text):
        terms_section = extract_section(
            text, "avtokreditining shartlari qanday ?", "Mashinaning egasi"
        )
        rate_match = _RATE_RE.search(terms_section)
        if rate_match is None:
            return None
        rate_min = float(rate_match.group(1).replace(",", "."))
        rate_max = float(rate_match.group(2).replace(",", "."))

        terms = extract_term_months(terms_section)
        amount = extract_amount_som(terms_section)

        down_payment_section = extract_section(
            text, "Boshlang", "avtokreditining shartlari qanday ?"
        )
        down_payment_match = _DOWN_PAYMENT_RE.search(down_payment_section)
        down_payment_pct = float(down_payment_match.group(1).replace(",", ".")) if down_payment_match else None

        if not terms or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="avtokredit_brend_birlamchi",
            product_name=self.PRODUCT_NAMES["avtokredit_brend_birlamchi"],
            rate_min=rate_min,
            rate_max=rate_max,
            term_min_months=min(terms),
            term_max_months=max(terms),
            amount_max_som=amount,
            requires_collateral=self.FORCE_COLLATERAL["avtokredit_brend_birlamchi"],
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )
