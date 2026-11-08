import json

import httpx
import pytest
from aiogram.methods import SendMessage
from helpers import PRODUCT_URL, FakeBot, press, send
from sqlalchemy import select

from database.models import PriceHistory, Product, Subscription, User

USER = 5
OTHER = 6
NO_CITY = 7
ALMATY = "750000000"
ASTANA = "710000000"
TITLE = "Смартфон Apple iPhone 15 128Gb NanoSIM+eSIM черный"


@pytest.fixture(autouse=True)
async def users(session_maker):
    async with session_maker() as session:
        session.add_all(
            [
                User(telegram_id=USER, city_id=ALMATY),
                User(telegram_id=OTHER, city_id=ALMATY),
                User(telegram_id=NO_CITY),
            ]
        )
        await session.commit()


async def products(session_maker) -> list[Product]:
    async with session_maker() as session:
        return list(await session.scalars(select(Product)))


async def test_list_empty(session_maker):
    [reply] = await send("/list", USER, session_maker)
    assert "Список пуст" in reply and "/add" in reply


async def add_product(session_maker, user_ids, **fields) -> int:
    async with session_maker() as session:
        product = Product(
            kaspi_id=fields.get("kaspi_id", "1"),
            merchant_id="m",
            merchant_name="Магазин",
            title=fields.get("title", "Товар"),
            url="https://kaspi.kz/shop/p/x-1/",
            last_price=fields.get("last_price", 1000),
            in_stock=fields.get("in_stock", True),
            city_id=ALMATY,
        )
        session.add(product)
        await session.flush()
        session.add_all(Subscription(user_id=u, product_id=product.id) for u in user_ids)
        await session.commit()
        return product.id


async def test_list(session_maker):
    first = await add_product(session_maker, [USER], title="Чайник", last_price=15000)
    second = await add_product(
        session_maker, [USER], kaspi_id="2", title="Утюг", last_price=20990, in_stock=False
    )
    await add_product(session_maker, [OTHER], kaspi_id="3", title="Чужой")
    [reply] = await send("/list", USER, session_maker)
    assert f"№{first} Чайник" in reply and "15 000 ₸" in reply
    assert f"№{second} Утюг" in reply and "20 990 ₸ (нет в наличии)" in reply
    assert "Чужой" not in reply and "https://kaspi.kz/shop/p/x-1/" in reply


async def test_remove_keeps_other_user(session_maker):
    product_id = await add_product(session_maker, [USER, OTHER])
    [reply] = await send(f"/remove {product_id}", USER, session_maker)
    assert "удалён" in reply
    assert "Список пуст" in (await send("/list", USER, session_maker))[0]
    assert "Товар" in (await send("/list", OTHER, session_maker))[0]


async def test_remove_unknown(session_maker):
    foreign = await add_product(session_maker, [OTHER])
    for number in (str(foreign), "999"):
        [reply] = await send(f"/remove {number}", USER, session_maker)
        assert "нет в вашем списке" in reply
    assert "Товар" in (await send("/list", OTHER, session_maker))[0]


SHORT_URL = "https://kaspi.kz/shop/p/-113137790/"


async def add(user_id, session_maker, client, merchant_id="234005") -> list[str]:
    """/add по ссылке и нажатие кнопки продавца; возвращает ответ на нажатие."""
    await send(f"/add {PRODUCT_URL}", user_id, session_maker, client)
    return await press(f"add:113137790:{merchant_id}", user_id, session_maker, client)


async def test_add_shows_sellers(session_maker, kaspi_client, kaspi_requests):
    bot = FakeBot()
    [reply] = await send(f"/add {PRODUCT_URL}", USER, session_maker, kaspi_client, bot=bot)
    assert "Выберите продавца" in reply and "Алматы" in reply
    [message] = bot.sent
    assert isinstance(message, SendMessage)
    buttons = [row[0] for row in message.reply_markup.inline_keyboard]
    assert len(buttons) == 10
    assert (buttons[0].text, buttons[0].callback_data) == (
        "ALPHA — 360 054 ₸",
        "add:113137790:234005",
    )
    assert json.loads(kaspi_requests[0].content) == {"cityId": ALMATY, "limit": 10, "page": 0}
    assert await products(session_maker) == []


