"""Module 1: Quan ly tai khoan ChatGPT — tai khoan, thanh vien, nhat ky.

Mot tai khoan = email | mat khau | ma 2FA + nguoi cam + trang thai + ghi chu.
Khong bao gio xoa that tai khoan: "Xoa" chi doi trang thai sang 'deleted' (van tim lai duoc).
Tat ca API nam duoi /api/gpt/...
"""
from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request

from .. import db, totp

bp = Blueprint("chatgpt", __name__, url_prefix="/api/gpt")

STATUS = {
    "active": "Hoạt động",
    "pending": "Chờ bảo hành",
    "warrantied": "Đã bảo hành",
    "refunded": "Đã hoàn tiền",
    "deleted": "Đã xoá",
}
EDITABLE = ("email", "password", "totp_secret", "member_id", "status", "supplier", "bought_at", "note")


class BadRequest(Exception):
    pass


@bp.errorhandler(BadRequest)
def _bad_request(e):
    return jsonify({"error": str(e)}), 400


def _body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest("Dữ liệu gửi lên không hợp lệ")
    return data


def _member_name(con, member_id) -> str:
    if member_id is None:
        return "(chưa phân)"
    r = db.row(con, "SELECT name FROM members WHERE id = ?", (member_id,))
    return r["name"] if r else "(không rõ)"


def _clean_account(data: dict, partial: bool) -> dict:
    out = {}
    for f in EDITABLE:
        if f not in data:
            continue
        v = data[f]
        if f == "member_id":
            if v in ("", None):
                v = None
            else:
                try:
                    v = int(v)
                except (TypeError, ValueError):
                    raise BadRequest("Người dùng không hợp lệ")
        else:
            v = "" if v is None else str(v).strip()
        if f == "email":
            if not v:
                v = None
            elif "@" not in v or " " in v:
                raise BadRequest("Email không hợp lệ")
        elif f == "totp_secret":
            v = totp.normalize(v)
        elif f == "status" and v not in STATUS:
            raise BadRequest("Trạng thái không hợp lệ")
        elif f == "bought_at" and v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise BadRequest("Ngày phải có dạng YYYY-MM-DD")
        out[f] = v
    if not partial and not out.get("email") and not out.get("note"):
        raise BadRequest("Nhập email (hoặc ghi chú nếu tài khoản không có email cụ thể)")
    return out


def label(acc: dict) -> str:
    """Ten goi cua tai khoan trong nhat ky: email, khong co thi dung ghi chu."""
    return acc.get("email") or f"[{acc.get('note') or 'không có email'}]"


def _check_member(con, member_id) -> None:
    if member_id is not None and not db.row(con, "SELECT id FROM members WHERE id = ?", (member_id,)):
        raise BadRequest("Không tìm thấy thành viên")


def _get_account(con, id_: int) -> dict:
    a = db.row(con, "SELECT * FROM accounts WHERE id = ?", (id_,))
    if a is None:
        raise BadRequest("Không tìm thấy tài khoản")
    return a


def _apply_change(con, acc: dict, data: dict) -> None:
    """Cap nhat 1 tai khoan + ghi nhat ky tung thay doi quan trong."""
    changes = {k: v for k, v in data.items() if acc.get(k) != v}
    if not changes:
        return
    if changes.get("email") and db.row(con, "SELECT id FROM accounts WHERE email = ? AND id != ?", (changes["email"], acc["id"])):
        raise BadRequest(f"Email {changes['email']} đã có trong danh sách")
    if "member_id" in changes:
        _check_member(con, changes["member_id"])
    changes["updated_at"] = db.now()
    con.execute(f"UPDATE accounts SET {', '.join(k + ' = ?' for k in changes)} WHERE id = ?", [*changes.values(), acc["id"]])
    email = label({**acc, **changes})
    if "member_id" in changes:
        db.log(con, f"{email}: {_member_name(con, acc['member_id'])} → {_member_name(con, changes['member_id'])}", acc["id"])
    if "status" in changes:
        db.log(con, f"{email}: {STATUS[acc['status']]} → {STATUS[changes['status']]}", acc["id"])
    if "email" in changes:
        db.log(con, f"Đổi email {acc['email'] or '(trống)'} → {changes['email'] or '(trống)'}", acc["id"])
    other = [lbl for k, lbl in (("password", "mật khẩu"), ("totp_secret", "mã 2FA"), ("note", "ghi chú"),
                                ("supplier", "nguồn"), ("bought_at", "ngày")) if k in changes]
    if other:
        db.log(con, f"{email}: sửa {', '.join(other)}", acc["id"])


