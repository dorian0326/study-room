"""不依赖数据库的纯函数单元测试。"""

from datetime import timedelta

from app.models.enums import RoleName
from app.permissions import permissions_of, roles_for
from app.security import (
    hash_password,
    password_problem,
    student_no_valid,
    token_digest,
    verify_password,
)
from app.services.gate import user_key_for_gate
from app.timeutil import now, tz


def test_password_policy_rejects_short_or_single_class():
    assert password_problem("Ab1") == "密码至少 8 位"
    assert password_problem("abcdefgh") == "密码须同时包含字母和数字"
    assert password_problem("12345678") == "密码须同时包含字母和数字"
    assert password_problem("a" * 73) == "密码不能超过 72 字节"
    assert password_problem("Demo1234") is None


def test_student_no_pattern():
    assert student_no_valid("20260001")
    assert student_no_valid("A0000001")
    assert not student_no_valid("12")
    assert not student_no_valid("学号2026")
    assert not student_no_valid("")


def test_password_hash_verifies_and_hides_plaintext():
    stored = hash_password("Demo1234")
    assert stored != "Demo1234"
    assert verify_password("Demo1234", stored)
    assert not verify_password("Demo1235", stored)
    assert not verify_password("Demo1234", "not-a-hash")


def test_token_digest_is_stable_and_not_the_token():
    digest = token_digest("session-token")
    assert digest == token_digest("session-token")
    assert digest != "session-token"
    assert len(digest) == 64


def test_permission_projection_matches_role_matrix():
    user = permissions_of({RoleName.USER})
    admin = permissions_of({RoleName.ADMIN})
    ops = permissions_of({RoleName.OPS})
    assert "room:read" in user and "user:manage" not in user
    assert "user:manage" in admin and "system:backup" not in admin
    assert "system:backup" in ops and "room:manage" not in ops
    assert permissions_of(set()) == set()
    assert RoleName.ADMIN in roles_for("stats:read")
    assert RoleName.USER not in roles_for("stats:read")


def test_now_is_shanghai_aware():
    moment = now()
    assert moment.tzinfo == tz()
    assert moment.utcoffset() == timedelta(hours=8)


def test_gate_user_key_does_not_expose_student_no():
    first = user_key_for_gate("20260001")
    assert first == user_key_for_gate("20260001")
    assert first != user_key_for_gate("20260002")
    assert "20260001" not in first
    assert len(first) == 64
