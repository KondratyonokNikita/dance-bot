from datetime import datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from dance_bot.config import DANCE_TYPES, get_settings
from dance_bot.extractor import Event

SCOPES = ["https://www.googleapis.com/auth/calendar"]

_DEFAULT_DURATION = timedelta(hours=2)

_TYPE_LABELS = {
    "party": "Party",
    "protanzovka": "Протанцовка",
    "openair": "Open-air",
    "dance_class": "Класс",
}

_TYPE_LABELS_RU = {
    "party": "вечеринка",
    "protanzovka": "протанцовка",
    "openair": "open-air",
    "dance_class": "класс",
}

_DANCE_LABELS = {
    "bachata": "Bachata",
    "kizomba": "Kizomba",
    "zouk": "Zouk",
}

_DANCE_LABELS_RU = {
    "bachata": "бачата",
    "kizomba": "кизомба",
    "zouk": "зук",
}

_service: Any | None = None
_calendar_ids: dict[str, str] = {}


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


def _get_calendar_id(dance: str) -> str:
    if dance in _calendar_ids:
        return _calendar_ids[dance]

    settings = get_settings()
    calendar_name = settings.google_calendars.get(dance)
    if calendar_name is None:
        raise RuntimeError(f"Unknown dance calendar: {dance}")

    service = _get_service()
    for entry in service.calendarList().list().execute().get("items", []):
        if entry.get("summary") == calendar_name:
            _calendar_ids[dance] = entry["id"]
            return _calendar_ids[dance]

    raise RuntimeError(
        f"Calendar '{calendar_name}' not found — "
        "create it manually at https://calendar.google.com"
    )


def _event_title(event: Event) -> str:
    type_label = _TYPE_LABELS[event.event_type]
    if event.dances:
        dance_part = " / ".join(_DANCE_LABELS[d] for d in event.dances)
        return f"{dance_part} — {type_label}"
    return type_label


def _event_description(
    event: Event, source_url: str, raw_message: str | None
) -> str:
    lines = [f"Тип: {_TYPE_LABELS_RU[event.event_type]}"]
    if event.dances:
        dances = ", ".join(_DANCE_LABELS_RU[d] for d in event.dances)
        lines.append(f"Танцы: {dances}")
    if event.price:
        lines.append(f"Цена: {event.price}")
    if raw_message:
        lines.extend(["", "—", "", raw_message])
    lines.extend(["", f"Источник: {source_url}"])
    return "\n".join(lines)


def _build_payload(
    event: Event,
    source_url: str,
    dedup_key: str,
    raw_message: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    tz = ZoneInfo(settings.timezone)

    payload: dict[str, Any] = {
        "id": dedup_key,
        "summary": _event_title(event),
        "description": _event_description(event, source_url, raw_message),
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
        payload["start"] = {
            "dateTime": start_dt.isoformat(),
            "timeZone": settings.timezone,
        }
        payload["end"] = {
            "dateTime": end_dt.isoformat(),
            "timeZone": settings.timezone,
        }
    else:
        payload["start"] = {"date": event.date}
        payload["end"] = {"date": event.date}

    return payload


def insert_calendar_event(
    event: Event,
    source_url: str,
    dedup_key: str,
    dance: str,
    raw_message: str | None = None,
) -> Literal["inserted", "restored", "skipped"]:
    """Insert one event into the Google Calendar for a dance style."""
    if not event.date:
        return "skipped"

    service = _get_service()
    calendar_id = _get_calendar_id(dance)
    payload = _build_payload(event, source_url, dedup_key, raw_message)

    try:
        service.events().insert(calendarId=calendar_id, body=payload).execute()
        return "inserted"
    except HttpError as e:
        if e.resp.status != 409:
            raise

        existing = (
            service.events()
            .get(calendarId=calendar_id, eventId=dedup_key)
            .execute()
        )
        if existing.get("status") == "cancelled":
            payload["status"] = "confirmed"
            service.events().update(
                calendarId=calendar_id, eventId=dedup_key, body=payload
            ).execute()
            return "restored"
        return "skipped"


def _clear_calendar(dance: str) -> int:
    service = _get_service()
    calendar_id = _get_calendar_id(dance)
    deleted = 0
    page_token: str | None = None

    while True:
        result = (
            service.events()
            .list(
                calendarId=calendar_id,
                showDeleted=True,
                singleEvents=True,
                maxResults=250,
                pageToken=page_token,
            )
            .execute()
        )
        for item in result.get("items", []):
            if item.get("status") == "cancelled":
                continue
            try:
                service.events().delete(
                    calendarId=calendar_id, eventId=item["id"]
                ).execute()
                deleted += 1
            except HttpError as e:
                if e.resp.status == 410:
                    continue
                raise

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return deleted


def clear_all_calendar_events() -> int:
    """Permanently delete all events from all dance calendars, including cancelled."""
    return sum(_clear_calendar(dance) for dance in DANCE_TYPES)
