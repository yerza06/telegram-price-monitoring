from datetime import UTC, datetime

from sqlalchemy import ForeignKey, MetaData, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    # именованные ограничения нужны Alembic batch-миграциям на SQLite
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    """Пользователь с доступом или админ (права админа всё равно из BOT_ADMIN_ID)."""

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    full_name: Mapped[str | None]
    username: Mapped[str | None]
    city_id: Mapped[str | None]  # None — город не выбран
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Product(Base):
    """Пара «товар + продавец» в городе, общая для подписчиков. Цены — целые тенге."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("kaspi_id", "merchant_id", "city_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kaspi_id: Mapped[str]
    merchant_id: Mapped[str]
    merchant_name: Mapped[str]
    title: Mapped[str]
    url: Mapped[str]
    last_price: Mapped[int | None]
    in_stock: Mapped[bool]
    checked_at: Mapped[datetime | None]
    city_id: Mapped[str]


class Subscription(Base):
    __tablename__ = "subscriptions"

    # без FK на users: строка админа появляется только после его первого сообщения
    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    price: Mapped[int | None]  # None — нет в наличии
    checked_at: Mapped[datetime] = mapped_column(default=utcnow)
