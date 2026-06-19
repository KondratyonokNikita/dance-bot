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
        skipped_no_time = 0

        for event in extraction.events:
            if not event.time_start:
                skipped_no_time += 1
                continue

            result = db.insert_event(
                parsed_message_id=row.id,
                raw_message_id=row.raw_message_id,
                channel=row.channel,
                event=event,
            )
            if result == "inserted":
                inserted += 1
            else:
                skipped += 1

        cancelled = unmatched = ambiguous = 0
        for cancellation in extraction.cancellations:
            candidates = db.find_active_events_for_cancellation(
                cancellation, channel=row.channel
            )
            if len(candidates) == 1:
                db.cancel_event(
                    candidates[0],
                    cancellation_raw_message_id=row.raw_message_id,
                )
                log.info(
                    "Event cancelled",
                    event_id=candidates[0],
                    raw_message_id=row.raw_message_id,
                    source_url=row.source_url,
                    cancellation=cancellation.model_dump(),
                )
                cancelled += 1
            elif len(candidates) == 0:
                log.warning(
                    "Cancellation unmatched",
                    raw_message_id=row.raw_message_id,
                    parsed_message_id=row.id,
                    source_url=row.source_url,
                    channel=row.channel,
                    cancellation=cancellation.model_dump(),
                    candidates_count=0,
                )
                unmatched += 1
            else:
                log.warning(
                    "Cancellation ambiguous",
                    raw_message_id=row.raw_message_id,
                    parsed_message_id=row.id,
                    source_url=row.source_url,
                    channel=row.channel,
                    cancellation=cancellation.model_dump(),
                    candidate_event_ids=candidates,
                    candidates_count=len(candidates),
                )
                ambiguous += 1

        if extraction.cancellations:
            log.info(
                "Cancellations processed",
                parsed_message_id=row.id,
                source_url=row.source_url,
                cancelled=cancelled,
                unmatched=unmatched,
                ambiguous=ambiguous,
            )

        db.mark_events_extracted(row.id)

        log.info(
            "Events extracted",
            parsed_message_id=row.id,
            raw_message_id=row.raw_message_id,
            source_url=row.source_url,
            inserted=inserted,
            skipped_duplicate=skipped,
            skipped_no_time=skipped_no_time,
        )
