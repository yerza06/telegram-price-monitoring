from aiogram import Router

from handlers import admin, city, common, products
from middlewares.access import access_middleware

router = Router()
# outer middleware на корневом router срабатывает до фильтров всех вложенных router
router.message.outer_middleware(access_middleware)
router.callback_query.outer_middleware(access_middleware)
router.include_routers(common.router, city.router, products.router, admin.router)
