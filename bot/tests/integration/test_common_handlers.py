import pytest
from aiogram.filters import Command
from helpers import ADMIN_ID, send

from common.texts import ADMIN_COMMANDS, USER_COMMANDS
from database.models import User
from handlers import router

USER = 5
OTHER = 6
TITLE = "Смартфон Apple iPhone 15 128Gb NanoSIM+eSIM черный"


@pytest.fixture(autouse=True)
async def users(session_maker):
    async with session_maker() as session:
        session.add_all([User(telegram_id=USER), User(telegram_id=OTHER)])
        await session.commit()


def shown_commands(text: str) -> set[str]:
    return {line.split()[0] for line in text.splitlines() if line.startswith("/")}


async def test_start(session_maker):
    [reply] = await send("/start", USER, session_maker)
    assert "/city" in reply and "/add" in reply and "/help" in reply


async def test_help_user(session_maker):
    [reply] = await send("/help", USER, session_maker)
    assert shown_commands(reply) == {"/start", "/help", "/city", "/add", "/list", "/remove"}


async def test_help_admin(session_maker):
    [reply] = await send("/help", ADMIN_ID, session_maker)
    assert shown_commands(reply) == {
        "/start",
        "/help",
        "/city",
        "/add",
        "/list",
        "/remove",
        "/allow",
        "/revoke",
        "/users",
    }


def test_every_router_command_in_help():
    documented = {command.split()[0] for command, _ in USER_COMMANDS + ADMIN_COMMANDS}
    registered = {
        f"/{name}"
        for r in router.chain_tail
        for handler in r.message.handlers
        for flt in handler.filters
        if isinstance(flt.callback, Command)
        for name in flt.callback.commands
    }
    assert registered == documented
