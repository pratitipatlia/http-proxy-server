
import time
import unittest

from member2_cache.cache_manager import (
    get_cached_response,
    store_response,
)


class TestCacheManager(unittest.TestCase):

    def setUp(self):
        self.response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/plain\r\n"
            b"Content-Length: 5\r\n"
            b"\r\n"
            b"Hello"
        )

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


if __name__ == "__main__":
    unittest.main()
