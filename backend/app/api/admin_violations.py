"""管理员违规查看、申诉审核和处罚审计接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.db import transaction
from app.deps import SessionDep, client_ip, require_permission
from app.models import Appeal, Reservation, Restriction, User, ViolationRecord
from app.models.enums import (
    AppealStatus,
    AuditOpType,
    NotificationType,
    RestrictionStatus,
    ViolationResult,
    ViolationState,
)
from app.schemas.workflows import (
    AppealOut,
    AppealReviewIn,
    ManualViolationIn,
    ViolationOut,
)
from app.services import audit
from app.services.notifications import create_notification
from app.services.violations import record_violation
from app.timeutil import now

router = APIRouter(prefix="/admin", tags=["admin-violations"])
ViolationAdmin = Annotated[User, Depends(require_permission("violation:manage"))]
AppealAdmin = Annotated[User, Depends(require_permission("appeal:manage"))]


@router.get("/violations", response_model=list[ViolationOut])
def list_all_violations(_: ViolationAdmin, session: SessionDep, user_id: int | None = None):
    """按时间倒序查询违规事件，可选按账号筛选。"""
    # 违规详情仅向具备违规管理权限的管理员开放。
    statement = select(ViolationRecord).order_by(ViolationRecord.occurred_at.desc())
    if user_id is not None:
        statement = statement.where(ViolationRecord.user_id == user_id)
    return list(session.scalars(statement.limit(500)))


@router.post("/violations", response_model=ViolationOut, status_code=status.HTTP_201_CREATED)
def create_manual_violation(
    body: ManualViolationIn,
    operator: ViolationAdmin,
    session: SessionDep,
    request: Request,
):
    """管理员登记违规事件并调用统一窗口统计和处罚流程。"""
    target = session.get(User, body.user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    # 手动违规若关联预约，必须确认该预约属于目标用户，避免错误归档或串号。
    if body.reservation_id is not None:
        reservation = session.get(Reservation, body.reservation_id)
        if reservation is None or reservation.user_id != target.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "目标用户的预约不存在")
    with transaction(session):
        record = record_violation(
            session,
            user_id=target.id,
            violation_type=body.violation_type,
            reservation_id=body.reservation_id,
            description=body.description,
            occurred_at=now(),
        )
        record.determined_by = "admin"
        audit.record(
            session,
            operator=operator,
            op_type=AuditOpType.VIOLATION,
            target_type="violation",
            target_id=record.id,
            after={"user_id": target.id, "description": body.description},
            ip=client_ip(request),
        )
    return record


@router.get("/appeals", response_model=list[AppealOut])
def list_appeals(_: AppealAdmin, session: SessionDep, pending_only: bool = True):
    """列出违规申诉队列，默认只显示尚未处理的申请。"""
    # 按提交时间排序，管理员审核界面可先处理最早的待办。
    statement = select(Appeal).order_by(Appeal.created_at)
    if pending_only:
        statement = statement.where(Appeal.result.is_(None))
    return list(session.scalars(statement.limit(500)))


@router.patch("/appeals/{appeal_id}", response_model=AppealOut)
def review_appeal(
    appeal_id: int,
    body: AppealReviewIn,
    operator: AppealAdmin,
    session: SessionDep,
    request: Request,
):
    """记录管理员申诉结论，批准时解除对应未到期禁约。"""
    # 审核结果、违规状态、处罚解除和用户通知在一个事务内保持一致。
    session.commit()
    with transaction(session, immediate=True):
        appeal = session.get(Appeal, appeal_id)
        if appeal is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "申诉不存在")
        if appeal.result is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "该申诉已处理")
        moment = now()
        appeal.reviewer_id = operator.id
        appeal.result = body.result
        appeal.reviewed_at = moment
        appeal.review_comment = body.review_comment.strip()
        violation = session.get(ViolationRecord, appeal.violation_id)
        violation.appeal_status = (
            AppealStatus.APPROVED if body.result.value == "approved" else AppealStatus.REJECTED
        )
        if body.result.value == "approved":
            violation.state = ViolationState.ARCHIVED
            violation.archived_at = moment
            violation.result = ViolationResult.WARNING
            restriction = (
                session.get(Restriction, appeal.restriction_id) if appeal.restriction_id else None
            )
            if restriction is not None and restriction.status == RestrictionStatus.ACTIVE:
                restriction.status = RestrictionStatus.LIFTED
                restriction.lifted_at = moment
                restriction.lift_reason = "申诉审核通过"
                restriction.lifted_by = operator.id
        review_label = "通过" if body.result.value == "approved" else "驳回"
        create_notification(
            session,
            user_id=appeal.user_id,
            notification_type=NotificationType.VIOLATION,
            content=f"你的违规申诉已{review_label}：{body.review_comment}",
            idempotency_key=f"appeal:{appeal.id}:reviewed",
        )
        audit.record(
            session,
            operator=operator,
            op_type=AuditOpType.VIOLATION,
            target_type="appeal",
            target_id=appeal.id,
            before={"result": None},
            after={"result": body.result, "comment": body.review_comment},
            ip=client_ip(request),
        )
    return appeal
