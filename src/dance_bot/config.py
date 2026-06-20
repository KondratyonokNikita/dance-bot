from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DANCE_TYPES = ("bachata", "kizomba", "zouk")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone: str

    session_path: Path = Path("data/bot.session")
    db_path: Path = Path("data/events.db")
    lock_path: Path = Path("data/dance-bot.lock")

    telegram_channels: list[str] = [
        "kredo_dance",
        "plyas_dance",
        "KIZonEVERYone",
        "danceforever_minsk",
        "estarico_dance",
    ]
    history_hours: int = 168  # 7 days — initial backfill when channel has no messages in DB

    google_credentials_path: Path = Path("data/google_credentials.json")
    google_token_path: Path = Path("data/google_token.json")
    google_calendars: dict[str, str] = {
        "bachata": "Танцы - Бачата",
        "kizomba": "Танцы - Кизомба",
        "zouk": "Танцы - Зук",
    }
    timezone: str = "Europe/Minsk"

    # Интервал автозапуска (launchd StartInterval, секунды).
    run_interval_seconds: int = 3600
    launchd_label: str = "com.user.dance-bot"

    telegram_log_chat: str = "Моя жизнь"
    telegram_log_topic: str = "Dance_bot_log"
    telegram_log_enabled: bool = True
    telegram_log_min_level: str = "WARNING"


def get_settings() -> Settings:
    return Settings()
