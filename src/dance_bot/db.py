import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from typing import Literal

from dance_bot.extractor import Cancellation, Event

EventType = Literal["party", "protanzovka", "openair", "dance_class"]
DanceType = Literal["bachata", "kizomba", "zouk"]

CALENDAR_SINK_PREFIX = "google_calendar"
DEFAULT_DANCE: DanceType = "bachata"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    message TEXT,
    message_date TEXT NOT NULL,
    source_url TEXT NOT NULL,
    fetch_date TEXT NOT NULL,
    filter_passed INTEGER NOT NULL DEFAULT 0,
    UNIQUE(channel, message_id)
);

CREATE TABLE IF NOT EXISTS parsed_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_message_id INTEGER NOT NULL UNIQUE REFERENCES raw_messages(id),
    parsed_message TEXT NOT NULL,
    parse_date TEXT NOT NULL,
    events_extracted_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parsed_message_id INTEGER NOT NULL REFERENCES parsed_messages(id),
    raw_message_id INTEGER NOT NULL REFERENCES raw_messages(id),
    channel TEXT NOT NULL,
    event_type TEXT NOT NULL,
    dances TEXT NOT NULL,
    date TEXT,
    time_start TEXT,
    time_end TEXT,
    location TEXT,
    price TEXT,
    dedup_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    cancellation_raw_message_id INTEGER REFERENCES raw_messages(id),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_channel_date
    ON events (channel, date, event_type, status);

CREATE INDEX IF NOT EXISTS idx_events_dedup_status
    ON events (dedup_key, status);

