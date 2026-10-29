"""自习室、座位与本人预约接口（#10–#16）。"""

from datetime import date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import timeutil
from app.deps import SessionDep, require_permission
from app.models import Reservation, Seat, User
from app.models import enums as E
from app.schemas.reservations import (
    ChangeSeatIn,
    CheckInIn,
    PublicRoom,
    PublicSeat,
    ReservationIn,
    ReservationOut,
)
from app.services import availability as catalog
from app.services import reservations as service

router = APIRouter(tags=["reservations"])
Reader = Annotated[User, Depends(require_permission("room:read"))]
Owner = Annotated[User, Depends(require_permission("reservation:own"))]
IdempotencyKey = Annotated[
    str, Header(alias="Idempotency-Key", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
]


def _window(day: date | None, start: time | None, end: time | None):
    if day is None and start is None and end is None:
        return timeutil.now(), None
    if day is None or start is None or end is None:
        raise catalog.BookingError(422, "查询时请同时提供日期、开始时间和结束时间")
    if start.tzinfo is not None or end.tzinfo is not None or start >= end:
        raise catalog.BookingError(422, "查询时段须为北京时间，开始早于结束且不跨零点")
    return datetime.combine(day, start, timeutil.tz()), datetime.combine(day, end, timeutil.tz())


@router.get("/rooms", response_model=list[PublicRoom])
def list_rooms(
    _: Reader,
    session: SessionDep,
    day: Annotated[date | None, Query(alias="date")] = None,
):
    with Session(session.get_bind()) as read:
        return catalog.room_list(read, day or timeutil.now().date())


@router.get("/seats", response_model=list[PublicSeat])
def list_seats(
    _: Reader,
    session: SessionDep,
    room_id: Annotated[int | None, Query(gt=0)] = None,
    zone_type: E.ZoneType | None = None,
    available_only: bool = False,
    day: Annotated[date | None, Query(alias="date")] = None,
    start_time: time | None = None,
    end_time: time | None = None,
):
    start, end = _window(day, start_time, end_time)
    service.expire_due(session)
    with Session(session.get_bind()) as read:
        return catalog.seat_list(read, start, end, room_id, zone_type, available_only)


@router.get("/seats/{seat_id}", response_model=PublicSeat)
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


@router.get("/reservations/current", response_model=list[ReservationOut])
def current_reservations(user: Owner, session: SessionDep):
    service.expire_due(session)
    with Session(session.get_bind()) as read:
        bookings = read.scalars(
            select(Reservation)
            .where(
                Reservation.user_id == user.id,
                Reservation.status.in_(E.ACTIVE_RESERVATION_STATUSES),
            )
            .order_by(Reservation.start_time)
        )
        return [service.reservation_out(read, r) for r in bookings]


@router.get("/reservations/{rid}", response_model=ReservationOut)
def reservation_detail(rid: int, user: Owner, session: SessionDep):
    service.expire_due(session)
    with Session(session.get_bind()) as read:
        return service.reservation_out(read, service._owned(read, user.id, rid))


@router.post("/reservations", response_model=ReservationOut, status_code=201)
def create_reservation(
    body: ReservationIn,
    user: Owner,
    session: SessionDep,
    response: Response,
    idempotency_key: IdempotencyKey,
):
    result, replay = service.create(session, user.id, body, idempotency_key)
    if replay:
        response.status_code = 200
        response.headers["Idempotent-Replayed"] = "true"
    return result


@router.patch("/reservations/{rid}/seat", response_model=ReservationOut)
def change_seat(rid: int, body: ChangeSeatIn, user: Owner, session: SessionDep):
    service.expire_due(session)
    return service.change_seat(session, user.id, rid, body.seat_id)


@router.post("/reservations/{rid}/cancel", response_model=ReservationOut)
def cancel_reservation(rid: int, user: Owner, session: SessionDep):
    service.expire_due(session)
    return service.cancel(session, user.id, rid)


@router.post("/reservations/{rid}/check-in", response_model=ReservationOut)
def check_in(rid: int, body: CheckInIn, user: Owner, session: SessionDep):
    # 超窗时由服务在同一事务中提交失效结果，再返回明确错误。
    return service.check_in(session, user.id, rid, body)
