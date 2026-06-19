import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from typing import Literal

from dance_bot.extractor import Event

EventType = Literal["party", "protanzovka", "openair", "dance_class"]
DanceType = Literal["bachata", "kizomba", "zouk"]

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
    event_type TEXT NOT NULL,
    dances TEXT NOT NULL,
    date TEXT,
    time_start TEXT,
    time_end TEXT,
    location TEXT,
    price TEXT,
    dedup_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

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


@dataclass(frozen=True)
class EventRow:
    id: int
    event_type: EventType
    dances: list[DanceType]
    date: str | None
    time_start: str | None
    time_end: str | None
    location: str | None
    price: str | None
    dedup_key: str
    source_url: str


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        if self._is_legacy_schema():
            self._migrate_from_legacy()
        else:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def _table_columns(self, table: str) -> set[str]:
        return {
            row["name"]
            for row in self._conn.execute(f"PRAGMA table_info({table})")
        }

    def _is_legacy_schema(self) -> bool:
        tables = {
            row[0]
            for row in self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "raw_messages_legacy" in tables:
            return False
        if "raw_messages" not in tables:
            return False
        return "id" not in self._table_columns("raw_messages")

    def _migrate_from_legacy(self) -> None:
        from dance_bot.filters import matches

        tables = {
            row[0]
            for row in self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        has_legacy_events = "events" in tables

        self._conn.execute("ALTER TABLE raw_messages RENAME TO raw_messages_legacy")
        if has_legacy_events:
            self._conn.execute("ALTER TABLE events RENAME TO events_legacy")
        self._conn.executescript(_SCHEMA)

        legacy_rows = self._conn.execute(
            """
            SELECT channel, message_id, message_date, text, source_url, fetched_at,
                   parsed_at, llm_raw_output
            FROM raw_messages_legacy
            """
        ).fetchall()

        for row in legacy_rows:
            text = row["text"]
            filter_passed = 1 if matches(text) else 0
            cursor = self._conn.execute(
                """
                INSERT INTO raw_messages
                    (channel, message_id, message, message_date, source_url,
                     fetch_date, filter_passed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["channel"],
                    row["message_id"],
                    text,
                    row["message_date"],
                    row["source_url"] or "",
                    row["fetched_at"],
                    filter_passed,
                ),
            )
            raw_id = cursor.lastrowid

            if row["parsed_at"] and row["llm_raw_output"]:
                pm_cursor = self._conn.execute(
                    """
                    INSERT INTO parsed_messages
                        (raw_message_id, parsed_message, parse_date)
                    VALUES (?, ?, ?)
                    """,
                    (raw_id, row["llm_raw_output"], row["parsed_at"]),
                )
                parsed_id = pm_cursor.lastrowid

                if has_legacy_events:
                    legacy_events = self._conn.execute(
                        """
                        SELECT event_type, dances, date, time_start, time_end, location,
                               price, extracted_at
                        FROM events_legacy
                        WHERE channel = ? AND message_id = ?
                        """,
                        (row["channel"], row["message_id"]),
                    ).fetchall()
                else:
                    legacy_events = []

                for event_row in legacy_events:
                    event = Event(
                        event_type=event_row["event_type"],
                        dances=json.loads(event_row["dances"]),
                        date=event_row["date"],
                        time_start=event_row["time_start"],
                        time_end=event_row["time_end"],
                        location=event_row["location"],
                        price=event_row["price"],
                    )
                    self._conn.execute(
                        """
                        INSERT OR IGNORE INTO events
                            (parsed_message_id, raw_message_id, event_type, dances,
                             date, time_start, time_end, location, price,
                             dedup_key, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            parsed_id,
                            raw_id,
                            event.event_type,
                            json.dumps(event.dances, ensure_ascii=False),
                            event.date,
                            event.time_start,
                            event.time_end,
                            event.location,
                            event.price,
                            event_dedup_key(event),
                            event_row["extracted_at"],
                        ),
                    )

                if legacy_events:
                    self._conn.execute(
                        """
                        UPDATE parsed_messages
                        SET events_extracted_at = ?
                        WHERE id = ?
                        """,
                        (row["parsed_at"], parsed_id),
                    )

        self._conn.execute("DROP TABLE IF EXISTS raw_messages_legacy")
        self._conn.execute("DROP TABLE IF EXISTS events_legacy")
        self._conn.commit()

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
                   r.message_date, r.message, r.source_url
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
            )
            for row in rows
        ]

    def insert_event(
        self,
        *,
        parsed_message_id: int,
        raw_message_id: int,
        event: Event,
    ) -> str:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO events
                (parsed_message_id, raw_message_id, event_type, dances, date,
                 time_start, time_end, location, price, dedup_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parsed_message_id,
                raw_message_id,
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

    def list_unsynced_for_calendar(
        self, sink: str = "google_calendar"
    ) -> list[EventRow]:
        rows = self._conn.execute(
            """
            SELECT e.id, e.event_type, e.dances, e.date, e.time_start, e.time_end,
                   e.location, e.price, e.dedup_key, r.source_url
            FROM events e
            JOIN raw_messages r ON r.id = e.raw_message_id
            LEFT JOIN sync_log s ON s.event_id = e.id AND s.sink = ?
            WHERE s.id IS NULL
            ORDER BY e.date ASC, e.time_start ASC, e.id ASC
            """,
            (sink,),
        ).fetchall()
        return [
            EventRow(
                id=row["id"],
                event_type=row["event_type"],
                dances=json.loads(row["dances"]),
                date=row["date"],
                time_start=row["time_start"],
                time_end=row["time_end"],
                location=row["location"],
                price=row["price"],
                dedup_key=row["dedup_key"],
                source_url=row["source_url"],
            )
            for row in rows
        ]

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

    def clear_sync_log(self, sink: str = "google_calendar") -> int:
        cursor = self._conn.execute(
            "DELETE FROM sync_log WHERE sink = ?",
            (sink,),
        )
        self._conn.commit()
        return cursor.rowcount
