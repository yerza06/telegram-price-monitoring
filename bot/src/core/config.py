from typing import Literal

from pydantic import Field, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def env(prefix: str) -> SettingsConfigDict:
    return SettingsConfigDict(env_prefix=prefix, env_file=".env", extra="ignore")


class BotSettings(BaseSettings):
    model_config = env("BOT_")

    token: SecretStr
    admin_id: int


class DatabaseSettings(BaseSettings):
    model_config = env("DATABASE_")

    url: str = "sqlite+aiosqlite:///bot.db"


class MonitorSettings(BaseSettings):
    model_config = env("MONITOR_")

    interval_minutes: PositiveInt = 60


class Settings(BaseSettings):
    model_config = env("")

    environment: Literal["local", "prod"] = "local"
    bot: BotSettings = Field(default_factory=BotSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    monitor: MonitorSettings = Field(default_factory=MonitorSettings)


settings = Settings()
