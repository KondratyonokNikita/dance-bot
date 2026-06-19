"""Интерактивный OAuth-флоу для Google Calendar.

Запускается один раз. Откроет браузер, попросит дать доступ к календарю.
Refresh-token сохраняется в data/google_token.json, дальше всё автоматически.

Usage:
    uv run python scripts/google_login.py
"""

import structlog
from google_auth_oauthlib.flow import InstalledAppFlow

from dance_bot.calendar_sync import SCOPES
from dance_bot.config import get_settings

log = structlog.get_logger()


def main() -> None:
    settings = get_settings()
    settings.google_token_path.parent.mkdir(parents=True, exist_ok=True)

    if not settings.google_credentials_path.exists():
        raise SystemExit(
            f"Google credentials file not found at {settings.google_credentials_path}. "
            "Скачай OAuth client (Desktop app) на https://console.cloud.google.com "
            "и положи как data/google_credentials.json"
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(settings.google_credentials_path), SCOPES
    )
    creds = flow.run_local_server(port=0)
    settings.google_token_path.write_text(creds.to_json(), encoding="utf-8")

    log.info("Google login complete", token=str(settings.google_token_path))


if __name__ == "__main__":
    main()
