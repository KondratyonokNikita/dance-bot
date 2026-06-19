from datetime import datetime, timedelta, timezone

import structlog
from telethon.sync import TelegramClient

# from dance_bot.calendar_sync import sync as calendar_sync
from dance_bot.config import get_settings
from dance_bot.db import Database
from dance_bot.extractor import extract
from dance_bot.filters.telegram import matches

log = structlog.get_logger()


def _source_url(username: str | None, channel: str, message_id: int) -> str:
    if username:
        return f"https://t.me/{username}/{message_id}"
    return f"{channel}#{message_id}"


def _ingest_channel(
    client: TelegramClient,
    db: Database,
    *,
    channel: str,
    entity,
    username: str | None,
    history_hours: int,
) -> tuple[int, int]:
    last = db.get_last_message(channel)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=history_hours)
    last_date = last[0] if last else None
    last_message_id = last[1] if last else None

    fetched = 0
    inserted = 0
    for msg in client.iter_messages(entity):
        if last_date is not None:
            if msg.date < last_date:
                break
            if msg.date == last_date and msg.id <= last_message_id:
                break
        elif msg.date < cutoff:
            break

        fetched += 1
        if db.insert_raw(
            channel=channel,
            message_id=msg.id,
            message_date=msg.date,
            text=msg.message,
            source_url=_source_url(username, channel, msg.id),
        ):
            inserted += 1

    log.info(
        "Channel ingested",
        channel=channel,
        fetched=fetched,
        inserted=inserted,
        since=last_date.isoformat() if last_date else f"last_{history_hours}h",
    )
    return fetched, inserted


def _parse_unparsed(db: Database) -> None:
    for row in db.list_unparsed():
        if not matches(row.text):
            db.mark_parsed(row.channel, row.message_id)
            log.info(
                "Message skipped by filter",
                channel=row.channel,
                message_id=row.message_id,
                source_url=row.source_url,
            )
            continue

        parsed, raw = extract(row.text or "", row.message_date.date())
        event_count = db.insert_events(row.channel, row.message_id, parsed.events)
        db.mark_parsed(row.channel, row.message_id, llm_raw_output=raw)

        print()
        print(f"--- {row.channel} / msg {row.message_id} ---")
        print(row.source_url)
        print(row.text)
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
            source_url=row.source_url,
            events=event_count,
        )

        # for ev in parsed.events:
        #     result = calendar_sync(ev, row.source_url)
        #     log.info(
        #         "Calendar sync",
        #         result=result,
        #         date=ev.date,
        #         time=ev.time_start,
        #         title=ev.event_type,
        #     )


def main() -> None:
    log.info("Starting dance-bot")

    settings = get_settings()
    settings.session_path.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(
        str(settings.session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )
    client.connect()

    if not client.is_user_authorized():
        log.error(
            "Not authorized — run `uv run python scripts/login.py` first",
            session=str(settings.session_path),
        )
        client.disconnect()
        return

    me = client.get_me()
    log.info("Logged in", user_id=me.id, username=me.username)

    dialogs_by_title = {d.name: d.entity for d in client.iter_dialogs()}

    db = Database(settings.db_path)
    try:
        for channel in settings.telegram_channels:
            entity = dialogs_by_title.get(channel) or client.get_entity(channel)
            username = getattr(entity, "username", None)
            _ingest_channel(
                client,
                db,
                channel=channel,
                entity=entity,
                username=username,
                history_hours=settings.history_hours,
            )

        _parse_unparsed(db)
    finally:
        db.close()

    client.disconnect()


if __name__ == "__main__":
    main()
