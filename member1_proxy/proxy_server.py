
import socket
import threading

from config import HOST, PORT
from member1_proxy.http_handler import handle_client


class ProxyServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.client_threads = []

    def start(self):
        """Start the proxy and accept client connections."""

        self.server_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        self.server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(50)
        self.server_socket.settimeout(1)

        self.running = True

        print(f"Proxy running at http://{self.host}:{self.port}")
        print("Press Ctrl+C to stop.")

        try:
            while self.running:
                try:
                    client_socket, client_address = (
                        self.server_socket.accept()
                    )

                    print(f"[CONNECTED] {client_address}")

                    client_thread = threading.Thread(
                        target=handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )

                    self.client_threads.append(client_thread)
                    client_thread.start()

                except socket.timeout:
                    continue

        finally:
            self.stop()

    def stop(self):
        """Stop accepting connections and close the server socket."""

        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass

            self.server_socket = None

        print("Proxy server stopped.")
