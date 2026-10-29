"""用户与角色管理（FR-005 角色分配、FR-007 账户状态、FR-004 签发重置码）。仅管理员。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.auth import user_out
from app.db import transaction
from app.deps import SessionDep, client_ip, require_permission
from app.models import Role, User
from app.models.enums import AccountStatus, AuditOpType, RoleName
from app.schemas.auth import ResetCodeOut, RolesIn, StatusIn, UserOut
from app.services import audit
from app.services import auth as auth_svc

router = APIRouter(prefix="/admin/users", tags=["admin-users"])
Admin = Annotated[User, Depends(require_permission("user:manage"))]


def _get_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    return user


def _roles(user: User) -> list[str]:
    return sorted(r.name for r in user.roles)


@router.get("", response_model=dict)
def list_users(
    _: Admin,
    session: SessionDep,
    q: str | None = None,
    role: RoleName | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    stmt = select(User)
    if q:
        stmt = stmt.where(or_(User.student_no.contains(q), User.name.contains(q)))
    if role:
        stmt = stmt.where(User.roles.any(Role.name == role))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    users = session.scalars(stmt.order_by(User.id).offset((page - 1) * size).limit(size))
    return {"total": total, "items": [user_out(u).model_dump() for u in users]}


@router.put("/{user_id}/roles", response_model=UserOut)
def set_roles(user_id: int, body: RolesIn, admin: Admin, session: SessionDep, request: Request):
    user = _get_user(session, user_id)
    before = _roles(user)
    new = sorted(set(body.roles))
    if user.id == admin.id and RoleName.ADMIN not in new:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能移除自己的管理员角色")
    with transaction(session):
        user.roles = list(session.scalars(select(Role).where(Role.name.in_(new))))
        audit.record(
            session,
            operator=admin,
            op_type=AuditOpType.PERMISSION_CHANGE,
            target_type="user",
            target_id=user.id,
            before={"roles": before},
            after={"roles": new},
            ip=client_ip(request),
        )
    return user_out(user)


@router.patch("/{user_id}/status", response_model=UserOut)
def set_status(user_id: int, body: StatusIn, admin: Admin, session: SessionDep, request: Request):
    user = _get_user(session, user_id)
    if user.id == admin.id and body.status != AccountStatus.NORMAL:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能禁用自己的账户")
    before = user.status
    with transaction(session):
        user.status = body.status
        if body.status != AccountStatus.NORMAL:
            auth_svc.revoke_all_sessions(session, user.id)  # 禁用即下线
        audit.record(
            session,
            operator=admin,
            op_type=AuditOpType.ADMIN_ACTION,
            target_type="user_status",
            target_id=user.id,
            before={"status": before},
            after={"status": body.status},
            ip=client_ip(request),
        )
    return user_out(user)


@router.post("/{user_id}/reset-code", response_model=ResetCodeOut)
def issue_reset_code(user_id: int, admin: Admin, session: SessionDep, request: Request):
    user = _get_user(session, user_id)
    code, ttl = auth_svc.issue_reset_code(session, user, admin)
    with transaction(session):
        audit.record(
            session,
            operator=admin,
            op_type=AuditOpType.ADMIN_ACTION,
            target_type="password_reset",
            target_id=user.id,
            ip=client_ip(request),
        )
    return ResetCodeOut(reset_code=code, expires_in=ttl)
