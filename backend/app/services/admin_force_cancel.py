"""管理员强制取消预约（关闭自习室 / 改开放时间 / 座位维护共用模式）。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Reservation, StudyRoom, User
from app.models import enums as E
from app.models.enums import AuditOpType, NotificationType
from app.services import audit
from app.services.availability import covers
from app.services.notifications import create_notification
from app.timeutil import now


def cancel_future_reserved(
    session: Session,
    *,
    reservations: list[Reservation],
    operator: User,
    reason: str,
    notify_content,
    target_type: str,
    target_id: int | None,
    moment: datetime | None = None,
) -> int:
    """把未签到的未来预约标为 ADMIN_CANCELLED 并通知用户。"""
    moment = moment or now()
    for reservation in reservations:
        reservation.status = E.ReservationStatus.ADMIN_CANCELLED
        reservation.cancel_type = E.CancelType.SYSTEM
        reservation.cancelled_at = moment
        reservation.cancel_reason = reason
        create_notification(
            session,
            user_id=reservation.user_id,
            notification_type=NotificationType.MAINTENANCE,
            content=notify_content(reservation),
            idempotency_key=f"reservation:{reservation.id}:admin-force-cancelled",
        )
    audit.record(
        session,
        operator=operator,
        op_type=AuditOpType.ADMIN_ACTION,
        target_type=target_type,
        target_id=target_id,
        before=None,
        after={"reason": reason, "cancelled_reservations": len(reservations)},
    )
    return len(reservations)


def cancel_for_room_close(session: Session, room: StudyRoom, operator: User) -> int:
    """BR-065：关闭自习室时取消该室全部未开始的预约并通知。"""
    moment = now()
    pending = list(
        session.scalars(
            select(Reservation).where(
                Reservation.room_id == room.id,
                Reservation.status == E.ReservationStatus.RESERVED,
                Reservation.start_time > moment,
            )
        )
    )
    return cancel_future_reserved(
        session,
        reservations=pending,
        operator=operator,
        reason="自习室关闭，系统强制取消（不补偿）",
        notify_content=lambda r: (
            f"自习室 {room.name} 已关闭，你的预约 {r.reservation_no} 已取消；本次不提供补偿。"
        ),
        target_type="room_close",
        target_id=room.id,
        moment=moment,
    )


def cancel_for_schedule_change(session: Session, room_id: int, operator: User) -> int:
    """BR-062：修改开放时间后，取消不再落在开放窗口内的未来预约。"""
    moment = now()
    pending = list(
        session.scalars(
            select(Reservation).where(
                Reservation.room_id == room_id,
                Reservation.status == E.ReservationStatus.RESERVED,
                Reservation.start_time > moment,
            )
        )
    )
    conflicting = [r for r in pending if not covers(session, room_id, r.start_time, r.end_time)]
    room = session.get(StudyRoom, room_id)
    name = room.name if room else str(room_id)
    return cancel_future_reserved(
        session,
        reservations=conflicting,
        operator=operator,
        reason="开放时间调整，预约时段不再开放，系统强制取消（不补偿）",
        notify_content=lambda r: (
            f"自习室 {name} 开放时间已调整，你的预约 {r.reservation_no} "
            "因时段不再开放已取消；本次不提供补偿。"
        ),
        target_type="schedule_change",
        target_id=room_id,
        moment=moment,
    )
