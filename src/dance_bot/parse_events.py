import structlog

from dance_bot.db import Database
from dance_bot.extractor import parse_extraction

log = structlog.get_logger()


def parse_events(db: Database) -> None:
    rows = db.list_unprocessed_for_events()
    if not rows:
        log.info("No parsed messages to extract events from")
        return

    for row in rows:
        extraction = parse_extraction(row.parsed_message)
        inserted = 0
        skipped = 0

        for event in extraction.events:
            result = db.insert_event(
                parsed_message_id=row.id,
                raw_message_id=row.raw_message_id,
                event=event,
            )
            if result == "inserted":
                inserted += 1
            else:
                skipped += 1

        db.mark_events_extracted(row.id)

        log.info(
            "Events extracted",
            parsed_message_id=row.id,
            raw_message_id=row.raw_message_id,
            source_url=row.source_url,
            inserted=inserted,
            skipped_duplicate=skipped,
        )
