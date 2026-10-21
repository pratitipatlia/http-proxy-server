from collections import deque
from threading import Lock
from datetime import datetime

_events = deque(maxlen=100)
_lock = Lock()


def record_event(url, method, status, cache_status, elapsed):
    event = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "url": url,
        "method": method,
        "status": status,
        "cache": cache_status,
        "elapsed_ms": round(elapsed * 1000, 2),
    }

    with _lock:
        _events.appendleft(event)


def get_events():
    with _lock:
        return list(_events)