from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.config import settings
from database.models import User


async def access_middleware(
    handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
    event: Message | CallbackQuery,
    data: dict[str, Any],
) -> Any:
    """Пускает админа и пользователей из `users`; хендлерам отдаёт `session` и `user`."""
    tg_user = event.from_user
    if tg_user is None:
        return None
    session_maker: async_sessionmaker = data["session_maker"]
    async with session_maker() as session:
        user = await session.get(User, tg_user.id)
        if user is None:
            if tg_user.id != settings.bot.admin_id:
                await event.answer(
                    f"Нет доступа к боту. Ваш Telegram ID: {tg_user.id}\n"
                    "Передайте его администратору, чтобы получить доступ."
                )
                return None
            user = User(telegram_id=tg_user.id)
            session.add(user)
        if (user.full_name, user.username) != (tg_user.full_name, tg_user.username):
            user.full_name, user.username = tg_user.full_name, tg_user.username
            await session.commit()
        data["session"] = session
        data["user"] = user
        return await handler(event, data)
