from database.models import Product
from services.kaspi.cities import CITIES


def format_price(price: int) -> str:
    return f"{price:,} ₸".replace(",", " ")


def describe_product(product: Product) -> str:
    if product.last_price is None:
        price = "—"
    else:
        price = format_price(product.last_price)
    if not product.in_stock:
        price += " (нет в наличии)"
    city = CITIES.get(product.city_id, product.city_id)
    return (
        f"{product.title}\nПродавец: {product.merchant_name}\nГород: {city}\n"
        f"Цена: {price}\n{product.url}"
    )
