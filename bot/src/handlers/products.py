import logging

import httpx
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.callbacks import finish_callback
from common.formatting import describe_product
from common.texts import ADD_USAGE
from database.models import PriceHistory, Product, Subscription, User, utcnow
from keyboards.offers import OfferCallback, offers_keyboard
from services.kaspi.cities import CITIES
from services.kaspi.client import PRODUCT_URL, fetch_offer, fetch_offers, fetch_product
from services.kaspi.exceptions import KaspiError
from services.kaspi.parser import parse_product_id

log = logging.getLogger(__name__)

router = Router()

KASPI_UNAVAILABLE = "Не удалось получить данные с Kaspi. Попробуйте позже."


@router.message(Command("add"))
async def add(
    message: Message, command: CommandObject, client: httpx.AsyncClient, user: User
) -> None:
    if user.city_id is None:
        await message.answer("Сначала выберите город: /city")
        return
    args = (command.args or "").split()
    product_id = parse_product_id(args[0]) if len(args) == 1 else None
    if product_id is None:
        await message.answer(ADD_USAGE)
        return
    try:
        offers = await fetch_offers(client, product_id, user.city_id)
    except KaspiError:
        log.exception("Kaspi: не удалось получить продавцов товара %s", product_id)
        await message.answer(KASPI_UNAVAILABLE)
        return
    city = CITIES.get(user.city_id, user.city_id)
    if not offers:
        await message.answer(f"В городе {city} этот товар сейчас никто не продаёт.")
        return
    await message.answer(
        f"Выберите продавца — самые дешёвые в городе {city}:",
        reply_markup=offers_keyboard(product_id, offers),
    )


@router.callback_query(OfferCallback.filter())
async def choose_offer(
    callback: CallbackQuery,
    callback_data: OfferCallback,
    session: AsyncSession,
    client: httpx.AsyncClient,
    user: User,
) -> None:
    product_id, merchant_id, city_id = (
        callback_data.product_id,
        callback_data.merchant_id,
        user.city_id,
    )
    # callback_data приходит от клиента, а product_id попадает в URL
    if not product_id.isdigit() or city_id is None:
        await callback.answer("Не удалось добавить товар. Отправьте /add ещё раз.")
        return

    product = await session.scalar(
        select(Product).where(
            Product.kaspi_id == product_id,
            Product.merchant_id == merchant_id,
            Product.city_id == city_id,
        )
    )
    if product is None:
        url = PRODUCT_URL.format(product_id)
        try:
            _, title = await fetch_product(client, url)
            offer = await fetch_offer(client, product_id, merchant_id, city_id)
        except KaspiError:
            log.exception(
                "Kaspi: не удалось добавить товар %s продавца %s", product_id, merchant_id
            )
            await finish_callback(callback, KASPI_UNAVAILABLE)
            return
        if offer is None:
            await finish_callback(callback, "Продавец больше не продаёт этот товар в вашем городе.")
            return
        now = utcnow()
        product = Product(
            kaspi_id=product_id,
            merchant_id=offer.merchant_id,
            merchant_name=offer.merchant_name,
            title=title,
            url=url,
            last_price=offer.price,
            in_stock=True,
            checked_at=now,
            city_id=city_id,
        )
        session.add(product)
        await session.flush()
        session.add(PriceHistory(product_id=product.id, price=offer.price, checked_at=now))
    elif await session.get(Subscription, (user.telegram_id, product.id)):
        await finish_callback(callback, f"Товар уже отслеживается: №{product.id} в /list")
        return

    session.add(Subscription(user_id=user.telegram_id, product_id=product.id))
    await session.commit()
    await finish_callback(callback, f"Добавлено, №{product.id}\n{describe_product(product)}")


@router.message(Command("list"))
async def list_(message: Message, session: AsyncSession) -> None:
    products = (
        await session.scalars(
            select(Product)
            .join(Subscription)
            .where(Subscription.user_id == message.from_user.id)
            .order_by(Product.id)
        )
    ).all()
    if not products:
        await message.answer("Список пуст. Добавьте товар: /add <ссылка на товар>")
        return
    items = [f"№{product.id} {describe_product(product)}" for product in products]
    # не больше 10 товаров в сообщении, чтобы не упереться в лимит Telegram 4096 символов
    for i in range(0, len(items), 10):
        await message.answer("\n\n".join(items[i : i + 10]))


@router.message(Command("remove"))
async def remove(message: Message, command: CommandObject, session: AsyncSession) -> None:
    args = (command.args or "").strip()
    if not args.isdigit():
        await message.answer("Формат: /remove <номер> (номер из /list)")
        return
    subscription = await session.get(Subscription, (message.from_user.id, int(args)))
    if subscription is None:
        await message.answer(f"Товара №{args} нет в вашем списке. Номера — в /list")
        return
    await session.delete(subscription)
    await session.commit()
    await message.answer(f"Товар №{args} удалён из списка.")