# ---------- meta ----------

@bp.get("/meta")
def meta():
    return jsonify({"status": STATUS})


# ---------- tai khoan ----------

@bp.get("/accounts")
def list_accounts():
    with db.connect() as con:
        accs = db.rows(
            con,
            """SELECT a.*, m.name AS member_name FROM accounts a LEFT JOIN members m ON m.id = a.member_id
               ORDER BY a.id""",
        )
    for a in accs:
        a["totp_ok"] = totp.is_valid(a["totp_secret"])
    return jsonify(accs)


@bp.post("/accounts")
def create_account():
    data = _clean_account(_body(), partial=False)
    data.setdefault("status", "active")
    data.setdefault("bought_at", db.today())
    data["created_at"] = data["updated_at"] = db.now()
    with db.connect() as con:
        if data.get("email") and db.row(con, "SELECT id FROM accounts WHERE email = ?", (data["email"],)):
            raise BadRequest(f"Email {data['email']} đã có trong danh sách")
        _check_member(con, data.get("member_id"))
        cols = list(data)
        id_ = con.execute(f"INSERT INTO accounts ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                          [data[c] for c in cols]).lastrowid
        db.log(con, f"Thêm {label(data)}" + (f", giao cho {_member_name(con, data.get('member_id'))}" if data.get("member_id") else ""), id_)
    return jsonify({"id": id_}), 201


@bp.put("/accounts/<int:id_>")
def update_account(id_):
    data = _clean_account(_body(), partial=True)
    with db.connect() as con:
        _apply_change(con, _get_account(con, id_), data)
    return jsonify({"ok": True})


@bp.delete("/accounts/<int:id_>")
def purge_account(id_):
    """Xoa han — chi cho tai khoan da o trang thai 'Da xoa' (buoc 2, co hoi xac nhan o giao dien)."""
    with db.connect() as con:
        acc = _get_account(con, id_)
        if acc["status"] != "deleted":
            raise BadRequest("Chỉ xoá hẳn được tài khoản đã ở mục Đã xoá")
        con.execute("DELETE FROM accounts WHERE id = ?", (id_,))
        db.log(con, f"Xoá hẳn {label(acc)} (người cầm cuối: {_member_name(con, acc['member_id'])})", id_)
    return jsonify({"ok": True})


@bp.post("/accounts/bulk")
def bulk_update():
    """Nhieu tai khoan cung luc: giao cho 1 nguoi va/hoac doi trang thai."""
    body = _body()
    ids = body.get("ids") or []
    if not isinstance(ids, list) or not ids:
        raise BadRequest("Chưa chọn tài khoản nào")
    data = _clean_account({k: body[k] for k in ("member_id", "status") if k in body}, partial=True)
    if not data:
        raise BadRequest("Chưa chọn thay đổi")
    with db.connect() as con:
        for id_ in ids:
            _apply_change(con, _get_account(con, int(id_)), data)
    return jsonify({"ok": True, "count": len(ids)})


@bp.get("/accounts/<int:id_>/totp")
def account_totp(id_):
    with db.connect() as con:
        a = _get_account(con, id_)
    if not totp.is_valid(a["totp_secret"]):
        raise BadRequest("Tài khoản không có mã 2FA hợp lệ")
    code, left = totp.code(a["totp_secret"])
    return jsonify({"code": code, "seconds_left": left})


@bp.get("/accounts/<int:id_>/log")
def account_log(id_):
    with db.connect() as con:
        return jsonify(db.rows(con, "SELECT * FROM activity WHERE account_id = ? ORDER BY id DESC", (id_,)))


# ---------- nhap tu sheet ----------

def parse_lines(text: str) -> list[dict]:
    """Moi dong: email|mat khau|ma 2FA<TAB>ten nguoi dung (dung dinh dang copy tu Google Sheet).
    Cung nhan email|mat khau|ma 2FA|ten nguoi dung."""
    out = []
    for n, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        cells = line.split("\t")
        creds, member = cells[0], (cells[1] if len(cells) > 1 else "")
        parts = [p.strip() for p in creds.split("|")]
        if not member and len(parts) >= 4:
            member = parts[3]
        member = " ".join(member.split()).lstrip("-–—•* ").strip()
        email = parts[0] if parts else ""
        if len(parts) == 1 and "@" not in email:
            # dong khong co email cu the, VD "1 tk uu dai" -> luu thanh tai khoan khong email, chu nam o ghi chu
            out.append({"line": n, "raw": raw, "email": None, "note": " ".join(email.split()),
                        "password": "", "totp_secret": "", "member": member, "problem": ""})
            continue
        item = {
            "line": n, "raw": raw, "email": email,
            "password": parts[1] if len(parts) > 1 else "",
            "totp_secret": totp.normalize(parts[2]) if len(parts) > 2 else "",
            "member": member, "problem": "", "note": "",
        }
        if "@" not in email or " " in email:
            item["problem"] = "Không đọc được email"
        elif item["totp_secret"] and not totp.is_valid(item["totp_secret"]):
            item["warning"] = "Mã 2FA không hợp lệ"
        out.append(item)
    return out


@bp.post("/import")
def import_paste():
    """Dan tu sheet -> them ngay. Email da co thi bo qua (khong sua gi); khong co ten nguoi dung -> 'chua phan'."""
    body = _body()
    ignore_members = bool(body.get("ignore_members"))
    supplier = (body.get("supplier") or "").strip()
    bought_at = (body.get("bought_at") or "").strip() or db.today()
    try:
        datetime.strptime(bought_at, "%Y-%m-%d")
    except ValueError:
        raise BadRequest("Ngày phải có dạng YYYY-MM-DD")
    items = parse_lines(body.get("text", ""))
    if not items:
        raise BadRequest("Danh sách trống")
    added, existing, dup, invalid, bad_2fa = 0, [], [], [], []
    with db.connect() as con:
        known = {a["email"].lower() for a in db.rows(con, "SELECT email FROM accounts WHERE email IS NOT NULL")}
        members = {m["name"].lower(): m["id"] for m in db.rows(con, "SELECT id, name FROM members")}
        seen = set()
        for it in items:
            if it["problem"]:
                invalid.append(it["raw"].strip())
                continue
            key = (it["email"] or "").lower()
            if key and key in known:
                (dup if key in seen else existing).append(it["email"])
                continue
            name = "" if ignore_members else it["member"]
            mid = None
            if name:
                if name.lower() not in members:
                    members[name.lower()] = con.execute(
                        "INSERT INTO members (name, created_at) VALUES (?, ?)", (name, db.now())).lastrowid
                    db.log(con, f"Thêm thành viên {name}")
                mid = members[name.lower()]
            id_ = con.execute(
                """INSERT INTO accounts (email, password, totp_secret, member_id, status, supplier, bought_at, note,
                   created_at, updated_at) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)""",
                (it["email"], it["password"], it["totp_secret"], mid, supplier, bought_at, it["note"], db.now(), db.now()),
            ).lastrowid
            db.log(con, f"Thêm {label(it)}" + (f", giao cho {name}" if name else " (chưa phân)"), id_)
            if it.get("warning"):
                bad_2fa.append(it["email"])
            if key:
                known.add(key)
                seen.add(key)
            added += 1
        if added:
            db.log(con, f"Dán từ sheet: +{added} tài khoản")
    return jsonify({"ok": True, "added": added, "existing": existing, "duplicate": dup,
                    "invalid_lines": invalid, "bad_2fa": bad_2fa})


# ---------- thanh vien ----------

@bp.get("/members")
def list_members():
    with db.connect() as con:
        mems = db.rows(con, "SELECT * FROM members ORDER BY active DESC, name COLLATE NOCASE")
        counts = db.rows(con, "SELECT member_id, status, COUNT(*) AS n FROM accounts WHERE member_id IS NOT NULL GROUP BY member_id, status")
    by = {}
    for c in counts:
        by.setdefault(c["member_id"], {})[c["status"]] = c["n"]
    for m in mems:
        m["count"] = by.get(m["id"], {})
    return jsonify(mems)


def _clean_member(data: dict) -> dict:
    out = {}
    if "name" in data:
        out["name"] = " ".join(str(data["name"] or "").split())
        if not out["name"]:
            raise BadRequest("Nhập tên")
    if "note" in data:
        out["note"] = str(data["note"] or "").strip()
    if "active" in data:
        out["active"] = 1 if data["active"] in (1, True, "1", "true") else 0
    return out


@bp.post("/members")
def create_member():
    data = _clean_member(_body())
    if "name" not in data:
        raise BadRequest("Nhập tên")
    with db.connect() as con:
        if db.row(con, "SELECT id FROM members WHERE name = ?", (data["name"],)):
            raise BadRequest(f"Đã có thành viên {data['name']}")
        data["created_at"] = db.now()
        cols = list(data)
        id_ = con.execute(f"INSERT INTO members ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                          [data[c] for c in cols]).lastrowid
        db.log(con, f"Thêm thành viên {data['name']}")
    return jsonify({"id": id_}), 201


@bp.put("/members/<int:id_>")
def update_member(id_):
    data = _clean_member(_body())
    with db.connect() as con:
        old = db.row(con, "SELECT * FROM members WHERE id = ?", (id_,))
        if old is None:
            raise BadRequest("Không tìm thấy thành viên")
        if "name" in data and db.row(con, "SELECT id FROM members WHERE name = ? AND id != ?", (data["name"], id_)):
            raise BadRequest(f"Đã có thành viên {data['name']}")
        if data:
            con.execute(f"UPDATE members SET {', '.join(k + ' = ?' for k in data)} WHERE id = ?", [*data.values(), id_])
        if data.get("name") and data["name"] != old["name"]:
            db.log(con, f"Đổi tên thành viên {old['name']} → {data['name']}")
        if "active" in data and data["active"] != old["active"]:
            db.log(con, f"{'Mở lại' if data['active'] else 'Ngưng'} thành viên {data.get('name', old['name'])}")
    return jsonify({"ok": True})


@bp.post("/members/<int:id_>/move")
def move_accounts(id_):
    """Chuyen het tai khoan (chua xoa) cua mot nguoi sang nguoi khac, hoac ve 'chua phan'."""
    to = _body().get("to_member_id")
    to = None if to in ("", None) else int(to)
    if to == id_:
        raise BadRequest("Chọn người khác")
    with db.connect() as con:
        accs = db.rows(con, "SELECT * FROM accounts WHERE member_id = ? AND status != 'deleted'", (id_,))
        for a in accs:
            _apply_change(con, a, {"member_id": to})
    return jsonify({"ok": True, "count": len(accs)})


@bp.delete("/members/<int:id_>")
def delete_member(id_):
    with db.connect() as con:
        m = db.row(con, "SELECT * FROM members WHERE id = ?", (id_,))
        if m is None:
            raise BadRequest("Không tìm thấy thành viên")
        accs = db.rows(con, "SELECT * FROM accounts WHERE member_id = ?", (id_,))
        body = request.get_json(silent=True) or {}
        if accs and "move_to" not in body:
            raise BadRequest(f"{m['name']} còn {len(accs)} tài khoản — chọn người nhận (hoặc Chưa phân) trước khi xoá")
        to = body.get("move_to")
        to = None if to in ("", None) else int(to)
        if to == id_:
            raise BadRequest("Chọn người khác")
        # chuyen MOI tai khoan (ca da xoa) truoc, de khong tai khoan nao mat dau vet nguoi cam
        for a in accs:
            _apply_change(con, a, {"member_id": to})
        con.execute("DELETE FROM members WHERE id = ?", (id_,))
        db.log(con, f"Xoá thành viên {m['name']}" + (f", chuyển {len(accs)} tài khoản sang {_member_name(con, to)}" if accs else ""))
    return jsonify({"ok": True, "moved": len(accs)})


# ---------- nhat ky ----------

@bp.get("/activity")
def activity():
    q = (request.args.get("q") or "").strip()
    with db.connect() as con:
        if q:
            return jsonify(db.rows(con, "SELECT * FROM activity WHERE message LIKE ? ORDER BY id DESC LIMIT 500", (f"%{q}%",)))
        return jsonify(db.rows(con, "SELECT * FROM activity ORDER BY id DESC LIMIT 500"))
