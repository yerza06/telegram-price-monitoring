from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.kaspi.cities import CITIES


class CityCallback(CallbackData, prefix="city"):
    id: str


def cities_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city_id, name in CITIES.items():
        builder.button(text=name, callback_data=CityCallback(id=city_id))
    builder.adjust(2)
    return builder.as_markup()
