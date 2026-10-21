"""Xuat / nhap du lieu CHUYEN MAY (cung y tuong file .nxmx cua NXM DZS1TG).

File .tlx:
  - khong mat khau: file zip thuong (manifest.json, data.json);
  - co mat khau: b"TLX1E" + salt(16) + nonce(12) + AES-256-GCM(zip), khoa = scrypt(mat khau, salt).
Ben trong co MAT KHAU va MA 2FA cua tai khoan -> NEN dat mat khau.

Nhap = gop vao du lieu dang co, khong xoa gi:
  - thanh vien khop theo ten;
  - tai khoan khop theo email -> nguoi dung chon ghi de hay giu ban tren may; tai khoan moi them vao;
  - nhat ky duoc nhap them, bo dong trung.
"""
from __future__ import annotations

import io
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from flask import Blueprint, jsonify, request

from . import db
from .version import VERSION

bp = Blueprint("transfer", __name__, url_prefix="/api/transfer")

FORMAT = "tasklead-chuyen-may"
FORMAT_VERSION = 2
MAGIC = b"TLX1E"
TABLES = ("members", "accounts", "activity")
MAX_FILE = 50 * 1024 * 1024
PENDING_TTL = 30 * 60

_pending: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()
_last_export: dict[str, str] = {}


class TransferError(Exception):
    def __init__(self, msg: str, need_password: bool = False):
        super().__init__(msg)
        self.need_password = need_password


@bp.errorhandler(TransferError)
def _err(e):
    return jsonify({"error": str(e), "need_password": e.need_password}), 400


# ---------- dong goi ----------

def _key(password: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1).derive(password.encode("utf-8"))


def encrypt(raw: bytes, password: str) -> bytes:
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    return MAGIC + salt + nonce + AESGCM(_key(password, salt)).encrypt(nonce, raw, MAGIC)


def decrypt(blob: bytes, password: str) -> bytes:
    if not password:
        raise TransferError("File này có mật khẩu — nhập mật khẩu để mở", need_password=True)
    salt, nonce, ct = blob[5:21], blob[21:33], blob[33:]
    try:
        return AESGCM(_key(password, salt)).decrypt(nonce, ct, MAGIC)
    except InvalidTag:
        raise TransferError("Sai mật khẩu (hoặc file bị hỏng)", need_password=True)


def build_package(password: str = "") -> tuple[bytes, dict]:
    with db.connect() as con:
        data = {t: db.rows(con, f"SELECT * FROM {t}") for t in TABLES}
    counts = {t: len(v) for t, v in data.items()}
    manifest = {
        "format": FORMAT, "version": FORMAT_VERSION, "app_version": VERSION,
        "exported_at": db.now(), "machine": os.uname().nodename if hasattr(os, "uname") else "", "counts": counts,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
        z.writestr("data.json", json.dumps(data, ensure_ascii=False))
    raw = buf.getvalue()
    return (encrypt(raw, password) if password else raw), manifest


def read_package(blob: bytes, password: str = "") -> tuple[dict, dict]:
    if blob.startswith(MAGIC):
        blob = decrypt(blob, password)
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            manifest = json.loads(z.read("manifest.json"))
            data = json.loads(z.read("data.json"))
    except (zipfile.BadZipFile, KeyError, ValueError):
        raise TransferError("Không phải file chuyển máy của Task Lead")
    if manifest.get("format") != FORMAT:
        raise TransferError("Không phải file chuyển máy của Task Lead")
    if manifest.get("version", 0) != FORMAT_VERSION:
        raise TransferError("File tạo từ phiên bản app khác — cập nhật app ở cả hai máy cho giống nhau")
    for t in TABLES:
        if not isinstance(data.get(t, []), list):
            raise TransferError("File bị hỏng")
        data.setdefault(t, [])
    return manifest, data


# ---------- gop du lieu ----------

def _lower(s) -> str:
    return (s or "").strip().lower()


def account_key(a: dict) -> str:
    """Email; tai khoan khong co email thi khop theo luc tao + ghi chu."""
    if a.get("email"):
        return _lower(a["email"])
    return f"~{a.get('created_at')}|{a.get('note') or ''}"


def _fmt(v) -> str:
    return "" if v is None else str(v)


def plan(data: dict) -> dict:
    with db.connect() as con:
        local = {account_key(a): a for a in db.rows(
            con, "SELECT a.*, m.name AS member_name FROM accounts a LEFT JOIN members m ON m.id = a.member_id")}
        known = {_lower(m["name"]) for m in db.rows(con, "SELECT name FROM members")}
    names = {m["id"]: m["name"] for m in data["members"]}
    accounts = []
    for a in data["accounts"]:
        k = account_key(a)
        loc = local.get(k)
        diff = []
        if loc:
            if loc["password"] != a.get("password"):
                diff.append("mật khẩu")
            if loc["totp_secret"] != a.get("totp_secret"):
                diff.append("mã 2FA")
            if _lower(loc["member_name"]) != _lower(names.get(a.get("member_id"))):
                diff.append(f"người dùng: {loc['member_name'] or '(chưa phân)'} → {names.get(a.get('member_id')) or '(chưa phân)'}")
            if loc["status"] != a.get("status"):
                diff.append(f"trạng thái: {loc['status']} → {a.get('status')}")
            if _fmt(loc["note"]) != _fmt(a.get("note")):
                diff.append("ghi chú")
        accounts.append({
            "key": k, "email": a.get("email") or f"[{a.get('note') or 'không có email'}]", "exists": bool(loc), "diff": diff,
            "local_updated": loc["updated_at"] if loc else "", "incoming_updated": a.get("updated_at", ""),
        })
    matched = sum(1 for m in data["members"] if _lower(m["name"]) in known)
    return {
        "accounts": accounts,
        "members": {"new": len(data["members"]) - matched, "matched": matched},
        "counts": {t: len(data[t]) for t in TABLES},
    }


def _insert(con, table: str, row: dict, cols: set) -> int:
    row = {k: v for k, v in row.items() if k in cols and k != "id"}
    keys = list(row)
    return con.execute(
        f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})", [row[k] for k in keys]
    ).lastrowid


