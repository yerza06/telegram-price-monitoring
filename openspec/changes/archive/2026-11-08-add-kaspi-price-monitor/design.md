# Design

## Context

`bot/` — пустой uv-проект на Python 3.13: `bot/src/bot/__init__.py` содержит только заглушку `main()`, которая зарегистрирована как скрипт `bot` и собирается через `uv_build`; зависимостей нет. Решено отказаться от вложенного пакета: модули лежат прямо в `bot/src/`. Мотивация и границы — в proposal.md, требования — в specs/.

Что известно о Kaspi (проверено GET-запросом страницы товара):
- Ссылка `https://kaspi.kz/shop/p/<slug>-<productId>/` редиректит (301) на актуальный slug, поэтому HTTP-клиент должен следовать редиректам. ID товара — число в конце slug.
- HTML страницы содержит `<script>` с `BACKEND.components.item = {...}`: там `card.id`, `card.title` и минимальная цена по всем продавцам.
- Цен отдельных продавцов в статичном HTML нет: их отдаёт JSON-эндпоинт `POST https://kaspi.kz/yml/offer-view/offers/{productId}` с телом, где есть `cityId`. Формат запроса и ответа (поля `merchantId`, `merchantName`, `price`, пагинация, фильтр по продавцу) ещё не проверен — это первая задача реализации.

## Goals / Non-Goals

**Goals:**
- Минимум модулей: один процесс, где вместе работают polling aiogram и планировщик.
- Весь разбор Kaspi в одном модуле, покрытом тестами на сохранённых ответах, чтобы при смене разметки чинить одно место.
- Логика «что отправить» — чистая функция без I/O, легко тестировать.

**Non-Goals:**
- Очереди, воркеры, Redis, webhook — хватит long polling.
- Прокси и обход защиты Kaspi.
- Репозиторный слой и DI-контейнер — сессии SQLAlchemy используются прямо в хендлерах и задаче.

## Decisions

**Пакеты по слоям внутри `bot/src/`, сам проект — не пакет:** вложенного `bot/src/bot/` нет, код разложен по пакетам верхнего уровня в `bot/src/` (`core/`, `database/`, `handlers/` и т.д., см. «Модули»), чтобы ни один файл не смешивал слои. Без пакета `uv_build` собирать нечего, поэтому в `pyproject.toml` ставится `[tool.uv] package = false`, а `[build-system]` и `[project.scripts]` удаляются. Запуск — `uv run python src/main.py`: Python сам кладёт `src/` в `sys.path`, поэтому пакеты импортируют друг друга абсолютно: `from core.config import settings`. Pytest получает тот же путь через `pythonpath = ["src", "tests"]`, Alembic — через `prepend_sys_path = src` в `alembic.ini`. Альтернативы — пакет `bot/src/bot/` с относительными импортами и плоские модули в одном каталоге — отброшены по решению пользователя.

**Модули:**
- `core/config.py` — Pydantic Settings, группы на `BaseSettings` со своим `env_prefix`, у всех `env_file=".env"` и `extra="ignore"`:
  - `BotSettings` (`BOT_`): `token: SecretStr`, `admin_id: int` → `BOT_TOKEN`, `BOT_ADMIN_ID`;
  - `DatabaseSettings` (`DATABASE_`): `url: str = "sqlite+aiosqlite:///bot.db"` → `DATABASE_URL`;
  - `MonitorSettings` (`MONITOR_`): `interval_minutes: PositiveInt = 60` → `MONITOR_INTERVAL_MINUTES`;
  - `Settings` объединяет группы полями с `default_factory` (`settings.bot.token`, `settings.monitor.interval_minutes`). Модульный синглтон `settings = Settings()`; ошибка валидации (нет `BOT_TOKEN`, нечисловой `BOT_ADMIN_ID`) падает при старте с сообщением pydantic, где указано поле. Префикс у каждой группы строгий, исключений по алиасам нет. `.env` читает сам pydantic-settings, поэтому `uv run --env-file` и `python-dotenv` не нужны. Альтернатива `os.environ` + dataclass отброшена: пользователь выбрал Pydantic Settings, к тому же он даёт валидацию типов и `SecretStr`, который не светит токен в логах.
