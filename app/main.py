"""Server Flask: giao dien + API. Chay rieng (khong cua so): python -m app.main"""
from __future__ import annotations

import os
import socket
import subprocess
import sys

from flask import Flask, jsonify, render_template, request

from . import config, db, transfer
from .modules import MODULES
from .version import VERSION

HOST = "127.0.0.1"
PORT = 8520

app = Flask(
    __name__,
    template_folder=str(config.RES_DIR / "app" / "templates"),
    static_folder=str(config.RES_DIR / "app" / "static"),
)
app.json.ensure_ascii = False
app.json.sort_keys = False
for bp in MODULES:
    app.register_blueprint(bp)
app.register_blueprint(transfer.bp)

db.init()
db.backup()


@app.get("/")
def index():
    return render_template("index.html", app_title=config.APP_NAME, version=VERSION)


@app.after_request
def _after(resp):
    resp.headers["Cache-Control"] = "no-store"
    # moi lan du lieu thay doi: chep DB ra backups/ (moi ngay mot file)
    if request.method in ("POST", "PUT", "DELETE") and resp.status_code < 400 and request.path.startswith("/api/"):
        try:
            db.backup()
        except Exception as e:  # sao luu loi khong duoc lam hong thao tac chinh
            app.logger.warning("backup failed: %s", e)
    return resp


@app.get("/api/backups")
def backups():
    files = sorted(db.backup_dir().glob("tasklead-*.db"), reverse=True)
    return jsonify({"dir": str(db.backup_dir()), "files": [f.name for f in files]})


@app.post("/api/backups/open")
def open_backups():
    d = str(db.backup_dir())
    if sys.platform == "darwin":
        subprocess.Popen(["open", d])
    elif os.name == "nt":
        subprocess.Popen(["explorer", d])
    return jsonify({"ok": True})


def pick_free_port(start: int) -> int:
    for p in range(start, start + 50):
        with socket.socket() as s:
            if s.connect_ex((HOST, p)) != 0:
                return p
    raise RuntimeError("Không tìm được cổng trống")


if __name__ == "__main__":
    import webbrowser

    port = pick_free_port(PORT)
    webbrowser.open(f"http://{HOST}:{port}/")
    app.run(host=HOST, port=port, threaded=True)
