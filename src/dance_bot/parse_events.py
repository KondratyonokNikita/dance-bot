import structlog

from dance_bot.db import Database
from dance_bot.extractor import parse_extraction

log = structlog.get_logger()


class ParseEventsSummary:
    __slots__ = (
        "messages_processed",
        "inserted",
        "skipped_duplicate",
        "skipped_no_time",
        "cancelled",
        "cancellation_unmatched",
        "cancellation_ambiguous",
    )

    def __init__(self) -> None:
        self.messages_processed = 0
        self.inserted = 0
        self.skipped_duplicate = 0
        self.skipped_no_time = 0
        self.cancelled = 0
        self.cancellation_unmatched = 0
        self.cancellation_ambiguous = 0


def _log_events_summary(summary: ParseEventsSummary) -> None:
    log.warning(
        "New events",
        messages_processed=summary.messages_processed,
        inserted=summary.inserted,
        skipped_duplicate=summary.skipped_duplicate,
        skipped_no_time=summary.skipped_no_time,
        cancelled=summary.cancelled,
        cancellation_unmatched=summary.cancellation_unmatched,
        cancellation_ambiguous=summary.cancellation_ambiguous,
    )


def parse_events(db: Database) -> ParseEventsSummary:
    rows = db.list_unprocessed_for_events()
    summary = ParseEventsSummary()
    if not rows:
        log.info("No parsed messages to extract events from")
        _log_events_summary(summary)
        return summary

    for row in rows:
        summary.messages_processed += 1
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
                log.info(
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
                log.info(
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
        summary.inserted += inserted
        summary.skipped_duplicate += skipped
        summary.skipped_no_time += skipped_no_time
        summary.cancelled += cancelled
        summary.cancellation_unmatched += unmatched
        summary.cancellation_ambiguous += ambiguous

    _log_events_summary(summary)
    return summary
