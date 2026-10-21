"""Cua so app (pywebview: WKWebView tren Mac) tro toi UI web tai 127.0.0.1 — cung kieu NXM DZS1TG."""
from __future__ import annotations

import os
import socket
import threading
import time
import traceback

from app.main import HOST, app
import app.main as app_main


def _wait_port(port, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection((HOST, port), 0.4):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def main() -> None:
    try:
        port = app_main.pick_free_port(int(os.environ.get("TASKLEAD_PORT") or app_main.PORT))
        app_main.PORT = port
        threading.Thread(target=lambda: app.run(host=HOST, port=port, threaded=True, use_reloader=False), daemon=True).start()
        if not _wait_port(port):
            raise RuntimeError(f"Server khong mo duoc cong {port}")
        if os.environ.get("TASKLEAD_NO_WINDOW"):   # chi chay server (kiem thu)
            print(f"TASKLEAD_READY port={port}", flush=True)
            while True:
                time.sleep(3600)
        import webview
        webview.create_window("Task Lead", f"http://{HOST}:{port}/", width=1280, height=840, min_size=(960, 620))
        webview.start()
    except Exception:
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
