# Kaspi price monitor

Telegram-бот следит за ценой конкретного продавца на товар в Kaspi.kz и пишет, когда цена
меняется или продавец перестаёт продавать товар.

## Установка

Нужен [uv](https://docs.astral.sh/uv/). Все команды — из папки `bot/`.

```sh
uv sync
cp .env.example .env   # и заполнить
```

## Переменные окружения

Читаются из окружения или из `.env` в текущей папке.

| Переменная | Обязательна | По умолчанию | Что это |
|---|---|---|---|
| `ENVIRONMENT` | нет | `local` | `local` — красивый вывод Rich; `prod` — одна JSON-запись на строку, включая ошибки |
| `BOT_TOKEN` | да | — | токен бота от [@BotFather](https://t.me/BotFather) |
| `BOT_ADMIN_ID` | да | — | ваш Telegram ID (узнать: [@userinfobot](https://t.me/userinfobot)); админ выдаёт доступ остальным |
| `DATABASE_URL` | нет | `sqlite+aiosqlite:///bot.db` | база SQLite |
| `MONITOR_INTERVAL_MINUTES` | нет | `60` | как часто проверять цены, минут |

## Миграции

Создать или обновить схему базы (нужен заполненный `.env`):

```sh
uv run alembic upgrade head
```

После изменения моделей в `src/database/models.py`: `uv run alembic revision --autogenerate -m "..."`,
проверить сгенерированный файл в `alembic/versions/` и снова `upgrade head`.

## Запуск

```sh
uv run python src/main.py
```

Первая проверка цен идёт сразу при старте, дальше — раз в `MONITOR_INTERVAL_MINUTES`.
Не запускайте два экземпляра на одной базе.

## Как пользоваться

- Посторонним бот отвечает отказом и показывает их Telegram ID. Админ выдаёт доступ:
  `/allow <telegram_id>`, отзывает: `/revoke <telegram_id>`, список: `/users`.
- Сначала выбрать город: `/city` и кнопка с городом. Товар отслеживается в городе, который был
  выбран при добавлении; смена города влияет только на новые товары.
- Добавить товар: `/add <ссылка на товар>`, например
  `/add https://kaspi.kz/shop/p/apple-iphone-15-128gb-chernyi-113137790/`. Бот покажет кнопками
  10 самых дешёвых продавцов в вашем городе — нажмите нужного, и бот будет следить за его ценой.
- `/list` — ваши товары с номерами, `/remove <номер>` — убрать, `/help` — все команды.

## Разработка

```sh
uv run pytest
uv run ruff format && uv run ruff check
```

```
src/
  main.py        точка входа: бот, планировщик, polling
  core/          настройки (Pydantic Settings)
  database/      engine, сессии, модели SQLAlchemy
  handlers/      команды бота по темам: common, products, admin
  filters/       фильтры aiogram (is_admin)
  middlewares/   проверка доступа
  keyboards/     inline-клавиатуры (выбор города)
  features/      проверка цен и тексты уведомлений
  services/kaspi/  клиент и разбор Kaspi (формат ответов — в docstring пакета)
  common/        общие тексты и форматирование
tests/
  unit/          без базы и сети
  integration/   in-memory SQLite и dispatcher с фейковым Bot
  fixtures/      сохранённые ответы Kaspi
```
