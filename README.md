# dance-bot

Агрегатор анонсов социальных танцев из Telegram-каналов. Парсит сообщения через LLM, складывает структурированные события в JSONL-лог.

Подробный план — в `.claude/plans/mvp.md`.

## Требования

- **macOS** (запуск под `launchd`; на Linux/Windows тоже заработает, но автозапуск надо адаптировать)
- **Python 3.11+** — поставится автоматически через `uv`, отдельно ставить не нужно
- **[uv](https://docs.astral.sh/uv/)** — менеджер пакетов и виртуальных окружений

### Установка uv

```sh
brew install uv
```

или официальным инсталлером:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Установка зависимостей

Из корня проекта:

```sh
uv sync
```

Команда создаст `.venv/`, поставит нужную версию Python и зависимости из `pyproject.toml`.

## Первый вход в Telegram

Перед первым запуском бота нужно один раз авторизовать Telethon в твоём Telegram-аккаунте.

1. Зайти на [my.telegram.org/apps](https://my.telegram.org/apps), залогиниться по номеру.
2. Создать приложение (App title: `dance-bot`, Platform: Desktop, остальное по умолчанию).
3. Скопировать `api_id` (число) и `api_hash` (строка).
4. Заполнить `.env` в корне проекта:

   ```
   TELEGRAM_API_ID=12345
   TELEGRAM_API_HASH=abcdef0123456789abcdef0123456789
   TELEGRAM_PHONE=+375291234567
   ```

5. Запустить интерактивный логин:

   ```sh
   uv run python scripts/login.py
   ```

   Telegram пришлёт код подтверждения в само приложение Telegram (если ты залогинен где-то) или SMS. Введи код в терминале. Если включена 2FA — введи cloud password.

После успешного входа создаётся файл `data/bot.session` — все последующие запуски бота автоматические, ничего вводить не надо.

> `data/bot.session` = полный доступ к аккаунту. Файл уже в `.gitignore`, никуда не загружай.

## Подключение Google Calendar

Бот пишет извлечённые события в отдельный календарь «Танцы Минск» твоего Google-аккаунта. Настройка — один раз.

1. Зайти на [console.cloud.google.com](https://console.cloud.google.com), создать проект (например, `dance-bot`).
2. `APIs & Services` → `Library` → включить **Google Calendar API**.
3. `APIs & Services` → `OAuth consent screen`:
   - User type: `External`
   - App name: `dance-bot`, email — твой
   - Test users: добавить свой Google-аккаунт
4. `APIs & Services` → `Credentials` → `Create Credentials` → `OAuth client ID`:
   - Application type: `Desktop app`
   - Скачать JSON и положить как `data/google_credentials.json`
5. В [calendar.google.com](https://calendar.google.com) создать отдельный календарь с названием **«Танцы Минск»** (или поменяй `google_calendar_name` в `config.py`).
6. Запустить интерактивный логин:

   ```sh
   uv run python scripts/google_login.py
   ```

   Откроется браузер, дашь согласие. В `data/google_token.json` сохранится refresh-token.

После этого бот пишет события в календарь автоматически. Дедуп по `(дата, время начала, место)` — повторный запуск не задублирует событие.

## Запуск

```sh
uv run dance-bot
```

Ожидаемый вывод:

```
2026-06-19 09:41:15 [info     ] Starting dance-bot
```

## Структура проекта

```
dance-bot/
  pyproject.toml        # зависимости и entry-point
  .env                  # секреты Telegram API (gitignored)
  src/dance_bot/
    main.py             # точка входа
    config.py           # pydantic-settings, чтение .env
    calendar_sync.py    # запись событий в Google Calendar
  scripts/
    login.py            # интерактивный первый вход в Telegram
    google_login.py     # OAuth-флоу для Google Calendar
  data/                 # bot.session, токены Google (gitignored)
  .claude/plans/        # план разработки
```
