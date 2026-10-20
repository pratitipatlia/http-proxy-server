
import socket
from urllib.parse import urlsplit

from config import CONNECTION_TIMEOUT, BUFFER_SIZE
from member1_proxy.blocklist import is_blocked


def send_error(client_socket, status_code, message):
    """Send a basic HTTP error response to the client."""
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
    """Handle one client's HTTP request."""

    try:
        client_socket.settimeout(CONNECTION_TIMEOUT)

        # Read the request headers.
        request_data = b""

        while b"\r\n\r\n" not in request_data:
            chunk = client_socket.recv(BUFFER_SIZE)

            if not chunk:
                return

            request_data += chunk

            if len(request_data) > 65536:
                send_error(client_socket, 431, "Request Header Fields Too Large")
                return

        header_end = request_data.index(b"\r\n\r\n")
        header_bytes = request_data[:header_end]
        body_bytes = request_data[header_end + 4:]

        lines = header_bytes.decode("iso-8859-1").split("\r\n")
        method, target, version = lines[0].split(" ", 2)

        # This initial version supports ordinary HTTP GET requests.
        if method.upper() != "GET":
            send_error(client_socket, 501, "Not Implemented")
            return

        # Browsers and curl normally send an absolute URL to a forward proxy.
        url = urlsplit(target)

        if url.scheme.lower() != "http" or not url.hostname:
            send_error(client_socket, 400, "Bad Request")
            return

        hostname = url.hostname
        port = url.port or 80

        # Check the domain before connecting to the origin server.
        if is_blocked(hostname):
            print(f"[BLOCKED] {hostname}")
            send_error(client_socket, 403, "Forbidden")
            return

        path = url.path or "/"

        if url.query:
            path += "?" + url.query

        # Remove hop-by-hop and proxy-specific headers.
        forwarded_headers = []

        for line in lines[1:]:
            if ":" not in line:
                continue

            name, value = line.split(":", 1)
            name_lower = name.strip().lower()

            if name_lower in {
                "connection",
                "proxy-connection",
                "keep-alive",
                "transfer-encoding",
                "te",
                "trailer",
                "upgrade",
                "host",
            }:
                continue

            forwarded_headers.append(line)

        forwarded_headers.append(f"Host: {hostname}" if port == 80
                                 else f"Host: {hostname}:{port}")
        forwarded_headers.append("Connection: close")

        origin_request = (
            f"{method} {path} HTTP/1.1\r\n"
            + "\r\n".join(forwarded_headers)
            + "\r\n\r\n"
        ).encode("iso-8859-1") + body_bytes

        print(f"[FORWARD] {hostname}{path}")

        # Connect to the destination server.
        with socket.create_connection(
            (hostname, port),
            timeout=CONNECTION_TIMEOUT
        ) as origin_socket:

            origin_socket.settimeout(CONNECTION_TIMEOUT)
            origin_socket.sendall(origin_request)

            # Read the response and relay it to the client.
            while True:
                response_chunk = origin_socket.recv(BUFFER_SIZE)

                if not response_chunk:
                    break

                client_socket.sendall(response_chunk)

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
        client_socket.close()
