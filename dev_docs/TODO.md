# TODO

Приоритеты: **P0** — без этого продукт не работает сам; **P1** — качество данных; **P2** — удобство разработки и UX; **P3** — расширения.

---

## P0 — Автозапуск

- [x] **Настроить автозапуск через `launchd`** — plist, обёртка и скрипты установки в `scripts/`; инструкция в [dev_docs/setup.md](setup.md#автозапуск-macos-launchd).

  Осталось при необходимости:
  - [x] Lockfile в `main()` — не запускать второй прогон, если предыдущий ещё идёт
  - [ ] Проверить на своей машине: `./scripts/launchd_enable.sh`, `data/launchd.log`, Telegram-логи

---

## P1 — Качество данных

- [x] **Справочник адресов в промпте** — проанализированы `location` в `events`, справочник в [`dev_docs/locations.md`](locations.md), таблица и правила нормализации в [`prompts/extract_event.md`](../prompts/extract_event.md).

- [x] **Обработка отмены мероприятий** — LLM → `cancellations`, каскадный матчинг, `(ОТМЕНА)` в Google Calendar. План: [`.claude/plans/event-cancellations.md`](../.claude/plans/event-cancellations.md).

- [ ] **Реструктуризация пайплайна: единая таблица `messages`** — объединить `raw_messages` + `parsed_messages`, скользящее окно fetch, upsert при редактировании, retry LLM, update events в БД и календаре. План: [`.claude/plans/unified-messages-restructure.md`](../.claude/plans/unified-messages-restructure.md).

- [ ] **Обновление событий в календаре** (`events().update`) — при изменении времени, места или цены в посте обновлять запись в календаре. Сейчас только insert и restore cancelled. Входит в реструктуризацию (см. план выше).

- [ ] **Обработка `MessageEdited`** — при редактировании поста в Telegram обновлять текст в `raw_messages`, сбрасывать парсинг и перепроходить пайплайн для этого сообщения. Входит в реструктуризацию (см. план выше).

---

## P2 — UX и разработка

- [ ] **Отдельные CLI-команды для этапов пайплайна** — `fetch`, `parse`, `events`, `sync` (и, возможно, `clear-calendar`) для дебага без полного прогона. Entry-points в `pyproject.toml` или subcommands через `argparse`/`typer` в `main.py`.

- [x] **Отдельные Google Calendar по танцам** — три календаря (Bachata / Kizomba / Zouk), дублирование mixed events, embed на GitHub Pages. План: [`.claude/plans/dance-calendars.md`](../.claude/plans/dance-calendars.md).

---

## P3 — Оптимизация и расширения

- [ ] **Таблица `channel_cursors`** — явный курсор последнего сообщения по каналу (сейчас вычисляется из `raw_messages`). Низкий приоритет — текущая схема работает.

- [ ] **Telegram-дайджест** — форматированные посты со ссылкой на оригинал в личный канал.

- [ ] **OCR на афишах** — если окажется, что много анонсов с датами только в картинках.

- [ ] **Дополнительные источники / города**.
