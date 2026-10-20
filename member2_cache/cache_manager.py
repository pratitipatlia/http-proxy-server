
import time
import threading

# Shared cache storage
_cache = {}
_cache_lock = threading.RLock()
MAX_ENTRIES = 500

# Shared statistics
_stats = {
    "total_requests": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "total_response_time": 0.0,
}
_stats_lock = threading.Lock()


def get_cached_response(cache_key):
    """
    Return cached response bytes if valid.
    Return None if missing or expired.
    """
    with _cache_lock:
        
        entry = _cache.get(cache_key)

        if entry is None:
            return None

        now = time.monotonic()

        if now >= entry["expires_at"]:
            del _cache[cache_key]
            return None

        # Update access time for LRU eviction.
        entry["last_access"] = now
        return entry["response"]


def store_response(cache_key, response, ttl=60):
    """
    Store an eligible HTTP response as bytes.
    Return True if stored, otherwise False.
    """
    if not isinstance(response, bytes):
        raise TypeError("Response must be bytes")

    if ttl <= 0:
        return False

    # Parse the HTTP response headers.
    try:
        header_section, _ = response.split(b"\r\n\r\n", 1)
        lines = header_section.decode(
            "iso-8859-1"
        ).split("\r\n")

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

            headers[name] = (
                headers.get(name, "") + "," + value
            ).strip(",")

        directives = {
            item.strip().lower()
            for item in headers.get("cache-control", "").split(",")
        }

        if directives & {"no-store", "no-cache", "private"}:
            return False

        if "set-cookie" in headers:
            return False

    except (ValueError, UnicodeDecodeError):
        return False

    now = time.monotonic()

    with _cache_lock:
        # Remove expired entries.
        expired_keys = [
            key for key, entry in _cache.items()
            if now >= entry["expires_at"]
        ]

        for key in expired_keys:
            del _cache[key]

        # Evict the least recently used entry if full.
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
    """
    Update request and performance statistics.

    cache_hit:
        True  -> cache hit
        False -> cache miss
        None  -> request bypassed caching

    response_time is measured in seconds.
    """
    with _stats_lock:
        _stats["total_requests"] += 1
        _stats["total_response_time"] += response_time

        if cache_hit is True:
            _stats["cache_hits"] += 1
        elif cache_hit is False:
            _stats["cache_misses"] += 1


def get_stats():
    """
    Return statistics as a dictionary.
    """
    with _stats_lock:
        total = _stats["total_requests"]
        hits = _stats["cache_hits"]
        misses = _stats["cache_misses"]
        lookups = hits + misses

        return {
            "total_requests": total,
            "cache_hits": hits,
            "cache_misses": misses,
            "cache_hit_ratio": round(
                hits / lookups * 100, 2
            ) if lookups else 0.0,
            "average_response_time_ms": round(
                _stats["total_response_time"] / total * 1000, 2
            ) if total else 0.0,
        }
