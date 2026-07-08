from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest


def _mock_products_response() -> MagicMock:
    response = MagicMock()
    response.json.return_value = []
    return response


def test_dashboard_renders_without_exception():
    with patch("requests.get", return_value=_mock_products_response()):
        at = AppTest.from_file("dashboard/app.py")
        at.run(timeout=10)

    assert not at.exception


def test_dashboard_shows_category_selectbox():
    with patch("requests.get", return_value=_mock_products_response()):
        at = AppTest.from_file("dashboard/app.py")
        at.run(timeout=10)

    assert len(at.selectbox) >= 1
    assert at.selectbox[0].label == "Kategoriya"
