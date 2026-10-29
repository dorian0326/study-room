"""#9：备份、恢复与运行状态。"""

import pytest
from sqlalchemy import func, select

from app.config import get_settings
from app.metrics import METRICS
from app.models import User
from app.services.backup import create_backup, list_backups, restore_backup


@pytest.fixture(autouse=True)
def _backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "backup_dir", str(tmp_path / "bk"))
    monkeypatch.setattr(get_settings(), "backup_keep", 3)


def test_backup_api_ops_only(client, make_user, login):
    make_user("A0000001", roles=("admin",))
    make_user("O0000001", roles=("ops",))
    assert (
        client.post("/api/ops/backups", headers=login("A0000001", "secret123")).status_code == 403
    )
    ops = login("O0000001", "secret123")
    r = client.post("/api/ops/backups", headers=ops)
    assert r.status_code == 201 and r.json()["size_bytes"] > 0
    names = [b["name"] for b in client.get("/api/ops/backups", headers=ops).json()]
    assert names == [r.json()["name"]]
    logs = client.get("/api/ops/audit-logs", headers=ops, params={"target_type": "backup"}).json()
    assert logs["total"] == 1


def test_backup_rotation_and_restore(api_db, make_user):
    make_user("20260001")
    eng = api_db.kw["bind"]
    first = create_backup(eng)
    make_user("20260002")
    for _ in range(3):
        create_backup(eng)
    assert len(list_backups()) == 3 and first not in list_backups()

    with api_db() as s:
        assert s.scalar(select(func.count()).select_from(User)) == 2
    keep = list_backups()[-1]
    make_user("20260003")
    restore_backup(eng, keep.name)
    with api_db() as s:
        assert s.scalar(select(func.count()).select_from(User)) == 2
    with pytest.raises(FileNotFoundError):
        restore_backup(eng, "../nope.db")


def test_status(client, make_user, login):
    make_user("O0000001", roles=("ops",))
    make_user("A0000001", roles=("admin",))
    METRICS.reset()
    ops = login("O0000001", "secret123")
    assert client.get("/api/ops/status", headers=login("A0000001", "secret123")).status_code == 403
    data = client.get("/api/ops/status", headers=ops).json()
    assert data["users"] == 2 and data["active_sessions"] == 2
    assert data["database"]["size_bytes"] > 0 and data["latest_backup"] is None
    assert data["requests"]["requests"] == 3 and data["requests"]["by_status"]["4xx"] == 1
