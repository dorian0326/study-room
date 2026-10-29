"""#6：注册、登录、注销、改密、重置密码（FR-001~004）。"""

from datetime import timedelta

from sqlalchemy import select

from app.models import AuthSession, User
from app.services import auth as svc
from app.timeutil import now

REG = {"student_no": "20260001", "name": "张三", "password": "secret123"}


def _login(client, student_no="20260001", password="secret123"):
    return client.post("/api/auth/login", json={"student_no": student_no, "password": password})


def test_register_then_login_and_me(client):
    r = client.post("/api/auth/register", json=REG)
    assert r.status_code == 201, r.text
    assert r.json()["roles"] == ["user"]  # FR-005：新用户默认「用户」角色
    assert "password" not in r.text

    r = _login(client)
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["student_no"] == "20260001"


def test_password_is_stored_hashed(client, api_db):
    client.post("/api/auth/register", json=REG)
    with api_db() as s:
        h = s.scalar(select(User.password_hash))
    assert h != "secret123" and h.startswith("$2")  # bcrypt


def test_register_rejects_duplicate_and_bad_input(client):
    client.post("/api/auth/register", json=REG)
    r = client.post("/api/auth/register", json=REG)
    assert r.status_code == 409 and r.json()["detail"]["message"] == "该学号已注册"

    r = client.post("/api/auth/register", json={**REG, "student_no": "a-b"})
    assert r.json()["detail"]["code"] == "invalid_student_no"
    r = client.post(
        "/api/auth/register", json={**REG, "student_no": "20260002", "password": "short1"}
    )
    assert r.json()["detail"]["code"] == "weak_password"
    r = client.post(
        "/api/auth/register", json={**REG, "student_no": "20260002", "password": "onlyletters"}
    )
    assert r.status_code == 422


def test_login_failures_have_clear_messages(client, make_user):
    make_user()
    # 统一提示，不暴露学号是否存在。
    r = _login(client, "99999999")
    assert r.status_code == 401
    assert r.json()["detail"]["message"] == "学号或密码错误"
    assert r.json()["detail"]["code"] == "invalid_credentials"
    r = _login(client, password="wrong1234")
    assert r.status_code == 401
    assert r.json()["detail"]["message"] == "学号或密码错误"
    assert r.json()["detail"]["code"] == "invalid_credentials"


def test_login_lockout_after_failures(client, make_user, monkeypatch):
    make_user()
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "login_max_failures", 3)
    monkeypatch.setattr(settings, "login_lockout_minutes", 15)
    for _ in range(3):
        assert _login(client, password="wrong1234").status_code == 401
    locked = _login(client, password="wrong1234")
    assert locked.status_code == 429
    assert locked.json()["detail"]["code"] == "login_locked"
    # 正确密码在锁定窗口内也被拒绝
    assert _login(client).status_code == 429


def test_disabled_account_cannot_login(client, make_user):
    make_user(status="disabled")
    r = _login(client)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_disabled"


def test_logout_revokes_token(client, make_user, login):
    make_user()
    h = login("20260001", "secret123")
    assert client.post("/api/auth/logout", headers=h).status_code == 204
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_unauthenticated_and_expired(client, make_user, login, api_db):
    assert client.get("/api/auth/me").status_code == 401
    make_user()
    h = login("20260001", "secret123")
    with api_db() as s:
        s.scalar(select(AuthSession)).expires_at = now() - timedelta(seconds=1)
        s.commit()
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_change_password(client, make_user, login):
    make_user()
    h = login("20260001", "secret123")
    r = client.post(
        "/api/auth/change-password",
        headers=h,
        json={"old_password": "bad", "new_password": "newpass123"},
    )
    assert r.status_code == 400
    r = client.post(
        "/api/auth/change-password",
        headers=h,
        json={"old_password": "secret123", "new_password": "newpass123"},
    )
    assert r.status_code == 204
    assert client.get("/api/auth/me", headers=h).status_code == 401  # 旧会话失效
    assert _login(client).status_code == 401
    assert _login(client, password="newpass123").status_code == 200


def test_reset_password_with_code(client, make_user, api_db):
    make_user()
    with api_db() as s:
        user = s.scalar(select(User))
        code, _ = svc.issue_reset_code(s, user, None)
    body = {"student_no": "20260001", "reset_code": "nope", "new_password": "reset1234"}
    assert client.post("/api/auth/reset-password", json=body).status_code == 400

    body["reset_code"] = code
    assert client.post("/api/auth/reset-password", json=body).status_code == 204
    assert _login(client, password="reset1234").status_code == 200
    # 重置码一次性
    assert client.post("/api/auth/reset-password", json=body).status_code == 400


def test_reset_code_expires_and_reissue_invalidates_old(client, make_user, api_db):
    make_user()
    with api_db() as s:
        user = s.scalar(select(User))
        first, _ = svc.issue_reset_code(s, user, None)
        second, _ = svc.issue_reset_code(s, user, None)
    body = {"student_no": "20260001", "reset_code": first, "new_password": "reset1234"}
    assert client.post("/api/auth/reset-password", json=body).status_code == 400

    from app.models import PasswordResetToken

    with api_db() as s:
        for t in s.scalars(select(PasswordResetToken)):
            t.expires_at = now() - timedelta(seconds=1)
        s.commit()
    body["reset_code"] = second
    assert client.post("/api/auth/reset-password", json=body).status_code == 400
