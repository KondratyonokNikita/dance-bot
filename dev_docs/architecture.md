# Архитектура

## Пайплайн

```
fetch_messages → parse_messages → parse_events → sync_calendar
```

| Этап | Модуль | Что делает |
|------|--------|------------|
| 1 | `fetch_messages.py` | Telegram → `raw_messages` (инкрементально, keyword-фильтр) |
| 2 | `parse_messages.py` | LLM → `parsed_messages` (только новые, прошедшие фильтр) |
| 3 | `parse_events.py` | JSON → `events` (с дедупом по `dedup_key`; без `time_start` не пишется) |
| 4 | `sync_calendar.py` | `events` → Google Calendar (через `sync_log`) |

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
- Описание: тип, танцы, цена, полный текст поста, ссылка на источник
- Дедуп: `dedup_key = SHA256(date|time_start|location)` как `event.id`
- Удалённые в UI события (`cancelled`) восстанавливаются при следующей синхронизации
- `clear_calendar(db)` — удаляет все активные события из календаря и очищает `sync_log`

## Конфигурация

Основные параметры в `src/dance_bot/config.py`:

| Параметр | По умолчанию |
|----------|--------------|
| `telegram_channels` | `kredo_dance`, `plyas_dance`, `KIZonEVERYone`, `danceforever_minsk`, `estarico_dance` |
| `history_hours` | `168` (7 дней — глубина при первой загрузке канала, если в БД нет сообщений) |
| `google_calendar_name` | `Танцы Минск` |
| `timezone` | `Europe/Minsk` |

## Источники

Telegram-каналы:

- [kredo_dance](https://t.me/kredo_dance)
- [plyas_dance](https://t.me/plyas_dance)
- KIZonEVERYone (приватный, резолвится по названию диалога)
- [danceforever_minsk](https://t.me/danceforever_minsk)
- [estarico_dance](https://t.me/estarico_dance)
