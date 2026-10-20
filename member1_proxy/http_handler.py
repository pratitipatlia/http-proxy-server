
import socket
import time
from urllib.parse import urlsplit

from config import (
    CONNECTION_TIMEOUT,
    BUFFER_SIZE,
    DEFAULT_CACHE_TTL,
)
from member1_proxy.blocklist import is_blocked
from member2_cache.cache_manager import (
    get_cached_response,
    store_response,
    record_request,
    get_stats,
)


def send_error(client_socket, status_code, message):
    body = (message + "\n").encode("utf-8")

    response = (
        f"HTTP/1.1 {status_code} {message}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8") + body

    client_socket.sendall(response)


def handle_client(client_socket, client_address):
    start_time = time.perf_counter()
    cache_hit = None

    try:
        client_socket.settimeout(CONNECTION_TIMEOUT)

        # Read request headers.
        request_data = b""

        while b"\r\n\r\n" not in request_data:
            chunk = client_socket.recv(BUFFER_SIZE)

            if not chunk:
                return

            request_data += chunk

            if len(request_data) > 65536:
                send_error(
                    client_socket, 431,
                    "Request Header Fields Too Large"
                )
                return

        header_end = request_data.index(b"\r\n\r\n")
        header_bytes = request_data[:header_end]

        lines = header_bytes.decode(
            "iso-8859-1"
        ).split("\r\n")

        parts = lines[0].split(" ", 2)

        if len(parts) != 3:
            send_error(client_socket, 400, "Bad Request")
            return

        method, target, version = parts

        # Initial project version supports GET only.
        if method.upper() != "GET":
            send_error(client_socket, 501, "Not Implemented")
            return

        url = urlsplit(target)

        if url.scheme.lower() != "http" or not url.hostname:
            send_error(client_socket, 400, "Bad Request")
            return

        hostname = url.hostname
        port = url.port or 80

        # Block domains before accessing the origin or cache.
        if is_blocked(hostname):
            print(f"[BLOCKED] {hostname}")
            send_error(client_socket, 403, "Forbidden")
            return

        path = url.path or "/"

        if url.query:
            path += "?" + url.query

        # Parse request headers.
        request_headers = {}

        for line in lines[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                request_headers[name.strip().lower()] = value.strip()

        # Do not cache requests containing user-specific credentials
        # or explicit cache-bypass directives.
        request_cache_control = request_headers.get(
            "cache-control", ""
        ).lower()

        bypass_cache = (
            "authorization" in request_headers
            or "cookie" in request_headers
            or "no-cache" in request_cache_control
            or "no-store" in request_cache_control
            or request_headers.get("pragma", "").lower() == "no-cache"
        )

        # Include host, port, method and path in the cache key.
        cache_key = f"GET http://{hostname.lower()}:{port}{path}"

        if not bypass_cache:
            
            cached_response = get_cached_response(cache_key)

            if cached_response is not None:
                cache_hit = True

                print(f"[CACHE HIT] {hostname}{path}")
                client_socket.sendall(cached_response)
                return

            cache_hit = False
            print(f"[CACHE MISS] {hostname}{path}")
        else:
            print(f"[CACHE BYPASS] {hostname}{path}")

        # Prepare the request to send to the origin.
        excluded_headers = {
            "connection",
            "proxy-connection",
            "keep-alive",
            "transfer-encoding",
            "te",
            "trailer",
            "upgrade",
            "host",
        }

        forwarded_headers = [
            line for line in lines[1:]
            if ":" in line
            and line.split(":", 1)[0].strip().lower()
            not in excluded_headers
        ]

        host_header = (
            hostname if port == 80
            else f"{hostname}:{port}"
        )

        forwarded_headers.append(f"Host: {host_header}")
        forwarded_headers.append("Connection: close")

        origin_request = (
            f"GET {path} HTTP/1.1\r\n"
            + "\r\n".join(forwarded_headers)
            + "\r\n\r\n"
        ).encode("iso-8859-1")

        print(f"[FORWARD] {hostname}{path}")

        # Fetch the full origin response.
        response_parts = []

        with socket.create_connection(
            (hostname, port),
            timeout=CONNECTION_TIMEOUT,
        ) as origin_socket:

            origin_socket.settimeout(CONNECTION_TIMEOUT)
            origin_socket.sendall(origin_request)

            while True:
                response_chunk = origin_socket.recv(BUFFER_SIZE)

                if not response_chunk:
                    break

                response_parts.append(response_chunk)

        response_bytes = b"".join(response_parts)

        if not response_bytes:
            send_error(client_socket, 502, "Bad Gateway")
            return

        # Store only eligible responses. The cache module checks
        # status code and response cache-control headers.
        if not bypass_cache:
            

            stored = store_response(
                cache_key,
                response_bytes,
                ttl=DEFAULT_CACHE_TTL,
            )

            if stored:
                print(f"[CACHE STORED] {hostname}{path}")
            else:
                print(f"[NOT CACHED] {hostname}{path}")

        # Return the response to the client.
        client_socket.sendall(response_bytes)

        elapsed = time.perf_counter() - start_time
        print(
            f"[COMPLETED] {hostname}{path} "
            f"| {len(response_bytes)} bytes "
            f"| {elapsed:.3f}s"
        )

    except (ValueError, UnicodeError):
        try:
            send_error(client_socket, 400, "Bad Request")
        except OSError:
            pass

    except (socket.timeout, TimeoutError):
        try:
            send_error(client_socket, 504, "Gateway Timeout")
        except OSError:
            pass

    except OSError as error:
        print(f"[ERROR] {client_address}: {error}")

        try:
            send_error(client_socket, 502, "Bad Gateway")
        except OSError:
            pass

    
    finally:
        elapsed = time.perf_counter() - start_time

        record_request(cache_hit, elapsed)

        stats = get_stats()

        print("\n========== PROXY STATISTICS ==========")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Cache Hits: {stats['cache_hits']}")
        print(f"Cache Misses: {stats['cache_misses']}")
        print(f"Cache Hit Ratio: {stats['cache_hit_ratio']}%")
        print(
            "Average Response Time: "
            f"{stats['average_response_time_ms']} ms"
        )
        print("======================================\n")

        client_socket.close()

