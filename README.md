# dance-bot

Агрегатор анонсов социальных танцев из Telegram-каналов (Минск). Скачивает посты, извлекает события через LLM, сохраняет в SQLite и синхронизирует с Google Calendar.

Открытые задачи — в [TODO.md](TODO.md).

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

## Установка

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

### Google Calendar

1. Создать проект на [console.cloud.google.com](https://console.cloud.google.com), включить **Google Calendar API**.
2. OAuth consent screen (External) + Desktop OAuth client → скачать JSON как `data/google_credentials.json`.
3. Создать календарь **«Танцы Минск»** на [calendar.google.com](https://calendar.google.com) (или поменять `google_calendar_name` в `config.py`).
4. Авторизоваться:

   ```sh
   uv run python scripts/google_login.py
   ```

## Запуск

```sh
uv run dance-bot
```

## Пайплайн

```
fetch_messages → parse_messages → parse_events → sync_calendar
```

| Этап | Модуль | Что делает |
|------|--------|------------|
| 1 | `fetch_messages.py` | Telegram → `raw_messages` (инкрементально, keyword-фильтр) |
| 2 | `parse_messages.py` | LLM → `parsed_messages` (только новые, прошедшие фильтр) |
| 3 | `parse_events.py` | JSON → `events` (с дедупом по `dedup_key`) |
| 4 | `sync_calendar.py` | `events` → Google Calendar (через `sync_log`) |

Каждый этап идемпотентен — повторный запуск обрабатывает только новые данные.

## База данных

Файл `data/events.db` (SQLite):

| Таблица | Назначение |
|---------|------------|
| `raw_messages` | Сырые посты из Telegram + `filter_passed` |
| `parsed_messages` | Сырой JSON-ответ LLM по каждому посту |
| `events` | Структурированные события с `dedup_key` |
| `sync_log` | Что и когда отправлено в календарь |

## Google Calendar

- Календарь: **«Танцы Минск»**
- Title: `Bachata / Kizomba — Party`
- Цвета: party — красный, open-air — зелёный, протанцовка — бирюзовый, класс — синий
- Дедуп: `dedup_key = SHA256(date|time_start|location)` как `event.id`
- Удалённые в UI события (`cancelled`) восстанавливаются при следующей синхронизации

## Конфигурация

Основные параметры в `src/dance_bot/config.py`:

| Параметр | По умолчанию |
|----------|--------------|
| `telegram_channels` | `kredo_dance`, `plyas_dance`, `KIZonEVERYone`, `danceforever_minsk`, `estarico_dance` |
| `history_hours` | `168` (7 дней — глубина при первой загрузке канала, если в БД нет сообщений) |
| `google_calendar_name` | `Танцы Минск` |
| `timezone` | `Europe/Minsk` |

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
