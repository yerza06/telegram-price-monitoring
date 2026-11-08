from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from common.formatting import format_price
from services.kaspi.client import Offer


class OfferCallback(CallbackData, prefix="add"):
    product_id: str
    merchant_id: str


def offers_keyboard(product_id: str, offers: list[Offer]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for offer in offers:
        builder.button(
            text=f"{offer.merchant_name} — {format_price(offer.price)}",
            callback_data=OfferCallback(product_id=product_id, merchant_id=offer.merchant_id),
        )
    builder.adjust(1)
    return builder.as_markup()
