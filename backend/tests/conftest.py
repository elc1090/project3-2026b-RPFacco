import importlib

import pytest

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

    import app as server
    server = importlib.reload(server)
    server.app.testing = True

    return server.app.test_client()
