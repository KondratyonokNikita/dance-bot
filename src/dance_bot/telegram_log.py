"""Логирование в тему Telegram-чата и отправка текста туда же."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetForumTopicsRequest
from telethon.tl.types import ForumTopic

from dance_bot.config import Settings, get_settings

_TELEGRAM_MAX_MESSAGE_LEN = 4096
_TRUNCATION_SUFFIX = "\n…(обрезано)"

_LEVEL_EMOJI = {
    "debug": "🔍",
    "info": "ℹ️",
    "warning": "⚠️",
    "warn": "⚠️",
    "error": "❌",
    "critical": "🔥",
}

_LEVEL_NUMBERS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

_SKIP_KEYS = frozenset({"event", "level", "timestamp", "exception", "stack"})


class TelegramLogSink:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._min_level = _parse_log_level(settings.telegram_log_min_level)
        self._client: TelegramClient | None = None
        self._chat_id: int | None = None
        self._topic_id: int | None = None

    def bind_client(self, client: TelegramClient) -> None:
        self._client = client

    def send(self, method_name: str, event_dict: dict[str, Any]) -> None:
        if not _should_send_to_telegram(event_dict, method_name, self._min_level):
            return
        if self._client is None:
            return
        try:
            self._deliver(format_telegram_message(event_dict, method_name))
        except Exception as exc:
            print(f"Failed to send log to Telegram: {exc}", file=sys.stderr)

    def close(self) -> None:
        self._client = None
        self._chat_id = None
        self._topic_id = None

    def _deliver(self, text: str) -> None:
        chat, topic_id = self._resolve_destination(self._client)
        self._client.send_message(chat, _truncate_text(text), reply_to=topic_id)

    def _resolve_destination(self, client: TelegramClient):
        if self._chat_id is not None and self._topic_id is not None:
            return client.get_entity(self._chat_id), self._topic_id

        chat, topic_id = _resolve_log_topic(client, self._settings)
        self._chat_id = chat.id
        self._topic_id = topic_id
        return chat, topic_id


def configure_logging(settings: Settings) -> TelegramLogSink | None:
    """Настраивает structlog: stderr + опциональная отправка в Telegram."""
    sink = TelegramLogSink(settings) if settings.telegram_log_enabled else None
    console_renderer = structlog.dev.ConsoleRenderer()

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if sink is not None:
        processors.append(_tee_to_telegram(sink, console_renderer))
    else:
        processors.append(console_renderer)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
    return sink


def close_telegram_log(sink: TelegramLogSink | None) -> None:
    if sink is not None:
        sink.close()


def format_telegram_message(event_dict: dict[str, Any], method_name: str) -> str:
    level = str(event_dict.get("level") or method_name or "info").lower()
    event = event_dict.get("event", "")

    if level in ("warning", "warn"):
        lines = [str(event)]
    else:
        emoji = _LEVEL_EMOJI.get(level, "•")
        lines = [f"{emoji} {level.upper()} · {event}"]
    if timestamp := event_dict.get("timestamp"):
        lines.append(f"🕐 {timestamp}")

    extras = sorted(
        (key, value)
        for key, value in event_dict.items()
        if key not in _SKIP_KEYS and not key.startswith("_")
    )
    if extras:
        lines.append("")
        lines.extend(f"  {key}: {value}" for key, value in extras)

    if exc := event_dict.get("exception"):
        lines.extend(["", exc])

    return "\n".join(lines)


def send_text_to_log_topic(text: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    client = open_telegram_client(settings)
    try:
        chat, topic_id = _resolve_log_topic(client, settings)
        client.send_message(chat, _truncate_text(text), reply_to=topic_id)
    finally:
        client.disconnect()


def _tee_to_telegram(sink: TelegramLogSink, renderer: Any):
    def processor(logger: Any, method_name: str, event_dict: dict[str, Any]) -> str:
        # ConsoleRenderer очищает event_dict — в TG отправляем до рендера в консоль.
        sink.send(method_name, event_dict)
        return renderer(logger, method_name, event_dict)

    return processor


def _should_send_to_telegram(
    event_dict: dict[str, Any], method_name: str, min_level: int
) -> bool:
    return _event_level(event_dict, method_name) >= min_level


def _parse_log_level(name: str) -> int:
    level = _LEVEL_NUMBERS.get(name.lower())
    if level is None:
        raise ValueError(f"Unknown log level: {name!r}")
    return level


def _event_level(event_dict: dict[str, Any], method_name: str) -> int:
    level = str(event_dict.get("level", method_name))
    return _LEVEL_NUMBERS.get(level.lower(), logging.INFO)


def format_next_run_hours(seconds: int) -> str:
    hours = seconds / 3600
    if hours == 1:
        return "1 hour"
    if hours == int(hours):
        return f"{int(hours)} hours"
    return f"{hours:g} hours"


def open_telegram_client(settings: Settings) -> TelegramClient:
    client = TelegramClient(
        str(settings.session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )
    client.connect()
    if not client.is_user_authorized():
        raise RuntimeError("Session not authorized — run: uv run python scripts/login.py")
    return client


def _find_chat(client: TelegramClient, title: str):
    for dialog in client.iter_dialogs():
        if dialog.name == title:
            return dialog.entity
    return None


def _find_topic_id(client: TelegramClient, chat, topic_title: str) -> int | None:
    result = client(
        GetForumTopicsRequest(
            peer=chat,
            offset_date=None,
            offset_id=0,
            offset_topic=0,
            limit=100,
            q=topic_title,
        )
    )
    for topic in result.topics:
        if isinstance(topic, ForumTopic) and topic.title == topic_title:
            return topic.id
    return None


def _resolve_log_topic(client: TelegramClient, settings: Settings):
    chat = _find_chat(client, settings.telegram_log_chat)
    if chat is None:
        raise RuntimeError(f"Chat not found: {settings.telegram_log_chat}")
    if not getattr(chat, "forum", False):
        raise RuntimeError(f"Chat has no forum topics: {settings.telegram_log_chat}")

    topic_id = _find_topic_id(client, chat, settings.telegram_log_topic)
    if topic_id is None:
        raise RuntimeError(
            f"Topic not found: {settings.telegram_log_topic!r} "
            f"in chat {settings.telegram_log_chat!r}"
        )
    return chat, topic_id


def _truncate_text(text: str, max_len: int = _TELEGRAM_MAX_MESSAGE_LEN) -> str:
    if len(text) <= max_len:
        return text
    keep = max_len - len(_TRUNCATION_SUFFIX)
    return text[:keep] + _TRUNCATION_SUFFIX
