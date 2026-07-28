from pathlib import Path
from unittest.mock import patch

from scrapers.tbc import TBCBankScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_BY_URL = {
    TBCBankScraper.CATEGORY_URLS["avtokredit_brend_birlamchi"]: (
        FIXTURES_DIR / "tbc_avtokredit.html"
    ).read_text(encoding="utf-8"),
}


def _fake_fetch(url, *args, **kwargs):
    return FIXTURE_BY_URL[url]


def test_tbc_avtokredit_brend_birlamchi_parses_correctly():
    """"TBC Avtokredit" — rasmiy dilerlar orqali ko'p turli chet el brendi
    (BMW, BYD, Changan, Chery, Chevrolet, Haval, Hyundai, KIA, Toyota,
    Zeekr va boshqalar) uchun, faqat yangi avtomobil sotib olishga
    mo'ljallangan — shu sabab avtokredit_brend_birlamchi toifasiga
    to'g'ri keladi (bitta brendga cheklanmagan bo'lsa ham, xuddi NBU'ning
    "Avtokredit KIA, Chery"si kabi).

    Aniq raqamlar "TBC Bank avtokreditining shartlari qanday?" FAQ
    javobidan olinadi: "12 oydan 60 oygacha" muddat, "1 mlrd so'mgacha"
    summa, "yillik 0% dan 29,5% gacha" stavka — bu javob sahifadagi
    boshqa, faqat yuqori chegarani ("yillik 29,5% gacha") takrorlaydigan
    qisqa marketing ro'yxatidan ustuvor, chunki u yagona aniq quyi
    chegarani (0%) beradi. Boshlang'ich to'lov alohida "Boshlang'ich
    to'lov kerakmi?" javobida "kamida 25%" deb yozilgan.

    Sahifaning "Kreditning asosiy shartlari to'g'risida axborot varaqasi"
    bo'limi aslida avtokreditga aloqasi yo'q "Mikroqarz" nomli boshqa
    mahsulot uchun to'ldirilgan demo namunasi (kalkulyator vidjeti bir xil
    shablonni ishlatgani sabab) — shu sabab butunlay e'tiborga olinmaydi,
    undagi "Annuitet" so'zi ham to'lov usuli sifatida ishlatilmaydi.

    Garov: FAQ'da "Kredit to'liq yopilguncha avtomobil bankda garovda
    turadi" deb aniq aytilgan, lekin aloqasiz Mikroqarz namunasidagi
    "Qo'shimcha xarajatlar: Mavjud emas" ham bir xil sahifada bor bo'lgani
    uchun umumiy has_collateral_requirement() "mavjud emas"ni butun sahifa
    bo'yicha yolg'on-manfiy signal deb o'qiydi — shu sabab FORCE_COLLATERAL
    orqali aniq True qilib belgilangan."""
    with patch("scrapers.tbc.fetch_html", side_effect=_fake_fetch):
        products = TBCBankScraper().run()

    assert len(products) == 1
    product = products[0]
    assert product.bank == "TBC Bank"
    assert product.category == "avtokredit_brend_birlamchi"
    assert product.product_name == "TBC Avtokredit"
    assert product.rate_min == 0.0
    assert product.rate_max == 29.5
    assert product.term_min_months == 12
    assert product.term_max_months == 60
    assert product.amount_max_som == 1_000_000_000
    assert product.down_payment_pct == 25.0
    assert product.grace_period_months is None
    assert product.payment_method is None
    assert product.requires_collateral is True
