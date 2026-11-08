# Tasks

Все команды запускаются из `bot/`. Перед отметкой каждой задачи с кодом выполнить `uv run ruff format` и `uv run ruff check`, оба без ошибок.

## 1. Настройка проекта

- [x] 1.1 Перевести проект на плоскую структуру: удалить `src/bot/` (заглушку `__init__.py` и `__pycache__`), убрать из `pyproject.toml` `[build-system]` и `[project.scripts]`, добавить `[tool.uv] package = false`, создать пустой `src/main.py`; проверить, что `uv sync` проходит, `src/bot/` больше нет и `uv run python src/main.py` завершается без ошибок
- [x] 1.2 Добавить зависимости `uv add aiogram pydantic-settings sqlalchemy aiosqlite alembic "apscheduler>=3.10,<4" httpx selectolax` и dev-зависимости `uv add --dev pytest pytest-asyncio ruff`; проверить, что `uv run python -c "import aiogram, pydantic_settings, sqlalchemy, aiosqlite, alembic, apscheduler, httpx, selectolax"` не падает
- [x] 1.3 Настроить в `pyproject.toml` `[tool.ruff]` (line-length, target py313) и `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`, `testpaths = ["tests"]`, `pythonpath = ["src"]`), а также поменять `description`; проверить, что `uv run ruff check` и `uv run pytest` запускаются (тестов пока 0)
- [x] 1.4 Создать `bot/.env.example` с `BOT_TOKEN`, `BOT_ADMIN_ID`, `DATABASE_URL=sqlite+aiosqlite:///bot.db`, `MONITOR_INTERVAL_MINUTES=60`, `KASPI_CITY_ID=750000000` и добавить `.env` и `*.db` в `bot/.gitignore`; проверить, что оба файла на месте

## 2. Клиент Kaspi

- [x] 2.1 Спайк: вручную запросить offers-эндпоинт `POST https://kaspi.kz/yml/offer-view/offers/{productId}` для реального товара, выяснить минимальное тело запроса (`cityId`, фильтр по продавцу, пагинация) и поля ответа (`merchantId`, `merchantName`, `price`); сохранить страницу товара как `tests/fixtures/product.html`, ответ — как `tests/fixtures/offers.json`, а найденный формат записать в docstring `services/kaspi/__init__.py`. Проверить: оба fixture-файла существуют, в `offers.json` есть хотя бы один продавец с ценой
- [x] 2.2 Реализовать в `src/services/kaspi/` функции `parse_product_id(url)`, `parse_product(html)`, `fetch_offer(client, product_id, merchant_id, city_id)` и `KaspiError` по design.md; проверить тестами `tests/unit/test_kaspi_parser.py` и `tests/unit/test_kaspi_client.py`: ID из ссылки (и отказ для не-Kaspi ссылки), название из `product.html`, цена продавца из `offers.json`, `None` для отсутствующего продавца, `KaspiError` для битого HTML/JSON и HTTP-ошибки (через `httpx.MockTransport`)

## 3. База данных и миграции

- [x] 3.1 Реализовать `src/core/config.py` на Pydantic Settings с группами `BotSettings`, `DatabaseSettings`, `MonitorSettings`, `KaspiSettings` и общим `Settings` по design.md; проверить тестом `tests/unit/test_config.py` через `monkeypatch.setenv`: значения читаются из `BOT_TOKEN`, `BOT_ADMIN_ID`, `DATABASE_URL`, `MONITOR_INTERVAL_MINUTES`, `KASPI_CITY_ID`; без переменных берутся значения по умолчанию; без `BOT_TOKEN`, с нечисловым `BOT_ADMIN_ID` или с `MONITOR_INTERVAL_MINUTES=0` — `ValidationError`; токен не виден в `repr(settings)`
- [x] 3.2 Реализовать `src/database/`: engine и `async_sessionmaker` в `engine.py`, модели в `models.py` `User`, `Product`, `Subscription`, `PriceHistory` по design.md; проверить, что `uv run python -c "import database.models"` из `src/` проходит
- [x] 3.3 Выполнить `uv run alembic init -t async alembic`, прописать `prepend_sys_path = src` в `alembic.ini`, настроить `alembic/env.py` (URL из `settings.database.url`, `target_metadata = Base.metadata`, `render_as_batch=True`), сгенерировать первую ревизию через autogenerate и проверить её руками; проверить, что `uv run alembic upgrade head` на пустой базе создаёт 4 таблицы, а `uv run alembic downgrade base` их удаляет

