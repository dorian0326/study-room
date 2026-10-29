from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app


def test_health_ok():
    resp = TestClient(app).get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "sqlite"
    assert body["timezone"] == "Asia/Shanghai"


def test_server_time_is_utc_plus_8():
    from app.timeutil import now

    assert now().utcoffset() == timedelta(hours=8)


def test_sqlite_pragmas_enabled():
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
