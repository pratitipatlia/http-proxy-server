
from threading import Thread

from member1_proxy.proxy_server import ProxyServer
from config import HOST, PORT
from dashboard import app


def run_dashboard():
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


def main():
    dashboard_thread = Thread(
        target=run_dashboard,
        daemon=True,
    )
    dashboard_thread.start()

    print("Dashboard: http://127.0.0.1:5000")

    server = ProxyServer(HOST, PORT)

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nProxy server stopped.")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