- `core/logging.py` — `configure_logging(environment)`: для `local` — `RichHandler`, для `prod` — `JsonFormatter` (timestamp UTC, level, logger, message, exception) в stderr. `Settings.environment: Literal["local", "prod"] = "local"` → `ENVIRONMENT`; `main()` вызывает `configure_logging` первым делом.
- `database/engine.py` — `create_async_engine` + `async_sessionmaker`; `database/models.py` — модели SQLAlchemy 2 (`DeclarativeBase`, `Mapped`).
- `services/kaspi/` — клиент Kaspi, формат ответов в docstring пакета: `parser.py` — `parse_product_id(url)`, `parse_product(html) -> (id, title)` (selectolax ищет нужный `<script>`, JSON достаётся через `json.loads`); `client.py` — `fetch_product`, `fetch_offers(client, product_id, city_id, limit=10)` (самые дешёвые предложения, Kaspi сортирует по цене), `fetch_offer(client, product_id, merchant_id, city_id) -> Offer | None` (`None` — продавец не продаёт); `exceptions.py` — `KaspiError` на любую ошибку сети или разбора.
- `services/kaspi/cities.py` — `CITIES`: ID → название для 10 крупных городов (ID проверены по `BACKEND.components.citySelection` на странице товара).
- `features/notifications.py` — чистая функция `build_message(product, old_price, old_in_stock, new_price | None) -> str | None`; в тексте есть город товара, иначе пользователь с одним товаром в двух городах получит два одинаковых сообщения.
- `common/` — общее для нескольких слоёв: `formatting.py` (`format_price`, `describe_product`) и `texts.py` (`ADD_USAGE`, `USER_COMMANDS`, `ADMIN_COMMANDS`).
- `handlers/` — aiogram-router по темам: `common.py` (`/start`, `/help`), `products.py` (`/add`, `/list`, `/remove`), `city.py` (`/city` и нажатия кнопок города), `admin.py` (`/allow`, `/revoke`, `/users` с фильтром `is_admin`); `handlers/__init__.py` собирает их в корневой `router` и вешает на него middleware доступа для `message` и `callback_query`.
- `filters/admin.py` — `is_admin = F.from_user.id == settings.bot.admin_id`. Справка для `/help` собирается из двух констант-списков `(команда, описание)`: `USER_COMMANDS` и `ADMIN_COMMANDS`; админ получает оба списка. Так команда и её описание лежат рядом, а тест проверяет, что каждая зарегистрированная команда есть в справке.
- `middlewares/access.py` — outer middleware на `Message` и `CallbackQuery`: пропускает админа и пользователей из таблицы `users`, остальным отвечает отказом с их ID и ничего не сохраняет. Пропущенным: создаёт строку админа в `users`, если её нет, обновляет `full_name`/`username` из Telegram (commit только при изменении) и отдаёт хендлерам `session` и `user`.
- `features/monitoring.py` — `check_prices(bot, session_maker, client)`: проходит по парам с подписчиками, вызывает `fetch_offer`, пишет историю, обновляет пару, рассылает `build_message`.
- `keyboards/offers.py` — `OfferCallback` (prefix `add`, поля `product_id`, `merchant_id`) и `offers_keyboard()` — по кнопке на продавца «имя — цена».
- `keyboards/cities.py` — `CityCallback` (`CallbackData`, prefix `city`) и `cities_keyboard()` с кнопками `CITIES`, по две в ряд.
- `main.py` — `main()` под `if __name__ == "__main__": asyncio.run(main())`: создаёт engine, `httpx.AsyncClient`, `Bot`/`Dispatcher`, запускает планировщик и `dp.start_polling`.

**Модель данных (SQLite):**
- `users(telegram_id PK, full_name NULL, username NULL, city_id NULL, created_at)` — пользователи с доступом и админ. Права админа всё равно берутся из `BOT_ADMIN_ID`; строку админа создаёт middleware, чтобы у него тоже были город и имя. `city_id NULL` — город не выбран, `/add` просит `/city`. Имя и username заполняются при первом сообщении: `/allow` знает только ID.
- `products(id PK, kaspi_id, merchant_id, merchant_name, title, url, last_price NULL, in_stock, checked_at NULL, city_id, UNIQUE(kaspi_id, merchant_id, city_id))` — одна строка на пару «товар + продавец» в городе, общая для всех подписчиков из этого города. Город фиксируется при `/add`: цена у Kaspi зависит от города, а смена города пользователем не переносит его товары. Альтернатива — переносить подписки при смене города — отброшена пользователем.
- `subscriptions(user_id, product_id FK, created_at, PK(user_id, product_id))` — `user_id` без FK на `users`: строка админа появляется только после его первого сообщения.
- `price_history(id PK, product_id FK, price NULL, checked_at)` — `price NULL` = «нет в наличии». Нужна по спеке и пригодится будущим графикам.
- Цены хранятся как `int` в тенге: у Kaspi нет копеек, а целые числа без float-ошибок.
- Номер в `/list` и `/remove` — `products.id`; `/remove` удаляет только подписку текущего пользователя. Товары без подписчиков остаются в таблице, но не проверяются. Альтернатива — удалять их сразу — отброшена, чтобы не терять историю.
- `/revoke` явно удаляет подписки пользователя в той же транзакции (без каскада, потому что FK на `users` нет).

**Миграции:** `alembic init -t async alembic` в `bot/`; `alembic.ini` получает `prepend_sys_path = src`; `env.py` берёт URL из `settings.database.url` и `target_metadata` из `db.Base`, `render_as_batch=True` (SQLite не умеет большинство `ALTER`). Первая ревизия создаётся через autogenerate и проверяется руками. Миграции запускаются отдельной командой `uv run alembic upgrade head`, а не при старте бота: так видно, что схема поменялась. Альтернатива `Base.metadata.create_all` отброшена — пользователь выбрал Alembic.

