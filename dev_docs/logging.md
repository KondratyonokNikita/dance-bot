# Логи пайплайна

Порядок строк — по flow кода `dance-bot`. В Telegram попадают записи с уровнем ≥ `telegram_log_min_level` (дефолт `WARNING`), если `telegram_log_enabled=true`.

| Описание | Пример текста | Уровень | В TG |
|----------|---------------|---------|------|
| Старт прогона | `Starting dance-bot` | `warning` | ✅ |
| Предыдущий прогон ещё идёт | `dance-bot already running, skipping` | `warning` | ✅ |
| Успешный вход в Telegram | `Logged in` `user_id=123` `username=foo` | `info` | |
| Итог загрузки канала *(×5 каналов)* | `Channel fetched` `channel=kredo_dance` `fetched=5` `inserted=2` `filter_passed=1` `since=…` | `warning` | ✅ |
| Нечего парсить LLM | `No messages to parse` | `info` | |
| Сообщение распарсено LLM *(×N постов)* | `Message parsed` `channel=…` `message_id=…` `events=2` `cancellations=0` | `info` | |
| Нечего извлекать в события | `No parsed messages to extract events from` | `info` | |
| Событие отменено в БД | `Event cancelled` `event_id=42` `source_url=…` | `info` | |
| Отмена без совпадения в БД | `Cancellation unmatched` `channel=…` `candidates_count=0` | `info` | |
| Отмена с несколькими кандидатами | `Cancellation ambiguous` `candidate_event_ids=[…]` | `info` | |
| Итог отмен по одному посту | `Cancellations processed` `cancelled=1` `unmatched=0` `ambiguous=0` | `info` | |
| Итог извлечения по одному посту | `Events extracted` `inserted=2` `skipped_duplicate=0` `skipped_no_time=0` | `info` | |
| Сводка по всем событиям прогона | `New events` `messages_processed=3` `inserted=5` `cancelled=1` … | `warning` | ✅ |
| Очистка календарей (`clear_calendar`, сейчас выкл.) | `Calendars cleared` `deleted=10` `sync_log_cleared=10` | `info` | |
| Отмена в календаре без поста-отмены | `Calendar cancellation skipped — no cancellation post` `event_id=…` `dance=bachata` | `warning` | ✅ |
| Синк одной отмены в календарь | `Calendar cancellation sync` `result=updated` `calendar=Танцы - Бачата` | `info` | |
| Нечего синкать в календарь | `No events to sync to calendar` | `info` | |
| Событие без даты — пропуск синка | `Calendar sync skipped — no date` `event_id=…` | `info` | |
| Синк одного события в календарь *(×N)* | `Calendar sync` `result=inserted` `date=2026-06-21` `title=party` | `info` | |
| Итог синка календаря | `Calendar sync complete` `inserted=3` `restored=0` `cancelled_updated=1` … | `info` | |
| Успешное завершение | `Finish dance-bot. Next run in 1 hour.` | `warning` | ✅ |
| Падение скрипта *(при любом необработанном исключении; вместо finish)* | `dance-bot crashed` `error='RuntimeError: …'` + traceback | `critical` | ✅ |

`sync_calendar` / `clear_calendar` в `main.py` сейчас закомментированы — соответствующие строки в обычном прогоне не появляются.

**Не structlog:** `print()` в `parse_messages.py` (текст поста, raw LLM, JSON) — только терминал, в TG не идёт.
