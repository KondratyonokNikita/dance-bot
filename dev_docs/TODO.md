# TODO

Приоритеты: **P0** — без этого продукт не работает сам; **P1** — качество данных; **P2** — удобство разработки и UX; **P3** — расширения.

---

## P0 — Автозапуск

- [ ] **Настроить автозапуск через `launchd`** — сейчас бот запускается только вручную (`uv run dance-bot`). Нужно, чтобы пайплайн крутился сам, например раз в час.

  **Что сделать:**

  1. **Создать `scripts/com.user.dance-bot.plist`** (user-agent, не system):
     - `Label`: `com.user.dance-bot`
     - `ProgramArguments`: полный путь к `uv` + `run` + `dance-bot` (или обёртка-скрипт `scripts/run.sh`)
     - `WorkingDirectory`: абсолютный путь к репозиторию (где лежат `.env`, `data/`)
     - `StartInterval`: `3600` (каждый час) или `StartCalendarInterval` для фиксированного расписания
     - `EnvironmentVariables` → `PATH`: пути к `uv`, Python, `claude` CLI (Homebrew: `/opt/homebrew/bin`, `~/.local/bin` и т.д.)
     - `StandardOutPath` / `StandardErrorPath`: логи, например `data/launchd.log`
     - `RunAtLoad`: `true` — один прогон сразу после логина (опционально)

  2. **Проверить, что сервис находит зависимости:**
     - `uv` в PATH
     - `claude` CLI в PATH (для `parse_messages`)
     - `.env` и `data/` доступны из `WorkingDirectory`

  3. **Установить и включить:**
     ```sh
     launchctl bootstrap gui/$(id -u) ~/path/to/dance-bot/scripts/com.user.dance-bot.plist
     launchctl enable gui/$(id -u)/com.user.dance-bot
     ```

  4. **Проверить:** `launchctl print gui/$(id -u)/com.user.dance-bot`, дождаться прогона, посмотреть `data/launchd.log`.

  5. **Задокументировать** в `dev_docs/setup.md`: установка, перезапуск (`kickstart`), отключение.

---

## P1 — Качество данных

- [ ] **Обработка отмены мероприятий** — иногда в каналах приходят посты об отмене. Распознавать их (keyword-фильтр +/или LLM) и снимать/отменять соответствующие события в `events`, Google Calendar и `sync_log`.

- [ ] **Обновление событий в календаре** (`events().update`) — при изменении времени, места или цены в посте обновлять запись в календаре. Сейчас только insert и restore cancelled.

- [ ] **Обработка `MessageEdited`** — при редактировании поста в Telegram обновлять текст в `raw_messages`, сбрасывать парсинг и перепроходить пайплайн для этого сообщения. Связано с пунктом выше.

---

## P2 — UX и разработка

- [ ] **Отдельные CLI-команды для этапов пайплайна** — `fetch`, `parse`, `events`, `sync` (и, возможно, `clear-calendar`) для дебага без полного прогона. Entry-points в `pyproject.toml` или subcommands через `argparse`/`typer` в `main.py`.

- [ ] **Отдельные Google Calendar по танцам** — разделить мероприятия на календари Bachata / Kizomba / Zouk, чтобы у подписчиков и в embed на GitHub Pages были разные цвета (Google не показывает `colorId` per-event в одном календаре).

  **Что сделать:**

  1. Создать в Google Calendar три публичных календаря (или по одному на танец).
  2. Конфиг: маппинг `dance → calendar_name` / `calendar_id` в `config.py`.
  3. **`sync_calendar`:** для каждого события с `dances: ["bachata", "kizomba"]` — записать копию в оба календаря (разные `dedup_key` или `(dedup_key, dance)` в `sync_log`).
  4. **`sync_log`:** учитывать sink на пару `(event_id, calendar)` — одно событие может быть в нескольких календарях.
  5. **`index.html`:** embed с несколькими `src=` (по одному на календарь).
  6. **README:** ссылки на подписку для каждого календаря (или одна страница с тремя embed).

---

## P3 — Оптимизация и расширения

- [ ] **Таблица `channel_cursors`** — явный курсор последнего сообщения по каналу (сейчас вычисляется из `raw_messages`). Низкий приоритет — текущая схема работает.

- [ ] **Telegram-дайджест** — форматированные посты со ссылкой на оригинал в личный канал.

- [ ] **OCR на афишах** — если окажется, что много анонсов с датами только в картинках.

- [ ] **Дополнительные источники / города**.
