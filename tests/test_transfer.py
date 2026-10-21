import io


def _export(c, password=""):
    r = c.post("/api/transfer/export", json={"password": password})
    assert r.status_code == 200, r.get_json()
    with open(r.get_json()["path"], "rb") as f:
        return f.read()


def _preview(c, blob, password=""):
    return c.post("/api/transfer/preview", data={"file": (io.BytesIO(blob), "x.tlx"), "password": password},
                  content_type="multipart/form-data")


def test_roundtrip_encrypted(env):
    c, use = env
    c.post("/api/gpt/import", json={"text": "a@g.com|matkhau123|JBSWY3DPEHPK3PXP\tAn\nb@g.com|pb\tBình\n1 tk ưu đãi\tBình"})
    blob = _export(c, "bimat123")
    assert blob.startswith(b"TLX1E") and b"matkhau123" not in blob and b"a@g.com" not in blob

    use("b")
    r = _preview(c, blob)
    assert r.status_code == 400 and r.get_json()["need_password"]
    assert _preview(c, blob, "sai").get_json()["need_password"]
    p = _preview(c, blob, "bimat123").get_json()
    assert [a["exists"] for a in p["accounts"]] == [False, False, False]
    out = c.post("/api/transfer/apply", json={"token": p["token"]}).get_json()
    assert out["accounts_added"] == 3 and out["members_added"] == 2
    accs = {a["email"]: a for a in c.get("/api/gpt/accounts").get_json()}
    assert accs["a@g.com"]["password"] == "matkhau123" and accs["a@g.com"]["member_name"] == "An"
    assert any("Thêm a@g.com" in x["message"] for x in c.get("/api/gpt/accounts/%d/log" % accs["a@g.com"]["id"]).get_json())
    assert c.post("/api/transfer/apply", json={"token": p["token"]}).status_code == 400   # token dung 1 lan

    p = _preview(c, blob, "bimat123").get_json()
    out = c.post("/api/transfer/apply", json={"token": p["token"], "overwrite": [a["key"] for a in p["accounts"]]}).get_json()
    assert out["accounts_added"] == 0 and out["members_added"] == 0 and out["log"] == 0
    assert len(c.get("/api/gpt/accounts").get_json()) == 3     # tk khong email cung khong bi nhan doi


def test_skip_keeps_local(env):
    c, use = env
    c.post("/api/gpt/accounts", json={"email": "a@g.com", "password": "cu"})
    blob = _export(c)
    use("b")
    c.post("/api/gpt/accounts", json={"email": "A@g.com", "password": "moi"})
    p = _preview(c, blob).get_json()
    assert p["accounts"][0]["exists"] and "mật khẩu" in p["accounts"][0]["diff"]
    out = c.post("/api/transfer/apply", json={"token": p["token"], "overwrite": []}).get_json()
    assert out["accounts_skipped"] == 1
    assert c.get("/api/gpt/accounts").get_json()[0]["password"] == "moi"


def test_rejects_garbage(client):
    r = _preview(client, b"not a zip")
    assert r.status_code == 400 and "Task Lead" in r.get_json()["error"]
