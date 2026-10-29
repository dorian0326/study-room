"""开放日历、时段冲突与座位展示状态（#10–#12）。"""

from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import CalendarDay, OpeningSchedule, Reservation, Seat, StudyRoom
from app.models import enums as E
from app.schemas.reservations import OpeningWindow, PublicRoom, PublicSeat
from app.services.settings import get_business_settings
from app.timeutil import tz


class BookingError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


BLOCKED_SEAT_STATUSES = (E.SeatStatus.MAINTENANCE, E.SeatStatus.CLOSED, E.SeatStatus.DISABLED)


def opening_windows(session: Session, room_id: int, day: date) -> list[tuple[time, time]]:
    special = session.get(CalendarDay, day)
    kind = (
        special.day_type
        if special
        else (E.DayType.WEEKEND if day.weekday() >= 5 else E.DayType.WEEKDAY)
    )
    settings = get_business_settings(session)
    schedules = session.scalars(
        select(OpeningSchedule)
        .where(
            OpeningSchedule.room_id == room_id,
            OpeningSchedule.day_type == kind,
            OpeningSchedule.enabled.is_(True),
            (OpeningSchedule.effective_from.is_(None) | (OpeningSchedule.effective_from <= day)),
            (OpeningSchedule.effective_to.is_(None) | (OpeningSchedule.effective_to >= day)),
        )
        .order_by(OpeningSchedule.open_time)
    )
    merged: list[tuple[time, time]] = []
    for schedule in schedules:
        start = max(schedule.open_time, settings.opening_earliest, time(6))
        end = min(schedule.close_time, settings.opening_latest, time(23, 30))
        if start >= end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def covers(session: Session, room_id: int, start: datetime, end: datetime | None) -> bool:
    start = start.astimezone(tz())
    end = end.astimezone(tz()) if end is not None else None
    if end is not None and (end <= start or start.date() != end.date()):
        return False
    return any(
        opened <= start.time() < closed and (end is None or end.time() <= closed)
        for opened, closed in opening_windows(session, room_id, start.date())
    )


def overlapping(session: Session, seat_id: int, start: datetime, end: datetime):
    """半开区间 [start,end)，相邻预约不冲突。调用方在写入前须持有写锁。"""
    return session.scalars(
        select(Reservation).where(
            Reservation.seat_id == seat_id,
            Reservation.status.in_(E.ACTIVE_RESERVATION_STATUSES),
            Reservation.start_time < end,
            Reservation.end_time > start,
        )
    )


def seat_status(
    session: Session, seat: Seat, start: datetime, end: datetime | None = None
) -> E.SeatStatus:
    if seat.status in BLOCKED_SEAT_STATUSES:
        return seat.status
    if seat.room.status != E.RoomStatus.OPEN or not covers(session, seat.room_id, start, end):
        return E.SeatStatus.CLOSED
    if end is None:
        bookings = session.scalars(
            select(Reservation).where(
                Reservation.seat_id == seat.id,
                Reservation.status.in_(E.ACTIVE_RESERVATION_STATUSES),
            )
        )
        bookings = [
            r
            for r in bookings
            if r.status != E.ReservationStatus.RESERVED or r.start_time <= start < r.end_time
        ]
    else:
        bookings = list(overlapping(session, seat.id, start, end))
    if any(
        r.status in (E.ReservationStatus.ACTIVE, E.ReservationStatus.TEMP_LEAVE) for r in bookings
    ):
        return E.SeatStatus.IN_USE
    return E.SeatStatus.RESERVED if bookings else E.SeatStatus.AVAILABLE


def room_list(session: Session, day: date) -> list[PublicRoom]:
    return [
        PublicRoom(
            id=room.id,
            name=room.name,
            location=room.location,
            floor=room.floor,
            capacity=room.capacity,
            facilities=room.facilities,
            status=room.status,
            date=day,
            opening_hours=[
                OpeningWindow(open_time=a, close_time=b)
                for a, b in opening_windows(session, room.id, day)
            ],
        )
        for room in session.scalars(select(StudyRoom).order_by(StudyRoom.id))
    ]


def seat_out(session: Session, seat: Seat, start: datetime, end: datetime | None) -> PublicSeat:
    return PublicSeat(
        id=seat.id,
        room_id=seat.room_id,
        room_name=seat.room.name,
        code=seat.code,
        location=seat.room.location,
        floor=seat.room.floor,
        facilities=seat.room.facilities,
        zone_type=seat.zone_type,
        has_power=seat.has_power,
        by_window=seat.by_window,
        accessible=seat.accessible,
        status=seat_status(session, seat, start, end),
        qr_payload=f"studyroom:seat:{seat.id}",
    )


def seat_list(
    session: Session,
    start: datetime,
    end: datetime | None,
    room_id: int | None,
    zone_type: E.ZoneType | None,
    available_only: bool,
) -> list[PublicSeat]:
    query = select(Seat).options(selectinload(Seat.room)).order_by(Seat.room_id, Seat.code)
    if room_id is not None:
        if session.get(StudyRoom, room_id) is None:
            raise BookingError(404, "自习室不存在")
        query = query.where(Seat.room_id == room_id)
    if zone_type is not None:
        query = query.where(Seat.zone_type == zone_type)
    result = [seat_out(session, seat, start, end) for seat in session.scalars(query)]
    return [s for s in result if s.status == E.SeatStatus.AVAILABLE] if available_only else result
