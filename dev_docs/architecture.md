# Архитектура

## Пайплайн

```
fetch_messages → parse_messages → parse_events → sync_calendar
```

| Этап | Модуль | Что делает |
|------|--------|------------|
| 1 | `fetch_messages.py` | Telegram → `raw_messages` (инкрементально, keyword-фильтр) |
| 2 | `parse_messages.py` | LLM → `parsed_messages` (только новые, прошедшие фильтр) |
| 3 | `parse_events.py` | JSON → `events` (insert) + отмены (`cancellations` → `status=cancelled`) |
| 4 | `sync_calendar.py` | Отмены в Google Calendar (`(ОТМЕНА)` в title) → insert новых `active` |

## База данных

Файл `data/events.db` (SQLite):

| Таблица | Назначение |
|---------|------------|
| `raw_messages` | Сырые посты из Telegram + `filter_passed` |
| `parsed_messages` | Сырой JSON-ответ LLM по каждому посту |
| `events` | Структурированные события с `channel`, `dedup_key`, `status` (`active` / `cancelled`), `cancellation_raw_message_id` |
| `sync_log` | Что и когда отправлено в календарь |

## Google Calendar

Три календаря — по одному на танец:

| Танец | Календарь |
|-------|-----------|
| `bachata` | Танцы - Бачата |
| `kizomba` | Танцы - Кизомба |
| `zouk` | Танцы - Зук |

- Title: `Bachata / Kizomba — Party` (полный список танцев из события)
- Цвет: задаётся календарём в Google UI (не `colorId` per-event)
- Описание: тип, танцы, цена, полный текст поста, ссылка на источник
- Маршрутизация: событие попадает в календарь каждого танца из `dances`; если `dances: []` — в бачата
- Mixed events дублируются во все соответствующие календари
- Дедуп: `dedup_key = SHA256(date|time_start|location)` как `event.id` (уникален внутри календаря)
- `sync_log.sink`: `google_calendar:bachata` / `kizomba` / `zouk`
- Удалённые в UI события (`cancelled`) восстанавливаются при следующей синхронизации **только для `active`**
- **Отмена:** LLM возвращает `cancellations`; событие помечается `cancelled` в БД; в Google Calendar title → `(ОТМЕНА) …`, в description добавляется текст и ссылка на пост об отмене
- `clear_calendar(db)` — удаляет все активные события из всех трёх календарей и очищает `sync_log`

## Конфигурация

Основные параметры в `src/dance_bot/config.py`:

| Параметр | По умолчанию |
|----------|--------------|
| `telegram_channels` | `kredo_dance`, `plyas_dance`, `KIZonEVERYone`, `danceforever_minsk`, `estarico_dance` |
| `history_hours` | `168` (7 дней — глубина при первой загрузке канала, если в БД нет сообщений) |
| `google_calendars` | `bachata` → «Танцы - Бачата», `kizomba` → «Танцы - Кизомба», `zouk` → «Танцы - Зук» |
| `timezone` | `Europe/Minsk` |

## Источники

Telegram-каналы:

- [kredo_dance](https://t.me/kredo_dance)
- [plyas_dance](https://t.me/plyas_dance)
- KIZonEVERYone (приватный, резолвится по названию диалога)
- [danceforever_minsk](https://t.me/danceforever_minsk)
- [estarico_dance](https://t.me/estarico_dance)
