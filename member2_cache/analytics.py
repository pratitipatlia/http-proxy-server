
import threading


class ProxyAnalytics:
    def __init__(self):
        self._lock = threading.Lock()
        self._reset_stats()

    def _reset_stats(self):
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.blocked_requests = 0
        self.total_response_time = 0.0
        self.timed_requests = 0
        self.bytes_served_from_cache = 0

    def record_request(self, cache_hit, response_time):
        """
        Record one request.
        response_time is in seconds.
        cache_hit: True, False, or None if caching was bypassed.
        """
        with self._lock:
            self.total_requests += 1
            self.total_response_time += response_time
            self.timed_requests += 1

            if cache_hit is True:
                self.cache_hits += 1
            elif cache_hit is False:
                self.cache_misses += 1

    def record_blocked_request(self):
        with self._lock:
            self.blocked_requests += 1

    def record_cached_bytes(self, byte_count):
        with self._lock:
            self.bytes_served_from_cache += byte_count

    def get_stats(self):
        with self._lock:
            lookups = self.cache_hits + self.cache_misses

            return {
                "total_requests": self.total_requests,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_ratio": round(
                    self.cache_hits / lookups * 100, 2
                ) if lookups else 0.0,
                "average_response_time_ms": round(
                    self.total_response_time
                    / self.timed_requests * 1000, 2
                ) if self.timed_requests else 0.0,
                "blocked_requests": self.blocked_requests,
                "bytes_served_from_cache":
                    self.bytes_served_from_cache,
            }

    def print_stats(self):
        stats = self.get_stats()

        print("\n========== PROXY STATISTICS ==========")
        print(f"Total requests: {stats['total_requests']}")
        print(f"Cache hits: {stats['cache_hits']}")
        print(f"Cache misses: {stats['cache_misses']}")
        print(f"Cache hit ratio: {stats['cache_hit_ratio']}%")
        print(
            "Average response time: "
            f"{stats['average_response_time_ms']} ms"
        )
        print(f"Blocked requests: {stats['blocked_requests']}")
        print(
            "Bytes served from cache: "
            f"{stats['bytes_served_from_cache']}"
        )
        print("======================================\n")


analytics = ProxyAnalytics()
