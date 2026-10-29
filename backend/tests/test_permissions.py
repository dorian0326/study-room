"""#7：三类角色权限、账户状态、角色变更留痕。"""

import json

from sqlalchemy import select

from app.models import AuditLog, Permission, Role
from app.permissions import PERMISSIONS


def test_db_permission_matrix_matches_code(api_db):
    with api_db() as s:
        db = {
            p.code: sorted(
                r.name for r in s.scalars(select(Role).where(Role.permissions.any(id=p.id)))
            )
            for p in s.scalars(select(Permission))
        }
    assert db == {c: sorted(v[3]) for c, v in PERMISSIONS.items()}


def test_me_lists_permissions(client, make_user, login):
    make_user("20260001", roles=("ops",))
    me = client.get("/api/auth/me", headers=login("20260001", "secret123")).json()
    assert "system_log:read" in me["permissions"]
    assert "room:manage" not in me["permissions"]


def test_only_admin_can_manage_users(client, make_user, login):
    make_user("20260001")
    make_user("20260002", roles=("ops",))
    make_user("A0000001", roles=("admin",))
    for sno, code in [("20260001", 403), ("20260002", 403), ("A0000001", 200)]:
        r = client.get("/api/admin/users", headers=login(sno, "secret123"))
        assert r.status_code == code
    assert client.get("/api/admin/users").status_code == 401


def test_admin_promotes_user_and_change_is_logged(client, make_user, login, api_db):
    make_user("20260001")
    make_user("A0000001", roles=("admin",))
    h = login("A0000001", "secret123")
    users = client.get("/api/admin/users", headers=h, params={"q": "2026"}).json()
    assert users["total"] == 1
    uid = users["items"][0]["id"]

    r = client.put(f"/api/admin/users/{uid}/roles", headers=h, json={"roles": ["user", "ops"]})
    assert r.status_code == 200 and r.json()["roles"] == ["ops", "user"]
    with api_db() as s:
        log = s.scalar(select(AuditLog))
    assert log.op_type == "permission_change" and log.target_id == str(uid)
    assert json.loads(log.before_value) == {"roles": ["user"]}
    assert json.loads(log.after_value) == {"roles": ["ops", "user"]}
    # 新角色立即生效
    me = client.get("/api/auth/me", headers=login("20260001", "secret123")).json()
    assert "system_log:read" in me["permissions"]


def test_admin_cannot_demote_or_disable_self(client, make_user, login):
    make_user("A0000001", roles=("admin",))
    h = login("A0000001", "secret123")
    uid = client.get("/api/auth/me", headers=h).json()["id"]
    r = client.put(f"/api/admin/users/{uid}/roles", headers=h, json={"roles": ["user"]})
    assert r.status_code == 400
    r = client.patch(f"/api/admin/users/{uid}/status", headers=h, json={"status": "disabled"})
    assert r.status_code == 400


def test_disable_account_logs_out_and_blocks_login(client, make_user, login):
    make_user("20260001")
    make_user("A0000001", roles=("admin",))
    admin = login("A0000001", "secret123")
    user = login("20260001", "secret123")
    uid = client.get("/api/auth/me", headers=user).json()["id"]

    r = client.patch(f"/api/admin/users/{uid}/status", headers=admin, json={"status": "disabled"})
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=user).status_code == 401
    r = client.post("/api/auth/login", json={"student_no": "20260001", "password": "secret123"})
    assert r.status_code == 403
    r = client.patch(f"/api/admin/users/{uid}/status", headers=admin, json={"status": "normal"})
    assert login("20260001", "secret123")


def test_admin_issues_reset_code(client, make_user, login):
    make_user("20260001")
    make_user("A0000001", roles=("admin",))
    admin = login("A0000001", "secret123")
    uid = client.get("/api/admin/users", headers=admin, params={"role": "user"}).json()["items"][0][
        "id"
    ]
    code = client.post(f"/api/admin/users/{uid}/reset-code", headers=admin).json()["reset_code"]
    r = client.post(
        "/api/auth/reset-password",
        json={"student_no": "20260001", "reset_code": code, "new_password": "brandnew1"},
    )
    assert r.status_code == 204
    assert login("20260001", "brandnew1")


def test_cli_create_admin(monkeypatch, api_db, client, login):
    import app.cli as cli

    monkeypatch.setattr(cli, "SessionLocal", api_db)
    assert cli.main(["create-user", "--student-no", "A0000009", "--name", "管理员",
                     "--role", "admin", "--password", "adminpw123"]) == 0  # fmt: skip
    me = client.get("/api/auth/me", headers=login("A0000009", "adminpw123")).json()
    assert me["roles"] == ["admin"]
