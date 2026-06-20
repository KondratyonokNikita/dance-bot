from datetime import datetime, timedelta, timezone

import structlog
from telethon.sync import TelegramClient

from dance_bot.config import get_settings
from dance_bot.db import Database
from dance_bot.filters import matches

log = structlog.get_logger()


def _source_url(username: str | None, channel: str, message_id: int) -> str:
    if username:
        return f"https://t.me/{username}/{message_id}"
    return f"{channel}#{message_id}"


def _fetch_channel(
    client: TelegramClient,
    db: Database,
    *,
    channel: str,
    entity,
    username: str | None,
    history_hours: int,
) -> tuple[int, int, int]:
    last = db.get_last_raw_message(channel)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=history_hours)
    last_date = last[0] if last else None
    last_message_id = last[1] if last else None

    fetched = 0
    inserted = 0
    filter_passed = 0

    for msg in client.iter_messages(entity):
        if last_date is not None:
            if msg.date < last_date:
                break
            if msg.date == last_date and msg.id <= last_message_id:
                break
        elif msg.date < cutoff:
            break

        fetched += 1
        passed = matches(msg.message)
        if passed:
            filter_passed += 1

        if db.insert_raw_message(
            channel=channel,
            message_id=msg.id,
            message_date=msg.date,
            message=msg.message,
            source_url=_source_url(username, channel, msg.id),
            filter_passed=passed,
        ):
            inserted += 1

    log.warning(
        "Channel fetched",
        channel=channel,
        fetched=fetched,
        inserted=inserted,
        filter_passed=filter_passed,
        since=last_date.isoformat() if last_date else f"last_{history_hours}h",
    )
    return fetched, inserted, filter_passed


def fetch_messages(db: Database, client: TelegramClient) -> None:
    settings = get_settings()

    me = client.get_me()
    log.info("Logged in", user_id=me.id, username=me.username)

    dialogs_by_title = {d.name: d.entity for d in client.iter_dialogs()}

    for channel in settings.telegram_channels:
        entity = dialogs_by_title.get(channel) or client.get_entity(channel)
        username = getattr(entity, "username", None)
        _fetch_channel(
            client,
            db,
            channel=channel,
            entity=entity,
            username=username,
            history_hours=settings.history_hours,
        )
