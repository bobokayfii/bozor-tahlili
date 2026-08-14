import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_percentages,
    extract_section,
    extract_term_months,
    fetch_html,
    has_collateral_requirement,
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
        "mikroqarz_onlayn": "https://tbcbank.uz/product/mikrokredit/",
        "kredit_karta": "https://tbcbank.uz/product/credit-card/",
    }
    FORCE_COLLATERAL = {
        "avtokredit_brend_birlamchi": True,
        "kredit_karta": False,
    }
    PRODUCT_NAMES = {
        "avtokredit_brend_birlamchi": "TBC Avtokredit",
        "mikroqarz_onlayn": "TBC mikroqarz",
        "kredit_karta": '"TBC Osmon" kredit kartasi',
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)
                if category == "avtokredit_brend_birlamchi":
                    product = self._build_avtokredit_brend_birlamchi_product(url, now, text)
                elif category == "kredit_karta":
                    product = self._build_kredit_karta_product(url, now)
                else:
                    product = self._build_mikroqarz_onlayn_product(url, now, text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_kredit_karta_product(self, url, now):
        """"TBC Osmon" kredit kartasi — sahifaning o'zida (55 kunlik
        imtiyozli davr, 50 mln so'mlik limit va jarima stavkalari bundan
        mustasno) haqiqiy foiz stavkasi umuman ko'rsatilmagan — "Bu foiz
        stavkasini TBC UZ ilovasining ... 'Shartlar' bo'limida bilib
        olishingiz mumkin" deb aniq yozilgan. Saytdan stavka olib
        bo'lmagani uchun (foydalanuvchining aniq ko'rsatmasiga ko'ra)
        raqamlar mustaqil tasdiqlangan pptx manbasidan olindi (0-50%,
        55 kun imtiyozli davr, 50 mln so'm limit, "Аннуитетный,
        дифференциальный" to'lov usuli) — bu bitta istisno, boshqa hech
        bir toifada pptx raqamlari to'g'ridan-to'g'ri ishlatilmaydi."""
        return Product(
            bank=self.bank_name,
            category="kredit_karta",
            product_name=self.PRODUCT_NAMES["kredit_karta"],
            rate_min=0.0,
            rate_max=50.0,
            term_min_months=1,
            term_max_months=2,
            amount_max_som=50_000_000,
            requires_collateral=self.FORCE_COLLATERAL["kredit_karta"],
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method="Annuitet, Differensial",
            special_terms=(
                "Imtiyozli (foizsiz) davr: 55 kungacha — aylanma kredit karta, "
                "oylik muddat emas (pptx manbasidan, saytda raqamlar ko'rsatilmagan)"
            ),
        )

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

    def _build_mikroqarz_onlayn_product(self, url, now, text):
        """"TBC mikroqarz" — butun mahsulot ilova (TBC Bank Uzbekistan)
        orqali onlayn rasmiylashtiriladi, filialga borish shart emas —
        mikroqarz_onlayn ta'rifiga to'g'ri keladi. Sahifada bosh kalkulyator
        vidjeti "3 oy"dan "36 oy"gacha bo'lgan barcha oylik variantlarni
        alohida-alohida sanab o'tadi (dropdown ro'yxati) — bu FAQ javobidagi
        "3 oydan 36 oygacha" oralig'i bilan mos, shuning uchun ziddiyat
        yo'q. Foiz stavkasi FAQ javobida ("Foiz stavkasini ham tizim
        belgilaydi: yiliga 29% dan 48% gacha") aniq oraliq sifatida
        berilgan — shu FAQ javobi tor bo'lim sifatida ajratib olinadi,
        chunki sahifada boshqa joyda ("Oshirilgan foiz ... kuniga 0,5%"
        kechiktirilgan to'lov jarimasi) aloqasiz "%" bor, butun sahifa
        matni ishlatilsa rate_min noto'g'ri 0,5%ga tushib qolardi.

        Maksimal summa alohida marketing bandida ("Uydan turib 100 000 000
        so'mgacha kredit") aniq so'm bilan berilgan.

        "Garovsiz va kafillarsiz" iborasi sahifada ikki marta aniq
        yozilgan — has_collateral_requirement() "garovsiz" so'zini inkor
        signali sifatida taniydi, shuning uchun to'g'ri False qaytaradi,
        FORCE_COLLATERAL kerak emas."""
        rate_term_section = extract_section(
            text, "mikroqarz olish 3 oydan 36 oygacha beriladi", "Arizangiz tasdiqlangandan"
        )
        rates = extract_percentages(rate_term_section)
        terms = extract_term_months("3 oydan 36 oygacha " + rate_term_section)

        amount_section = extract_section(text, "Uydan turib", "kredit")
        amount = extract_amount_som(amount_section)

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
            grace_period_months=None,
            payment_method=None,
        )
