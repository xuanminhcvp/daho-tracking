import importlib

import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKLEAD_DATA_DIR", str(tmp_path / "a"))
    monkeypatch.setenv("TASKLEAD_EXPORT_DIR", str(tmp_path / "out"))
    import app.config, app.db, app.main
    importlib.reload(app.config)
    importlib.reload(app.db)
    app.db.init()

    def use_machine(name):
        d = tmp_path / name
        d.mkdir(exist_ok=True)
        monkeypatch.setattr(app.config, "DATA_DIR", d)
        monkeypatch.setattr(app.config, "DB_PATH", d / "tasklead.db")
        app.db.init()

    return app.main.app.test_client(), use_machine


@pytest.fixture()
def client(env):
    return env[0]
