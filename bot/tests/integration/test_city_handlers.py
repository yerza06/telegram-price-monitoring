import pytest
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from helpers import FakeBot, press, send

from database.models import User
from services.kaspi.cities import CITIES

USER = 5


@pytest.fixture(autouse=True)
async def user(session_maker):
    async with session_maker() as session:
        session.add(User(telegram_id=USER))
        await session.commit()


async def city_id(session_maker) -> str | None:
    async with session_maker() as session:
        return (await session.get(User, USER)).city_id


async def test_city_shows_keyboard(session_maker):
    bot = FakeBot()
    [reply] = await send("/city", USER, session_maker, bot=bot)
    assert "Ваш город: не выбран" in reply
    [message] = bot.sent
    assert isinstance(message, SendMessage)
    buttons = {b.text: b.callback_data for row in message.reply_markup.inline_keyboard for b in row}
    assert buttons == {name: f"city:{cid}" for cid, name in CITIES.items()}


async def test_choose_city(session_maker):
    bot = FakeBot()
    await press("city:710000000", USER, session_maker, bot=bot)
    edit, answer = bot.sent
    assert isinstance(edit, EditMessageText) and "Город: Астана" in edit.text
    assert isinstance(answer, AnswerCallbackQuery)
    assert await city_id(session_maker) == "710000000"
    assert "Ваш город: Астана" in (await send("/city", USER, session_maker))[0]


async def test_unknown_city_rejected(session_maker):
    await press("city:710000000", USER, session_maker)
    [reply] = await press("city:999", USER, session_maker)
    assert "Неизвестный город" in reply
    assert await city_id(session_maker) == "710000000"
