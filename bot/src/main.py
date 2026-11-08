import asyncio
from datetime import datetime

import httpx
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.config import settings
from core.logging import configure_logging
from database.engine import engine, session_maker
from features.monitoring import check_prices
from handlers import router
from services.kaspi.client import HEADERS


async def main() -> None:
    configure_logging(settings.environment)
    bot = Bot(settings.bot.token.get_secret_value())
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        dp = Dispatcher(session_maker=session_maker, client=client)
        dp.include_router(router)

        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            check_prices,
            IntervalTrigger(minutes=settings.monitor.interval_minutes),
            args=(bot, session_maker, client),
            max_instances=1,
            coalesce=True,
            next_run_time=datetime.now(),
        )
        scheduler.start()
        try:
            await dp.start_polling(bot)
        finally:
            scheduler.shutdown(wait=False)
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
