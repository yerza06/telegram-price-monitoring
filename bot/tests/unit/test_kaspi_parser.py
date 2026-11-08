import pytest
from helpers import FIXTURES

from services.kaspi.exceptions import KaspiError
from services.kaspi.parser import parse_product, parse_product_id


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://kaspi.kz/shop/p/apple-iphone-15-128gb-chernyi-113137790/", "113137790"),
        (
            "https://kaspi.kz/shop/p/apple-iphone-15-128gb-chernyi-113137790/?c=750000000",
            "113137790",
        ),
        ("kaspi.kz/shop/p/x-1/", None),
        ("https://example.com/shop/p/apple-iphone-15-113137790/", None),
        ("https://kaspi.kz/shop/c/smartphones/", None),
        ("https://kaspi.kz.evil.com/shop/p/x-113137790/", None),
    ],
)
def test_parse_product_id(url, expected):
    assert parse_product_id(url) == expected


def test_parse_product():
    product_id, title = parse_product((FIXTURES / "product.html").read_text())
    assert product_id == "113137790"
    assert title == "Смартфон Apple iPhone 15 128Gb NanoSIM+eSIM черный"


@pytest.mark.parametrize(
    "page",
    [
        "<html><body>нет карточки</body></html>",
        "<script>BACKEND.components.item = {broken</script>",
        '<script>BACKEND.components.item = {"nocard": 1}</script>',
    ],
)
def test_parse_product_broken(page):
    with pytest.raises(KaspiError):
        parse_product(page)
