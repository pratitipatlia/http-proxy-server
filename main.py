from member1_proxy.proxy_server import ProxyServer
from config import HOST, PORT


def main():
    server = ProxyServer(HOST, PORT)

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nProxy server stopped.")
    finally:
        server.stop()


if __name__ == "__main__":
    main()