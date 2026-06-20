import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import structlog
from telethon.sync import TelegramClient

from dance_bot.config import get_settings
from dance_bot.telegram_log import (
    close_telegram_log,
    configure_logging,
    format_next_run_hours,
    open_telegram_client,
)

_settings = get_settings()
_log_sink = configure_logging(_settings)

# Импорты пайплайна — только после configure_logging().
# В fetch_messages и др. на уровне модуля вызывается structlog.get_logger();
# если импортировать их раньше, логгеры закэшируются с дефолтной конфигурацией
# и логи не попадут в Telegram.
from dance_bot.db import Database
from dance_bot.fetch_messages import fetch_messages
from dance_bot.parse_events import parse_events
from dance_bot.parse_messages import parse_messages
from dance_bot.sync_calendar import clear_calendar, sync_calendar

log = structlog.get_logger()


@contextmanager
def _run_lock(lock_path: Path) -> Iterator[bool]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        try:
            yield True
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _run_pipeline(db: Database, client: TelegramClient) -> None:
    fetch_messages(db, client)
    # parse_messages(db)
    # parse_events(db)
    # sync_calendar(db)

    # clear_calendar(db)


def main() -> None:
    _settings.session_path.parent.mkdir(parents=True, exist_ok=True)

    with _run_lock(_settings.lock_path) as acquired:
        if not acquired:
            log.warning("dance-bot already running, skipping")
            return

        client = open_telegram_client(_settings)
        if _log_sink is not None:
            _log_sink.bind_client(client)

        crashed = False
        try:
            log.warning("Starting dance-bot")

            db = Database(_settings.db_path)
            try:
                _run_pipeline(db, client)
            finally:
                db.close()
        except Exception as exc:
            crashed = True
            log.critical(
                "dance-bot crashed",
                error=f"{type(exc).__name__}: {exc}",
                exc_info=exc,
            )
            raise
        finally:
            if not crashed:
                next_run = format_next_run_hours(_settings.run_interval_seconds)
                log.warning(f"Finish dance-bot. Next run in {next_run}.")
            close_telegram_log(_log_sink)
            client.disconnect()


if __name__ == "__main__":
    main()