async def test_add(session_maker, kaspi_client, kaspi_requests):
    [reply] = await add(USER, session_maker, kaspi_client)
    assert TITLE in reply and "ALPHA" in reply and "360 054 ₸" in reply and "Город: Алматы" in reply
    [product] = await products(session_maker)
    assert (product.kaspi_id, product.merchant_id, product.last_price, product.city_id) == (
        "113137790",
        "234005",
        360054,
        ALMATY,
    )
    assert product.in_stock and product.url == SHORT_URL and product.title == TITLE
    assert kaspi_requests[1].url == SHORT_URL
    assert json.loads(kaspi_requests[2].content)["merchantUID"] == "234005"
    async with session_maker() as session:
        assert list(await session.scalars(select(PriceHistory.price))) == [360054]
    assert TITLE in (await send("/list", USER, session_maker))[0]


@pytest.mark.parametrize(
    "text",
    [
        "/add",
        f"/add {PRODUCT_URL} 234005",
        "/add https://example.com/shop/p/x-113137790/",
    ],
)
async def test_add_bad_format(session_maker, kaspi_client, kaspi_requests, text):
    [reply] = await send(text, USER, session_maker, kaspi_client)
    assert "Формат: /add" in reply
    assert kaspi_requests == []


async def test_add_without_city(session_maker, kaspi_client, kaspi_requests):
    [reply] = await send(f"/add {PRODUCT_URL}", NO_CITY, session_maker, kaspi_client)
    assert "/city" in reply
    assert kaspi_requests == []


async def test_add_nobody_sells(session_maker):
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"offers": []}))
    )
    bot = FakeBot()
    [reply] = await send(f"/add {PRODUCT_URL}", USER, session_maker, client, bot=bot)
    assert "никто не продаёт" in reply
    assert bot.sent[0].reply_markup is None


async def test_add_kaspi_error(session_maker):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    [reply] = await send(f"/add {PRODUCT_URL}", USER, session_maker, client)
    assert "Попробуйте позже" in reply
    [reply] = await press("add:113137790:234005", USER, session_maker, client)
    assert "Попробуйте позже" in reply
    assert await products(session_maker) == []


async def test_add_seller_gone(session_maker, kaspi_client):
    [reply] = await add(USER, session_maker, kaspi_client, merchant_id="999")
    assert "больше не продаёт" in reply
    assert await products(session_maker) == []


async def test_add_bad_callback(session_maker, kaspi_client, kaspi_requests):
    [reply] = await press("add:../x:234005", USER, session_maker, kaspi_client)
    assert "Отправьте /add ещё раз" in reply
    assert kaspi_requests == [] and await products(session_maker) == []


async def test_add_twice(session_maker, kaspi_client):
    await add(USER, session_maker, kaspi_client)
    [reply] = await add(USER, session_maker, kaspi_client)
    assert "уже отслеживается" in reply
    async with session_maker() as session:
        assert len(list(await session.scalars(select(Subscription)))) == 1


async def test_second_user_reuses_product(session_maker, kaspi_client, kaspi_requests):
    await add(USER, session_maker, kaspi_client)
    kaspi_requests.clear()
    [reply] = await press("add:113137790:234005", OTHER, session_maker, kaspi_client)
    assert "360 054 ₸" in reply and kaspi_requests == []
    assert len(await products(session_maker)) == 1
    async with session_maker() as session:
        assert sorted(await session.scalars(select(Subscription.user_id))) == [USER, OTHER]


async def test_same_product_in_two_cities(session_maker, kaspi_client, kaspi_requests):
    await add(USER, session_maker, kaspi_client)
    await press(f"city:{ASTANA}", OTHER, session_maker)
    [reply] = await add(OTHER, session_maker, kaspi_client)
    assert "Город: Астана" in reply
    assert json.loads(kaspi_requests[-1].content)["cityId"] == ASTANA
    assert sorted(p.city_id for p in await products(session_maker)) == [ASTANA, ALMATY]


async def test_city_change_keeps_added_products(session_maker, kaspi_client):
    await add(USER, session_maker, kaspi_client)
    await press(f"city:{ASTANA}", USER, session_maker)
    [product] = await products(session_maker)
    assert product.city_id == ALMATY
    assert "Город: Алматы" in (await send("/list", USER, session_maker))[0]
