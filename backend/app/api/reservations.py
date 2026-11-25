"""学生预约、座位查询、签到签退、个人违规申诉和站内通知接口。"""

from datetime import date, datetime, time, timedelta
from hashlib import sha256
from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    status,
)
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import timeutil
from app.db import transaction
from app.deps import CurrentUser, SessionDep, require_permission
from app.models import Appeal, Notification, Reservation, Seat, StudyRoom, User, ViolationRecord
from app.models import enums as E
from app.schemas.reservations import ChangeSeatIn, CheckInIn, ReservationIn
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
from app.services import availability as catalog
from app.services import reservations as service


def now():
    """可被测试替换；默认转发到 timeutil.now。"""
    return timeutil.now()


router = APIRouter(tags=["student-workflows"])
Reader = Annotated[User, Depends(require_permission("room:read"))]
Owner = Annotated[User, Depends(require_permission("reservation:own"))]
AllReservationsReader = Annotated[User, Depends(require_permission("reservation:read_all"))]
HistoryScope = Annotated[str, Query(pattern="^(all|current|history|pending-confirmation)$")]
IdempotencyKey = Annotated[
    str | None,
    Header(alias="Idempotency-Key", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$"),
]


def _window(day: date | None, start: time | None, end: time | None):
    if day is None and start is None and end is None:
        return timeutil.now(), None
    if day is None or start is None or end is None:
        raise catalog.BookingError(422, "查询时请同时提供日期、开始时间和结束时间")
    if start.tzinfo is not None or end.tzinfo is not None or start >= end:
        raise catalog.BookingError(422, "查询时段须为北京时间，开始早于结束且不跨零点")
    return datetime.combine(day, start, timeutil.tz()), datetime.combine(day, end, timeutil.tz())


@router.get("/rooms")
def public_rooms(
    user: Reader,
    session: SessionDep,
    day: Annotated[date | None, Query(alias="date")] = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
):
    """返回自习室列表：含楼层/容量/开放时间；若给起止时间则附带座位占用状态。"""
    if (start_time is None) != (end_time is None):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "查询可用座位需要同时提供起止时间"
        )
    service.expire_due(session)
    target_day = day or (
        start_time.astimezone(timeutil.tz()).date() if start_time else timeutil.now().date()
    )
    with Session(session.get_bind()) as read:
        rooms = catalog.room_list(read, target_day)
        if start_time is None:
            return rooms
        if start_time.tzinfo is None or end_time.tzinfo is None or start_time >= end_time:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "查询时间范围无效")
        busy_seat_ids = set(
            read.scalars(
                select(Reservation.seat_id)
                .where(
                    Reservation.status.in_(E.ACTIVE_RESERVATION_STATUSES),
                    Reservation.start_time < end_time,
                    Reservation.end_time > start_time,
                )
                .distinct()
            )
        )
        result = []
        for room in rooms:
            if room.status != E.RoomStatus.OPEN:
                continue
            seats = read.scalars(select(Seat).where(Seat.room_id == room.id).order_by(Seat.code))
            result.append(
                {
                    **room.model_dump(mode="json"),
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
                                if seat.id in busy_seat_ids
                                and seat.status == E.SeatStatus.AVAILABLE
                                else seat.status
                            ),
                        }
                        for seat in seats
                    ],
                }
            )
        return result


@router.get("/seats")
def list_seats(
    _: Reader,
    session: SessionDep,
    room_id: Annotated[int | None, Query(gt=0)] = None,
    zone_type: E.ZoneType | None = None,
    available_only: bool = False,
    has_power: bool | None = None,
    by_window: bool | None = None,
    accessible: bool | None = None,
    day: Annotated[date | None, Query(alias="date")] = None,
    start_time: time | None = None,
    end_time: time | None = None,
):
    start, end = _window(day, start_time, end_time)
    service.expire_due(session)
    with Session(session.get_bind()) as read:
        return catalog.seat_list(
            read,
            start,
            end,
            room_id,
            zone_type,
            available_only,
            has_power=has_power,
            by_window=by_window,
            accessible=accessible,
        )


@router.get("/seats/{seat_id}")
def seat_detail(
    seat_id: int,
    _: Reader,
    session: SessionDep,
    day: Annotated[date | None, Query(alias="date")] = None,
    start_time: time | None = None,
    end_time: time | None = None,
):
    start, end = _window(day, start_time, end_time)
    service.expire_due(session)
    with Session(session.get_bind()) as read:
        seat = read.get(Seat, seat_id)
        if seat is None:
            raise catalog.BookingError(404, "座位不存在")
        return catalog.seat_out(read, seat, start, end)


@router.get("/reservations", response_model=list[ReservationHistoryOut])
def list_my_reservations(user: Owner, session: SessionDep, scope: HistoryScope = "all"):
    """返回当前用户过去和当前预约，支持按当前或历史状态筛选。"""
    service.expire_due(session)
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
            reservation.status in E.ACTIVE_RESERVATION_STATUSES and reservation.end_time > moment
        )
        pending_confirmation = (
            reservation.status in (E.ReservationStatus.ACTIVE, E.ReservationStatus.TEMP_LEAVE)
            and reservation.end_time <= moment < reservation.end_time + service.CHECKOUT_GRACE
        )
        if scope == "pending-confirmation" and not pending_confirmation:
            continue
        if scope == "current" and not is_current:
            continue
        if scope == "history" and is_current:
            continue
        visible.append(
            ReservationHistoryOut(
                **ReservationOut.model_validate(reservation).model_dump(),
                room_name=room_name,
                seat_code=seat_code,
            )
        )
    return visible


