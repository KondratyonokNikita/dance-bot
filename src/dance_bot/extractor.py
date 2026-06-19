import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "extract_event.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_MODEL = "claude-haiku-4-5"
_TIMEOUT_SEC = 300


class Event(BaseModel):
    event_type: Literal["party", "protanzovka", "openair", "dance_class"]
    dances: list[Literal["bachata", "kizomba", "zouk"]] = []
    date: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    location: Optional[str] = None
    price: Optional[str] = None


class Extraction(BaseModel):
    events: list[Event]


def extract(text: str, message_date: date) -> tuple[Extraction, str]:
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Дата публикации поста: {message_date.isoformat()}\n\n"
        f"Текст поста:\n{text}\n\n"
        'Ответь ТОЛЬКО валидным JSON вида {"events": [...]} без markdown, без объяснений.'
    )
    result = subprocess.run(
        ["claude", "--print", "--model", _MODEL, "--output-format", "json", prompt],
        capture_output=True,
        text=True,
        check=True,
        timeout=_TIMEOUT_SEC,
    )
    raw = json.loads(result.stdout)["result"]
    parsed = Extraction.model_validate_json(_strip_fences(raw))
    return parsed, raw


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.startswith("json"):
            s = s[4:]
        s = s.strip()
    return s
