from common.formatting import format_price
from database.models import Product
from services.kaspi.cities import CITIES


def format_change(old: int, new: int) -> str:
    diff = new - old
    sign = "+" if diff > 0 else "−"
    percent = abs(diff) / old * 100
    return (
        f"{format_price(old)} → {format_price(new)} "
        f"({sign}{format_price(abs(diff))}, {sign}{percent:.1f}%)"
    )


def build_message(
    product: Product, old_price: int | None, old_in_stock: bool, new_price: int | None
) -> str | None:
    """Текст уведомления или None, если цена и наличие не изменились."""
    if new_price is None:
        if not old_in_stock:
            return None
        body = "Нет в наличии у продавца"
    elif not old_in_stock:
        if old_price is None or old_price == new_price:
            body = f"Снова в продаже: {format_price(new_price)}"
        else:
            body = f"Снова в продаже: {format_change(old_price, new_price)}"
    elif old_price == new_price:
        return None
    else:
        verb = "выросла" if new_price > old_price else "снизилась"
        body = f"Цена {verb}: {format_change(old_price, new_price)}"
    city = CITIES.get(product.city_id, product.city_id)
    return f"{product.title}\nПродавец: {product.merchant_name}, {city}\n{body}\n{product.url}"
