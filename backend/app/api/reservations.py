"""学生预约、签到签退、个人违规申诉和站内通知接口。"""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.db import transaction
from app.deps import CurrentUser, SessionDep, client_ip
from app.models import (
    Appeal,
    Notification,
    Reservation,
    Seat,
    StudyRoom,
    ViolationRecord,
)
from app.models import enums as E
from app.models.enums import AuditOpType
from app.schemas.workflows import (
    AppealCreate,
    AppealOut,
    EndUseIn,
    NotificationOut,
    ReservationCreate,
    ReservationHistoryOut,
    ReservationOut,
    ViolationOut,
)
from app.services import audit
from app.services.notifications import create_notification
from app.services.reservations import (
    check_in,
    create_reservation,
    end_use,
    return_from_temporary_leave,
    start_temporary_leave,
)
from app.services.settings import get_business_settings
from app.services.violations import record_violation
from app.timeutil import now

router = APIRouter(tags=["student-workflows"])
HistoryScope = Annotated[str, Query(pattern="^(all|current|history)$")]


@router.get("/rooms")
def public_rooms(
    _: CurrentUser,
    session: SessionDep,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
):
    """返回已开放自习室与座位布局，供预约表单查看可选资源。"""
    # 查询结果只包含公开的房间、座位状态和偏好属性，不返回预约人的身份资料。
    if (start_time is None) != (end_time is None):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "查询可用座位需要同时提供起止时间"
        )
    busy_seat_ids: set[int] = set()
    if start_time is not None and end_time is not None:
        # 可用状态按指定预约区间即时计算，不把静态座位状态当成冲突缓存。
        if start_time.tzinfo is None or end_time.tzinfo is None or start_time >= end_time:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "查询时间范围无效")
        busy_seat_ids = set(
            session.scalars(
                select(Reservation.seat_id)
                .where(
                    Reservation.status.in_(E.ACTIVE_RESERVATION_STATUSES),
                    Reservation.start_time < end_time,
                    Reservation.end_time > start_time,
                )
                .distinct()
            )
        )
    rooms = session.scalars(
        select(StudyRoom).where(StudyRoom.status == E.RoomStatus.OPEN).order_by(StudyRoom.name)
    )
    result = []
    for room in rooms:
        seats = session.scalars(select(Seat).where(Seat.room_id == room.id).order_by(Seat.code))
        result.append(
            {
                "id": room.id,
                "name": room.name,
                "location": room.location,
                "seats": [
                    {
                        "id": seat.id,
                        "code": seat.code,
                        "zone_type": seat.zone_type,
                        "has_power": seat.has_power,
                        "by_window": seat.by_window,
                        "accessible": seat.accessible,
                        "status": (
                            E.SeatStatus.RESERVED
                            if seat.id in busy_seat_ids and seat.status == E.SeatStatus.AVAILABLE
                            else seat.status
                        ),
                    }
                    for seat in seats
                ],
            }
        )
    return result


@router.get("/reservations", response_model=list[ReservationHistoryOut])
def list_my_reservations(user: CurrentUser, session: SessionDep, scope: HistoryScope = "all"):
    """返回当前用户过去和当前预约，支持按当前或历史状态筛选。"""
    # 当前预约按时间窗定义，终态预约始终归入历史；查询在数据库端先按本人隔离。
    moment = now()
    statement = (
        select(Reservation, StudyRoom.name, Seat.code)
        .join(StudyRoom, StudyRoom.id == Reservation.room_id)
        .join(Seat, Seat.id == Reservation.seat_id)
        .where(Reservation.user_id == user.id)
        .order_by(Reservation.start_time.desc(), Reservation.id.desc())
    )
    rows = session.execute(statement).all()
    visible = []
    for reservation, room_name, seat_code in rows:
        is_current = (
            reservation.status in E.ACTIVE_RESERVATION_STATUSES
            and reservation.start_time <= moment <= reservation.end_time
        ) or reservation.start_time > moment
        if scope == "current" and not is_current:
            continue
        if scope == "history" and is_current:
            continue
        visible.append(
            ReservationHistoryOut.model_validate(reservation).model_copy(
                update={"room_name": room_name, "seat_code": seat_code}
            )
        )
    return visible


