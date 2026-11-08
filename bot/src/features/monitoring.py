import asyncio
import logging

import httpx
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models import PriceHistory, Product, Subscription, utcnow
from features.notifications import build_message
from services.kaspi.client import fetch_offer
from services.kaspi.exceptions import KaspiError

log = logging.getLogger(__name__)

REQUEST_PAUSE_SECONDS = 2


async def check_prices(
    bot: Bot,
    session_maker: async_sessionmaker,
    client: httpx.AsyncClient,
    pause: float = REQUEST_PAUSE_SECONDS,
) -> None:
    """Одна проверка всех пар с подписчиками: история, новая цена, уведомления."""
    async with session_maker() as session:
        products = (
            await session.scalars(
                select(Product)
                .where(Product.id.in_(select(Subscription.product_id)))
                .order_by(Product.id)
            )
        ).all()
        log.info("Проверка цен: %d товаров", len(products))
        for i, product in enumerate(products):
            if i:
                await asyncio.sleep(pause)
            try:
                offer = await fetch_offer(
                    client, product.kaspi_id, product.merchant_id, product.city_id
                )
            except KaspiError:
                log.exception("Kaspi: товар %s продавца %s", product.kaspi_id, product.merchant_id)
                continue

            new_price = offer.price if offer else None
            text = build_message(product, product.last_price, product.in_stock, new_price)
            now = utcnow()
            if offer:
                product.last_price = offer.price  # без предложения храним последнюю известную цену
            product.in_stock = offer is not None
            product.checked_at = now
            session.add(PriceHistory(product_id=product.id, price=new_price, checked_at=now))
            await session.commit()  # цена сохранена до рассылки, даже если доставка упадёт

            if text is None:
                continue
            user_ids = await session.scalars(
                select(Subscription.user_id).where(Subscription.product_id == product.id)
            )
            for user_id in user_ids.all():
                try:
                    await bot.send_message(user_id, text)
                except TelegramAPIError:
                    log.exception("Не удалось отправить уведомление пользователю %s", user_id)