CREATE INDEX IF NOT EXISTS idx_raw_filter_unparsed
    ON raw_messages (filter_passed)
    WHERE filter_passed = 1;

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    sink TEXT NOT NULL,
    external_id TEXT NOT NULL,
    status TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    UNIQUE(event_id, sink)
);
"""


def event_dedup_key(event: Event) -> str:
    key = (
        f"{event.date or ''}|{event.time_start or ''}|"
        f"{(event.location or '').strip().lower()}"
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def cancellation_dedup_key(cancellation: Cancellation) -> str:
    event = Event(
        event_type=cancellation.event_type,
        dances=cancellation.dances,
        date=cancellation.date,
        time_start=cancellation.time_start,
        location=cancellation.location,
    )
    return event_dedup_key(event)


def calendar_sink(dance: DanceType) -> str:
    return f"{CALENDAR_SINK_PREFIX}:{dance}"


def target_dances(dances: list[DanceType]) -> list[DanceType]:
    valid = [d for d in dances if d in ("bachata", "kizomba", "zouk")]
    if valid:
        return list(dict.fromkeys(valid))
    return [DEFAULT_DANCE]


@dataclass(frozen=True)
class RawMessageRow:
    id: int
    channel: str
    message_id: int
    message_date: datetime
    message: str | None
    source_url: str


@dataclass(frozen=True)
class ParsedMessageRow:
    id: int
    raw_message_id: int
    parsed_message: str
    message_date: datetime
    message: str | None
    source_url: str
    channel: str


@dataclass(frozen=True)
class EventRow:
    id: int
    channel: str
    event_type: EventType
    dances: list[DanceType]
    date: str | None
    time_start: str | None
    time_end: str | None
    location: str | None
    price: str | None
    dedup_key: str
    source_url: str
    message: str | None


@dataclass(frozen=True)
class CalendarSyncRow:
    event: EventRow
    dance: DanceType
    cancellation_source_url: str | None = None
    cancellation_message: str | None = None


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def get_last_raw_message(
        self, channel: str
    ) -> tuple[datetime, int] | None:
        row = self._conn.execute(
            """
            SELECT message_date, message_id
            FROM raw_messages
            WHERE channel = ?
            ORDER BY message_date DESC, message_id DESC
            LIMIT 1
            """,
            (channel,),
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row["message_date"]), row["message_id"]

    def insert_raw_message(
        self,
        *,
        channel: str,
        message_id: int,
        message_date: datetime,
        message: str | None,
        source_url: str,
        filter_passed: bool,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO raw_messages
                (channel, message_id, message, message_date, source_url,
                 fetch_date, filter_passed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                channel,
                message_id,
                message,
                message_date.isoformat(),
                source_url,
                now,
                int(filter_passed),
            ),
        )
        self._conn.commit()
        return cursor.rowcount == 1

    def list_unparsed_for_llm(self) -> list[RawMessageRow]:
        rows = self._conn.execute(
            """
            SELECT r.id, r.channel, r.message_id, r.message_date, r.message,
                   r.source_url
            FROM raw_messages r
            LEFT JOIN parsed_messages p ON p.raw_message_id = r.id
            WHERE r.filter_passed = 1 AND p.id IS NULL
            ORDER BY r.message_date ASC, r.message_id ASC
            """
        ).fetchall()
        return [
            RawMessageRow(
                id=row["id"],
                channel=row["channel"],
                message_id=row["message_id"],
                message_date=datetime.fromisoformat(row["message_date"]),
                message=row["message"],
                source_url=row["source_url"],
            )
            for row in rows
        ]

    def insert_parsed_message(
        self, raw_message_id: int, parsed_message: str
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """
            INSERT INTO parsed_messages
                (raw_message_id, parsed_message, parse_date)
            VALUES (?, ?, ?)
            """,
            (raw_message_id, parsed_message, now),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_unprocessed_for_events(self) -> list[ParsedMessageRow]:
        rows = self._conn.execute(
            """
            SELECT p.id, p.raw_message_id, p.parsed_message,
                   r.message_date, r.message, r.source_url, r.channel
            FROM parsed_messages p
            JOIN raw_messages r ON r.id = p.raw_message_id
            WHERE p.events_extracted_at IS NULL
            ORDER BY p.parse_date ASC, p.id ASC
            """
        ).fetchall()
        return [
            ParsedMessageRow(
                id=row["id"],
                raw_message_id=row["raw_message_id"],
                parsed_message=row["parsed_message"],
                message_date=datetime.fromisoformat(row["message_date"]),
                message=row["message"],
                source_url=row["source_url"],
                channel=row["channel"],
            )
            for row in rows
        ]

    def insert_event(
        self,
        *,
        parsed_message_id: int,
        raw_message_id: int,
        channel: str,
        event: Event,
    ) -> str:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO events
                (parsed_message_id, raw_message_id, channel, event_type, dances,
                 date, time_start, time_end, location, price, dedup_key, status,
                 created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                parsed_message_id,
                raw_message_id,
                channel,
                event.event_type,
                json.dumps(event.dances, ensure_ascii=False),
                event.date,
                event.time_start,
                event.time_end,
                event.location,
                event.price,
                event_dedup_key(event),
                now,
            ),
        )
        self._conn.commit()
        return "inserted" if cursor.rowcount == 1 else "skipped"

    def find_active_events_for_cancellation(
        self, cancellation: Cancellation, *, channel: str
    ) -> list[int]:
        rows = self._conn.execute(
            """
            SELECT e.id, e.dances, e.location, e.time_start, e.dedup_key
            FROM events e
            WHERE e.status = 'active'
              AND e.date = ?
              AND e.event_type = ?
              AND e.channel = ?
            """,
            (cancellation.date, cancellation.event_type, channel),
        ).fetchall()
        if not rows:
            return []

        candidates = [dict(row) for row in rows]

        if cancellation.time_start and cancellation.location:
            key = cancellation_dedup_key(cancellation)
            exact = [row["id"] for row in candidates if row["dedup_key"] == key]
            if len(exact) == 1:
                return exact
            if len(exact) > 1:
                candidates = [row for row in candidates if row["id"] in exact]

        if cancellation.time_start:
            candidates = [
                row
                for row in candidates
                if row["time_start"] == cancellation.time_start
            ]

        if cancellation.location:
            location = cancellation.location.strip().lower()
            candidates = [
                row
                for row in candidates
                if (row["location"] or "").strip().lower() == location
            ]

        if cancellation.dances:
            cancel_dances = set(cancellation.dances)
            filtered: list[dict] = []
            for row in candidates:
                event_dances = json.loads(row["dances"])
                effective = set(target_dances(event_dances))
                if effective & cancel_dances:
                    filtered.append(row)
            candidates = filtered

        return [row["id"] for row in candidates]

    def cancel_event(
        self, event_id: int, *, cancellation_raw_message_id: int
    ) -> None:
        self._conn.execute(
            """
            UPDATE events
            SET status = 'cancelled',
                cancellation_raw_message_id = ?
            WHERE id = ? AND status = 'active'
            """,
            (cancellation_raw_message_id, event_id),
        )
        self._conn.commit()

    def mark_events_extracted(self, parsed_message_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            UPDATE parsed_messages
            SET events_extracted_at = ?
            WHERE id = ?
            """,
            (now, parsed_message_id),
        )
        self._conn.commit()

    def list_unsynced_for_calendar(self) -> list[CalendarSyncRow]:
        rows = self._conn.execute(
            """
            SELECT e.id, e.channel, e.event_type, e.dances, e.date, e.time_start,
                   e.time_end, e.location, e.price, e.dedup_key, r.source_url,
                   r.message
            FROM events e
            JOIN raw_messages r ON r.id = e.raw_message_id
            WHERE e.status = 'active'
            ORDER BY e.date ASC, e.time_start ASC, e.id ASC
            """
        ).fetchall()
        synced_rows = self._conn.execute(
            """
            SELECT event_id, sink
            FROM sync_log
            WHERE sink LIKE ?
            """,
            (f"{CALENDAR_SINK_PREFIX}:%",),
        ).fetchall()
        synced = {(row["event_id"], row["sink"]) for row in synced_rows}

        result: list[CalendarSyncRow] = []
        for row in rows:
            event = EventRow(
                id=row["id"],
                channel=row["channel"],
                event_type=row["event_type"],
                dances=json.loads(row["dances"]),
                date=row["date"],
                time_start=row["time_start"],
                time_end=row["time_end"],
                location=row["location"],
                price=row["price"],
                dedup_key=row["dedup_key"],
                source_url=row["source_url"],
                message=row["message"],
            )
            for dance in target_dances(event.dances):
                if (event.id, calendar_sink(dance)) not in synced:
                    result.append(CalendarSyncRow(event=event, dance=dance))
        return result

    def list_cancelled_unsynced(self) -> list[CalendarSyncRow]:
        rows = self._conn.execute(
            """
            SELECT e.id, e.channel, e.event_type, e.dances, e.date, e.time_start,
                   e.time_end, e.location, e.price, e.dedup_key,
                   r.source_url, r.message,
                   cr.source_url AS cancellation_source_url,
                   cr.message AS cancellation_message,
                   sl.sink
            FROM events e
            JOIN raw_messages r ON r.id = e.raw_message_id
            JOIN raw_messages cr ON cr.id = e.cancellation_raw_message_id
            JOIN sync_log sl ON sl.event_id = e.id
            WHERE e.status = 'cancelled'
              AND sl.status != 'cancelled'
              AND sl.sink LIKE ?
            ORDER BY e.date ASC, e.time_start ASC, e.id ASC, sl.sink ASC
            """,
            (f"{CALENDAR_SINK_PREFIX}:%",),
        ).fetchall()

        result: list[CalendarSyncRow] = []
        for row in rows:
            sink = row["sink"]
            dance = sink.split(":", 1)[1]
            if dance not in ("bachata", "kizomba", "zouk"):
                continue
            event = EventRow(
                id=row["id"],
                channel=row["channel"],
                event_type=row["event_type"],
                dances=json.loads(row["dances"]),
                date=row["date"],
                time_start=row["time_start"],
                time_end=row["time_end"],
                location=row["location"],
                price=row["price"],
                dedup_key=row["dedup_key"],
                source_url=row["source_url"],
                message=row["message"],
            )
            result.append(
                CalendarSyncRow(
                    event=event,
                    dance=dance,
                    cancellation_source_url=row["cancellation_source_url"],
                    cancellation_message=row["cancellation_message"],
                )
            )
        return result

    def record_sync(
        self,
        *,
        event_id: int,
        sink: str,
        external_id: str,
        status: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT OR IGNORE INTO sync_log
                (event_id, sink, external_id, status, synced_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, sink, external_id, status, now),
        )
        self._conn.commit()

    def mark_sync_cancelled(self, event_id: int, sink: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            UPDATE sync_log
            SET status = 'cancelled', synced_at = ?
            WHERE event_id = ? AND sink = ?
            """,
            (now, event_id, sink),
        )
        self._conn.commit()

    def clear_sync_log(self) -> int:
        cursor = self._conn.execute(
            "DELETE FROM sync_log WHERE sink LIKE ?",
            (f"{CALENDAR_SINK_PREFIX}:%",),
        )
        self._conn.commit()
        return cursor.rowcount