@router.post("/reservations", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
def reserve_seat(body: ReservationCreate, user: CurrentUser, session: SessionDep):
    """校验并创建本人预约，冲突检测和插入由一个写事务完成。"""
    return create_reservation(session, user, body)


@router.post("/reservations/{reservation_id}/check-in", response_model=ReservationOut)
def check_in_reservation(reservation_id: int, user: CurrentUser, session: SessionDep):
    """验证预约归属和签到窗口后记录签到时间。"""
    return check_in(session, user, reservation_id)


@router.post("/reservations/{reservation_id}/temporary-leave", response_model=ReservationOut)
def temporary_leave(reservation_id: int, user: CurrentUser, session: SessionDep):
    """登记用户临时离开，默认保留座位 30 分钟。"""
    return start_temporary_leave(session, user, reservation_id)


@router.post("/reservations/{reservation_id}/return", response_model=ReservationOut)
def return_to_seat(reservation_id: int, user: CurrentUser, session: SessionDep):
    """在临时离开期限内确认返回并恢复预约使用状态。"""
    return return_from_temporary_leave(session, user, reservation_id)


@router.post("/reservations/{reservation_id}/end")
def end_reservation(
    reservation_id: int,
    body: EndUseIn,
    user: CurrentUser,
    session: SessionDep,
):
    """要求用户显式确认后结束当前连续预约时段。"""
    # 连续时段以一次确认完成，响应列出受影响的预约编号及累计学习分钟。
    ended, duration_minutes = end_use(session, user, reservation_id, confirmed=body.confirm)
    return {
        "ended_reservations": [item.id for item in ended],
        "duration_minutes": duration_minutes,
    }


@router.post("/reservations/{reservation_id}/cancel", response_model=ReservationOut)
def cancel_reservation(
    reservation_id: int,
    user: CurrentUser,
    session: SessionDep,
    request: Request,
    confirm: bool = True,
):
    """取消尚未签到的本人预约，并在临近开始时自动记一条违规。"""
    # 只能取消未开始预约；较晚取消会保留历史并触发可申诉的违规记录。
    if not confirm:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "取消预约前必须确认")
    # 使用写事务重新读取预约，避免并发签到或重复取消导致状态被覆盖。
    session.commit()
    with transaction(session, immediate=True):
        reservation = session.get(Reservation, reservation_id)
        if reservation is None or reservation.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "预约不存在")
        moment = now()
        if reservation.status != E.ReservationStatus.RESERVED or reservation.start_time <= moment:
            raise HTTPException(status.HTTP_409_CONFLICT, "该预约当前不能取消")
        settings = get_business_settings(session)
        late = reservation.start_time - moment <= timedelta(minutes=settings.late_cancel_minutes)
        reservation.status = E.ReservationStatus.CANCELLED
        reservation.cancel_type = E.CancelType.LATE if late else E.CancelType.NORMAL
        reservation.cancelled_at = moment
        reservation.cancel_reason = "本人取消预约"
        create_notification(
            session,
            user_id=user.id,
            notification_type=E.NotificationType.SYSTEM,
            content=f"预约 {reservation.reservation_no} 已取消。",
            idempotency_key=f"reservation:{reservation.id}:cancelled",
        )
        if late:
            record_violation(
                session,
                user_id=user.id,
                violation_type=E.ViolationType.LATE_CANCEL,
                reservation_id=reservation.id,
                description="预约开始前临近时段取消。",
                occurred_at=moment,
            )
        audit.record(
            session,
            operator=user,
            op_type=AuditOpType.ADMIN_ACTION,
            target_type="reservation_cancel",
            target_id=reservation.id,
            after={"status": reservation.status, "late": late},
            ip=client_ip(request),
        )
    return reservation


@router.get("/violations", response_model=list[ViolationOut])
def list_my_violations(user: CurrentUser, session: SessionDep):
    """列出当前用户自己的违规事件和申诉状态。"""
    # 违规记录可能包含身份和行为信息，查询严格限制在当前登录用户。
    return list(
        session.scalars(
            select(ViolationRecord)
            .where(ViolationRecord.user_id == user.id)
            .order_by(ViolationRecord.occurred_at.desc())
        )
    )


@router.post("/appeals", response_model=AppealOut, status_code=status.HTTP_201_CREATED)
def submit_appeal(body: AppealCreate, user: CurrentUser, session: SessionDep):
    """为本人尚在可申诉期内的违规记录提交一份申诉。"""
    # 申诉只能关联本人违规；写锁内复核状态和期限，防止并发提交重复待审核记录。
    session.commit()
    with transaction(session, immediate=True):
        violation = session.get(ViolationRecord, body.violation_id)
        if violation is None or violation.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "违规记录不存在")
        if violation.appeal_status == E.AppealStatus.PENDING:
            raise HTTPException(status.HTTP_409_CONFLICT, "该违规已有待审核申诉")
        moment = now()
        if moment > violation.occurred_at + timedelta(days=7):
            raise HTTPException(status.HTTP_409_CONFLICT, "该违规已超过申诉期限")
        appeal = Appeal(
            user_id=user.id,
            violation_id=violation.id,
            restriction_id=violation.restriction_id,
            reason=body.reason.strip(),
            evidence=body.evidence,
            deadline=violation.occurred_at + timedelta(days=7),
        )
        violation.appeal_status = E.AppealStatus.PENDING
        session.add(appeal)
        session.flush()
    return appeal


@router.get("/appeals", response_model=list[AppealOut])
def list_my_appeals(user: CurrentUser, session: SessionDep):
    """列出本人申诉和管理员审核结论。"""
    # 审核意见同步返回申请人，方便查看处理进度和结果。
    return list(
        session.scalars(
            select(Appeal).where(Appeal.user_id == user.id).order_by(Appeal.created_at.desc())
        )
    )


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    user: CurrentUser,
    session: SessionDep,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """列出当前用户的站内通知，可只看未读并限制返回数量。"""
    # 站内通知无外发渠道；账号之间通过 user_id 隔离。
    statement = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        statement = statement.where(Notification.is_read.is_(False))
    return list(session.scalars(statement.order_by(Notification.sent_at.desc()).limit(limit)))


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(notification_id: int, user: CurrentUser, session: SessionDep):
    """将本人站内通知标记为已读，重复请求保持幂等。"""
    # 先验证所有权，不能通过通知编号读取或修改其他用户的数据。
    notification = session.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "通知不存在")
    with transaction(session):
        notification.is_read = True
    return notification
