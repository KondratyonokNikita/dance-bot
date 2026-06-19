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


def get_settings() -> Settings:
    return Settings()
