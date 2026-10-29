# ruff: noqa: E501
"""#8：登录日志、操作日志查询与保留期清理。"""

from datetime import timedelta

from sqlalchemy import select

from app.models import AuditLog, LoginLog
from app.models.enums import AuditOpType
from app.services.logs import purge_expired
from app.timeutil import now


def _try_login(client, sno, pw):
    return client.post("/api/auth/login", json={"student_no": sno, "password": pw})


def test_login_events_are_logged(client, make_user, login, api_db):
    make_user("20260001")
    _try_login(client, "20260001", "wrong1234")
    _try_login(client, "nobody99", "x")
    h = login("20260001", "secret123")
    client.post("/api/auth/logout", headers=h)
    with api_db() as s:
        rows = [(r.student_no, r.event, r.success, r.reason, r.user_id is not None)
                for r in s.scalars(select(LoginLog).order_by(LoginLog.id))]  # fmt: skip
    assert rows == [
        ("20260001", "login", False, "wrong_password", True),
        ("nobody99", "login", False, "user_not_found", False),
        ("20260001", "login", True, None, True),
        ("20260001", "logout", True, None, True),
    ]


def test_login_logs_only_for_ops(client, make_user, login):
    make_user("O0000001", roles=("ops",))
    make_user("A0000001", roles=("admin",))
    _try_login(client, "O0000001", "bad12345")
    ops = login("O0000001", "secret123")
    assert (
        client.get("/api/ops/login-logs", headers=login("A0000001", "secret123")).status_code == 403
    )

    data = client.get("/api/ops/login-logs", headers=ops, params={"success": False}).json()
    assert data["total"] == 1 and data["items"][0]["reason"] == "wrong_password"
    data = client.get("/api/ops/login-logs", headers=ops, params={"student_no": "A0000001"}).json()
    assert data["total"] == 1
    future = (now() + timedelta(hours=1)).isoformat()
    assert (
        client.get("/api/ops/login-logs", headers=ops, params={"start": future}).json()["total"]
        == 0
    )


def test_audit_logs_query_filters(client, make_user, login):
    make_user("20260001")
    make_user("A0000001", roles=("admin",))
    make_user("O0000001", roles=("ops",))
    admin = login("A0000001", "secret123")
    user = login("20260001", "secret123")
    assert client.get("/api/ops/audit-logs", headers=user).status_code == 403
    client.post("/api/admin/rooms", headers=admin, json={"name": "301"})
    uid = client.get("/api/admin/users", headers=admin, params={"q": "20260001"}).json()["items"][
        0
    ]["id"]
    client.put(f"/api/admin/users/{uid}/roles", headers=admin, json={"roles": ["user", "ops"]})
    for who in (admin, login("O0000001", "secret123")):  # PERM-025 管理员与运维均可查
        data = client.get("/api/ops/audit-logs", headers=who).json()
        assert data["total"] == 2
    data = client.get(
        "/api/ops/audit-logs", headers=admin, params={"op_type": "permission_change"}
    ).json()
    assert data["total"] == 1 and data["items"][0]["operator_student_no"] == "A0000001"
    data = client.get("/api/ops/audit-logs", headers=admin, params={"operator": "O0000001"}).json()
    assert data["total"] == 0
    data = client.get(
        "/api/ops/audit-logs", headers=admin, params={"target_type": "study_room", "size": 1}
    ).json()
    assert data["total"] == 1 and len(data["items"]) == 1


def test_purge_expired_logs(api_db):
    old = now() - timedelta(days=200)
    with api_db() as s:
        s.add_all([
            AuditLog(op_type=AuditOpType.ADMIN_ACTION, target_type="x", occurred_at=old),
            AuditLog(op_type=AuditOpType.ADMIN_ACTION, target_type="x", occurred_at=now()),
            LoginLog(student_no="a", event="login", success=True, occurred_at=old),
        ])  # fmt: skip
        s.commit()
        assert purge_expired(s) == {"audit_logs": 1, "login_logs": 1}
        assert s.scalar(select(AuditLog.target_type)) == "x"
