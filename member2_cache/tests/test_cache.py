
import time
import unittest

from member2_cache.cache_manager import (
    MAX_ENTRIES,
    _cache,
    _cache_lock,
    get_cached_response,
    store_response,
    record_request,
    get_stats,
)
from member2_cache.analytics import analytics


class TestCacheManager(unittest.TestCase):

    def setUp(self):
        self.response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/plain\r\n"
            b"Content-Length: 5\r\n"
            b"\r\n"
            b"Hello"
        )

        # Isolate each test from previous tests.
        with _cache_lock:
            _cache.clear()

        with analytics._lock:
            analytics._reset_stats()

    def test_cache_miss(self):
        self.assertIsNone(
            get_cached_response("missing-url")
        )

    def test_cache_hit(self):
        self.assertTrue(
            store_response("cache-hit-test", self.response)
        )
        self.assertEqual(
            get_cached_response("cache-hit-test"),
            self.response,
        )

    def test_expired_entry(self):
        store_response("expiry-test", self.response, ttl=0.1)
        time.sleep(0.2)

        self.assertIsNone(
            get_cached_response("expiry-test")
        )

    def test_error_response_not_cached(self):
        response = (
            b"HTTP/1.1 404 Not Found\r\n"
            b"Content-Length: 0\r\n\r\n"
        )

        self.assertFalse(
            store_response("error-test", response)
        )

    def test_no_store_not_cached(self):
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Cache-Control: no-store\r\n"
            b"Content-Length: 0\r\n\r\n"
        )

        self.assertFalse(
            store_response("no-store-test", response)
        )

    def test_private_and_no_cache_not_cached(self):
        for directive in ("private", "no-cache"):
            response = (
                b"HTTP/1.1 200 OK\r\n"
                + f"Cache-Control: {directive}\r\n".encode()
                + b"Content-Length: 0\r\n\r\n"
            )

            with self.subTest(directive=directive):
                self.assertFalse(
                    store_response(f"{directive}-test", response)
                )

    def test_set_cookie_response_not_cached(self):
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Set-Cookie: session=abc\r\n"
            b"Content-Length: 0\r\n\r\n"
        )

        self.assertFalse(
            store_response("cookie-test", response)
        )

    def test_vary_response_not_cached(self):
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Vary: Accept-Encoding\r\n"
            b"Content-Length: 0\r\n\r\n"
        )

        self.assertFalse(
            store_response("vary-test", response)
        )

    def test_invalid_response_not_cached(self):
        self.assertFalse(
            store_response("malformed-test", b"not an HTTP response")
        )

    def test_non_positive_ttl_rejected(self):
        self.assertFalse(
            store_response("zero-ttl-test", self.response, ttl=0)
        )
        self.assertFalse(
            store_response("negative-ttl-test", self.response, ttl=-1)
        )

    def test_lru_eviction(self):
        # Fill the cache to its maximum capacity.
        for i in range(MAX_ENTRIES):
            self.assertTrue(
                store_response(f"lru-{i}", self.response)
            )

        # Refresh the first entry so the second becomes least recently used.
        self.assertEqual(
            get_cached_response("lru-0"), self.response
        )

        self.assertTrue(
            store_response("lru-overflow", self.response)
        )

        self.assertEqual(
            get_cached_response("lru-0"), self.response
        )
        self.assertIsNone(
            get_cached_response("lru-1")
        )
        self.assertEqual(
            get_cached_response("lru-overflow"), self.response
        )

    def test_analytics_statistics(self):
        record_request(False, 0.1)  # Cache miss
        record_request(True, 0.05)  # Cache hit
        analytics.record_blocked_request()
        analytics.record_cached_bytes(123)

        stats = get_stats()

        self.assertEqual(stats["total_requests"], 2)
        self.assertEqual(stats["cache_hits"], 1)
        self.assertEqual(stats["cache_misses"], 1)
        self.assertEqual(stats["cache_hit_ratio"], 50.0)
        self.assertEqual(stats["blocked_requests"], 1)
        self.assertEqual(stats["bytes_served_from_cache"], 123)
        self.assertAlmostEqual(
            stats["average_response_time_ms"], 75.0
        )


if __name__ == "__main__":
    unittest.main()