@router.get("/reservations/current")
def current_reservations(user: Owner, session: SessionDep):
    service.expire_due(session)
    with Session(session.get_bind()) as read:
        bookings = read.scalars(
            select(Reservation)
            .where(
                Reservation.user_id == user.id,
                Reservation.status.in_(E.ACTIVE_RESERVATION_STATUSES),
                Reservation.end_time > now(),
            )
            .order_by(Reservation.start_time)
        )
        return [service.reservation_out(read, r) for r in bookings]


@router.get("/admin/reservations")
def all_reservations(
    _: AllReservationsReader,
    session: SessionDep,
    user_id: int | None = None,
    booking_status: Annotated[E.ReservationStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    statement = select(Reservation)
    if user_id is not None:
        statement = statement.where(Reservation.user_id == user_id)
    if booking_status is not None:
        statement = statement.where(Reservation.status == booking_status)
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    rows = session.scalars(
        statement.order_by(Reservation.start_time.desc(), Reservation.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return {"total": total, "items": [ReservationOut.model_validate(row) for row in rows]}


@router.get("/reservations/{rid}")
def reservation_detail(rid: int, user: Owner, session: SessionDep):
    service.expire_due(session)
    with Session(session.get_bind()) as read:
        return service.reservation_out(read, service._owned(read, user.id, rid))


@router.post("/reservations", status_code=status.HTTP_201_CREATED)
def reserve_seat(
    body: ReservationCreate,
    user: Owner,
    session: SessionDep,
    response: Response,
    idempotency_key: IdempotencyKey = None,
):
    """创建预约。优先使用 Idempotency-Key；否则回退到 body.request_key。"""
    key = idempotency_key
    if key is None and body.request_key:
        key = sha256(f"{user.id}:{body.request_key}".encode()).hexdigest()
    try:
        payload = ReservationIn(
            seat_id=body.seat_id,
            room_id=body.room_id,
            zone_type=body.zone_type,
            start_time=body.start_time,
            end_time=body.end_time,
        )
    except ValidationError as exc:
        detail = "; ".join(err.get("msg", "校验失败") for err in exc.errors()) or "请求无效"
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail) from exc
    result, replay = service.create(session, user.id, payload, key)
    if replay:
        response.headers["Idempotent-Replayed"] = "true"
        # Header 幂等键走 200 重放；body.request_key 保持 201，兼容 #33 用例。
        if idempotency_key is not None:
            response.status_code = 200
    return result


@router.patch("/reservations/{rid}/seat")
def change_seat(rid: int, body: ChangeSeatIn, user: Owner, session: SessionDep):
    service.expire_due(session)
    return service.change_seat(session, user.id, rid, body.seat_id)


@router.post("/reservations/{reservation_id}/check-in")
def check_in_reservation(
    reservation_id: int,
    user: Owner,
    session: SessionDep,
    body: Annotated[CheckInIn, Body()],
):
    """验证预约归属和签到窗口；若带扫码座位信息则校验座位一致。"""
    return service.check_in(session, user.id, reservation_id, body)


@router.post("/reservations/{reservation_id}/temporary-leave", response_model=ReservationOut)
def temporary_leave(reservation_id: int, user: Owner, session: SessionDep):
    return service.start_temporary_leave(session, user, reservation_id)


@router.post("/reservations/{reservation_id}/return", response_model=ReservationOut)
def return_to_seat(reservation_id: int, user: Owner, session: SessionDep):
    return service.return_from_temporary_leave(session, user, reservation_id)


@router.post("/reservations/{reservation_id}/end")
def end_reservation(
    reservation_id: int,
    body: EndUseIn,
    user: Owner,
    session: SessionDep,
):
    ended, duration_minutes = service.end_use(session, user, reservation_id, confirmed=body.confirm)
    return {
        "ended_reservations": [item.id for item in ended],
        "duration_minutes": duration_minutes,
    }


@router.post("/reservations/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    user: Owner,
    session: SessionDep,
    confirm: bool = True,
):
    if not confirm:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "取消预约前必须确认")
    return service.cancel(session, user.id, reservation_id)


@router.get("/violations", response_model=list[ViolationOut])
def list_my_violations(user: Owner, session: SessionDep):
    return list(
        session.scalars(
            select(ViolationRecord)
            .where(ViolationRecord.user_id == user.id)
            .order_by(ViolationRecord.occurred_at.desc())
        )
    )


@router.post("/appeals", response_model=AppealOut, status_code=status.HTTP_201_CREATED)
def submit_appeal(body: AppealCreate, user: Owner, session: SessionDep):
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
def list_my_appeals(user: Owner, session: SessionDep):
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
    statement = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        statement = statement.where(Notification.is_read.is_(False))
    return list(session.scalars(statement.order_by(Notification.sent_at.desc()).limit(limit)))


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(notification_id: int, user: CurrentUser, session: SessionDep):
    notification = session.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "通知不存在")
    with transaction(session):
        notification.is_read = True
    return notification
