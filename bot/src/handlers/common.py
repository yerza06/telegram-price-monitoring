from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from common.texts import ADD_USAGE, ADMIN_COMMANDS, USER_COMMANDS
from core.config import settings

router = Router()


def format_commands(commands: list[tuple[str, str]]) -> str:
    return "\n".join(f"{command} — {description}" for command, description in commands)


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Привет! Я слежу за ценами продавцов на Kaspi.kz и пишу, когда цена меняется "
        "или товар пропадает из продажи.\n\n"
        f"Сначала выберите город: /city\n\n{ADD_USAGE}\n\nВсе команды: /help"
    )


@router.message(Command("help"))
async def help_(message: Message) -> None:
    text = format_commands(USER_COMMANDS)
    if message.from_user.id == settings.bot.admin_id:
        text += "\n\nАдминистратор:\n" + format_commands(ADMIN_COMMANDS)
    await message.answer(text)
