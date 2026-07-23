import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_payment_method,
    extract_section,
    fetch_html,
    html_to_text,
)

_MORTGAGE_RATE_RE = re.compile(r"(\d{1,2}[.,]\d{1,2})%")
_MORTGAGE_TERM_RE = re.compile(r"(\d{1,3})\s*oygacha")
_MORTGAGE_DOWN_RE = re.compile(r"kamida\s*(\d{1,2})\s*%")
_KREDIT_KARTA_TERM_RE = re.compile(r"(\d{1,2})\s*yil\s*\n*\s*Kredit limitining mavjudlik muddati")


class InfinBankScraper(TextSectionScraper):
    """InfinBank (infinbank.com) retail kredit kategoriyalari SQB kabi
    alohida sahifalarda joylashgan. Saytning TLS sertifikati oraliq
    (intermediate) CA'siz yuboriladi — EXTRA_CA_CERT shu bo'shliqni
    to'ldiradi (scrapers/utils.py va scrapers/certs/ ga qarang).

    Har bir sahifada "Axborot varaqasi" uslubidagi aniq label:qiymat
    bloki bor, lekin ikkita kategoriya uchun bu blok to'liq mahsulot
    yaratish uchun yetarli emas:
      - avtokredit ("UzAutoMotors aksiyasi", car_loan_promo/ sahifasi):
        sahifada avtomobil modeli x muddat x boshlang'ich badal ulushi
        bo'yicha guruhlangan katta bir "0% promo" matritsasi bor (aksariyat
        katakchalar "0,00%"), lekin sahifaning birorta joyida ham aniq
        "N mln so'm" shaklida kredit miqdori ko'rsatilmagan — faqat
        "Umumiy ta'minot summasi kredit miqdorining kamida 125 foiziga
        teng bo'lishi kerak" deyilgan (nisbat, aniq son emas).
        amount_max_som topilmagani uchun _build_product bu kategoriyani
        o'tkazib yuboradi — bu XATO EMAS, sahifada haqiqatan ham son
        ko'rinishidagi chegara yo'q (shu sabab murakkab reyting
        matritsasini alohida regex bilan tahlil qilishga urinilmadi —
        natija baribir amount yo'qligi sababli chiqarib tashlanadi).
      - kredit_karta (InfinBLACK): aylanma kredit liniyasi mahsuloti,
        muddat o'rniga "5 yil" (limit amal qilish muddati) faqat sahifaning
        boshqa, interaktiv kalkulyator qismida ko'rsatilgan — u yerda esa
        foiz stavkasi kalkulyator slayder qiymatlari va naqd pul/o'tkazma
        komissiya foizlari bilan aralashib ketadi (kontaminatsiya). Shuning
        uchun CATEGORY_HEADINGS faqat toza tarif jadvalini (limit, stavka
        oralig'i) qamrab oladi; "5 yil" esa butun sahifa matnidan aniq
        "Kredit limitining mavjudlik muddati" sarlavhasiga bog'langan
        maxsus regex bilan, kontaminatsiyaga uchramasdan alohida olinadi
        (_build_kredit_karta_product metodiga qarang). Sahifada "garov"/
        "ta'minot" so'zlari umuman yo'q — bu haqiqiy manfiy (ta'minotsiz
        kredit karta), yolg'on-manfiy emas.

    Garov (kafolat) tekshiruvi har doim TO'LIQ sahifa matnida o'tkaziladi
    (narrowed section'da emas — bazaviy klass dizayni shunday, chunki garov
    ma'lumoti ko'pincha stavka jadvalidan tashqarida joylashadi). Bu InfinBank
    sahifalarida yolg'on-manfiy (false negative) beradi: mikroqarz va
    istemol_krediti sahifalarida boshqa bir bo'lim ("qo'shimcha to'lovlar")
    uchun "Mavjud emas" deb yozilgan bo'lib, has_collateral_requirement buni
    umumiy "mavjud emas" signali sifatida noto'g'ri o'qib, garov YO'Q deb
    xulosa chiqaradi — holbuki ikkala mahsulotning o'z "Ta'minot" bo'limida
    aniq "garov" talab qilinishi yozilgan (narrowed section'ni qo'lda
    tekshirganda tasdiqlangan). FORCE_COLLATERAL shu ikkala kategoriya uchun
    to'g'ri qiymatni aniq belgilaydi — IpotekaBank scraper'idagi xuddi shu
    turdagi yechimga qarang.

    ipoteka_tijorat ("Ipoteka" sahifasi) — davlat/Moliya vazirligi mablag'i
    haqida hech qanday ishora yo'q, bankning o'z mahsuloti; yakka tartibdagi
    uy-joy yoki kvartira sotib olish uchun. Muddat "180 oygacha" (15 yil) —
    bazaviy klassning extract_term_months orqali ishlaydigan umumiy
    CATEGORY_HEADINGS mexanizmi bu yerda ishlatilmaydi, chunki uning 120
    oylik avtokredit-cheklovi 180 ni chetlab o'tar edi; shu sabab bu
    kategoriya uchun run() maxsus qayta yozilgan, cheklovsiz regex bilan.
    Boshlang'ich badal "%" belgisisiz, so'z shaklida ("kamida 26 %
    miqdorida") — alohida regex bilan olinadi. Imtiyozli davr va to'lov
    usuli sahifada umuman tilga olinmagan — ikkalasi ham None qoladi."""

    bank_name = "InfinBank"
    url = "https://infinbank.com/uz/private/credits/"
    EXTRA_CA_CERT = "infinbank_intermediate.pem"
    CATEGORY_URLS = {
        # Foydalanuvchi so'ragan aniq mahsulot ("UzAutoMotors aksiyasi",
        # ko'p model/muddat/badal kombinatsiyalarida 0% promo stavkasi):
        "avtokredit": "https://www.infinbank.com/uz/private/credits/car_loan_promo/",
        "ipoteka_tijorat": "https://infinbank.com/uz/private/credits/ipoteka/",
        "mikroqarz": "https://infinbank.com/uz/private/credits/microloans/",
        "kredit_karta": "https://infinbank.com/uz/private/credits/overdraft/",
        "istemol_krediti": "https://infinbank.com/uz/private/credits/consumer/",
    }
    CATEGORY_HEADINGS = {
        "avtokredit": ("Axborot varaqasi", "Potensial qarz oluvchiga talablar"),
        "mikroqarz": ("Kredit muddati", "Potensial qarz oluvchiga talablar"),
        "kredit_karta": ("Maksimal kredit limiti", "Minimal toʻlov"),
        # "Potentsial" (t harfi bilan) — mikroqarz sahifasidagi
        # "Potensial"dan farqli imlo, sahifada shunday yozilgan.
        "istemol_krediti": ("Kredit muddati", "Potentsial qarz oluvchiga talablar"),
    }
    FORCE_COLLATERAL = {
        # "Asosiy qarz va foizlar bo'yicha imtiyozli davr: Mavjud emas"
        # iborasi butun sahifada "garov" tekshiruvi uchun ham umumiy
        # "mavjud emas" signali bilan aralashib, avtokredit uchun ham
        # yolg'on-manfiy beradi — sahifada "Avtotransport vositasi garovi
        # shartnomasi" hujjati aniq mavjud.
        "avtokredit": True,
        "mikroqarz": True,
        "istemol_krediti": True,
        "ipoteka_tijorat": True,
    }
    PRODUCT_NAMES = {
        "avtokredit": "UzAutoMotors aksiyasi",
        "ipoteka_tijorat": "Ipoteka",
        "kredit_karta": "InfinBLACK",
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)

                if category == "ipoteka_tijorat":
                    product = self._build_ipoteka_tijorat_product(url, now, text)
                elif category == "kredit_karta":
                    product = self._build_kredit_karta_product(url, now, text)
                else:
                    heading_pair = self.CATEGORY_HEADINGS.get(category)
                    section = extract_section(text, *heading_pair) if heading_pair else text
                    product = self._build_product(category, section, url, now, full_text=text)
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_kredit_karta_product(self, url, now, text):
        """"InfinBLACK" — aylanma kredit liniyali kredit karta. Toza
        "Maksimal kredit limiti" -> "Minimal to'lov" bo'limi stavka/limit
        beradi, lekin muddat ("5 yil" — kredit limitining mavjudlik
        muddati) shu bo'limda yo'q, faqat sahifaning yuqorisidagi alohida
        statistik kartada bor. Sahifaning pastki interaktiv kalkulyator
        qismida ham "Kredit muddati: 5 yil" takrorlanadi, lekin u yerda
        stavka slayder belgilari va komissiya foizlari bilan aralashib
        ketishi mumkinligi uchun kengaytirilgan bo'lim o'rniga aniq
        "Kredit limitining mavjudlik muddati" sarlavhasiga bog'langan
        maxsus regex butun sahifa matnidan ishlatiladi.

        Sahifada "garov"/"ta'minot" so'zlari umuman yo'q — bu ta'minotsiz
        kredit karta ekanini bildiradi (yolg'on-manfiy emas)."""
        section = extract_section(text, "Maksimal kredit limiti", "Minimal to")
        amount = extract_amount_som(section)
        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_RE.findall(section)]

        term_match = _KREDIT_KARTA_TERM_RE.search(text)
        term = int(term_match.group(1)) * 12 if term_match else None

        if not rates or term is None or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="kredit_karta",
            product_name=self.PRODUCT_NAMES["kredit_karta"],
            rate_min=min(rates),
            rate_max=max(rates),
            term_min_months=term,
            term_max_months=term,
            amount_max_som=amount,
            requires_collateral=False,
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=None,
        )

    def _build_ipoteka_tijorat_product(self, url, now, text):
        term_section = extract_section(text, "Kredit muddati", "Kredit maqsadi")
        terms = [int(m) for m in _MORTGAGE_TERM_RE.findall(term_section)]

        rate_section = extract_section(text, "Yillik foiz stavkasi", "Kredit miqdori")
        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_RE.findall(rate_section)]

        amount_section = extract_section(text, "Kredit miqdori", "Ta")
        amount = extract_amount_som(amount_section)

        down_match = _MORTGAGE_DOWN_RE.search(text)
        down_payment_pct = float(down_match.group(1)) if down_match else None

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
            grace_period_months=None,
            payment_method=payment_method,
        )
