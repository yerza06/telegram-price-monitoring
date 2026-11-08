# telegram-price-monitoring

Telegram-бот, который следит за ценой выбранного продавца на товар в [Kaspi.kz](https://kaspi.kz)
и сообщает, когда цена выросла, упала или продавец перестал продавать товар.

## Возможности

- `/add <ссылка на товар>` — бот показывает 10 самых дешёвых продавцов в вашем городе, вы выбираете
  нужного кнопкой.
- `/city` — свой город у каждого пользователя: цены и наличие на Kaspi зависят от города.
- Уведомления об изменении цены (старая и новая цена, разница в ₸ и %) и о наличии.
- `/list`, `/remove` — личный список товаров; история цен хранится в базе.
- Доступ по списку: администратор из `BOT_ADMIN_ID` выдаёт и отзывает доступ (`/allow`, `/revoke`,
  `/users`).

## Быстрый старт

Нужен [uv](https://docs.astral.sh/uv/) и токен бота от [@BotFather](https://t.me/BotFather).

```sh
cd bot
uv sync
cp .env.example .env          # указать BOT_TOKEN и BOT_ADMIN_ID
uv run alembic upgrade head   # создать базу
uv run python src/main.py
```

Переменные окружения, команды, разработка и структура кода — в [bot/README.md](bot/README.md).

## Стек

Python 3.13, aiogram 3, SQLAlchemy 2 (async) + SQLite + Alembic, APScheduler, httpx, selectolax,
Pydantic Settings, Rich. Тесты — pytest.

## Структура репозитория

- `bot/` — код бота, тесты и миграции.
- `openspec/` — спецификации ([OpenSpec](https://github.com/Fission-AI/OpenSpec)) и архив изменений.

## Лицензия

[MIT](LICENSE)