## 4. Доступ

- [x] 4.1 Реализовать в `src/middlewares/access.py` outer middleware: админ и пользователи из `users` проходят, остальные получают отказ со своим Telegram ID; проверить тестом `tests/integration/test_access_middleware.py` на in-memory SQLite (админ проходит, пользователь из `users` проходит, посторонний получает отказ, хендлер не вызывается)
- [x] 4.2 Реализовать в `src/handlers/admin.py` команды `/allow`, `/revoke` (с удалением подписок и запретом отзыва у админа) и `/users` с фильтром админа; проверить тестами на in-memory SQLite сценарии из `specs/access-control/spec.md` (выдача, повтор, неверный ID, отзыв с удалением подписок, отзыв у админа, вызов не-админом)

## 5. Отслеживание товаров

- [x] 5.1 Реализовать `/start` (приветствие, пример `/add`, где взять ID продавца, подсказка про `/help`) и `/help` со списками `USER_COMMANDS` и `ADMIN_COMMANDS` по design.md; проверить тестами: пользователь видит только `/start`, `/help`, `/add`, `/list`, `/remove`; админ видит ещё `/allow`, `/revoke`, `/users`; каждая команда из router есть в одном из списков
- [x] 5.2 Реализовать `/add` по design.md (существующая пара — только подписка; новая — страница + offer, начальная цена и первая запись истории); проверить тестами с подменённым клиентом Kaspi сценарии из `specs/product-tracking/spec.md`: успех, неверная ссылка, продавец не продаёт, `KaspiError`, повтор, второй пользователь на ту же пару без запроса к Kaspi
- [x] 5.3 Реализовать `/list` и `/remove <номер>`; проверить тестами: пустой список, список с ценами и наличием, удаление своей подписки не трогает чужую, несуществующий номер

## 6. Мониторинг и уведомления

- [x] 6.1 Реализовать в `src/features/notifications.py` функции `format_price` и `build_message`; проверить тестами `tests/unit/test_notifications.py` примеры из `specs/price-notifications/spec.md`: падение −10.0%, рост +5.0%, без изменений → `None`, пропал → одно сообщение, повторно пропал → `None`, вернулся с другой ценой
- [x] 6.2 Реализовать в `src/features/monitoring.py` функцию `check_prices`: только пары с подписчиками, одна проверка на пару, пауза между запросами, запись истории, коммит до рассылки, `KaspiError` и `TelegramAPIError` логируются и не останавливают цикл; проверить тестом `tests/integration/test_monitoring.py` на in-memory SQLite с подменёнными `fetch_offer` и `bot.send_message` (ошибка на одной из трёх пар, история записана, заблокированный получатель не мешает второму)

## 7. Запуск и документация

- [x] 7.1 Собрать `main()` в `src/main.py`: `settings`, engine, `httpx.AsyncClient`, `Bot`/`Dispatcher` с middleware и router, `AsyncIOScheduler` + `IntervalTrigger(max_instances=1, coalesce=True, next_run_time=now)`, `start_polling`, корректное закрытие клиента и engine; проверить, что `uv run python src/main.py` с заполненным `.env` стартует, сразу проверяет цены и отвечает на `/start` и `/help`
- [x] 7.2 Описать в `bot/README.md` установку, переменные окружения, миграции, запуск и где взять ID продавца; проверить, пройдя README с нуля на чистой базе

