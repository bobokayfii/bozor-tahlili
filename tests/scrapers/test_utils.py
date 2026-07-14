import socket
from unittest.mock import Mock, patch

import pytest
import requests

from scrapers.utils import (
    _resolve_hostname_as,
    extract_amount_som,
    extract_percentages,
    extract_section,
    extract_term_months,
    fetch_html,
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


def test_extract_percentages_ignores_three_digit_collateral_ratios():
    # A "125%" collateral-coverage ratio (common phrasing: "Ta'minotning
    # umumiy miqdori kredit miqdoridan 125%dan kam bo'lmasligi kerak") is
    # not an interest rate and must not be misread as "25%".
    text = "Yillik foiz stavkasi: 26,99%. Ta'minot kredit miqdoridan 125%dan kam bo'lmasligi kerak."
    assert extract_percentages(text) == [26.99]


def test_extract_term_months_finds_range():
    text = "Muddati: 12 oydan 60 oygacha"
    assert extract_term_months(text) == [12, 60]


def test_extract_term_months_excludes_grace_period_figure_when_range_present():
    # Reproduces the NBU bug: a grace-period ("imtiyozli davr") figure phrased
    # as a bare "N oygacha" must not pollute the main term range.
    text = "Muddati: 12 oydan 60 oygacha. Imtiyozli davr: 6 oygacha."
    assert extract_term_months(text) == [12, 60]


def test_extract_term_months_converts_single_year_figure():
    # Ipoteka Bank's autocredit page states duration in years, not months
    # ("5 yilgacha"), unlike every other bank which uses "oygacha".
    text = "Muddati: 5 yilgacha"
    assert extract_term_months(text) == [60]


def test_extract_term_months_converts_year_range():
    text = "Muddati: 1 yildan 5 yilgacha"
    assert extract_term_months(text) == [12, 60]


def test_extract_term_months_falls_back_to_bare_month_figure():
    # InfinBank's consumer-credit page states "Kredit muddati: 18 oy"
    # without the usual "oygacha" suffix.
    text = "Kredit muddati: 18 oy"
    assert extract_term_months(text) == [18]


def test_extract_term_months_falls_back_to_bare_year_figure():
    # InfinBLACK's card page states "5 yil" (limit validity) without the
    # usual "yilgacha" suffix.
    text = "Kredit limitining mavjudlik muddati: 5 yil"
    assert extract_term_months(text) == [60]


def test_extract_term_months_prefers_gacha_phrasing_over_bare_fallback():
    # When a proper "N oygacha" range or single figure exists, the bare
    # fallback must not also contribute unrelated bare "N oy" mentions
    # elsewhere in the same text (e.g. "6 oylik ish stajiga" job-tenure
    # requirements often sit near the real term on real bank pages).
    text = "Kredit muddati: 48 oygacha. Ariza uchun kamida 6 oylik ish stajiga ega bo'lish kerak."
    assert extract_term_months(text) == [48]


def test_extract_amount_som_parses_million():
    text = "Kredit miqdori: 800 mln.so'mgacha"
    assert extract_amount_som(text) == 800_000_000


def test_extract_amount_som_parses_billion():
    text = "Kredit miqdori: 5 mlrd.so'mgacha"
    assert extract_amount_som(text) == 5_000_000_000


def test_extract_amount_som_parses_uzs_currency_code():
    text = "Maksimal kredit limiti: 100 mln UZS"
    assert extract_amount_som(text) == 100_000_000


def test_extract_amount_som_parses_grouped_exact_sum():
    # InfinBank's consumer-credit page spells out the exact ceiling instead
    # of rounding to "mln so'm": "100 BHMgacha ... 41 200 000 so'mgacha".
    text = "Kredit miqdori: 100 BHMgacha (BHM - bazaviy hisoblash miqdori) - 41 200 000 so'mgacha"
    assert extract_amount_som(text) == 41_200_000


def test_extract_amount_som_returns_none_when_absent():
    assert extract_amount_som("Bu yerda summa yo'q") is None


def test_has_collateral_requirement_true_when_garov_mentioned():
    assert has_collateral_requirement("Sotib olingan avtomobil garov sifatida olinadi") is True


def test_has_collateral_requirement_false_when_mavjud_emas():
    assert has_collateral_requirement("Kredit kafolati: Mavjud emas") is False


def test_fetch_html_returns_response_text_on_success():
    mock_response = Mock(text="<html>ok</html>")
    mock_response.raise_for_status = Mock()
    with patch("scrapers.utils.requests.get", return_value=mock_response) as mock_get:
        result = fetch_html("https://bank.uz/kredit")

    assert result == "<html>ok</html>"
    assert mock_get.call_args.kwargs["verify"] is True


def test_fetch_html_falls_back_to_doh_resolved_ip_on_connection_error():
    """Some bank domains fail plain requests.get with a DNS resolution
    error even though the site is reachable; fetch_html should recover by
    resolving via DNS-over-HTTPS and retrying against that IP."""
    ok_response = Mock(text="<html>recovered</html>")
    ok_response.raise_for_status = Mock()
    call_count = {"n": 0}

    def fake_get(url, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise requests.exceptions.ConnectionError("DNS lookup failed")
        return ok_response

    with (
        patch("scrapers.utils.requests.get", side_effect=fake_get),
        patch("scrapers.utils._resolve_via_doh", return_value="203.0.113.10"),
    ):
        result = fetch_html("https://bank.uz/kredit")

    assert result == "<html>recovered</html>"
    assert call_count["n"] == 2


def test_fetch_html_reraises_original_error_when_no_fallback_ip_available():
    connection_error = requests.exceptions.ConnectionError("DNS lookup failed")

    with (
        patch("scrapers.utils.requests.get", side_effect=connection_error),
        patch("scrapers.utils._resolve_via_doh", return_value=None),
    ):
        with pytest.raises(requests.exceptions.ConnectionError):
            fetch_html("https://unreachable-bank.uz/kredit")


def test_resolve_hostname_as_only_patches_the_given_hostname():
    original = socket.getaddrinfo
    seen_hosts = []

    def fake_getaddrinfo(host, *args, **kwargs):
        seen_hosts.append(host)
        return []

    with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
        with _resolve_hostname_as("bank.uz", "203.0.113.10"):
            socket.getaddrinfo("bank.uz", 443)
            socket.getaddrinfo("other.uz", 443)

    assert socket.getaddrinfo is original
    # fake_getaddrinfo receives whatever _resolve_hostname_as substituted
    assert seen_hosts == ["203.0.113.10", "other.uz"]