**Планировщик:** APScheduler 3.x `AsyncIOScheduler` + `IntervalTrigger(minutes=settings.monitor.interval_minutes)`, `max_instances=1`, `coalesce=True`, `next_run_time=now`, чтобы первая проверка была сразу при старте. 4.x отброшен — всё ещё pre-release, API ломается. Cron не используется по требованию пользователя.

**HTTP:** один `httpx.AsyncClient` на процесс: `follow_redirects=True`, `timeout=15`, браузерный `User-Agent`, `Referer` страницы товара для offers-запроса. Между парами `asyncio.sleep(2)`. Проверка идёт последовательно: для личного бота с десятками товаров параллельность не нужна, а риск бана выше.

**Добавление товара:** без выбранного города `/add` отвечает подсказкой `/city`. Иначе `/add <ссылка>` запрашивает 10 самых дешёвых предложений в городе пользователя и показывает их кнопками; ничего не сохраняется. В кнопке только `product_id` и `merchant_id` (лимит callback_data — 64 байта), поэтому после нажатия бот ищет тройку в `products`: если она есть — только создаёт подписку без похода в Kaspi; иначе загружает страницу `https://kaspi.kz/shop/p/-{id}/` (название), запрашивает offer продавца и сохраняет пару с начальной ценой и первой записью истории. В `products.url` пишется эта короткая ссылка. ID продавца берётся из ответа Kaspi, поэтому проблема регистра (`sulpak`/`Sulpak`) и запрос к странице магазина больше не нужны. Альтернатива — ID продавца вторым аргументом `/add` — отброшена пользователем: его неудобно искать. `product_id` из callback проверяется на цифры, т.к. подставляется в URL.

**Уведомления:** `build_message` возвращает `None`, если цена и наличие не изменились. Процент считается от старой цены и округляется до 0.1. Рассылка через `bot.send_message` в `try/except TelegramAPIError` для каждого получателя, чтобы один заблокировавший бота не ломал остальным. Изменения пары коммитятся до рассылки, поэтому новая цена сохраняется независимо от доставки.

**Тесты:** pytest + pytest-asyncio, разложены на `tests/unit/` (без базы и сети: настройки, разбор и клиент Kaspi на `httpx.MockTransport`, форматирование, уведомления) и `tests/integration/` (in-memory SQLite, апдейты через настоящий `Dispatcher` с фейковым `Bot`: middleware, хендлеры, `check_prices`). Общие помощники — `tests/helpers.py`, тесты запускаются с `--import-mode=importlib`. Fixtures — реальные страницы товара и магазина и ответ offers из `bot/tests/fixtures/`. Тестируются `services/kaspi/` (разбор, продавец не найден, битый ответ), `build_message` (рост, падение, пропал, вернулся, без изменений) и один тест `check_prices` на in-memory SQLite с подменённым `fetch_offer`: ошибка на одной паре не останавливает остальные, история пишется.

## Risks / Trade-offs

- [Kaspi меняет разметку или формат offers] → разбор только в `services/kaspi/`, при ошибке — `KaspiError` и лог без порчи данных; fixtures помогают быстро сравнить старый и новый формат.
- [Kaspi блокирует частые запросы или требует капчу] → пауза между запросами и интервал по умолчанию 60 минут. При блокировке проверки падают в лог, бот работает дальше. Прокси — вне рамок.
- [Offers-эндпоинт требует дополнительных параметров (zoneId и т.п.) или отдаёт продавцов страницами] → решается в первой задаче (спайк); если фильтр по продавцу недоступен, перебираем страницы до нужного `merchantId`.
- [В `/city` только 10 крупных городов из 320] → список в `services/kaspi/cities.py`, расширяется добавлением строки; поиск по всем городам — отдельный change.
- [Пакеты верхнего уровня `core`, `database`, `handlers` и т.д. могут совпасть по имени с установленной библиотекой] → `src/` стоит первым в `sys.path`, поэтому выигрывают свои модули; новые пакеты не называть как зависимости (`httpx.py`, `alembic.py` и т.п.).
- [SQLite + один процесс] → для личного бота хватает. Запускать два экземпляра на одной базе нельзя: появятся дублирующиеся проверки.

## Migration Plan

Новый проект, данных нет. Развёртывание: `uv sync`, заполнить `.env` по `.env.example`, `uv run alembic upgrade head`, `uv run python src/main.py`. Откат — остановить процесс; база в одном файле, её можно сохранить копированием.

## Open Questions

- Точные поля ответа offers-эндпоинта и есть ли в нём фильтр по продавцу — выясняется в задаче 2.1 и не меняет ни спеку, ни структуру.