## 8. Сквозная проверка

- [x] 8.1 С `MONITOR_INTERVAL_MINUTES=1` в реальном Telegram: админ выдаёт доступ второму аккаунту, оба добавляют один товар, в логах один запрос к Kaspi за проверку; после ручного изменения `last_price` в базе оба получают уведомление; после `/revoke` второй аккаунт получает отказ и уведомления больше не приходят; второй аккаунт выбирает другой город через `/city`, добавляет тот же товар — в логах по запросу на каждый город, у каждого цена своего города
- [x] 8.2 Финально прогнать `uv run ruff format --check`, `uv run ruff check` и `uv run pytest` — всё зелёное

## 9. Город пользователя и данные профиля

- [x] 9.1 Добавить в `User` поля `full_name`, `username`, `city_id`, в `Product` — `city_id` с `UNIQUE(kaspi_id, merchant_id, city_id)`; удалить `KaspiSettings` и `KASPI_CITY_ID`; сгенерировать миграцию через autogenerate (существующим товарам `city_id = 750000000`) и проверить руками; проверить: `upgrade` со старой схемы с товаром даёт `city_id = 750000000`, `downgrade -1` проходит, `alembic check` без расхождений
- [x] 9.2 Расширить middleware доступа на `CallbackQuery`, создавать строку админа, обновлять `full_name`/`username`, отдавать хендлерам `user`; `/users` показывает имена и не показывает админа; проверить тестами в `tests/integration/test_access_middleware.py` и `test_admin_handlers.py`
- [x] 9.3 Добавить `services/kaspi/cities.py`, `keyboards/cities.py` и `handlers/city.py` (`/city` + кнопки, проверка ID города из callback); `/city` в `/help` и `/start`; проверить тестами `tests/integration/test_city_handlers.py`: город не выбран, выбор сохраняется, неизвестный ID отклоняется
- [x] 9.4 `/add` и проверка цен используют город пользователя/товара, `/list` показывает город; проверить тестами: `/add` без города не ходит в Kaspi, в offers уходит город пользователя, разные города дают разные строки `products`, смена города не трогает добавленные товары, `check_prices` передаёт город товара
- [x] 9.5 Обновить README (env без `KASPI_CITY_ID`, `/city`); smoke против настоящего Kaspi: `/city` → Астана, `/add`, в ответе цена Астаны

## 10. Добавление товара по ссылке

- [x] 10.1 Добавить `fetch_offers` (10 самых дешёвых предложений в городе), удалить `fetch_merchant_uid`, `parse_merchant_uid` и fixture `merchant.html`; проверить тестами `tests/unit/test_kaspi_client.py`: тело запроса с `limit`, разбор списка, ошибки
- [x] 10.2 `/add <ссылка>` показывает кнопки продавцов (`keyboards/offers.py`), нажатие добавляет товар; обновить `/start`, `/help`, README; проверить тестами `tests/integration/test_product_handlers.py` сценарии из `specs/product-tracking/spec.md`: кнопки, без города, неверная ссылка, никто не продаёт, продавец пропал к моменту нажатия, `KaspiError`, повтор, второй пользователь без запроса к Kaspi, неверный `product_id` в callback
- [x] 10.3 Smoke против настоящего Kaspi: `/add <ссылка>` показывает 10 продавцов по возрастанию цены, нажатие сохраняет товар

## 11. Логирование

- [x] 11.1 Добавить `core/logging.py` (Rich для `local`, JSON для `prod`) и настройку `ENVIRONMENT`; проверить тестами `tests/unit/test_logging.py` и `tests/unit/test_config.py`

## Workflow follow-up

- После реализации и проверки заархивировать change через `/opsx:archive`.
- Следующие change'и: отчёты (Quarkdown PDF, Google Sheets, Plotly), затем Mini App (FastAPI + React).