def apply(data: dict, overwrite: set[str]) -> dict:
    out = {"members_added": 0, "accounts_added": 0, "accounts_updated": 0, "accounts_skipped": 0, "log": 0}
    with db.connect() as con:
        cols = {t: set(db.columns(con, t)) for t in TABLES}

        members = {_lower(m["name"]): m["id"] for m in db.rows(con, "SELECT id, name FROM members")}
        mem_map: dict[int, int] = {}
        for m in data["members"]:
            k = _lower(m["name"])
            if k not in members:
                members[k] = _insert(con, "members", m, cols["members"])
                out["members_added"] += 1
            mem_map[m["id"]] = members[k]

        local = {account_key(a): a["id"] for a in db.rows(con, "SELECT id, email, created_at, note FROM accounts")}
        acc_map: dict[int, int] = {}
        for a in data["accounts"]:
            row = dict(a, member_id=mem_map.get(a.get("member_id")))
            k = account_key(a)
            if k in local:
                acc_map[a["id"]] = local[k]
                if k not in overwrite:
                    out["accounts_skipped"] += 1
                    continue
                upd = {c: v for c, v in row.items() if c in cols["accounts"] and c not in ("id", "created_at", "email")}
                con.execute(f"UPDATE accounts SET {', '.join(c + ' = ?' for c in upd)} WHERE id = ?", [*upd.values(), local[k]])
                out["accounts_updated"] += 1
            else:
                local[k] = acc_map[a["id"]] = _insert(con, "accounts", row, cols["accounts"])
                out["accounts_added"] += 1

        for e in data["activity"]:
            aid = acc_map.get(e.get("account_id"))
            if not con.execute("SELECT 1 FROM activity WHERE at = ? AND message = ?", (e.get("at"), e.get("message"))).fetchone():
                _insert(con, "activity", dict(e, account_id=aid), cols["activity"])
                out["log"] += 1

        db.log(con, f"Nhập file chuyển máy: +{out['accounts_added']} tài khoản, ghi đè {out['accounts_updated']}, "
                    f"giữ nguyên {out['accounts_skipped']}, +{out['members_added']} thành viên")
    return out


# ---------- API ----------

def export_dir() -> Path:
    d = Path(os.environ.get("TASKLEAD_EXPORT_DIR") or Path.home() / "Downloads")
    d.mkdir(parents=True, exist_ok=True)
    return d


@bp.post("/export")
def api_export():
    body = request.get_json(silent=True) or {}
    password = body.get("password") or ""
    if password and len(password) < 4:
        raise TransferError("Mật khẩu tối thiểu 4 ký tự")
    blob, manifest = build_package(password)
    name = f"TaskLead-chuyen-may-{datetime.now():%Y%m%d-%H%M%S}.tlx"
    path = export_dir() / name
    path.write_bytes(blob)
    _last_export["path"] = str(path)
    with db.connect() as con:
        db.log(con, f"Xuất file chuyển máy {name}" + (" (có mật khẩu)" if password else ""))
    return jsonify({"path": str(path), "name": name, "encrypted": bool(password), "counts": manifest["counts"]})


@bp.post("/reveal")
def api_reveal():
    """Mo Finder tai file vua xuat (chi file nay, khong nhan duong dan tuy y)."""
    path = _last_export.get("path")
    if not path or not Path(path).exists():
        raise TransferError("Không tìm thấy file vừa xuất")
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", path])
    elif os.name == "nt":
        subprocess.Popen(["explorer", "/select,", path])
    return jsonify({"ok": True})


def _gc_pending() -> None:
    now = time.time()
    for k in [k for k, (t, _) in _pending.items() if now - t > PENDING_TTL]:
        _pending.pop(k, None)


@bp.post("/preview")
def api_preview():
    f = request.files.get("file")
    if f is None:
        raise TransferError("Chọn file .tlx")
    blob = f.read(MAX_FILE + 1)
    if len(blob) > MAX_FILE:
        raise TransferError("File quá lớn")
    manifest, data = read_package(blob, request.form.get("password") or "")
    token = secrets.token_urlsafe(16)
    with _lock:
        _gc_pending()
        _pending[token] = (time.time(), data)
    return jsonify({"token": token, "manifest": manifest, **plan(data)})


@bp.post("/apply")
def api_apply():
    body = request.get_json(silent=True) or {}
    with _lock:
        item = _pending.pop(body.get("token") or "", None)
    if item is None:
        raise TransferError("Phiên nhập đã hết hạn — chọn lại file")
    overwrite = set(body.get("overwrite") or [])
    return jsonify({"ok": True, **apply(item[1], overwrite)})
