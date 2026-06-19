import structlog

from dance_bot.db import Database
from dance_bot.extractor import extract

log = structlog.get_logger()


def parse_messages(db: Database) -> None:
    rows = db.list_unparsed_for_llm()
    if not rows:
        log.info("No messages to parse")
        return

    for row in rows:
        parsed, raw = extract(row.message or "", row.message_date.date())
        parsed_message_id = db.insert_parsed_message(row.id, raw)

        print()
        print(f"--- {row.channel} / msg {row.message_id} ---")
        print(row.source_url)
        print(row.message)
        print()
        print("Raw LLM output:")
        print(raw)
        print()
        print("Parsed:")
        print(parsed.model_dump_json(indent=2))

        log.info(
            "Message parsed",
            channel=row.channel,
            message_id=row.message_id,
            raw_message_id=row.id,
            parsed_message_id=parsed_message_id,
            source_url=row.source_url,
            events=len(parsed.events),
        )
