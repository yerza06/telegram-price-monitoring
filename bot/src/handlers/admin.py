from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from database.models import Subscription, User
from filters.admin import is_admin

router = Router()


def parse_telegram_id(args: str | None) -> int | None:
    return int(args) if args and args.strip().isdigit() else None


@router.message(Command("allow"), is_admin)
async def allow(message: Message, command: CommandObject, session: AsyncSession) -> None:
    user_id = parse_telegram_id(command.args)
    if user_id is None:
        await message.answer("Формат: /allow <telegram_id>")
        return
    if user_id == settings.bot.admin_id or await session.get(User, user_id):
        await message.answer(f"У пользователя {user_id} уже есть доступ.")
        return
    session.add(User(telegram_id=user_id))
    await session.commit()
    await message.answer(f"Доступ выдан пользователю {user_id}.")


@router.message(Command("revoke"), is_admin)
async def revoke(message: Message, command: CommandObject, session: AsyncSession) -> None:
    user_id = parse_telegram_id(command.args)
    if user_id is None:
        await message.answer("Формат: /revoke <telegram_id>")
        return
    if user_id == settings.bot.admin_id:
        await message.answer("Нельзя отозвать доступ администратора.")
        return
    user = await session.get(User, user_id)
    if user is None:
        await message.answer(f"У пользователя {user_id} нет доступа.")
        return
    await session.delete(user)
    await session.execute(delete(Subscription).where(Subscription.user_id == user_id))
    await session.commit()
    await message.answer(f"Доступ пользователя {user_id} отозван, его товары удалены.")


@router.message(Command("users"), is_admin)
async def users(message: Message, session: AsyncSession) -> None:
    rows = (
        await session.scalars(
            select(User).where(User.telegram_id != settings.bot.admin_id).order_by(User.created_at)
        )
    ).all()
    if not rows:
        await message.answer("Кроме администратора, доступа ни у кого нет.")
        return
    await message.answer("Пользователи с доступом:\n" + "\n".join(map(describe_user, rows)))


def describe_user(user: User) -> str:
    name = " ".join(filter(None, [user.full_name, user.username and f"@{user.username}"]))
    return f"{user.telegram_id} — {name}" if name else str(user.telegram_id)


@router.message(Command("allow", "revoke", "users"))
async def admin_only(message: Message) -> None:
    await message.answer("Эта команда доступна только администратору.")
