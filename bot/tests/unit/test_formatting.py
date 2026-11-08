from common.formatting import format_price


def test_format_price():
    assert format_price(360581) == "360 581 ₸"
    assert format_price(990) == "990 ₸"
