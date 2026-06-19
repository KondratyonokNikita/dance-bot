import hashlib
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from dance_bot.config import get_settings
from dance_bot.extractor import Event

SCOPES = ["https://www.googleapis.com/auth/calendar"]

_DEFAULT_DURATION = timedelta(hours=2)

_TYPE_LABELS = {
    "party": "Party",
    "protanzovka": "Протанцовка",
    "openair": "Open-air",
    "dance_class": "Класс",
}

_DANCE_LABELS = {
    "bachata": "Bachata",
    "kizomba": "Kizomba",
    "zouk": "Zouk",
}

_service: Any | None = None
_calendar_id: str | None = None


def _get_service() -> Any:
    global _service
    if _service is not None:
        return _service

    settings = get_settings()
    creds = Credentials.from_authorized_user_file(
        str(settings.google_token_path), SCOPES
    )
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            settings.google_token_path.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError(
                "Google credentials invalid — run `uv run python scripts/google_login.py`"
            )

    _service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return _service


def _get_calendar_id() -> str:
    global _calendar_id
    if _calendar_id is not None:
        return _calendar_id

    settings = get_settings()
    service = _get_service()
    for entry in service.calendarList().list().execute().get("items", []):
        if entry.get("summary") == settings.google_calendar_name:
            _calendar_id = entry["id"]
            return _calendar_id

    raise RuntimeError(
        f"Calendar '{settings.google_calendar_name}' not found — "
        "create it manually at https://calendar.google.com"
    )


def _event_title(event: Event) -> str:
    type_label = _TYPE_LABELS[event.event_type]
    if event.dances:
        dance_part = " / ".join(_DANCE_LABELS[d] for d in event.dances)
        return f"{dance_part} — {type_label}"
    return type_label


def _event_id(event: Event) -> str:
    key = f"{event.date}|{event.time_start}|{(event.location or '').strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _build_payload(event: Event, source_url: str) -> dict[str, Any]:
    settings = get_settings()
    tz = ZoneInfo(settings.timezone)

    description_lines = [f"Источник: {source_url}"]
    if event.price:
        description_lines.append(f"Цена: {event.price}")

    payload: dict[str, Any] = {
        "id": _event_id(event),
        "summary": _event_title(event),
        "description": "\n".join(description_lines),
    }
    if event.location:
        payload["location"] = event.location

    if event.time_start:
        start_dt = datetime.fromisoformat(f"{event.date}T{event.time_start}").replace(
            tzinfo=tz
        )
        if event.time_end:
            end_dt = datetime.fromisoformat(f"{event.date}T{event.time_end}").replace(
                tzinfo=tz
            )
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
        else:
            end_dt = start_dt + _DEFAULT_DURATION
        payload["start"] = {"dateTime": start_dt.isoformat(), "timeZone": settings.timezone}
        payload["end"] = {"dateTime": end_dt.isoformat(), "timeZone": settings.timezone}
    else:
        payload["start"] = {"date": event.date}
        payload["end"] = {"date": event.date}

    return payload


def sync(event: Event, source_url: str) -> str:
    """Upsert one event into the calendar. Returns "inserted" or "skipped"."""
    if not event.date:
        return "skipped"

    service = _get_service()
    calendar_id = _get_calendar_id()
    payload = _build_payload(event, source_url)

    try:
        service.events().insert(calendarId=calendar_id, body=payload).execute()
        return "inserted"
    except HttpError as e:
        if e.resp.status == 409:
            return "skipped"
        raise
