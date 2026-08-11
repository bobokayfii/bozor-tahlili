import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import extract_payment_method, extract_section, fetch_html, html_to_text

_DOWN_PAYMENT_RE = re.compile(r"Первоначальный взнос не менее (\d{1,2})%")
_AMOUNT_RE = re.compile(r"Сумма кредита до (\d{1,4})\s*млн\s*сум")
_RATE_RE = re.compile(r"Процентная ставка (\d{1,2}(?:,\d)?)%\s*годовых")
_TERM_RE = re.compile(r"Срок до (\d{1,3})\s*месяцев")
_MIKROZAYM_AMOUNT_RE = re.compile(r"До (\d{1,4})\s*млн\s*сум")
_MIKROZAYM_RATE_RE = re.compile(r"от (\d{1,2})% до (\d{1,2})%")
_MIKROZAYM_TERM_RE = re.compile(r"Срок (\d{1,3}) месяцев")


class AnorbankScraper(TextSectionScraper):
    """Anorbank (anorbank.uz) mahsulot sahifalari /uz/ manzil ostida ham
    (masalan https://anorbank.uz/uz/credits/avtokredit/) navigatsiyasi
    o'zbekcha, lekin CMS'dan olinadigan asosiy mahsulot matni (stavka/
    muddat/summa) baribir ruscha (kirill) qoladi — o'zbekcha-lotin
    muqobili umuman yo'q, to'g'ridan-to'g'ri tekshirilgan. scrapers/
    utils.py'dagi extract_term_months/extract_amount_som o'zbekcha
    so'zlarga ("oygacha", "mln so'm") tayanadi va ruscha matnda umuman
    ishlamaydi, shu sabab bu ikkalasi uchun bankka xos regexlar
    ishlatiladi. extract_percentages (raqam+% shakli til-neytral) va
    extract_payment_method ("annuitet"/"differen" so'zlari kalkulyator
    vidjetining o'zida ham ishlatilgani uchun) ishlaydi, lekin aniqlik
    uchun bu yerda ham to'g'ridan-to'g'ri regex ishlatildi.

    "Условия автокредита" -> "Kalkulyator" sarlavhalari har bir avtokredit
    sahifasida aynan bir marta uchraydi va atigi ~500 belgilik tor blokni
    belgilaydi. Shu sabab ma'lumot doimo shu tor oraliqdan olinadi, butun
    sahifa matnidan emas — bu aniq bir kontaminatsiya holati kuzatilgani
    uchun emas, balki tor oraliqqa tayanish butun sahifani skanerlashga
    qaraganda umumiy ehtiyot chorasi sifatida afzalroq bo'lgani uchun.

    requires_collateral avtokredit ikkala toifasi uchun ham True qattiq
    kodlangan — avtomobilning o'zi garov bo'lishi kredit turi orqali
    nazarda tutiladi, biroq sahifa matnida bu alohida so'z bilan
    aytilmaydi. grace_period_months esa None qattiq kodlangan, chunki
    ikkala avtokredit sahifasida ham imtiyozli davr haqida hech qanday
    ma'lumot yo'q.

    "Автокредит 3.0" sahifasining o'zbekcha (JS-render qilinmagan) qismida
    "Foiz stavkasi" va "Avtokredit muddati" maydonlariga biriktirilgan
    izoh bor: "Ikkilamchi bozordan Avtokredit tanlash jarayonida, kredit
    muddati va uning boshlang'ich to'lovi avtotransport vositasining
    ishlab chiqarilgan yiliga bog'liq" — ya'ni bu BITTA mahsulot HAM
    birlamchi, HAM ikkilamchi bozorni qamrab oladi (talab: "Ishlab
    chiqarilgan Uzbekistanda, 5 yildan oshmagan" — mahalliy/UzAuto brend,
    Aloqabank'ning shunga o'xshash ikkilamchi mahsuloti bilan bir xil
    naqsh). Shu sabab bir xil sahifa/qiymatlar "avtokredit_ikkilamchi"
    toifasiga ham xaritalanadi (aniq alohida ikkilamchi-xos raqamlar
    berilmagani uchun bir xil e'lon qilingan bazaviy stavka ishlatiladi)."""

    bank_name = "Anorbank"
    url = "https://anorbank.uz/uz/credits/avtokredit/"
    CATEGORY_URLS = {
        "avtokredit": "https://anorbank.uz/uz/credits/avtokredit/",
        "avtokredit_ikkilamchi": "https://anorbank.uz/uz/credits/avtokredit/",
        "avtokredit_brend_birlamchi": "https://anorbank.uz/uz/credits/avtokredit4-0/",
        "mikroqarz_onlayn": "https://anorbank.uz/uz/credits/udobnyy-mikrozaym/",
    }
    PRODUCT_NAMES = {
        "avtokredit": "Автокредит 3.0",
        "avtokredit_ikkilamchi": "Автокредит 3.0",
        "avtokredit_brend_birlamchi": "Автокредит 4.0",
        "mikroqarz_onlayn": "Удобный микрозайм",
    }

    def run(self) -> list[Product]:
        now = datetime.now(timezone.utc)
        products: list[Product] = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)
                if category == "mikroqarz_onlayn":
                    product = self._build_mikrozaym_product(url, now, text)
                else:
                    product = self._build_avtokredit_product(category, url, now, text)
            except Exception:
                continue
            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, category: str, url: str, now: datetime, text: str) -> Product | None:
        section = extract_section(text, "Условия автокредита", "Kalkulyator")
        down_match = _DOWN_PAYMENT_RE.search(section)
        amount_match = _AMOUNT_RE.search(section)
        rate_match = _RATE_RE.search(section)
        term_match = _TERM_RE.search(section)
        if not (amount_match and rate_match and term_match):
            return None

        rate = float(rate_match.group(1).replace(",", "."))
        term = int(term_match.group(1))
        return Product(
            bank=self.bank_name,
            category=category,
            product_name=self.PRODUCT_NAMES[category],
            rate_min=rate,
            rate_max=rate,
            term_min_months=term,
            term_max_months=term,
            amount_max_som=int(amount_match.group(1)) * 1_000_000,
            requires_collateral=True,
            down_payment_pct=float(down_match.group(1)) if down_match else None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=extract_payment_method(section),
        )

    def _build_mikrozaym_product(self, url: str, now: datetime, text: str) -> Product | None:
        section = extract_section(text, "Кешбэк по микрозайму", "Увеличенный лимит")
        amount_section = extract_section(text, "5 причины", "Кешбэк по микрозайму")
        amount_match = _MIKROZAYM_AMOUNT_RE.search(amount_section)
        rate_match = _MIKROZAYM_RATE_RE.search(section)
        term_match = _MIKROZAYM_TERM_RE.search(section)
        if not (amount_match and rate_match and term_match):
            return None

        return Product(
            bank=self.bank_name,
            category="mikroqarz_onlayn",
            product_name=self.PRODUCT_NAMES["mikroqarz_onlayn"],
            rate_min=float(rate_match.group(1)),
            rate_max=float(rate_match.group(2)),
            term_min_months=int(term_match.group(1)),
            term_max_months=int(term_match.group(1)),
            amount_max_som=int(amount_match.group(1)) * 1_000_000,
            requires_collateral=False,
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )
