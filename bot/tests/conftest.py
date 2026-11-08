import os

# core.config.settings создаётся при импорте, поэтому окружение задаём до импорта модулей бота
os.environ["BOT_TOKEN"] = "42:TEST"
os.environ["BOT_ADMIN_ID"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

import json

import httpx
import pytest
from helpers import FIXTURES


@pytest.fixture
def kaspi_requests():
    """Запросы, которые ушли в подменённый Kaspi."""
    return []


@pytest.fixture
def kaspi_client(kaspi_requests):
    """httpx-клиент, который отвечает сохранённой страницей товара и offers."""

    def handler(request: httpx.Request) -> httpx.Response:
        kaspi_requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, text=(FIXTURES / "product.html").read_text())
        # как настоящий Kaspi: фильтр по merchantUID и limit
        body = json.loads(request.content)
        offers = json.loads((FIXTURES / "offers.json").read_text())["offers"]
        if "merchantUID" in body:
            offers = [o for o in offers if o["merchantId"] == body["merchantUID"]]
        return httpx.Response(200, json={"offers": offers[: body["limit"]]})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))
