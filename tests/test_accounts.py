from app import totp

SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"   # RFC 6238 vector

SHEET = (
    "a1@gmail.com|pass1 |" + SECRET + "\tAn\n"
    "A2@googlemail.com |pass2|JBSW Y3DP EHPK 3PXP\tBình\n"
    "1 tk ưu đãi\t- Bình\n"
    "khongphaiemail|pass\tAn\n"
    "a1@gmail.com|khac|" + SECRET + "\tBình\n"
    "a3+x@gmail.com|pass3|SAI-MA-@@\t An  \n"
    "\n"
    "a4@gmail.com|pass4\n"
)


def test_totp_rfc_vector():
    assert totp.code(SECRET, at=59)[0] == "287082"
    assert totp.code(SECRET, at=59)[1] == 1
    assert totp.is_valid("jbsw y3dp ehpk 3pxp") and not totp.is_valid("SAI-MA-@@")


def test_paste_adds_immediately(client):
    r = client.post("/api/gpt/import", json={"text": SHEET, "supplier": "Shop X"}).get_json()
    assert r["added"] == 5
    assert r["invalid_lines"] == ["khongphaiemail|pass\tAn"]
    assert r["duplicate"] == ["a1@gmail.com"] and r["existing"] == []
    assert r["bad_2fa"] == ["a3+x@gmail.com"]
    accs = {a["email"]: a for a in client.get("/api/gpt/accounts").get_json()}
    assert accs["a1@gmail.com"]["password"] == "pass1" and accs["a1@gmail.com"]["member_name"] == "An"
    assert accs["A2@googlemail.com"]["totp_secret"] == "JBSWY3DPEHPK3PXP"
    assert accs["a3+x@gmail.com"]["member_name"] == "An"                # khoang trang trong ten bi bo
    assert accs["a4@gmail.com"]["member_id"] is None                     # khong co ten -> chua phan
    assert accs["a1@gmail.com"]["supplier"] == "Shop X"
    assert {m["name"] for m in client.get("/api/gpt/members").get_json()} == {"An", "Bình"}
    promo = next(a for a in accs.values() if a["email"] is None)
    assert promo["note"] == "1 tk ưu đãi" and promo["member_name"] == "Bình"   # "- Bình" -> "Bình"

    # dan lai: email da co thi bo qua, khong sua gi
    r = client.post("/api/gpt/import", json={"text": "a1@gmail.com|moi|x\tBình\nnew@g.com|p"}).get_json()
    assert r["added"] == 1 and r["existing"] == ["a1@gmail.com"]
    a1 = next(a for a in client.get("/api/gpt/accounts").get_json() if a["email"] == "a1@gmail.com")
    assert a1["password"] == "pass1" and a1["member_name"] == "An"


def test_paste_ignore_members(client):
    r = client.post("/api/gpt/import", json={"text": "x@g.com|p|\tAn", "ignore_members": True}).get_json()
    assert r["added"] == 1
    assert client.get("/api/gpt/accounts").get_json()[0]["member_id"] is None
    assert client.get("/api/gpt/members").get_json() == []
    assert client.post("/api/gpt/import", json={"text": "  \n"}).status_code == 400


def test_paste_date_default_and_custom(client):
    import app.db
    client.post("/api/gpt/import", json={"text": "d1@g.com|p"})
    client.post("/api/gpt/import", json={"text": "d2@g.com|p", "bought_at": "2026-10-01"})
    assert client.post("/api/gpt/import", json={"text": "d3@g.com|p", "bought_at": "01/10/2026"}).status_code == 400
    accs = {a["email"]: a for a in client.get("/api/gpt/accounts").get_json()}
    assert accs["d1@g.com"]["bought_at"] == app.db.today() and accs["d2@g.com"]["bought_at"] == "2026-10-01"
    client.put(f"/api/gpt/accounts/{accs['d2@g.com']['id']}", json={"bought_at": "2026-10-05"})
    log = [x["message"] for x in client.get(f"/api/gpt/accounts/{accs['d2@g.com']['id']}/log").get_json()]
    assert log[0] == "d2@g.com: sửa ngày"


def _add(c, email, **kw):
    r = c.post("/api/gpt/accounts", json={"email": email, **kw})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["id"]


def _member(c, name):
    return c.post("/api/gpt/members", json={"name": name}).get_json()["id"]


def test_account_soft_then_purge(client):
    an = _member(client, "An")
    id_ = _add(client, "x@gmail.com", password="p", member_id=an)
    assert client.post("/api/gpt/accounts", json={"email": "X@gmail.com"}).status_code == 400
    assert client.post("/api/gpt/accounts", json={"email": "khongphaiemail"}).status_code == 400
    assert client.put(f"/api/gpt/accounts/{id_}", json={"status": "deleted"}).status_code == 200
    a = client.get("/api/gpt/accounts").get_json()[0]
    assert a["status"] == "deleted" and a["password"] == "p"
    log = [x["message"] for x in client.get(f"/api/gpt/accounts/{id_}/log").get_json()]
    assert log[0] == "x@gmail.com: Hoạt động → Đã xoá"
    keep = _add(client, "y@gmail.com")
    assert client.delete(f"/api/gpt/accounts/{keep}").status_code == 400        # chua o Da xoa -> khong xoa han
    assert client.delete(f"/api/gpt/accounts/{id_}").status_code == 200
    assert [x["email"] for x in client.get("/api/gpt/accounts").get_json()] == ["y@gmail.com"]
    log = [x["message"] for x in client.get(f"/api/gpt/accounts/{id_}/log").get_json()]
    assert log[0] == "Xoá hẳn x@gmail.com (người cầm cuối: An)"                 # nhat ky van giu


