"""运维可用的门禁 mock 事件接收端点。"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.config import get_settings
from app.db import transaction
from app.deps import CurrentUser, SessionDep, require_permission
from app.models import EntryExitRecord, Reservation, User
from app.models.enums import NotificationType
from app.schemas.workflows import GateEventIn, ManualGateAppealIn
from app.services.gate import process_gate_event, user_key_for_gate
from app.services.notifications import create_notification
from app.timeutil import now

router = APIRouter(prefix="/ops/entry-exit", tags=["entry-exit"])
GateOperator = Annotated[User, Depends(require_permission("entry_exit:read"))]


@router.post("/mock")
def sync_mock_gate_event(body: GateEventIn, _: GateOperator, session: SessionDep):
    """同步一条脱敏的门禁进出事件，超时或匹配失败时提示人工申诉。"""
    # 路由不接受学号、卡号或人脸数据，入口身份只能使用 keyed hash。
    return process_gate_event(session, body)


@router.post("/manual-appeals")
def submit_gate_manual_appeal(
    body: ManualGateAppealIn,
    user: CurrentUser,
    session: SessionDep,
):
    """留存门禁超时或不可用时的本人出入馆人工核验申请。"""
    reservation = None
    if body.reservation_id is not None:
        reservation = session.get(Reservation, body.reservation_id)
        if reservation is None or reservation.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "预约不存在")

    # 人工申请记录原事件及用户说明，后续运维可通过门禁记录查询接口核验。
    moment = now()
    with transaction(session):
        record = EntryExitRecord(
            external_id=f"manual-{user.id}-{moment:%Y%m%d%H%M%S%f}",
            source_system="manual-appeal",
            masked_user_key=user_key_for_gate(user.student_no),
            record_type=body.record_type,
            recorded_at=moment,
            received_at=moment,
            expires_at=moment + timedelta(days=get_settings().log_retention_days),
            sync_status="manual_review",
            reservation_id=reservation.id if reservation else None,
            manual_note=body.reason.strip(),
        )
        session.add(record)
        session.flush()
        create_notification(
            session,
            user_id=user.id,
            notification_type=NotificationType.SYSTEM,
            content=f"门禁人工核验申请已提交，编号 {record.id}。",
            idempotency_key=f"gate-manual-appeal:{record.id}",
        )
    return {"record_id": record.id, "status": record.sync_status}


@router.get("/records")
def list_gate_records(
    _: GateOperator,
    session: SessionDep,
    sync_status: str | None = None,
    limit: int = 100,
):
    """查询脱敏后的门禁同步记录和人工核验原因。"""
    # 默认记录上限避免运维接口一次加载全部门禁事件。
    statement = select(EntryExitRecord).order_by(EntryExitRecord.received_at.desc())
    if sync_status:
        statement = statement.where(EntryExitRecord.sync_status == sync_status)
    rows = session.scalars(statement.limit(min(max(limit, 1), 500)))
    return [
        {
            "id": row.id,
            "source_system": row.source_system,
            "masked_user_key": row.masked_user_key,
            "record_type": row.record_type,
            "recorded_at": row.recorded_at,
            "received_at": row.received_at,
            "sync_status": row.sync_status,
            "sync_delay_seconds": row.sync_delay_seconds,
            "reservation_id": row.reservation_id,
            "manual_note": row.manual_note,
        }
        for row in rows
    ]
