# Telegram Mood Tracker

Telegram-бот для ежедневной фиксации психологического состояния.

## Требования

- Python 3.14 и [uv](https://docs.astral.sh/uv/).
- Docker Engine с Docker Compose для PostgreSQL и integration tests.
- Токен Telegram-бота от [@BotFather](https://t.me/BotFather).

## Настройка

Создайте локальный файл окружения и заполните секреты:

```bash
cp .env.example .env
```

В `.env` обязательно замените `BOT_TOKEN`, `DB_PASS` и `POSTGRES_PASSWORD`.
Значения `DB_PASS` и `POSTGRES_PASSWORD` должны совпадать: первое использует
приложение, второе создаёт пользователя PostgreSQL.

Остальные значения по умолчанию подходят для локального запуска:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mood_tracker
DB_USER=mood_tracker
```

## Локальный запуск приложения

Установите зависимости, поднимите только базу данных, примените миграции и
запустите polling:

```bash
uv sync --all-groups
docker compose up -d db
uv run alembic upgrade head
uv run python -m mood_tracker.presentation.main
```

Проверить готовность базы можно командой `docker compose ps`. Для просмотра
логов базы используйте `docker compose logs -f db`.

## Запуск в Docker

Этот вариант запускает PostgreSQL, применяет миграции внутри app-контейнера и
начинает long polling:

```bash
docker compose up -d --build
docker compose logs -f app
```

Healthcheck приложения доступен внутри Docker-сети по `http://app:8000/health`.

## Разработка и проверки

Установите Git hooks один раз после клонирования:

```bash
uv sync --all-groups
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

Основные команды:

```bash
make lint
make typecheck
make test-unit
make test-integration
make test-all
make check
```

`test-integration` поднимает отдельный PostgreSQL-контейнер, ждёт healthcheck и
удаляет контейнер и test volume после завершения. Mypy проверяет только `src/`;
unit и integration tests запускаются отдельно.

## Остановка

```bash
docker compose down
```

Эта команда сохраняет данные в Docker volume. Команда `docker compose down -v`
удаляет volume PostgreSQL без возможности восстановления — используйте её только
когда данные больше не нужны.
