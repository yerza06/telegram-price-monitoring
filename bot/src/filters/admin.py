from aiogram import F

from core.config import settings

is_admin = F.from_user.id == settings.bot.admin_id
