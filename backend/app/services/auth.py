"""认证业务：注册、登录、注销、改密、重置（FR-001~004）。"""

from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import transaction
from app.models import AuthSession, LoginLog, PasswordResetToken, Role, User
from app.models.enums import AccountStatus, RoleName
from app.security import (
    hash_password,
    new_token,
    password_problem,
    student_no_valid,
    token_digest,
    verify_password,
)
from app.timeutil import now


class AuthError(Exception):
    """业务错误：status 为 HTTP 状态码，message 为给用户的明确提示。"""

    def __init__(self, status: int, message: str, code: str):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code


_INVALID = AuthError(401, "学号或密码错误", "invalid_credentials")


def _check_password(password: str) -> None:
    if problem := password_problem(password):
        raise AuthError(422, problem, "weak_password")


def register(session: Session, *, student_no: str, name: str, password: str, **extra) -> User:
    student_no = student_no.strip()
    if not student_no_valid(student_no):
        raise AuthError(422, "学号格式不正确", "invalid_student_no")
    _check_password(password)
    with transaction(session):
        if session.scalar(select(User.id).where(User.student_no == student_no)):
            raise AuthError(409, "该学号已注册", "student_no_taken")
        user_role = session.scalar(select(Role).where(Role.name == RoleName.USER))
        user = User(
            student_no=student_no,
            name=name.strip(),
            password_hash=hash_password(password),
            roles=[user_role] if user_role else [],
            **extra,
        )
        session.add(user)
    return user


def _assert_not_locked(session: Session, student_no: str) -> None:
    """连续失败达到阈值后，在锁定窗口内拒绝登录。"""
    settings = get_settings()
    if settings.login_max_failures <= 0:
        return
    since = now() - timedelta(minutes=settings.login_lockout_minutes)
    latest_success = session.scalar(
        select(func.max(LoginLog.id)).where(
            LoginLog.student_no == student_no.strip(),
            LoginLog.event == "login",
            LoginLog.success.is_(True),
        )
    )
    fails = int(
        session.scalar(
            select(func.count(LoginLog.id)).where(
                LoginLog.student_no == student_no.strip(),
                LoginLog.event == "login",
                LoginLog.success.is_(False),
                LoginLog.occurred_at >= since,
                LoginLog.id > (latest_success or 0),
            )
        )
        or 0
    )
    if fails >= settings.login_max_failures:
        raise AuthError(
            429,
            f"登录失败次数过多，请 {settings.login_lockout_minutes} 分钟后再试",
            "login_locked",
        )


def authenticate(session: Session, student_no: str, password: str) -> User:
    student_no = student_no.strip()
    _assert_not_locked(session, student_no)
    user = session.scalar(select(User).where(User.student_no == student_no))
    # 统一错误提示，不暴露学号是否存在或密码是否正确。
    if user is None or not verify_password(password, user.password_hash):
        raise _INVALID
    if user.status != AccountStatus.NORMAL:
        raise AuthError(403, "账户已被禁用，请联系管理员", "account_disabled")
    return user


def create_session(
    session: Session, user: User, *, ip: str | None = None, user_agent: str | None = None
) -> tuple[str, int]:
    ttl = get_settings().session_ttl_minutes * 60
    token = new_token()
    with transaction(session):
        session.add(
            AuthSession(
                token_hash=token_digest(token),
                user_id=user.id,
                expires_at=now() + timedelta(seconds=ttl),
                ip_address=ip,
                user_agent=(user_agent or "")[:255] or None,
            )
        )
    return token, ttl


def user_for_token(session: Session, token: str) -> tuple[User, AuthSession] | None:
    auth = session.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(token)))
    if auth is None or auth.revoked_at is not None or auth.expires_at <= now():
        return None
    return auth.user, auth


def revoke_session(session: Session, auth: AuthSession) -> None:
    with transaction(session):
        auth.revoked_at = now()


def revoke_all_sessions(session: Session, user_id: int) -> None:
    """撤销该用户全部有效会话（调用方负责事务）。"""
    session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now())
    )


def change_password(session: Session, user: User, old: str, new: str) -> None:
    if not verify_password(old, user.password_hash):
        raise AuthError(400, "原密码错误", "wrong_password")
    _check_password(new)
    with transaction(session):
        user.password_hash = hash_password(new)
        revoke_all_sessions(session, user.id)


def issue_reset_code(session: Session, user: User, issued_by: User | None) -> tuple[str, int]:
    """生成一次性重置码。本期无邮件/短信渠道（HD-38 仅站内），由管理员线下核验身份后签发。"""
    ttl = get_settings().password_reset_ttl_minutes * 60
    code = new_token()
    with transaction(session):
        session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
            .values(used_at=now())
        )
        session.add(
            PasswordResetToken(
                token_hash=token_digest(code),
                user_id=user.id,
                issued_by=issued_by.id if issued_by else None,
                expires_at=now() + timedelta(seconds=ttl),
            )
        )
    return code, ttl


def reset_password(session: Session, student_no: str, code: str, new: str) -> None:
    invalid = AuthError(400, "重置码无效或已过期", "invalid_reset_code")
    user = session.scalar(select(User).where(User.student_no == student_no.strip()))
    if user is None:
        raise invalid
    token = session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_digest(code),
            PasswordResetToken.user_id == user.id,
        )
    )
    if token is None or token.used_at is not None or token.expires_at <= now():
        raise invalid
    _check_password(new)
    with transaction(session):
        token.used_at = now()
        user.password_hash = hash_password(new)
        revoke_all_sessions(session, user.id)
