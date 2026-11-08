import json

import httpx
import pytest

from services.kaspi.client import Offer, fetch_offer, fetch_offers, fetch_product
from services.kaspi.exceptions import KaspiError


def client_returning(response: httpx.Response, requests: list | None = None) -> httpx.AsyncClient:
    def handler(request):
        if requests is not None:
            requests.append(request)
        return response

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetch_offer(kaspi_client, kaspi_requests):
    offer = await fetch_offer(kaspi_client, "113137790", "540017", "750000000")
    assert offer == Offer("540017", "FORTUNA", 363068)
    request = kaspi_requests[0]
    assert request.url == "https://kaspi.kz/yml/offer-view/offers/113137790"
    assert json.loads(request.content) == {
        "cityId": "750000000",
        "limit": 10,
        "page": 0,
        "merchantUID": "540017",
    }
    assert request.headers["Referer"] == "https://kaspi.kz/shop/p/-113137790/"


async def test_fetch_offer_text_merchant_id(kaspi_client):
    offer = await fetch_offer(kaspi_client, "113137790", "Sulpak", "750000000")
    assert offer is not None and offer.price == 430990


async def test_fetch_offer_missing_merchant(kaspi_client):
    assert await fetch_offer(kaspi_client, "113137790", "999", "750000000") is None


async def test_fetch_offer_empty_offers():
    client = client_returning(httpx.Response(200, json={"offers": [], "total": 51}))
    assert await fetch_offer(client, "113137790", "234005", "750000000") is None


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(403, text="Forbidden"),
        httpx.Response(200, text="<html>не json</html>"),
        httpx.Response(200, json={"something": "else"}),
        httpx.Response(200, json={"offers": [{"merchantId": "234005"}]}),
    ],
)
async def test_fetch_offer_errors(response):
    with pytest.raises(KaspiError):
        await fetch_offer(client_returning(response), "113137790", "234005", "750000000")


async def test_fetch_offer_network_error():
    def handler(request):
        raise httpx.ConnectTimeout("timeout", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(KaspiError):
        await fetch_offer(client, "113137790", "234005", "750000000")


async def test_fetch_product(kaspi_client):
    assert await fetch_product(kaspi_client, "https://kaspi.kz/shop/p/x-113137790/") == (
        "113137790",
        "Смартфон Apple iPhone 15 128Gb NanoSIM+eSIM черный",
    )


async def test_fetch_product_http_error():
    with pytest.raises(KaspiError):
        await fetch_product(client_returning(httpx.Response(500)), "https://kaspi.kz/shop/p/x-1/")


async def test_fetch_offers(kaspi_client, kaspi_requests):
    offers = await fetch_offers(kaspi_client, "113137790", "710000000")
    assert len(offers) == 10
    assert offers[0] == Offer("234005", "ALPHA", 360054)
    assert [o.price for o in offers] == sorted(o.price for o in offers)
    assert json.loads(kaspi_requests[0].content) == {"cityId": "710000000", "limit": 10, "page": 0}
