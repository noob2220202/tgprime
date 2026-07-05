import time
from collections import defaultdict

_MAX_ATTEMPTS = 10
_WINDOW_SECONDS = 300

_attempts: dict[str, list[float]] = defaultdict(list)


def is_rate_limited(key: str) -> bool:
    now = time.monotonic()
    window_start = now - _WINDOW_SECONDS
    attempts = [t for t in _attempts[key] if t > window_start]
    _attempts[key] = attempts
    return len(attempts) >= _MAX_ATTEMPTS


def record_attempt(key: str) -> None:
    _attempts[key].append(time.monotonic())
