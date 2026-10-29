"""登录日志写入、日志查询与过期清理（#8）。"""

from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import transaction
from app.models import AuditLog, LoginLog, User
from app.timeutil import now


def record_login(
    session: Session,
    *,
    student_no: str,
    user: User | None,
    event: str = "login",
    success: bool,
    reason: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """独立事务写入，失败的登录也要留痕。"""
    if session.in_transaction():
        session.rollback()
    with transaction(session):
        session.add(
            LoginLog(
                user_id=user.id if user else None,
                student_no=student_no.strip()[:32],
                event=event,
                success=success,
                reason=reason,
                occurred_at=now(),
                ip_address=ip,
                user_agent=(user_agent or "")[:255] or None,
            )
        )


def page(session: Session, stmt, order_col, page_no: int, size: int) -> tuple[int, list]:  # noqa: ANN001
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = session.scalars(stmt.order_by(order_col.desc()).offset((page_no - 1) * size).limit(size))
    return total, list(rows)


def time_filter(stmt, col, start: datetime | None, end: datetime | None):  # noqa: ANN001
    if start:
        stmt = stmt.where(col >= start)
    if end:
        stmt = stmt.where(col < end)
    return stmt


def purge_expired(session: Session, days: int | None = None) -> dict[str, int]:
    """删除超过保留期的操作日志与登录日志（BR-105 保留一个学期）。"""
    cutoff = now() - timedelta(days=days or get_settings().log_retention_days)
    with transaction(session):
        a = session.execute(delete(AuditLog).where(AuditLog.occurred_at < cutoff)).rowcount
        b = session.execute(delete(LoginLog).where(LoginLog.occurred_at < cutoff)).rowcount
    return {"audit_logs": a, "login_logs": b}
