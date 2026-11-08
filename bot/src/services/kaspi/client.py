from dataclasses import dataclass

import httpx

from services.kaspi.exceptions import KaspiError
from services.kaspi.parser import parse_product

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0 Safari/537.36"
    ),
}
OFFERS_URL = "https://kaspi.kz/yml/offer-view/offers/{}"
# короткая ссылка на товар без slug: Kaspi отдаёт по ней ту же страницу
PRODUCT_URL = "https://kaspi.kz/shop/p/-{}/"


@dataclass(frozen=True)
class Offer:
    merchant_id: str
    merchant_name: str
    price: int


async def fetch_product(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise KaspiError(f"страница товара: {e!r}") from e
    return parse_product(response.text)


async def fetch_offers(
    client: httpx.AsyncClient,
    product_id: str,
    city_id: str,
    limit: int = 10,
    merchant_id: str | None = None,
) -> list[Offer]:
    """Самые дешёвые предложения товара в городе (Kaspi сортирует по цене)."""
    body = {"cityId": city_id, "limit": limit, "page": 0}
    if merchant_id is not None:
        body["merchantUID"] = merchant_id
    try:
        response = await client.post(
            OFFERS_URL.format(product_id),
            json=body,
            headers={"Referer": PRODUCT_URL.format(product_id)},
        )
        response.raise_for_status()
        return [
            Offer(str(offer["merchantId"]), offer["merchantName"], round(offer["price"]))
            for offer in response.json()["offers"]
        ]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
        raise KaspiError(f"предложения товара {product_id}: {e!r}") from e


async def fetch_offer(
    client: httpx.AsyncClient, product_id: str, merchant_id: str, city_id: str
) -> Offer | None:
    """Предложение продавца в городе; `None` — продавец этот товар не продаёт."""
    offers = await fetch_offers(client, product_id, city_id, merchant_id=merchant_id)
    # фильтр merchantUID проверяем сами: если Kaspi его проигнорирует, не возьмём чужую цену
    return next((offer for offer in offers if offer.merchant_id == merchant_id), None)
