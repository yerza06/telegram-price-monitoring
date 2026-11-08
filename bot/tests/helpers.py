from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TgUser

from handlers import router

FIXTURES = Path(__file__).parent / "fixtures"
PRODUCT_URL = "https://kaspi.kz/shop/p/apple-iphone-15-128gb-chernyi-113137790/"
ADMIN_ID = 1

dispatcher = Dispatcher()
dispatcher.include_router(router)


class FakeBot(Bot):
    """Bot без сети: запоминает отправленные сообщения, `blocked` — кто заблокировал бота."""

    def __init__(self, blocked: set[int] = frozenset()):
        super().__init__("42:TEST")
        self.sent: list[TelegramMethod] = []
        self.blocked = blocked

    async def __call__(self, method, request_timeout=None):
        if getattr(method, "chat_id", None) in self.blocked:
            raise TelegramForbiddenError(method=method, message="bot was blocked by the user")
        self.sent.append(method)
        return True

    def texts(self, chat_id: int | None = None) -> list[str]:
        return [
            m.text
            for m in self.sent
            if getattr(m, "text", None) and (chat_id is None or m.chat_id == chat_id)
        ]


def tg_user(user_id: int, username: str | None = None) -> TgUser:
    return TgUser(
        id=user_id, is_bot=False, first_name="user", last_name=str(user_id), username=username
    )


def make_message(text: str, user_id: int, bot: Bot, username: str | None = None) -> Message:
    return Message(
        message_id=1,
        date=datetime.now(),
        chat=Chat(id=user_id, type="private"),
        from_user=tg_user(user_id, username),
        text=text,
    ).as_(bot)


def make_callback(data: str, user_id: int, bot: Bot) -> CallbackQuery:
    return CallbackQuery(
        id="1",
        from_user=tg_user(user_id),
        chat_instance="1",
        data=data,
        message=make_message("/city", user_id, bot),
    ).as_(bot)


async def send(
    text: str, user_id: int, session_maker, client=None, bot: FakeBot | None = None
) -> list[str]:
    """Прогоняет сообщение через dispatcher и возвращает ответы бота."""
    bot = bot or FakeBot()
    update = Update(update_id=1, message=make_message(text, user_id, bot))
    await dispatcher.feed_update(bot, update, session_maker=session_maker, client=client)
    return bot.texts()


async def press(
    data: str, user_id: int, session_maker, client=None, bot: FakeBot | None = None
) -> list[str]:
    """Прогоняет нажатие inline-кнопки через dispatcher и возвращает тексты ответов бота."""
    bot = bot or FakeBot()
    update = Update(update_id=1, callback_query=make_callback(data, user_id, bot))
    await dispatcher.feed_update(bot, update, session_maker=session_maker, client=client)
    return bot.texts()
