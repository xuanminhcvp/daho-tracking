"""SQLite: mo ket noi, tao bang, ghi nhat ky, sao luu tu dong. Moi request mo mot ket noi rieng (Flask chay threaded)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    note        TEXT DEFAULT '',
    active      INTEGER DEFAULT 1,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    email        TEXT UNIQUE COLLATE NOCASE,   -- NULL = tai khoan khong co email (VD "1 tk uu dai"), ten goi nam o note
    password     TEXT DEFAULT '',
    totp_secret  TEXT DEFAULT '',
    member_id    INTEGER REFERENCES members(id) ON DELETE SET NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    supplier     TEXT DEFAULT '',
    bought_at    TEXT DEFAULT '',
    note         TEXT DEFAULT '',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

-- account_id khong dat khoa ngoai: nhat ky giu nguyen ke ca khi du lieu thay doi
CREATE TABLE IF NOT EXISTS activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    at          TEXT NOT NULL,
    account_id  INTEGER,
    message     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS activity_account ON activity(account_id);
"""

BACKUP_KEEP = 30


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


@contextmanager
def connect():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _migrate(con) -> None:
    # ban dau email la NOT NULL -> bo NOT NULL de luu duoc tai khoan khong co email (SQLite phai dung lai bang)
    info = {r[1]: r for r in con.execute("PRAGMA table_info(accounts)").fetchall()}
    if info.get("email") and info["email"][3]:
        con.execute("PRAGMA foreign_keys = OFF")
        con.execute("ALTER TABLE accounts RENAME TO accounts_old")
        con.executescript(SCHEMA)
        cols = ", ".join(columns(con, "accounts"))
        con.execute(f"INSERT INTO accounts ({cols}) SELECT {cols} FROM accounts_old")
        con.execute("DROP TABLE accounts_old")
        con.execute("PRAGMA foreign_keys = ON")


def init() -> None:
    with connect() as con:
        con.executescript(SCHEMA)
    if config.DB_PATH.exists():
        backup()   # chep truoc khi doi cau truc bang
    with connect() as con:
        _migrate(con)


def columns(con, table: str) -> list[str]:
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]


def rows(con, sql: str, args=()) -> list[dict]:
    return [dict(r) for r in con.execute(sql, args).fetchall()]


def row(con, sql: str, args=()) -> dict | None:
    r = con.execute(sql, args).fetchone()
    return dict(r) if r else None


def log(con, message: str, account_id: int | None = None) -> None:
    con.execute("INSERT INTO activity (at, account_id, message) VALUES (?, ?, ?)", (now(), account_id, message))


def backup_dir():
    d = config.DATA_DIR / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def backup() -> None:
    """Chep DB ra backups/tasklead-YYYY-MM-DD.db (moi ngay mot file, ghi de trong ngay), giu BACKUP_KEEP ngay gan nhat."""
    if not config.DB_PATH.exists():
        return
    d = backup_dir()
    dst = sqlite3.connect(d / f"tasklead-{today()}.db")
    src = sqlite3.connect(config.DB_PATH)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    for old in sorted(d.glob("tasklead-*.db"))[:-BACKUP_KEEP]:
        old.unlink()