def test_bulk_assign_and_status(client):
    an, binh = _member(client, "An"), _member(client, "Bình")
    ids = [_add(client, f"{i}@g.com", member_id=an) for i in range(3)]
    r = client.post("/api/gpt/accounts/bulk", json={"ids": ids[:2], "member_id": binh, "status": "pending"})
    assert r.get_json()["count"] == 2
    accs = {a["id"]: a for a in client.get("/api/gpt/accounts").get_json()}
    assert accs[ids[0]]["member_name"] == "Bình" and accs[ids[0]]["status"] == "pending"
    assert accs[ids[2]]["member_name"] == "An"
    msgs = [x["message"] for x in client.get(f"/api/gpt/accounts/{ids[0]}/log").get_json()]
    assert "0@g.com: An → Bình" in msgs and "0@g.com: Hoạt động → Chờ bảo hành" in msgs
    client.post("/api/gpt/accounts/bulk", json={"ids": [ids[2]], "member_id": None})
    assert next(a for a in client.get("/api/gpt/accounts").get_json() if a["id"] == ids[2])["member_id"] is None


def test_totp_endpoint(client):
    id_ = _add(client, "t@g.com", totp_secret=SECRET)
    r = client.get(f"/api/gpt/accounts/{id_}/totp").get_json()
    assert len(r["code"]) == 6 and 1 <= r["seconds_left"] <= 30
    bad = _add(client, "u@g.com")
    assert client.get(f"/api/gpt/accounts/{bad}/totp").status_code == 400


def test_members_move_and_delete_guard(client):
    an, binh = _member(client, "An"), _member(client, "Bình")
    assert client.post("/api/gpt/members", json={"name": "an"}).status_code == 400
    _add(client, "1@g.com", member_id=an)
    gone = _add(client, "2@g.com", member_id=an, status="deleted")
    assert client.delete(f"/api/gpt/members/{an}").status_code == 400
    r = client.post(f"/api/gpt/members/{an}/move", json={"to_member_id": binh}).get_json()
    assert r["count"] == 1                                    # tai khoan da xoa khong chuyen
    mems = {m["name"]: m for m in client.get("/api/gpt/members").get_json()}
    assert mems["Bình"]["count"] == {"active": 1} and mems["An"]["count"] == {"deleted": 1}
    assert client.delete(f"/api/gpt/members/{an}").status_code == 400     # van con tk da xoa -> phai chon nguoi nhan
    r = client.delete(f"/api/gpt/members/{an}", json={"move_to": None}).get_json()
    assert r["moved"] == 1
    a = next(x for x in client.get("/api/gpt/accounts").get_json() if x["id"] == gone)
    assert a["member_id"] is None and a["status"] == "deleted"          # tai khoan van con
    assert [m["name"] for m in client.get("/api/gpt/members").get_json()] == ["Bình"]
    log = [x["message"] for x in client.get(f"/api/gpt/accounts/{gone}/log").get_json()]
    assert "2@g.com: An → (chưa phân)" in log


def test_auto_backup_after_change(client):
    import app.config
    _add(client, "b@g.com")
    files = list((app.config.DATA_DIR / "backups").glob("tasklead-*.db"))
    assert len(files) == 1
    import sqlite3
    con = sqlite3.connect(files[0])
    assert con.execute("SELECT email FROM accounts").fetchall() == [("b@g.com",)]
    con.close()


def test_account_without_email(client):
    an = _member(client, "Tấn")
    assert client.post("/api/gpt/accounts", json={"email": ""}).status_code == 400
    a = _add(client, "", note="1 tk ưu đãi", member_id=an)
    b = _add(client, "", note="1 tk ưu đãi")                               # nhieu tk khong email van duoc
    client.post("/api/gpt/import", json={"text": "1 tk ưu đãi\t- Tấn\n1 tk ưu đãi"})
    accs = client.get("/api/gpt/accounts").get_json()
    assert len(accs) == 4 and all(x["email"] is None for x in accs)
    client.put(f"/api/gpt/accounts/{b}", json={"status": "pending"})
    log = [x["message"] for x in client.get(f"/api/gpt/accounts/{b}/log").get_json()]
    assert log[0] == "[1 tk ưu đãi]: Hoạt động → Chờ bảo hành"
    client.put(f"/api/gpt/accounts/{a}", json={"email": "that@g.com"})          # sau co email that thi dien vao
    assert next(x for x in client.get("/api/gpt/accounts").get_json() if x["id"] == a)["email"] == "that@g.com"


def test_migrates_old_not_null_email(tmp_path, monkeypatch):
    import sqlite3
    import app.config, app.db
    old = app.db.SCHEMA.replace("    email        TEXT UNIQUE COLLATE NOCASE,", "    email        TEXT NOT NULL UNIQUE COLLATE NOCASE,")
    assert old != app.db.SCHEMA
    monkeypatch.setattr(app.config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(app.config, "DB_PATH", tmp_path / "tasklead.db")
    con = sqlite3.connect(tmp_path / "tasklead.db")
    con.executescript(old)
    con.execute("INSERT INTO members (name, created_at) VALUES ('An', 'x')")
    con.execute("INSERT INTO accounts (email, password, member_id, created_at, updated_at) VALUES ('a@g.com', 'p', 1, 'x', 'x')")
    con.commit()
    con.close()
    app.db.init()
    with app.db.connect() as con:
        assert app.db.rows(con, "SELECT email, password, member_id FROM accounts") == [{"email": "a@g.com", "password": "p", "member_id": 1}]
        con.execute("INSERT INTO accounts (email, note, created_at, updated_at) VALUES (NULL, 'tk', 'x', 'x')")
    assert list((tmp_path / "backups").glob("*.db"))                          # co ban sao truoc khi doi
