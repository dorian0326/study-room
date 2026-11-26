"""创建预约、输入校验与冲突检测的单元测试。"""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.models import ArrivalRecord, Reservation
from app.schemas.reservations import ReservationIn
from app.services import reservations as service
from app.services.availability import BookingError


def test_create_saves_booking_and_arrival(session, seat, booking, service_env):
    body = ReservationIn(seat_id=seat.id, start_time=booking.start_time, end_time=booking.end_time)

    result, replay = service.create(session, 7, body, "unit-create")

    assert replay is False
    assert isinstance(result, Reservation)
    assert (result.user_id, result.seat, result.start_time, result.end_time) == (
        7, seat, body.start_time, body.end_time,
    )
    added = [call.args[0] for call in session.add.call_args_list]
    assert any(isinstance(item, ArrivalRecord) and item.seat_id == seat.id for item in added)
    service_env._check_slot.assert_called_once_with(
        session, seat, body.start_time, body.end_time, 7,
    )
    service_env.create_notification.assert_called_once()


@pytest.mark.parametrize("offset", [timedelta(minutes=-1), timedelta(days=2)])
def test_create_rejects_past_or_too_distant_start(session, seat, moment, service_env, offset):
    start = moment + offset
    body = ReservationIn(seat_id=seat.id, start_time=start, end_time=start + timedelta(hours=1))
    with pytest.raises(BookingError) as error:
        service.create(session, 7, body, None)
    assert error.value.status_code == 422
    session.add.assert_not_called()


@pytest.mark.parametrize(
    "covered, overlaps, own_conflict, code",
    [(False, False, False, 422), (True, True, False, 409), (True, False, True, 409)],
)
def test_slot_rejects_closed_hours_or_conflicts(
    monkeypatch, session, seat, booking, covered, overlaps, own_conflict, code,
):
    monkeypatch.setattr(service, "covers", lambda *_: covered)
    monkeypatch.setattr(service, "overlapping", lambda *_: [booking] if overlaps else [])
    session.scalar.return_value = booking.id if own_conflict else None
    with pytest.raises(BookingError) as error:
        service._check_slot(session, seat, booking.start_time, booking.end_time, 7)
    assert error.value.status_code == code


def test_slot_ignores_the_booking_being_modified(monkeypatch, session, seat, booking):
    monkeypatch.setattr(service, "covers", lambda *_: True)
    monkeypatch.setattr(service, "overlapping", lambda *_: [booking])
    service._check_slot(session, seat, booking.start_time, booking.end_time, 7, booking.id)


@pytest.mark.parametrize("minutes", [0, -1, 24 * 60])
def test_invalid_time_range_is_rejected(moment, minutes):
    with pytest.raises(ValidationError):
        ReservationIn(seat_id=11, start_time=moment, end_time=moment + timedelta(minutes=minutes))


def test_valid_slot_passes(monkeypatch, session, seat, booking):
    monkeypatch.setattr(service, "covers", lambda *_: True)
    monkeypatch.setattr(service, "overlapping", lambda *_: [])
    service._check_slot(session, seat, booking.start_time, booking.end_time, 7)
