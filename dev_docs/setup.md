# Установка и запуск

## Требования

- **macOS** (для автозапуска через `launchd`; на Linux/Windows тоже работает, автозапуск надо адаптировать)
- **Python 3.11+** — ставится автоматически через `uv`
- **[uv](https://docs.astral.sh/uv/)** — менеджер пакетов
- **`claude` CLI** — LLM-парсинг через подписку Claude Code (`claude-haiku-4-5`)

### Установка uv

```sh
brew install uv
```

или:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Установка проекта

```sh
uv sync
```

## Настройка

### Telegram

1. Создать приложение на [my.telegram.org/apps](https://my.telegram.org/apps).
2. Заполнить `.env`:

   ```
   TELEGRAM_API_ID=12345
   TELEGRAM_API_HASH=abcdef0123456789abcdef0123456789
   TELEGRAM_PHONE=+375291234567
   ```

3. Авторизоваться:

   ```sh
   uv run python scripts/login.py
   ```

Сессия сохраняется в `data/bot.session` (в `.gitignore`).

### Google Calendar (для разработчика / владельца бота)

1. Создать проект на [console.cloud.google.com](https://console.cloud.google.com), включить **Google Calendar API**.
2. OAuth consent screen (External) + Desktop OAuth client → скачать JSON как `data/google_credentials.json`.
3. Создать три календаря на [calendar.google.com](https://calendar.google.com): **«Танцы - Бачата»**, **«Танцы - Кизомба»**, **«Танцы - Зук»** (или поменять `google_calendars` в `config.py`).
4. Авторизоваться:

   ```sh
   uv run python scripts/google_login.py
   ```

## Запуск

```sh
uv run dance-bot
```

Полный пайплайн: `fetch_messages` → `parse_messages` → `parse_events` → `sync_calendar`.

Каждый этап идемпотентен — повторный запуск обрабатывает только новые данные.

## Структура проекта

```
dance-bot/
  pyproject.toml
  .env                          # секреты (gitignored)
  prompts/
    extract_event.md            # промпт для LLM
  src/dance_bot/
    main.py                     # оркестратор
    config.py
    db.py                       # SQLite
    fetch_messages.py
    parse_messages.py
    parse_events.py
    sync_calendar.py
    calendar_sync.py            # Google Calendar API
    extractor.py                # LLM через claude CLI
    filters.py                  # keyword-фильтр
  scripts/
    login.py
    google_login.py
  data/                         # сессии, токены, БД (gitignored)
```
