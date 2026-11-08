from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from common.callbacks import finish_callback
from database.models import User
from keyboards.cities import CityCallback, cities_keyboard
from services.kaspi.cities import CITIES

router = Router()


@router.message(Command("city"))
async def city(message: Message, user: User) -> None:
    current = CITIES.get(user.city_id, "не выбран")
    await message.answer(
        f"Ваш город: {current}\nВыберите город, в котором смотреть цены:",
        reply_markup=cities_keyboard(),
    )


@router.callback_query(CityCallback.filter())
async def choose_city(
    callback: CallbackQuery, callback_data: CityCallback, session: AsyncSession, user: User
) -> None:
    # callback_data приходит от клиента, поэтому ID сверяем со списком
    name = CITIES.get(callback_data.id)
    if name is None:
        await callback.answer("Неизвестный город.")
        return
    user.city_id = callback_data.id
    await session.commit()
    text = (
        f"Город: {name}. Новые товары будут отслеживаться в нём, уже добавленные — в своём городе."
    )
    await finish_callback(callback, text)
