from unittest.mock import AsyncMock

from aiogram.methods import AnswerCallbackQuery
from helpers import ADMIN_ID, FakeBot, make_callback, make_message
from sqlalchemy import select

from database.models import User
from middlewares.access import access_middleware


async def call(event_factory, user_id: int, session_maker, **kwargs):
    bot = FakeBot()
    handler = AsyncMock(return_value="handled")
    data = {"session_maker": session_maker}
    result = await access_middleware(handler, event_factory(user_id, bot, **kwargs), data)
    return result, handler, bot, data


def message(user_id, bot, username=None):
    return make_message("/list", user_id, bot, username)


def callback(user_id, bot):
    return make_callback("city:710000000", user_id, bot)


async def stored_users(session_maker) -> list[tuple]:
    async with session_maker() as session:
        rows = await session.scalars(select(User).order_by(User.telegram_id))
        return [(u.telegram_id, u.full_name, u.username) for u in rows]


async def test_admin_passes_and_is_stored(session_maker):
    result, handler, bot, data = await call(message, ADMIN_ID, session_maker, username="boss")
    assert result == "handled"
    handler.assert_awaited_once()
    assert data["user"].telegram_id == ADMIN_ID and "session" in data
    assert bot.sent == []
    assert await stored_users(session_maker) == [(ADMIN_ID, "user 1", "boss")]


async def test_allowed_user_passes_and_names_update(session_maker):
    async with session_maker() as session:
        session.add(User(telegram_id=500))
        await session.commit()
    result, handler, _, data = await call(message, 500, session_maker, username="old")
    assert result == "handled"
    handler.assert_awaited_once()
    assert data["user"].username == "old"
    await call(message, 500, session_maker, username="new")
    assert await stored_users(session_maker) == [(500, "user 500", "new")]


async def test_stranger_denied(session_maker):
    result, handler, bot, _ = await call(message, 777, session_maker)
    assert result is None
    handler.assert_not_awaited()
    [text] = bot.texts(777)
    assert "Нет доступа" in text and "777" in text
    assert await stored_users(session_maker) == []


async def test_stranger_callback_denied(session_maker):
    result, handler, bot, _ = await call(callback, 777, session_maker)
    assert result is None
    handler.assert_not_awaited()
    [answer] = bot.sent
    assert isinstance(answer, AnswerCallbackQuery) and "777" in answer.text
    assert await stored_users(session_maker) == []
