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

CANCEL_PREFIX = "(ОТМЕНА) "
CANCEL_SOURCE_MARKER = "Источник отмены:"

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


def _event_metadata_lines(event: Event) -> list[str]:
    lines = [f"Тип: {_TYPE_LABELS_RU[event.event_type]}"]
    if event.dances:
        dances = ", ".join(_DANCE_LABELS_RU[d] for d in event.dances)
        lines.append(f"Танцы: {dances}")
    if event.price:
        lines.append(f"Цена: {event.price}")
    return lines


def _event_description(
    event: Event, source_url: str, raw_message: str | None
) -> str:
    lines = _event_metadata_lines(event)
    if raw_message:
        lines.extend(["", "—", "", raw_message])
    lines.extend(["", f"Источник: {source_url}"])
    return "\n".join(lines)


def _extract_announcement_from_description(description: str) -> str | None:
    if "\n—\n" not in description:
        return None
    _, rest = description.split("\n—\n", 1)
    if CANCEL_SOURCE_MARKER in rest:
        parts = rest.split("\n—\n", 1)
        return parts[-1].strip() if parts else None
    return rest.strip()


def _event_description_with_cancellation(
    event: Event,
    source_url: str,
    raw_message: str | None,
    *,
    cancellation_url: str,
    cancellation_message: str | None,
    existing_description: str | None = None,
) -> str:
    if existing_description and CANCEL_SOURCE_MARKER in existing_description:
        return existing_description

    if existing_description and "\n—\n" in existing_description:
        meta = existing_description.split("\n—\n", 1)[0].rstrip()
    else:
        meta = "\n".join(_event_metadata_lines(event))

    lines = [meta, "", "—", "Отмена:", ""]
    if cancellation_message:
        lines.append(cancellation_message)
    lines.extend(["", f"{CANCEL_SOURCE_MARKER} {cancellation_url}"])

    announcement = _extract_announcement_from_description(
        existing_description or ""
    )
    if announcement:
        lines.extend(["", "—", "", announcement])
    elif raw_message:
        lines.extend(["", "—", "", raw_message, "", f"Источник: {source_url}"])

    return "\n".join(lines)


def _cancelled_title(original: str) -> str:
    if original.startswith(CANCEL_PREFIX):
        return original
    return f"{CANCEL_PREFIX}{original}"


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
    *,
    allow_restore: bool = True,
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
        if allow_restore and existing.get("status") == "cancelled":
            payload["status"] = "confirmed"
            service.events().update(
                calendarId=calendar_id, eventId=dedup_key, body=payload
            ).execute()
            return "restored"
        return "skipped"


def mark_calendar_event_cancelled(
    event: Event,
    source_url: str,
    dedup_key: str,
    dance: str,
    raw_message: str | None = None,
    *,
    cancellation_url: str,
    cancellation_message: str | None,
) -> Literal["updated", "skipped", "not_found"]:
    service = _get_service()
    calendar_id = _get_calendar_id(dance)

    try:
        existing = (
            service.events()
            .get(calendarId=calendar_id, eventId=dedup_key)
            .execute()
        )
    except HttpError as e:
        if e.resp.status in (404, 410):
            return "not_found"
        raise

    summary = existing.get("summary", "")
    description = existing.get("description", "")
    if summary.startswith(CANCEL_PREFIX) and CANCEL_SOURCE_MARKER in description:
        return "skipped"

    updated = {
        **existing,
        "summary": _cancelled_title(summary),
        "description": _event_description_with_cancellation(
            event,
            source_url,
            raw_message,
            cancellation_url=cancellation_url,
            cancellation_message=cancellation_message,
            existing_description=description or None,
        ),
    }
    service.events().update(
        calendarId=calendar_id, eventId=dedup_key, body=updated
    ).execute()
    return "updated"


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
