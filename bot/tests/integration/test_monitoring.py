import logging

import pytest
from helpers import FakeBot
from sqlalchemy import select

from database.models import PriceHistory, Product, Subscription
from features import monitoring
from services.kaspi.client import Offer
from services.kaspi.exceptions import KaspiError


async def add(
    session_maker, kaspi_id: str, price: int, user_ids: list[int], city_id: str = "750000000"
) -> int:
    async with session_maker() as session:
        product = Product(
            kaspi_id=kaspi_id,
            merchant_id="m",
            merchant_name="M",
            title=f"Товар {kaspi_id}",
            url=f"https://kaspi.kz/shop/p/x-{kaspi_id}/",
            last_price=price,
            in_stock=True,
            city_id=city_id,
        )
        session.add(product)
        await session.flush()
        session.add_all(Subscription(user_id=u, product_id=product.id) for u in user_ids)
        await session.commit()
        return product.id


@pytest.fixture
def fetch_calls(monkeypatch):
    """Подменённый Kaspi: товар 1 — ошибка, 2 — подешевел, 3 — пропал, 4 — без изменений."""
    calls = []

    async def fake_fetch_offer(client, product_id, merchant_id, city_id):
        calls.append((product_id, city_id))
        match product_id:
            case "1":
                raise KaspiError("timeout")
            case "2":
                return Offer(merchant_id, "M", 900)
            case "4":
                return Offer(merchant_id, "M", 4000)
        return None

    monkeypatch.setattr(monitoring, "fetch_offer", fake_fetch_offer)
    return calls


async def test_check_prices(session_maker, fetch_calls, caplog):
    failing = await add(session_maker, "1", 1000, [10])
    cheaper = await add(session_maker, "2", 1000, [10, 20, 30], city_id="710000000")
    gone = await add(session_maker, "3", 3000, [10])
    same = await add(session_maker, "4", 4000, [10])
    await add(session_maker, "5", 5000, [])  # без подписчиков не проверяется
    bot = FakeBot(blocked={20})

    with caplog.at_level(logging.ERROR):
        await monitoring.check_prices(bot, session_maker, client=None, pause=0)

    assert fetch_calls == [
        ("1", "750000000"),
        ("2", "710000000"),
        ("3", "750000000"),
        ("4", "750000000"),
    ]
    assert "Kaspi" in caplog.text and "пользователю 20" in caplog.text

    async with session_maker() as session:
        by_id = {p.id: p for p in await session.scalars(select(Product))}
        history = list(await session.execute(select(PriceHistory.product_id, PriceHistory.price)))
    assert (by_id[failing].last_price, by_id[failing].checked_at) == (1000, None)
    assert (by_id[cheaper].last_price, by_id[cheaper].in_stock) == (900, True)
    assert (by_id[gone].last_price, by_id[gone].in_stock) == (3000, False)
    assert sorted(history) == [(cheaper, 900), (gone, None), (same, 4000)]

    # заблокированный 20 не мешает 10 и 30; без изменений — без сообщений
    assert len(bot.texts(30)) == 1 and "1 000 ₸ → 900 ₸" in bot.texts(30)[0]
    assert bot.texts(20) == []
    assert len(bot.texts(10)) == 2 and "Нет в наличии" in bot.texts(10)[1]

    # повторная проверка: «пропал» второй раз не шлётся, цена 900 та же
    bot = FakeBot()
    await monitoring.check_prices(bot, session_maker, client=None, pause=0)
    assert bot.sent == []
