
import time
import threading

from member2_cache.analytics import analytics

_cache = {}
_cache_lock = threading.RLock()
MAX_ENTRIES = 500


def get_cached_response(cache_key):
    with _cache_lock:
        entry = _cache.get(cache_key)

        if entry is None:
            return None

        if entry["expires_at"] <= time.monotonic():
            del _cache[cache_key]
            return None

        entry["last_access"] = time.monotonic()
        return entry["response"]


def store_response(cache_key, response, ttl=60):
    if not isinstance(response, bytes) or ttl <= 0:
        return False

    if b"\r\n\r\n" not in response:
        return False

    header_bytes = response.split(b"\r\n\r\n", 1)[0]

    try:
        lines = header_bytes.decode("iso-8859-1").split("\r\n")
        status_parts = lines[0].split()

        if len(status_parts) < 2 or status_parts[1] != "200":
            return False

        headers = {}

        for line in lines[1:]:
            if ":" not in line:
                continue

            name, value = line.split(":", 1)
            name = name.strip().lower()
            value = value.strip()

            if name in headers:
                headers[name] += "," + value
            else:
                headers[name] = value

        cache_control = {
            directive.strip().lower().split("=", 1)[0]
            for directive in headers.get("cache-control", "").split(",")
        }

        if cache_control.intersection(
            {"no-store", "no-cache", "private"}
        ):
            return False

        if "set-cookie" in headers or "vary" in headers:
            return False

    except (UnicodeError, ValueError):
        return False

    now = time.monotonic()

    with _cache_lock:
        expired_keys = [
            key for key, entry in _cache.items()
            if entry["expires_at"] <= now
        ]

        for key in expired_keys:
            del _cache[key]

        if cache_key not in _cache and len(_cache) >= MAX_ENTRIES:
            oldest_key = min(
                _cache,
                key=lambda key: _cache[key]["last_access"]
            )
            del _cache[oldest_key]

        _cache[cache_key] = {
            "response": response,
            "expires_at": now + ttl,
            "last_access": now,
        }

    return True


def record_request(cache_hit, response_time):
    analytics.record_request(cache_hit, response_time)


def get_stats():
    return analytics.get_stats()
