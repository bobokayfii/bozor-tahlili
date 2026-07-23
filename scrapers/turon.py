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
    has_collateral_requirement,
    html_to_text,
)

_BREND_RATE_RE = re.compile(r"(\d{1,2}[.,]\d{1,2})%")
_BREND_IKKILAMCHI_RATE_RE = re.compile(r"Ikkilamchi avtotransport uchun\s*-\s*(\d{1,2}(?:[.,]\d{1,2})?)%")
_BREND_IKKILAMCHI_TERM_RE = re.compile(r"Ikkilamchi bozor uchun\s*-\s*(\d+)\s*oy")
_BREND_IKKILAMCHI_DOWN_RE = re.compile(r"Ikkilamchi bozor uchun\s*-\s*(\d+)%")
_MORTGAGE_TERM_RE = re.compile(r"Kredit muddati\s*\n+\s*(\d{1,2})\s*yil\b")


class TuronBankScraper(TextSectionScraper):
    """Turonbank (turonbank.uz) "'UzAuto Motors' Avtokrediti" sahifasi
    Aloqabank bilan bir xil 1C-Bitrix shabloniga asoslangan: "Kredit
    shartlari" sarlavhasi yon menyu havolasida VA haqiqiy bo'lim
    sarlavhasida ikki marta uchraydi, shuning uchun boshlanish nuqtasi
    sifatida shu ikkalasidan farqli, faqat bitta joyda uchraydigan "Yillik
    foiz stavkasi" ishlatiladi (Aloqabank scraper'idagi xuddi shu yechim).

    "Kreditning maksimal summasi" qiymati esa so'm o'rniga "2000 (BHM)"
    (Bazaviy hisoblash miqdori) sifatida berilgan — BHM qiymati vaqt
    o'tishi bilan farmon asosida o'zgaradi, shuning uchun uni qandaydir
    qattiq kodlangan kursga ko'paytirib taxmin qilish noto'g'ri bo'lardi
    (InfinBank consumer-credit sahifasidagi "100 BHMgacha" holatiga
    o'xshab, faqat sahifaning o'zi aniq so'm ekvivalentini bersagina u
    olinadi). Baxtimizga sahifadagi interaktiv kalkulyator "Zarur summa"
    slayderining yuqori chegarasi sifatida bank hisoblab chiqqan aniq
    ekvivalentni beradi: "824 million so'mgacha" — bu HAQIQIY, bankning
    o'zi hisoblagan qiymat (bizning taxminimiz emas), shuning uchun run()
    orqali shu ikkinchi bo'lim (foiz/muddat bo'limidan ancha pastda,
    boshqa % qiymatlar — boshlang'ich badal/foiz slayderlari — bilan
    contaminatsiya bo'lmasligi uchun tor "Zarur summa" -> "Kredit muddati"
    oralig'ida) alohida olinib, birinchi bo'lim bilan birlashtiriladi.

    "Kredit shartlari" bo'limida boshlang'ich badal umuman ko'rsatilmagan —
    faqat interaktiv kalkulyatorning "Boshlang'ich badal miqdori" slayderi
    orqali 30%-50% oralig'i beriladi; pastrog'i (30%) olinadi. Rasmiy
    "Kredit shartlari"da "To'lov usuli: Annuitet" va "Imtiyozli davr: Yo'q"
    aniq ko'rsatilgan (pastroqdagi kalkulyatorda Annuitet/Differensial
    tanlovi ham bor, lekin rasmiy shart faqat Annuitetni tasdiqlaydi —
    Xalq Banki scraperidagi bir xil qarama-qarshilikka qarang)."""

    bank_name = "Turonbank"
    url = "https://turonbank.uz/uz/private/crediting/"
    CATEGORY_URLS = {
        "avtokredit": "https://turonbank.uz/uz/private/crediting/uzauto-motors-avtokredit/",
        "avtokredit_brend_birlamchi": "https://turonbank.uz/uz/private/crediting/avtokredit-ecogreencar/",
        # "Green Avto" sahifasining o'zi HAM birlamchi, HAM ikkilamchi bozor
        # shartlarini o'z ichiga oladi (bir xil URL, ikkinchi marta olinadi
        # — chunki ikkilamchi qismning stavka/muddat/badal qiymatlari
        # birlamchidan butunlay farq qiladi va alohida kategoriya hisoblanadi).
        "avtokredit_brend_ikkilamchi": "https://turonbank.uz/uz/private/crediting/avtokredit-ecogreencar/",
        "ipoteka_tijorat": "https://turonbank.uz/uz/private/crediting/ipoteka-krediti-yagona-oson/",
        "mikroqarz": "https://turonbank.uz/uz/private/crediting/mikroqarz/",
    }
    PRODUCT_NAMES = {
        "avtokredit": '"UzAuto Motors" Avtokrediti',
        "avtokredit_brend_birlamchi": '"Green Avto" Avtokrediti',
        "avtokredit_brend_ikkilamchi": '"Green Avto" Avtokrediti',
        "ipoteka_tijorat": '"Yanada oson" ipoteka krediti',
        "mikroqarz": "Mikroqarz",
    }

    def run(self):
        now = datetime.now(timezone.utc)
        products = []
        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)

                if category == "mikroqarz":
                    product = self._build_mikroqarz_product(url, now, text)
                elif category == "avtokredit_brend_birlamchi":
                    product = self._build_avtokredit_brend_birlamchi_product(url, now, text)
                elif category == "avtokredit_brend_ikkilamchi":
                    product = self._build_avtokredit_brend_ikkilamchi_product(url, now, text)
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
        rate_term_section = extract_section(text, "Yillik foiz stavkasi", "Kredit maqsadi")
        amount_section = extract_section(text, "Zarur summa", "Kredit muddati")
        section = f"{rate_term_section}\n{amount_section}"

        down_payment_section = extract_section(text, "badal miqdori", "Zarur summa")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        payment_method_section = extract_section(text, "lov usuli", "Rasmiylashtirish usuli")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(text, "Imtiyozli davr", "Jismoniy shaxslar uchun tariflar")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        return self._build_product(
            "avtokredit",
            section,
            url,
            now,
            full_text=text,
            down_payment_pct=down_payment_pct,
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )

    def _build_avtokredit_brend_birlamchi_product(self, url, now, text):
        """"Green Avto" Avtokrediti — "Chetdan import qilingan ...
        birlamchi bozordan (benzin, dizel, elektromobil hamda gibrid) va
        ikkilamchi bozordan (benzin) avtotransport vositalarini sotib olish
        uchun" — bitta sahifada HAM birlamchi, HAM ikkilamchi bozor
        shartlari aralash beriladi (stavka jadvali, muddat va boshlang'ich
        badal har ikkalasi uchun alohida-alohida ko'rsatilgan: "Birlamchi
        bozor uchun - 60 oy" / "Ikkilamchi bozor uchun - 48 oy" kabi) — bu
        toifa faqat BIRLAMCHI bozor qismini oladi, "Birlamchi bozor uchun:"
        so'zidan keyingi stavka jadvali (30-40% / 40-50% / 50%+ boshlang'ich
        badal ulushiga qarab 22.99% / 21.99% / 20.99%) va alohida
        "Birlamchi bozor uchun - N oy" / "- N% dan boshlab" iboralaridan
        muddat va boshlang'ich badal olinadi.

        "Kreditning maksimal summasi" rasmiy ro'yxatda so'm o'rniga "2000
        (BHM)" sifatida berilgan — BHM qiymati farmon asosida o'zgarib
        turadi, shuning uchun uni qattiq kodlangan kursga ko'paytirib
        taxmin qilish noto'g'ri bo'lardi (xuddi shu muammo mavjud "avtokredit"
        toifasi uchun ham hal qilingan edi). Sahifadagi interaktiv
        kalkulyatorning "Zarur summa" slayderi bank hisoblagan aniq so'm
        ekvivalentini beradi ("824 million so'mgacha"), shuning uchun BHM
        emas, shu qiymat ishlatiladi."""
        rate_block = extract_section(text, "Birlamchi bozor uchun:", "Ikkilamchi avtotransport")
        rates = [float(m.replace(",", ".")) for m in _BREND_RATE_RE.findall(rate_block)]

        term_match = re.search(r"Birlamchi bozor uchun\s*-\s*(\d+)\s*oy", text)
        term = int(term_match.group(1)) if term_match else None

        down_payment_match = re.search(r"Birlamchi bozor uchun\s*-\s*(\d+)%\s*dan boshlab", text)
        down_payment_pct = float(down_payment_match.group(1)) if down_payment_match else None

        amount_section = extract_section(text, "Zarur summa", "Kredit muddati")
        amount = extract_amount_som(amount_section)

        payment_method = extract_payment_method(text)

        grace_section = extract_section(text, "Imtiyozli davr", "Jismoniy shaxslar uchun tariflar")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        if not rates or term is None or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="avtokredit_brend_birlamchi",
            product_name=self.PRODUCT_NAMES["avtokredit_brend_birlamchi"],
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

    def _build_avtokredit_brend_ikkilamchi_product(self, url, now, text):
        """"Green Avto" Avtokrediti sahifasining ikkilamchi bozor qismi —
        birlamchidan farqli, bitta qat'iy stavka/muddat/badal beradi
        (tierlar yo'q): "Ikkilamchi avtotransport uchun - 25%" (stavka),
        "Ikkilamchi bozor uchun - 48 oy" (muddat), "Ikkilamchi bozor
        uchun - 50%" (boshlang'ich badal) — har biri o'z aniq iborasi
        bilan regex orqali ajratiladi, chunki bir xil "Ikkilamchi bozor
        uchun" prefiksi muddat va badal uchun ham takrorlanadi (faqat
        keyingi son va o'lchov birligi bilan farqlanadi). Summa/imtiyozli
        davr/to'lov usuli/garov — butun sahifaga tegishli umumiy
        ma'lumotlar, birlamchi qism bilan bir xil."""
        rate_match = _BREND_IKKILAMCHI_RATE_RE.search(text)
        rate = float(rate_match.group(1).replace(",", ".")) if rate_match else None

        term_match = _BREND_IKKILAMCHI_TERM_RE.search(text)
        term = int(term_match.group(1)) if term_match else None

        down_payment_match = _BREND_IKKILAMCHI_DOWN_RE.search(text)
        down_payment_pct = float(down_payment_match.group(1)) if down_payment_match else None

        amount_section = extract_section(text, "Zarur summa", "Kredit muddati")
        amount = extract_amount_som(amount_section)

        payment_method = extract_payment_method(text)

        grace_section = extract_section(text, "Imtiyozli davr", "Jismoniy shaxslar uchun tariflar")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

        if rate is None or term is None or amount is None:
            return None

        return Product(
            bank=self.bank_name,
            category="avtokredit_brend_ikkilamchi",
            product_name=self.PRODUCT_NAMES["avtokredit_brend_ikkilamchi"],
            rate_min=rate,
            rate_max=rate,
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

    def _build_ipoteka_tijorat_product(self, url, now, text):
        """"Yanada oson" ipoteka krediti — rasmiy daromad manbaiga ega
        bo'lmagan fuqarolarga birlamchi va ikkilamchi bozordan uy-joy
        sotib olish uchun (davlat/Moliya vazirligi mablag'i haqida hech
        qanday ishora yo'q — bankning o'z mahsuloti). Rasmiy ro'yxatda
        summa "4 000 (BHM)" deb berilgan — BHM qiymati o'zgarib turadi,
        shuning uchun "Zarur summa" kalkulyator slayderining bank
        hisoblagan so'm ekvivalenti ("1.5 milliard so'mgacha") ishlatiladi
        (xuddi shu bankning "Green Avto" sahifasidagi bir xil yechim).

        Muddat "Kredit muddati" sarlavhasidan keyin bare "10 yil" shaklida
        (yilgacha/oygacha qo'shimchasisiz) — sahifa oxirida yana bir marta
        aloqasiz "21 yosh" yosh talabi ham "yil" so'ziga mos kelgani uchun
        umumiy qidiruv o'rniga faqat "Kredit muddati" sarlavhasidan
        DARHOL keyin keladigan qiymat olinadi."""
        rate_section = extract_section(text, "Yillik foiz stavkasi", "Kreditning maksimal summasi")
        rates = extract_percentages(rate_section)

        term_match = _MORTGAGE_TERM_RE.search(text)
        term = int(term_match.group(1)) * 12 if term_match else None

        amount_section = extract_section(text, "Zarur summa", "Kredit muddati")
        amount = extract_amount_som(amount_section)

        down_payment_section = extract_section(text, "Boshlang'ich to'lov", "Кredit qaytarish usuli")
        down_payment_rates = extract_percentages(down_payment_section)
        down_payment_pct = min(down_payment_rates) if down_payment_rates else None

        grace_section = extract_section(text, "Imtiyozli davr", "Jismoniy shaxslar uchun tariflar")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

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

    def _build_mikroqarz_product(self, url, now, text):
        """"Mikroqarz" — "Rasmiylashtirish usuli: Bank ofisi" deb aniq
        yozilgan (garchi sahifada "Kreditni onlayn tarzda rasmiylashtiring"
        degan umumiy ariza-yuborish tashviqoti bo'lsa ham, rasmiy
        "Kredit shartlari" ro'yxati aniq "Bank ofisi" deydi) — oflayn
        "mikroqarz" toifasiga kiradi.

        "Yillik foiz stavkasi" sarlavhasi sahifada 2 marta uchraydi —
        birinchisi (haqiqiy "Kredit shartlari" ro'yxati) to'g'ri natija
        beradi, ikkinchisi extract_section tomonidan e'tiborga olinmaydi
        (faqat birinchi moslashuv qidiriladi)."""
        section = extract_section(text, "Yillik foiz stavkasi", "Ajratilish shakli")
        rates = extract_percentages(section)
        terms = extract_term_months(section)
        amount = extract_amount_som(section)

        payment_method_section = extract_section(text, "lov usuli", "Rasmiylashtirish usuli")
        payment_method = extract_payment_method(payment_method_section)

        grace_section = extract_section(text, "Imtiyozli davr", "Jismoniy shaxslar uchun tariflar")
        grace_period_months = extract_grace_period_months("Imtiyozli davr" + grace_section)

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
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )
