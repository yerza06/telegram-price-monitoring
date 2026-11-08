from helpers import ADMIN_ID, send
from sqlalchemy import select

from database.models import Product, Subscription, User


async def user_ids(session_maker) -> list[int]:
    """ID пользователей с доступом, кроме строки самого админа."""
    async with session_maker() as session:
        return list(
            await session.scalars(select(User.telegram_id).where(User.telegram_id != ADMIN_ID))
        )


async def test_allow(session_maker):
    [reply] = await send("/allow 123456789", ADMIN_ID, session_maker)
    assert "выдан" in reply
    assert await user_ids(session_maker) == [123456789]
    # новый пользователь теперь проходит проверку доступа
    assert "Формат" in (await send("/remove", 123456789, session_maker))[0]


async def test_allow_twice(session_maker):
    await send("/allow 5", ADMIN_ID, session_maker)
    [reply] = await send("/allow 5", ADMIN_ID, session_maker)
    assert "уже есть доступ" in reply
    assert await user_ids(session_maker) == [5]


async def test_allow_bad_id(session_maker):
    for text in ("/allow abc", "/allow", "/allow -5"):
        [reply] = await send(text, ADMIN_ID, session_maker)
        assert "Формат: /allow" in reply
    assert await user_ids(session_maker) == []


async def test_revoke_deletes_subscriptions(session_maker):
    async with session_maker() as session:
        session.add_all([User(telegram_id=5), User(telegram_id=6)])
        product = Product(
            kaspi_id="1",
            merchant_id="m",
            merchant_name="M",
            title="T",
            url="u",
            in_stock=True,
            city_id="750000000",
        )
        session.add(product)
        await session.flush()
        session.add_all(
            [
                Subscription(user_id=5, product_id=product.id),
                Subscription(user_id=6, product_id=product.id),
            ]
        )
        await session.commit()

    [reply] = await send("/revoke 5", ADMIN_ID, session_maker)
    assert "отозван" in reply
    assert await user_ids(session_maker) == [6]
    async with session_maker() as session:
        assert list(await session.scalars(select(Subscription.user_id))) == [6]
    assert "Нет доступа" in (await send("/list", 5, session_maker))[0]


async def test_revoke_admin(session_maker):
    [reply] = await send(f"/revoke {ADMIN_ID}", ADMIN_ID, session_maker)
    assert "Нельзя" in reply
    assert "Список пуст" in (await send("/list", ADMIN_ID, session_maker))[0]


async def test_revoke_unknown(session_maker):
    [reply] = await send("/revoke 999", ADMIN_ID, session_maker)
    assert "нет доступа" in reply


async def test_users(session_maker):
    assert "ни у кого" in (await send("/users", ADMIN_ID, session_maker))[0]
    await send("/allow 5", ADMIN_ID, session_maker)
    await send("/allow 6", ADMIN_ID, session_maker)
    await send("/start", 6, session_maker)  # имя и username появляются после первого сообщения
    [reply] = await send("/users", ADMIN_ID, session_maker)
    assert reply.splitlines()[1:] == ["5", "6 — user 6"]


async def test_admin_commands_denied_for_user(session_maker):
    await send("/allow 5", ADMIN_ID, session_maker)
    for text in ("/allow 1", "/revoke 5", "/users"):
        [reply] = await send(text, 5, session_maker)
        assert "только администратору" in reply
    assert await user_ids(session_maker) == [5]
