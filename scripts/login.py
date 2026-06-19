"""Интерактивный первый вход в Telegram.

Запускается один раз. Создаёт `data/bot.session` — после этого основной бот
стартует без ручных действий.

Usage:
    uv run python scripts/login.py
"""

import structlog
from telethon.sync import TelegramClient

from dance_bot.config import get_settings

log = structlog.get_logger()


def main() -> None:
    settings = get_settings()
    settings.session_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("Connecting to Telegram", phone=settings.telegram_phone)

    client = TelegramClient(
        str(settings.session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )
    client.start(phone=settings.telegram_phone)
    me = client.get_me()
    log.info(
        "Logged in",
        user_id=me.id,
        username=me.username,
        session=str(settings.session_path),
    )
    client.disconnect()


if __name__ == "__main__":
    main()
