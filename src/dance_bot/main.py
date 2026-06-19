import structlog

from dance_bot.config import get_settings
from dance_bot.db import Database
from dance_bot.fetch_messages import fetch_messages
from dance_bot.parse_events import parse_events
from dance_bot.parse_messages import parse_messages
from dance_bot.sync_calendar import clear_calendar, sync_calendar

log = structlog.get_logger()


def main() -> None:
    log.info("Starting dance-bot")

    settings = get_settings()
    db = Database(settings.db_path)
    try:
        fetch_messages(db)
        parse_messages(db)
        parse_events(db)
        sync_calendar(db)

        # clear_calendar(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
