from scrapers.utils import (
    extract_amount_som,
    extract_percentages,
    extract_section,
    extract_term_months,
    has_collateral_requirement,
    html_to_text,
)

SAMPLE_HTML = """
<html><body>
<h2>Avtokredit</h2>
<p>Yillik foiz stavkasi: 24.9% dan 27,9% gacha. Muddati: 12 oydan 60 oygacha.
Kredit miqdori: 800 mln.so'mgacha. Boshlang'ich badal: 30%.
Kredit kafolati: Sotib olingan avtomobil garov sifatida olinadi.</p>
<h2>Mikroqarz</h2>
<p>Yillik foiz stavkasi: 28% dan 31% gacha. Muddati: 3 oydan 36 oygacha.
Kredit miqdori: 100 mln.so'mgacha. Kredit kafolati: Mavjud emas.</p>
</body></html>
"""


def test_html_to_text_strips_tags():
    text = html_to_text(SAMPLE_HTML)
    assert "<h2>" not in text
    assert "Avtokredit" in text


def test_extract_section_isolates_category_block():
    text = html_to_text(SAMPLE_HTML)
    section = extract_section(text, "Avtokredit", "Mikroqarz")
    assert "24.9%" in section
    assert "28%" not in section


def test_extract_percentages_finds_all_rates():
    text = "24.9% dan 27,9% gacha, boshlang'ich badal 30%"
    assert extract_percentages(text) == [24.9, 27.9, 30.0]


def test_extract_term_months_finds_range():
    text = "Muddati: 12 oydan 60 oygacha"
    assert extract_term_months(text) == [12, 60]


def test_extract_amount_som_parses_million():
    text = "Kredit miqdori: 800 mln.so'mgacha"
    assert extract_amount_som(text) == 800_000_000


def test_extract_amount_som_parses_billion():
    text = "Kredit miqdori: 5 mlrd.so'mgacha"
    assert extract_amount_som(text) == 5_000_000_000


def test_extract_amount_som_returns_none_when_absent():
    assert extract_amount_som("Bu yerda summa yo'q") is None


def test_has_collateral_requirement_true_when_garov_mentioned():
    assert has_collateral_requirement("Sotib olingan avtomobil garov sifatida olinadi") is True


def test_has_collateral_requirement_false_when_mavjud_emas():
    assert has_collateral_requirement("Kredit kafolati: Mavjud emas") is False
