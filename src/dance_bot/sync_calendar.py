import structlog

from dance_bot.calendar_sync import (
    clear_all_calendar_events,
    insert_calendar_event,
    mark_calendar_event_cancelled,
)
from dance_bot.config import get_settings
from dance_bot.db import Database, calendar_sink
from dance_bot.extractor import Event

log = structlog.get_logger()


def clear_calendar(db: Database) -> int:
    """Delete all events from all dance Google Calendars and clear sync_log."""
    deleted = clear_all_calendar_events()
    cleared = db.clear_sync_log()
    log.info("Calendars cleared", deleted=deleted, sync_log_cleared=cleared)
    return deleted


def sync_calendar(db: Database) -> None:
    settings = get_settings()

    cancelled_updated = 0
    cancelled_skipped = 0
    cancelled_not_found = 0

    for item in db.list_cancelled_unsynced():
        row = item.event
        dance = item.dance
        calendar_name = settings.google_calendars[dance]

        event = Event(
            event_type=row.event_type,
            dances=row.dances,
            date=row.date,
            time_start=row.time_start,
            time_end=row.time_end,
            location=row.location,
            price=row.price,
        )

        if not event.date:
            continue

        if not item.cancellation_source_url:
            log.warning(
                "Calendar cancellation skipped — no cancellation post",
                event_id=row.id,
                dance=dance,
            )
            continue

        result = mark_calendar_event_cancelled(
            event,
            row.source_url,
            row.dedup_key,
            dance,
            row.message,
            cancellation_url=item.cancellation_source_url,
            cancellation_message=item.cancellation_message,
        )

        if result == "updated":
            db.mark_sync_cancelled(row.id, calendar_sink(dance))
            cancelled_updated += 1
        elif result == "skipped":
            db.mark_sync_cancelled(row.id, calendar_sink(dance))
            cancelled_skipped += 1
        else:
            cancelled_not_found += 1

        log.info(
            "Calendar cancellation sync",
            event_id=row.id,
            dance=dance,
            calendar=calendar_name,
            result=result,
            date=event.date,
            source_url=row.source_url,
            cancellation_url=item.cancellation_source_url,
        )

    rows = db.list_unsynced_for_calendar()
    if (
        not rows
        and cancelled_updated == 0
        and cancelled_skipped == 0
        and cancelled_not_found == 0
    ):
        log.info("No events to sync to calendar")
        return

    inserted = 0
    restored = 0
    skipped = 0
    skipped_no_date = 0

    for item in rows:
        row = item.event
        dance = item.dance
        calendar_name = settings.google_calendars[dance]

        event = Event(
            event_type=row.event_type,
            dances=row.dances,
            date=row.date,
            time_start=row.time_start,
            time_end=row.time_end,
            location=row.location,
            price=row.price,
        )

        if not event.date:
            skipped_no_date += 1
            log.info(
                "Calendar sync skipped — no date",
                event_id=row.id,
                dance=dance,
                source_url=row.source_url,
            )
            continue

        result = insert_calendar_event(
            event, row.source_url, row.dedup_key, dance, row.message
        )
        db.record_sync(
            event_id=row.id,
            sink=calendar_sink(dance),
            external_id=row.dedup_key,
            status=result,
        )

        if result == "inserted":
            inserted += 1
        elif result == "restored":
            restored += 1
        else:
            skipped += 1

        log.info(
            "Calendar sync",
            event_id=row.id,
            dance=dance,
            calendar=calendar_name,
            result=result,
            date=event.date,
            time=event.time_start,
            title=event.event_type,
            source_url=row.source_url,
        )

    log.info(
        "Calendar sync complete",
        cancelled_updated=cancelled_updated,
        cancelled_skipped=cancelled_skipped,
        cancelled_not_found=cancelled_not_found,
        inserted=inserted,
        restored=restored,
        skipped_already_active=skipped,
        skipped_no_date=skipped_no_date,
    )
