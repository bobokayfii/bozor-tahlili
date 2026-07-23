import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_grace_period_months,
    extract_payment_method,
    extract_percentages,
    extract_section,
    fetch_html,
    has_collateral_requirement,
    html_to_text,
)

_DOWN_PAYMENT_RE = re.compile(r"kamida (\d+) foizi")
_MIKROQARZ_TERM_RE = re.compile(r"(\d{1,2})\s*\([^)]*\)\s*oy")
_MORTGAGE_RATE_RE = re.compile(r"yillik\s*(\d{1,2}(?:[.,]\d{1,2})?)%")
_MORTGAGE_TERM_RE = re.compile(r"(\d{1,2})\s*yildan oshmagan")
_MORTGAGE_GRACE_RE = re.compile(r"(\d+)\s*oygacha bo['ʻ’]lgan imtiyozli davr")


class KapitalBankScraper(TextSectionScraper):
    """Kapitalbank (kapital24.uz) "Qulay Nasiya (Cobalt)" sahifasi — sarlavha
    va kalkulyatordagi avtomobil modeli tanlovi ("COBALT GX-OPTIMA AT PLUS"
    va h.k.) Chevrolet Cobalt sotib olish uchun ekanini tasdiqlaydi, lekin
    mahsulot o'zi klassik avtokredit emas, "O'zini o'zi band qilgan shaxslar
    uchun mikrokredit" (BNPL uslubidagi tovar/xizmat to'lovi mikrokrediti)
    sifatida rasmiylashtirilgan — sahifa matnining o'zi shunday deydi
    ("Mahsulot turi - O'zini o'zi band qilgan shaxslar uchun mikrokredit").
    Foydalanuvchi so'ragan aniq URL shu bo'lgani uchun shu mahsulot
    "avtokredit" kategoriyasiga xaritalangan.

    Ikkita alohida qiyinchilik bor:
      1. Foiz stavkasi "%" belgisi bilan EMAS, "0 (nol) foiz" so'z shaklida
         yozilgan — extract_percentages faqat "%" belgisini taniydi. Butun
         sahifada "%" belgisi FAQAT bitta joyda, garov mulkining bozor
         qiymatiga nisbatan ulushida uchraydi ("70%idan ko'p bo'lmagan"),
         bu esa foiz STAVKASI emas. Shu sabab standart CATEGORY_HEADINGS
         o'rniga run() qayta yozilgan: muddat "Mikrokredit muddati" ->
         "Shaxsiy ishtirok" oralig'idan olinadi, so'ng shu bo'lakdagi aniq
         "0 (nol) foiz" iborasi extract_percentages tushunadigan "0%"
         shakliga almashtiriladi (faqat shu ibora, global emas — "70%idan"
         kabi boshqa % contaminatsiyasidan xoli).
      2. Maksimal miqdori "300 000 000,00 so'mgacha" — ortiqcha ",00" tiyin
         qismi extract_amount_som'ning guruhlangan-raqam+"so" naqshini
         (oraliqda hech narsa bo'lmasligini talab qiladi) buzadi. Shu sabab
         ",00 so" -> " so" ga almashtiriladi (faqat shu bo'lakda).

    "Bankning kredit siyosatiga ko'ra ... qarzdorlikning mavjud emasligi"
    iborasi (talablar bo'limida) butun sahifa matnida "garov" tekshiruvi
    uchun umumiy "mavjud emas" signali bilan aralashib, yolg'on-manfiy
    beradi — holbuki "Ta'minot" bo'limida avtotransport vositasi garovi va
    sug'urta polisi aniq talab qilinishi yozilgan. FORCE_COLLATERAL bilan
    tuzatilgan.

    Boshlang'ich badal ("Shaxsiy ishtirok") "kamida 30 foizi" so'z shaklida
    berilgan — "Shaxsiy ishtirok" -> "Mikrokreditning maksimal miqdori"
    oralig'ida alohida regex bilan olinadi (toraytirilmasa, "Ta'minot"
    bo'limidagi boshqa "kamida N foizi" — garov 44%, sug'urta 120% —
    iboralari bilan aralashib ketardi). To'lov usuli (Annuitet/Differensial)
    va imtiyozli davr sahifada UMUMAN tilga olinmagan (bu klassik avtokredit
    emas, BNPL uslubidagi mikrokredit) — shu sabab ular uchun alohida
    qidiruv yozilmagan, ikkalasi ham tabiiy ravishda None (noma'lum) qoladi."""

    bank_name = "Kapitalbank"
    url = "https://www.kapital24.uz/uz/crediting/"
    CATEGORY_URLS = {
        "avtokredit": "https://www.kapital24.uz/uz/crediting/qulay-nasiya-cobalt/",
        "avtokredit_ikkilamchi": "https://www.kapital24.uz/uz/crediting/kapitalbankdan-avto-nasiya-ikkilamchi/",
        "ipoteka_tijorat": "https://www.kapital24.uz/uz/crediting/qulay-uy-ipoteka-krediti/",
        "mikroqarz_onlayn": "https://www.kapital24.uz/uz/crediting/onlayn-mikroqarz/",
    }
    FORCE_COLLATERAL = {
        "avtokredit": True,
        "avtokredit_ikkilamchi": True,
    }
    PRODUCT_NAMES = {
        "avtokredit": "Qulay Nasiya (Cobalt)",
        "avtokredit_ikkilamchi": "Kapitalbankdan Avto Nasiya (ikkilamchi)",
        "ipoteka_tijorat": "Qulay uy ipoteka krediti",
        "mikroqarz_onlayn": "Onlayn mikroqarz",
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)

                if category == "mikroqarz_onlayn":
                    product = self._build_mikroqarz_onlayn_product(url, now, text)
                elif category == "avtokredit_ikkilamchi":
                    product = self._build_avtokredit_ikkilamchi_product(url, now, text)
                elif category == "ipoteka_tijorat":
                    product = self._build_ipoteka_tijorat_product(url, now, text)
                elif category == "avtokredit":
                    product = self._build_avtokredit_product(url, now, text)
                else:
                    product = None
            except Exception:
                continue

            if product is not None:
                products.append(product)
        return products

    def _build_avtokredit_product(self, url, now, text):
        term_rate_section = extract_section(text, "Mikrokredit muddati", "Shaxsiy ishtirok").replace(
            "0 (nol) foiz", "0%"
        )
        amount_section = extract_section(text, "Mikrokreditning maksimal miqdori", "minot").replace(",00 so", " so")
        section = f"{term_rate_section}\n{amount_section}"

        down_payment_section = extract_section(text, "Shaxsiy ishtirok", "Mikrokreditning maksimal miqdori")
        down_payment_match = _DOWN_PAYMENT_RE.search(down_payment_section)
        down_payment_pct = float(down_payment_match.group(1)) if down_payment_match else None

        return self._build_product(
            "avtokredit", section, url, now, full_text=text, down_payment_pct=down_payment_pct
        )

    def _build_avtokredit_ikkilamchi_product(self, url, now, text):
        """"Kapitalbankdan Avto Nasiya (ikkilamchi)" — xuddi "Qulay Nasiya
        (Cobalt)" kabi, bu ham klassik avtokredit emas, BNPL uslubidagi
        "O'zini o'zi band qilgan shaxslar uchun mikrokredit" (0% foiz +
        hamkor/avtosalon savdo ustamasi orqali). Foiz "0 (nol) foiz" so'z
        shaklida yozilgan — "0%" ga almashtiriladi. Maksimal miqdor
        "300 000 000,00 so'mgacha" — ortiqcha ",00" tiyin qismi olib
        tashlanadi (Cobalt sahifasidagi bir xil naqsh).

        "O'z ishtiroki (boshlang'ich badal)" bo'limida UCHTA mahsulot
        varianti ro'yxatlanadi (bazaviy — 20%, plyus — 30%, Elektro —
        35%) — eng past qiymat (20%) bazaviy "(ikkilamchi)" varianti
        uchun ishlatiladi, bu bizning PRODUCT_NAMES nomimizga mos keladi."""
        term_rate_section = extract_section(text, "Mikrokredit muddati", "shtiroki").replace("0 (nol) foiz", "0%")
        amount_section = extract_section(text, "Mikrokreditning maksimal miqdori", "minot").replace(",00 so", " so")
        section = f"{term_rate_section}\n{amount_section}"

        down_payment_section = extract_section(text, "shtiroki", "Mikrokreditning maksimal miqdori")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        # Sahifada "Imtiyoz davri" deb yozilgan ("Imtiyozli" emas — "-li"
        # qo'shimchasisiz shakl), lekin extract_grace_period_months faqat
        # "imtiyozli" so'zini qidiradi — shu sabab prefiks sifatida
        # qo'shiladi (haqiqiy manfiy signal "mavjud emas" ekanligi allaqachon
        # tekshirilgan).
        grace_section = extract_section(text, "Imtiyoz davrining muddati", "minot")
        grace_period_months = extract_grace_period_months("imtiyozli" + grace_section)

        return self._build_product(
            "avtokredit_ikkilamchi",
            section,
            url,
            now,
            full_text=text,
            down_payment_pct=down_payment_pct,
            grace_period_months=grace_period_months,
        )

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """"Qulay uy ipoteka krediti" — davlat mablag'lari haqida hech
        qanday ishora yo'q, bankning o'z mablag'i hisobidan birlamchi/
        ikkilamchi bozordan turar-joy sotib olish uchun. "Foiz stavkasi:"
        bo'limida mijoz toifasi (rasmiy daromadli / o'zini o'zi band
        qilgan) x boshlang'ich to'lov ulushiga qarab 3 ta stavka beriladi
        ("Dastlabki to'lov 20%dan 25% gacha bo'lganda — yillik 26%" kabi)
        — faqat "yillik N%" naqshiga mos regex bilan ajratiladi, aks holda
        boshlang'ich to'lov ulushlari (20/25/30%) ham stavka sifatida
        hisoblanib ketardi.

        Muddat "10 yildan oshmagan" shaklida — faqat yuqori chegara
        berilgan, shuning uchun term_min=term_max=120. Imtiyozli davr
        "3 oygacha bo'lgan imtiyozli davr bilan YOKI imtiyozli davrsiz"
        deb ixtiyoriy tarzda tavsiflangan — mijoz tanlovi bo'lgani uchun
        taklif etilayotgan maksimal qiymat (3 oy) olinadi, umumiy
        extract_grace_period_months emas (u "imtiyozli davrsiz" inkor
        signalini ko'rib 0 qaytarardi, garchi 3 oylik variant ham real
        taklif bo'lsa ham). To'lov usuli faqat "annuitet usulida" deb
        tilga olingan (differensial variant yo'q)."""
        rate_section = extract_section(text, "Foiz stavkasi:", "Muddati")
        rates = [float(m.replace(",", ".")) for m in _MORTGAGE_RATE_RE.findall(rate_section)]

        term_match = _MORTGAGE_TERM_RE.search(text)
        term = int(term_match.group(1)) * 12 if term_match else None

        amount_section = extract_section(text, "Kreditning maksimal summasi", "Ta")
        amount = extract_amount_som(amount_section)

        down_payment_section = extract_section(text, "Dastlabki to'lov", "* Bilish")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        grace_match = _MORTGAGE_GRACE_RE.search(text)
        grace_period_months = int(grace_match.group(1)) if grace_match else None

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
            requires_collateral=has_collateral_requirement(text),
            down_payment_pct=down_payment_pct,
            source_url=url,
            scraped_at=now,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_mikroqarz_onlayn_product(self, url, now, text):
        """"Onlayn mikroqarz" — "Ariza topshirish usuli: Kapitalbank.Online
        mobil ilovasi orqali" deb aniq yozilgan (mobil ilova orqali, ofisga
        bormasdan) — mikroqarz_onlayn toifasiga kiradi. Sahifadagi ikkinchi
        mikrokredit mahsuloti ("Kapital Mikrokredit Universal", bank ofisi
        orqali rasmiylashtiriladigan oflayn variant) esa hech qanday aniq
        summa/stavka/muddat ko'rsatmaydi — barcha raqamlar faqat JS
        kalkulyatorida dinamik hisoblanadi, statik sahifa matnida yo'q,
        shuning uchun bu bank uchun faqat onlayn mahsulot qamrab olindi.

        Muddat "3 (uch) oy" kabi so'z bilan yozilgan raqam formatida —
        standart "N oygacha" naqshiga mos kelmaydi, shu sabab maxsus regex
        ishlatiladi. Xavfsizlik turi faqat sug'urta polisi (mulk garovi
        emas) — shu sabab requires_collateral aniq False."""
        section = extract_section(text, "Kredit summasi", "Ariza topshirish usuli")
        rates = extract_percentages(section)
        terms = [int(t) for t in _MIKROQARZ_TERM_RE.findall(section)]
        amount = extract_amount_som(section)

        payment_method_section = extract_section(text, "Kreditni so", "Muddatidan oldin")
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
            requires_collateral=False,
            down_payment_pct=None,
            source_url=url,
            scraped_at=now,
            grace_period_months=None,
            payment_method=payment_method,
        )
