import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dance_bot.extractor import Event

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_messages (
    channel TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    message_date TEXT NOT NULL,
    text TEXT,
    source_url TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    parsed_at TEXT,
    llm_raw_output TEXT,
    PRIMARY KEY (channel, message_id)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    dances TEXT NOT NULL,
    date TEXT,
    time_start TEXT,
    time_end TEXT,
    location TEXT,
    price TEXT,
    extracted_at TEXT NOT NULL,
    FOREIGN KEY (channel, message_id) REFERENCES raw_messages (channel, message_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_unparsed
    ON raw_messages (channel)
    WHERE parsed_at IS NULL;
"""


@dataclass(frozen=True)
class RawMessageRow:
    channel: str
    message_id: int
    message_date: datetime
    text: str | None
    source_url: str


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._migrate()

    def close(self) -> None:
        self._conn.close()

    def _migrate(self) -> None:
        columns = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(raw_messages)")
        }
        if "source_url" not in columns:
            self._conn.execute(
                "ALTER TABLE raw_messages ADD COLUMN source_url TEXT NOT NULL DEFAULT ''"
            )
        if "parsed_at" not in columns and "processed_at" in columns:
            self._conn.execute(
                "ALTER TABLE raw_messages ADD COLUMN parsed_at TEXT"
            )
            self._conn.execute(
                "UPDATE raw_messages SET parsed_at = processed_at"
            )
        if "llm_raw_output" not in columns:
            self._conn.execute(
                "ALTER TABLE raw_messages ADD COLUMN llm_raw_output TEXT"
            )
        self._conn.commit()

    def get_last_message(
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

    def insert_raw(
        self,
        *,
        channel: str,
        message_id: int,
        message_date: datetime,
        text: str | None,
        source_url: str,
    ) -> bool:
        """Store a message. Returns True if it was new."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO raw_messages
                (channel, message_id, message_date, text, source_url, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                channel,
                message_id,
                message_date.isoformat(),
                text,
                source_url,
                now,
            ),
        )
        self._conn.commit()
        return cursor.rowcount == 1

    def list_unparsed(self, channel: str | None = None) -> list[RawMessageRow]:
        query = """
            SELECT channel, message_id, message_date, text, source_url
            FROM raw_messages
            WHERE parsed_at IS NULL
        """
        params: tuple[str, ...] = ()
        if channel is not None:
            query += " AND channel = ?"
            params = (channel,)
        query += " ORDER BY message_date ASC, message_id ASC"

        rows = self._conn.execute(query, params).fetchall()
        return [
            RawMessageRow(
                channel=row["channel"],
                message_id=row["message_id"],
                message_date=datetime.fromisoformat(row["message_date"]),
                text=row["text"],
                source_url=row["source_url"],
            )
            for row in rows
        ]

    def insert_events(
        self, channel: str, message_id: int, events: list[Event]
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        for event in events:
            self._conn.execute(
                """
                INSERT INTO events
                    (channel, message_id, event_type, dances, date,
                     time_start, time_end, location, price, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    channel,
                    message_id,
                    event.event_type,
                    json.dumps(event.dances, ensure_ascii=False),
                    event.date,
                    event.time_start,
                    event.time_end,
                    event.location,
                    event.price,
                    now,
                ),
            )
        self._conn.commit()
        return len(events)

    def mark_parsed(
        self, channel: str, message_id: int, llm_raw_output: str | None = None
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            UPDATE raw_messages
            SET parsed_at = ?, llm_raw_output = ?
            WHERE channel = ? AND message_id = ?
            """,
            (now, llm_raw_output, channel, message_id),
        )
        self._conn.commit()
