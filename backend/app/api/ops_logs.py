"""日志查询（#8，FR-075 / US-402）。

- 操作日志：管理员与运维可查（PERM-025，只读）
- 登录日志：属于系统日志，仅运维可查（PERM-024，只读）
支持按时间段、用户、类型筛选并分页。
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.deps import SessionDep, require_permission
from app.models import AuditLog, LoginLog, User
from app.models.enums import AuditOpType
from app.services.logs import page, time_filter

router = APIRouter(prefix="/ops", tags=["ops-logs"])
Page = Annotated[int, Query(ge=1)]
Size = Annotated[int, Query(ge=1, le=200)]


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operator_id: int | None
    operator_student_no: str | None = None
    op_type: AuditOpType
    target_type: str
    target_id: str | None
    occurred_at: datetime
    before_value: str | None
    after_value: str | None
    ip_address: str | None
    result: str


class LoginLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    student_no: str
    event: str
    success: bool
    reason: str | None
    occurred_at: datetime
    ip_address: str | None
    user_agent: str | None


@router.get("/audit-logs")
def audit_logs(
    _: Annotated[User, Depends(require_permission("audit_log:read"))],
    session: SessionDep,
    start: datetime | None = None,
    end: datetime | None = None,
    operator: str | None = Query(None, description="操作人学号"),
    op_type: AuditOpType | None = None,
    target_type: str | None = None,
    page_no: Page = 1,
    size: Size = 50,
) -> dict:
    stmt = time_filter(select(AuditLog), AuditLog.occurred_at, start, end)
    if operator:
        stmt = stmt.where(
            AuditLog.operator_id.in_(select(User.id).where(User.student_no == operator))
        )
    if op_type:
        stmt = stmt.where(AuditLog.op_type == op_type)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)
    total, rows = page(session, stmt, AuditLog.id, page_no, size)
    ids = {r.operator_id for r in rows if r.operator_id}
    nos = dict(session.execute(select(User.id, User.student_no).where(User.id.in_(ids))).all())
    items = []
    for r in rows:
        item = AuditLogOut.model_validate(r)
        item.operator_student_no = nos.get(r.operator_id)
        items.append(item.model_dump(mode="json"))
    return {"total": total, "items": items}


@router.get("/login-logs")
def login_logs(
    _: Annotated[User, Depends(require_permission("system_log:read"))],
    session: SessionDep,
    start: datetime | None = None,
    end: datetime | None = None,
    student_no: str | None = None,
    event: str | None = Query(None, pattern="^(login|logout)$"),
    success: bool | None = None,
    page_no: Page = 1,
    size: Size = 50,
) -> dict:
    stmt = time_filter(select(LoginLog), LoginLog.occurred_at, start, end)
    if student_no:
        stmt = stmt.where(LoginLog.student_no == student_no)
    if event:
        stmt = stmt.where(LoginLog.event == event)
    if success is not None:
        stmt = stmt.where(LoginLog.success == success)
    total, rows = page(session, stmt, LoginLog.id, page_no, size)
    return {
        "total": total,
        "items": [LoginLogOut.model_validate(r).model_dump(mode="json") for r in rows],
    }
