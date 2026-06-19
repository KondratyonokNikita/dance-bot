import re

_KEYWORD_RE = re.compile(
    r"вечеринк|протанцовк|open[\s-]?air|party",
    re.IGNORECASE,
)


def matches(text: str | None) -> bool:
    if not text:
        return False
    return bool(_KEYWORD_RE.search(text))
