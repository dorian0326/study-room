"""座位详情与实时状态计算的单元测试。"""

from datetime import timedelta

import pytest

from app.models import enums as E
from app.services import availability as catalog


@pytest.mark.parametrize("status", catalog.BLOCKED_SEAT_STATUSES)
def test_blocked_seat_keeps_status(session, seat, moment, status):
    seat.status = status
    assert catalog.seat_status(session, seat, moment) == status
    session.scalars.assert_not_called()


@pytest.mark.parametrize("room_open, covered", [(False, True), (True, False)])
def test_closed_room_or_outside_opening_hours(
    monkeypatch, session, seat, moment, room_open, covered,
):
    seat.room.status = E.RoomStatus.OPEN if room_open else E.RoomStatus.CLOSED
    monkeypatch.setattr(catalog, "covers", lambda *_: covered)
    assert catalog.seat_status(session, seat, moment) == E.SeatStatus.CLOSED


@pytest.mark.parametrize(
    "status, expected",
    [
        (None, E.SeatStatus.AVAILABLE),
        (E.ReservationStatus.RESERVED, E.SeatStatus.RESERVED),
        (E.ReservationStatus.ACTIVE, E.SeatStatus.IN_USE),
        (E.ReservationStatus.TEMP_LEAVE, E.SeatStatus.IN_USE),
    ],
)
def test_current_booking_determines_status(
    monkeypatch, session, seat, booking, moment, status, expected,
):
    monkeypatch.setattr(catalog, "covers", lambda *_: True)
    booking.start_time = moment - timedelta(minutes=5)
    booking.status = status
    session.scalars.return_value = [booking] if status else []
    assert catalog.seat_status(session, seat, moment) == expected


def test_future_booking_does_not_occupy_seat_now(monkeypatch, session, seat, booking, moment):
    monkeypatch.setattr(catalog, "covers", lambda *_: True)
    session.scalars.return_value = [booking]
    assert catalog.seat_status(session, seat, moment) == E.SeatStatus.AVAILABLE


def test_detail_contains_facilities_and_qr_payload(monkeypatch, session, seat, moment):
    monkeypatch.setattr(catalog, "seat_status", lambda *_: E.SeatStatus.AVAILABLE)
    result = catalog.seat_out(session, seat, moment, None)
    assert (result.room_name, result.code, result.floor) == ("一号自习室", "A01", "3")
    assert result.has_power is True
    assert result.by_window is True
    assert result.accessible is False
    assert result.qr_payload == "studyroom:seat:11"
