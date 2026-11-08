from database.models import Product
from features.notifications import build_message

PRODUCT = Product(
    title="Чайник", merchant_name="ALPHA", url="https://kaspi.kz/shop/p/x-1/", city_id="710000000"
)


def test_price_dropped():
    text = build_message(PRODUCT, 400_000, True, 360_000)
    assert "400 000 ₸ → 360 000 ₸ (−40 000 ₸, −10.0%)" in text
    assert "Чайник" in text and "ALPHA, Астана" in text and PRODUCT.url in text


def test_price_rose():
    text = build_message(PRODUCT, 100_000, True, 105_000)
    assert "100 000 ₸ → 105 000 ₸ (+5 000 ₸, +5.0%)" in text


def test_no_change():
    assert build_message(PRODUCT, 100_000, True, 100_000) is None


def test_gone():
    text = build_message(PRODUCT, 100_000, True, None)
    assert "Нет в наличии" in text and PRODUCT.url in text


def test_still_gone():
    assert build_message(PRODUCT, 100_000, False, None) is None


def test_back_with_other_price():
    text = build_message(PRODUCT, 50_000, False, 45_000)
    assert "Снова в продаже: 50 000 ₸ → 45 000 ₸ (−5 000 ₸, −10.0%)" in text


def test_back_same_price():
    text = build_message(PRODUCT, 50_000, False, 50_000)
    assert "Снова в продаже: 50 000 ₸" in text and "→" not in text
