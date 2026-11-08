import pytest
from pydantic import ValidationError

from core.config import Settings

ENV_VARS = [
    "ENVIRONMENT",
    "BOT_TOKEN",
    "BOT_ADMIN_ID",
    "DATABASE_URL",
    "MONITOR_INTERVAL_MINUTES",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    # без .env разработчика и без переменных из conftest
    monkeypatch.chdir(tmp_path)
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("BOT_TOKEN", "123:secret-token")
    monkeypatch.setenv("BOT_ADMIN_ID", "42")


def test_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///other.db")
    monkeypatch.setenv("MONITOR_INTERVAL_MINUTES", "5")
    s = Settings()
    assert s.bot.token.get_secret_value() == "123:secret-token"
    assert s.bot.admin_id == 42
    assert s.database.url == "sqlite+aiosqlite:///other.db"
    assert s.monitor.interval_minutes == 5


def test_defaults():
    s = Settings()
    assert s.environment == "local"
    assert s.database.url == "sqlite+aiosqlite:///bot.db"
    assert s.monitor.interval_minutes == 60


def test_reads_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("BOT_ADMIN_ID")
    (tmp_path / ".env").write_text("BOT_ADMIN_ID=7\nMONITOR_INTERVAL_MINUTES=3\n")
    s = Settings()
    assert s.bot.admin_id == 7
    assert s.monitor.interval_minutes == 3


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("BOT_TOKEN", None),
        ("BOT_ADMIN_ID", None),
        ("BOT_ADMIN_ID", "abc"),
        ("MONITOR_INTERVAL_MINUTES", "0"),
    ],
)
def test_invalid(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError, match=name.split("_", 1)[1].lower()):
        Settings()


def test_token_hidden():
    s = Settings()
    assert "secret-token" not in repr(s)
    assert "secret-token" not in str(s)


@pytest.mark.parametrize("value", ["local", "prod"])
def test_environment(monkeypatch, value):
    monkeypatch.setenv("ENVIRONMENT", value)
    assert Settings().environment == value


def test_invalid_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    with pytest.raises(ValidationError, match="environment"):
        Settings()
