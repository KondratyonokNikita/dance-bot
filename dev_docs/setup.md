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

## Автозапуск (macOS launchd)

Бот может крутиться по расписанию без ручного `uv run dance-bot`. Используется user LaunchAgent — работает **только пока вы залогинены** в macOS (не на экране входа, не при выключенном Mac).

### Предусловия

Перед установкой агента должны работать:

- `uv sync`
- Telegram: `uv run python scripts/login.py` → `data/bot.session`
- Google (если нужен календарь): `uv run python scripts/google_login.py`
- Ручной прогон: `uv run dance-bot` — без ошибок

### Настройка интервала

В `.env` или дефолтах в `config.py`:

| Переменная | Дефолт | Описание |
|------------|--------|----------|
| `RUN_INTERVAL_SECONDS` | `3600` | Интервал между прогонами (`StartInterval`, секунды) |
| `LAUNCHD_LABEL` | `com.user.dance-bot` | Label LaunchAgent |

Пример — раз в 2 часа:

```env
RUN_INTERVAL_SECONDS=7200
```

После смены интервала переустановите агент: `./scripts/launchd_disable.sh && ./scripts/launchd_enable.sh`.

### Установка

Из корня репозитория:

```sh
./scripts/launchd_enable.sh
```

Скрипт:

1. Подставляет абсолютные пути и интервал в `scripts/com.user.dance-bot.plist`
2. Копирует plist в `~/Library/LaunchAgents/`
3. Загружает и включает агент через `launchctl`

Первый прогон — сразу после установки (`RunAtLoad: true`), далее — по `RUN_INTERVAL_SECONDS`.

### Управление

```sh
# Статус
launchctl print gui/$(id -u)/com.user.dance-bot

# Принудительный прогон (не дожидаясь интервала)
launchctl kickstart -k gui/$(id -u)/com.user.dance-bot

# Отключить и удалить plist
./scripts/launchd_disable.sh
```

После обновления кода или смены путей к репозиторию — переустановите агент (`disable` → `enable`).

### Логи

| Файл | Содержимое |
|------|------------|
| `data/launchd.log` | stdout/stderr прогонов из launchd |
| Telegram, тема `Dance_bot_log` | `warning` и выше (см. `TELEGRAM_LOG_MIN_LEVEL`, дефолт `WARNING`) |

Просмотр:

```sh
tail -f data/launchd.log
```

### Файлы launchd

| Файл | Назначение |
|------|------------|
| `scripts/com.user.dance-bot.plist` | шаблон plist (`__REPO_ROOT__`, `__START_INTERVAL__`) |
| `scripts/run_dance_bot.sh` | обёртка: `cd` в репо, PATH, `uv run dance-bot` |
| `scripts/launchd_enable.sh` | установка агента |
| `scripts/launchd_disable.sh` | остановка и удаление |

В `~/Library/LaunchAgents/` хранится сгенерированный plist с абсолютными путями — его не коммитят.

### Типичные проблемы

| Симптом | Причина | Действие |
|---------|---------|----------|
| `uv: command not found` в `launchd.log` | PATH в launchd урезан | Проверить `run_dance_bot.sh` и `EnvironmentVariables` в plist |
| `Session not authorized` | Нет `data/bot.session` | `uv run python scripts/login.py` |
| Ошибка чтения `.env` | Неверный `WorkingDirectory` | Переустановить агент из актуального пути к репо |
| Прогоны сдвигаются | Mac спал | Нормально для `StartInterval`; после пробуждения launchd догоняет |
| Два прогона параллельно | Пайплайн дольше интервала | Второй экземпляр завершится с `dance-bot already running, skipping` (`data/dance-bot.lock`) |

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
    run_dance_bot.sh           # обёртка для launchd
    launchd_enable.sh
    launchd_disable.sh
    com.user.dance-bot.plist   # шаблон LaunchAgent
  data/                         # сессии, токены, БД, launchd.log (gitignored)
```
