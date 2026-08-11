import re
from datetime import datetime, timezone

from scrapers.base import Product, TextSectionScraper
from scrapers.utils import (
    extract_amount_som,
    extract_grace_period_months,
    extract_payment_method,
    extract_section,
    extract_term_months,
    fetch_html,
    html_to_text,
)

# "Bankning o'z mablag'lari hisobidan ajratiladigan ipoteka krediti" sahifasi
# stavka/boshlang'ich badal foizlarini "%" belgisi bilan emas, so'z shaklida
# ("23 foiz", "20 foiz" kabi) yozadi — standart extract_percentages faqat
# "%" belgisini taniydi va bu sahifada bo'sh ro'yxat qaytaradi. Task 3
# (ipoteka_davlat) ham TrastBank'ning bir xil sahifa shablonini ishlatishi
# mumkinligi sababli qayta ishlatish uchun modul darajasida saqlanadi.
_FOIZ_RE = re.compile(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*foiz")


class TrastBankScraper(TextSectionScraper):
    """TrastBank (trustbank.uz).

    "Mikroqarzlar" sahifasida (https://trustbank.uz/uz/private/crediting/
    microloans/) UCHTA mijoz-toifasi ketma-ket keladi, har biri o'z stavka/
    muddat/summa jadvaliga ega:
      1. "Doimiy daromadga ega bo'lgan mijozlar uchun" — 100 mln so'mgacha,
         12/36/60 oygacha, ikkita stavka jadvali: kafillik/sug'urta asosida
         28%/29%/30%, so'ng avtotransport/ko'chmas mulk garovi asosida
         29%/30%/31,9%.
      2. "O'zini-o'zi band qilgan shaxslarga" — 50,0 mln so'mgacha, 12/24/36
         oy (bu yerda "oygacha"siz, yalang' "N oy" shaklida — standart
         extract_term_months bu qiymatlarni faqat "oygacha" ibora hech
         qayerda topilmasa oladi, shu sabab quyida tushuntirilganidek bu
         qiymatlar birlashtirilgan bo'lakda amalda e'tiborga olinmaydi).
      3. "...ish haqi loyihasi... Ta'lim va sog'liqni saqlash tizimlarida
         ishlovchi xodimlar uchun" — 100 mln so'mgacha, 12/36/60 oygacha,
         ikkita stavka jadvali: kafillik/sug'urta asosida 24%/25%/26%, so'ng
         garov asosida 25%/26,5%/27,9%.

    Uchala toifa ALOHIDA-ALOHIDA emas, BITTA umumiy bo'lak sifatida olinadi
    ("Doimiy daromadga ega bo" dan — apostrof ASCII-xavfsiz kesilgan,
    haqiqiy belgi U+2018 '‘' — "Mikroqarz rasmiylashtirishda" gacha, bu
    ikkinchisi sahifada FAQAT bir marta uchraydi va uchala toifadan keyin,
    hujjatlar ro'yxati boshida keladi), so'ng shu bo'lak ustida standart
    extract_percentages/extract_term_months/extract_amount_som ishlatiladi
    (CATEGORY_HEADINGS orqali, umumiy TextSectionScraper.run()ning standart
    yo'li bilan — bu kategoriya uchun maxsus run()/_build_* metodi shart
    emas, chunki barcha maydonlar bitta oddiy bo'lak ustida standart
    funksiyalar bilan to'g'ri chiqadi):
      - rates: {28,29,30,31.9,24,25,26,26.5,27.9} -> min=24.0, max=31.9
        (barcha besh stavka jadvalidan, uchala toifaning haqiqiysi).
      - terms: standart extract_term_months avval "N oydan M oygacha" range
        naqshini qidiradi (topilmaydi), so'ng "N oygacha" ibora to'plamiga
        tushadi — bu FAQAT 1- va 3-toifaning {12,36,60} qiymatlarini oladi
        (ikkalasida ham bir xil, "oygacha" bilan yozilgan). 2-toifaning
        yalang' "12 oy"/"24 oy"/"36 oy" (oygachasiz) qiymatlari bu yo'lda
        chiqarib tashlanadi, chunki "N oygacha" to'plami bo'sh emasligi
        sababli funksiya yalang' "N oy" fallback shoxobchasiga umuman
        o'tmaydi — lekin bu natijaga ta'sir qilmaydi: {12,36,60} allaqachon
        min=12/max=60 ni beradi, 2-toifaning eng kattasi (36) bu oraliqdan
        oshib ketmaydi.
      - amount: "100 mln so'mgacha" ikki marta (1- va 3-toifa) va "50,0 mln
        so'mgacha" (2-toifa, VERGUL bilan yozilgan — standart mln regex
        vergul-o'nlik qismini tanimaydi, shu sabab bu son mos kelmaydi va
        e'tiborga olinmaydi, lekin baribir muhim emas, chunki u 100 mlndan
        kichik) -> max = 100_000_000.

    Bu tasodifiy emas — barcha uch toifaning haqiqiy, jonli saytda e'lon
    qilingan stavka/muddat qiymatlari, faqat birlashtirilgan holda.

    Imtiyozli davr: sahifa muqaddimasida (birinchi jadvaldan OLDIN) aniq
    "Mikroqarzning imtiyozli davri: mavjud emas" deb yozilgan — bu real
    "yo'q" signali (0 oy), "noma'lum" emas. GRACE_PERIOD_HEADINGS orqali
    "Mikroqarzning imtiyozli davri" dan "Doimiy daromadga ega bo" gacha
    (bu ikkinchi sarlavha darhol undan keyin kelmaydi, lekin oralig'idagi
    bo'sh matnda "imtiyozli" so'zi boshqa hech qayerda uchramaydi, shu sabab
    bu tor chegara xavfsiz) chegaralanadi.

    down_payment_pct va payment_method: sahifaning bu bo'limida umuman
    tilga olinmagan (jonli sahifada "Boshlang'ich"/"Jadval turi"/
    "annuitet"/"differen" so'zlarining birortasi ham uchramasligi
    tasdiqlangan) — DOWN_PAYMENT_HEADINGS/PAYMENT_METHOD_HEADINGS
    belgilanmagani uchun ikkalasi ham tabiiy ravishda None qoladi.

    requires_collateral: FORCE_COLLATERAL orqali qat'iy True belgilangan —
    barcha uch toifa ham kafillik/sug'urta/garov turlaridan birortasini
    talab qiladi, hech qanday "garovsiz" variant yo'q. DIQQAT: umumiy
    has_collateral_requirement bu sahifada ishonchsiz bo'lardi — sahifa
    muqaddimasidagi "imtiyozli davri: mavjud emas" jumlasi tufayli butun
    sahifa matnida "mavjud emas" so'z birikmasi bor, bu esa
    has_collateral_requirement'ning yolg'on-manfiy shoxobchasini
    ("mavjud emas" bo'lsa False qaytarish) ishga tushirib, haqiqatda
    garov/kafillik/sug'urta talab qilinishiga qaramay False qaytarardi
    (tekshirilgan) — shu sabab bu yerda aniq force qilish ayniqsa muhim.

    ipoteka_davlat — TrastBank uchun boshqa, alohida topshiriq doirasida
    keyinroq shu faylga qo'shiladi; bu yerda u uchun joy egallovchi
    (placeholder) yozuv YO'Q.

    ipoteka_tijorat ("Bankning o'z mablag'lari hisobidan ajratiladigan
    ipoteka krediti", https://trustbank.uz/uz/private/crediting/bankning
    -o-z-mablag-lari-hisobidan-ajratiladigan-ipoteka-krediti/) — bu
    kategoriya "mikroqarz"dan farqli, GENERIK CATEGORY_HEADINGS yo'liga
    sig'maydi, shu sabab quyidagi run() ustidan yozilgan va o'zining
    _build_ipoteka_tijorat_product metodiga ega. Sahifa raqamlangan
    jadval (invoys-uslubidagi "1/2/3..." qatorlar) shaklida, har bir band
    nomi sahifada FAQAT bir marta uchraydi (tekshirilgan):
      - "Muddati" (3-band) -> "120 oygacha" — standart extract_term_months
        bilan muammosiz o'qiladi.
      - "Boshlang‘ich badal" (4-band, apostrof U+2018 — repr() bilan
        tasdiqlangan) -> "Doimiy daromad manbaiga ega bo'lgan mijozlarga:
        20 foiz" / "O'zini-o'zi band qilgan mijozlarga: 25 foiz" — foizlar
        SO'Z shaklida ("%" belgisisiz) yozilgan, shu sabab standart
        extract_percentages ishlamaydi va o'rniga _FOIZ_RE ishlatiladi;
        min() = 20.0.
      - "Kredit miqdori" (5-band) -> "Bazaviy hisoblash miqdorining 2 500/
        3 000 barobarigacha" (ikkita RELATIV, BHM-multiplikatorli qiymat —
        literal son emas, e'tiborga olinmaydi) va "700,0 mln so'mgacha"
        (literal, ASOSIY manba). DIQQAT: standart extract_amount_som'ning
        mln-regexi vergul-o'nlik qismini "700" bilan bog'liq deb
        tanimaydi va vergul-oldi "700"ni emas, vergul-keyingi "0"ni "mln"
        bilan mos deb topib, XATO ravishda 0 (deyarli nol) qaytaradi —
        tekshirilgan haqiqiy tuzoq, farazga asoslanmagan. Shu sabab
        ",0 mln" -> " mln" almashtirilgandan keyin chaqiriladi, natija:
        700_000_000.
      - "Yillik foiz stavkasi" (6-band) -> "23 foiz" (doimiy daromadli) /
        "24 foiz" (o'zini o'zi band) — _FOIZ_RE bilan, min=23.0, max=24.0.
      - "To‘lov usuli" (7-band, apostrof shu yerda ham U+2018) -> "Annuitet
        yoki differensial usulda" — standart extract_payment_method
        ishlaydi, natija "Annuitet, Differensial".

    Bo'lim chegaralari (barchasi sahifada FAQAT bir marta uchraydi, shu
    sabab ko'p bosqichli toraytirish shart emas):
      amount: "Kredit miqdori" -> "Yillik foiz stavkasi"
      term: "Muddati" -> "Boshlang" (qisqartirilgan, apostrofsiz —
        ASCII-xavfsiz, chunki extract_section end_heading'ni ASCII qism
        bo'yicha qidiradi, to'liq Unicode apostrofli iborani talab
        qilmaydi)
      rate: "Yillik foiz stavkasi" -> "To‘lov usuli" (bu yerda apostrof
        aniq kerak, chunki bu ibora end_heading sifatida ishlatilganda
        ASCII qisqartma "To" boshqa so'zlar — masalan "Toshkent" — bilan
        chalkashib ketishi mumkin edi, biroq sahifada "Toshkent" so'zi bu
        oraliqdan keyin joylashgan, shu sabab aslida "To" ham xavfsiz
        bo'lardi; aniqlik uchun to'liq ibora ishlatilgan)
      down_payment: "Boshlang" -> "Kredit miqdori"
      payment_method: "To‘lov usuli" -> "Kredit oluvchi yoshi"

    Imtiyozli davr: sahifa muqaddima paragrafida (raqamlangan jadvaldan
    OLDIN) aniq "Kreditning imtiyozli davri mavjud emas" deb yozilgan —
    extract_grace_period_months shu paragraf ustida to'g'ridan-to'g'ri
    ishlatiladi (matnda "imtiyozli" so'zi allaqachon bor, prefiks kerak
    emas), natija 0 oy.

    requires_collateral: FORCE_COLLATERAL orqali qat'iy True belgilangan —
    ipoteka doim ko'chmas mulk garovi bilan ta'minlanadi (boshqa
    banklardagi ipoteka_tijorat/ipoteka_davlat konvensiyasi bilan bir xil,
    masalan scrapers/sqb.py, scrapers/ofb.py, scrapers/aab.py), sahifaning
    "Ta'minot" bandida ham aynan "Kredit hisobiga sotib olinayotgan uy-joy
    (kvartira)" deyilgan bo'lsa-da, "garov" so'zining o'zi ishlatilmagan."""

    bank_name = "TrastBank"
    url = "https://trustbank.uz/uz/private/crediting/microloans/"
    CATEGORY_URLS = {
        "mikroqarz": "https://trustbank.uz/uz/private/crediting/microloans/",
        "ipoteka_tijorat": (
            "https://trustbank.uz/uz/private/crediting/"
            "bankning-o-z-mablag-lari-hisobidan-ajratiladigan-ipoteka-krediti/"
        ),
    }
    CATEGORY_HEADINGS = {
        "mikroqarz": ("Doimiy daromadga ega bo", "Mikroqarz rasmiylashtirishda"),
    }
    GRACE_PERIOD_HEADINGS = {
        "mikroqarz": ("Mikroqarzning imtiyozli davri", "Doimiy daromadga ega bo"),
    }
    PRODUCT_NAMES = {
        "mikroqarz": "Mikroqarz",
        # Sahifa <title>'i, H1 sarlavhasi va breadcrumb'i (qisqartirilgan
        # holda) bilan mos — jonli sahifadan tasdiqlangan. Boshqa
        # PRODUCT_NAMES yozuvlari bilan izchillik uchun sahifadagi haqiqiy
        # Unicode apostrof (U+2018) o'rniga ASCII apostrof ishlatilgan.
        "ipoteka_tijorat": "Bankning o'z mablag'lari hisobidan ajratiladigan ipoteka krediti",
    }
    FORCE_COLLATERAL = {
        "mikroqarz": True,
        "ipoteka_tijorat": True,
    }

    def run(self) -> list[Product]:
        """"mikroqarz" bir umumiy bo'lak ustida standart
        extract_percentages/extract_term_months/extract_amount_som bilan
        to'g'ri ishlaydigan oddiy hol bo'lgani uchun bazaviy klassning
        generik CATEGORY_URLS/CATEGORY_HEADINGS yo'lidan (BaseScraper.run())
        o'tadi — quyidagi else shoxobchasi shuning uchun mavjud, xuddi
        scrapers/ofb.py'ning run()idagi kabi. "ipoteka_tijorat" esa so'z
        shaklidagi foizlar va vergul-o'nlikli summa tufayli maxsus
        _build_ipoteka_tijorat_product'ga muhtoj (yuqoridagi docstring'ga
        qarang), shu sabab BITTA umumiy generik CATEGORY_HEADINGS bo'limiga
        sig'dirib bo'lmaydi."""
        now = datetime.now(timezone.utc)
        products: list[Product] = []

        for category, url in self.CATEGORY_URLS.items():
            try:
                html = fetch_html(url, extra_ca_cert=self.EXTRA_CA_CERT)
                text = html_to_text(html)

                if category == "ipoteka_tijorat":
                    product = self._build_ipoteka_tijorat_product(url, now, text)
                else:  # mikroqarz — generik yo'l
                    heading_pair = self.CATEGORY_HEADINGS.get(category)
                    if heading_pair is not None:
                        start_heading, end_heading = heading_pair
                        section = extract_section(text, start_heading, end_heading)
                    else:
                        section = text

                    product = self._build_product(
                        category,
                        section,
                        url,
                        now,
                        full_text=text,
                        down_payment_pct=self._extract_down_payment_pct(category, text),
                        grace_period_months=self._extract_grace_period_months(category, text),
                        payment_method=self._extract_payment_method(category, text),
                    )
            except Exception:
                continue
            if product is not None:
                products.append(product)
        return products

    def _build_ipoteka_tijorat_product(self, url: str, now: datetime, text: str) -> Product | None:
        """Yuqoridagi klass docstring'idagi izohga qarang — so'z shaklidagi
        foizlar (_FOIZ_RE) va vergul-o'nlikli "700,0 mln so'mgacha" summasi
        (",0 mln" -> " mln" almashtirilgandan keyin extract_amount_som)
        standart generik yo'l bilan ifodalab bo'lmaydigan ikkita maxsus
        holat."""
        amount_section = extract_section(text, "Kredit miqdori", "Yillik foiz stavkasi")
        amount = extract_amount_som(amount_section.replace(",0 mln", " mln"))

        term_section = extract_section(text, "Muddati", "Boshlang")
        terms = extract_term_months(term_section)

        rate_section = extract_section(text, "Yillik foiz stavkasi", "To‘lov usuli")
        rates = [float(m.replace(",", ".")) for m in _FOIZ_RE.findall(rate_section)]

        down_section = extract_section(text, "Boshlang", "Kredit miqdori")
        down_rates = [float(m.replace(",", ".")) for m in _FOIZ_RE.findall(down_section)]
        down_payment_pct = min(down_rates) if down_rates else None

        payment_section = extract_section(text, "To‘lov usuli", "Kredit oluvchi yoshi")
        payment_method = extract_payment_method(payment_section)

        grace_period_months = extract_grace_period_months(text)

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
            grace_period_months=grace_period_months,
            payment_method=payment_method,
        )
