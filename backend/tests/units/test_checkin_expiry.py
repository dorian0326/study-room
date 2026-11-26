"""扫码签到与超窗自动释放的单元测试。"""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models import enums as E
from app.schemas.reservations import CheckInIn
from app.services import reservations as service
from app.services.availability import BookingError


@pytest.mark.parametrize("use_code", [False, True])
@pytest.mark.parametrize(
    "offset, arrival_status",
    [(-900, E.ArrivalStatus.EARLY), (0, E.ArrivalStatus.ON_TIME), (900, E.ArrivalStatus.LATE)],
)
def test_qr_checkin_within_window(
    monkeypatch, session, booking, moment, service_env, use_code, offset, arrival_status,
):
    booking.start_time = moment - timedelta(seconds=offset)
    arrival = SimpleNamespace()
    monkeypatch.setattr(service, "_arrival", lambda *_: arrival)
    body = CheckInIn(room_id=1, seat_code="A01") if use_code else CheckInIn(seat_id=11)

    result = service.check_in(session, 7, booking.id, body)

    assert result.status == E.ReservationStatus.ACTIVE
    assert arrival.arrived_at == moment
    assert arrival.arrival_method == E.ArrivalMethod.QR
    assert arrival.arrival_status == arrival_status
    service_env._sync_seat.assert_called_once_with(session, booking.seat, moment)


def test_qr_seat_must_match_booking(session, booking, service_env):
    with pytest.raises(BookingError) as error:
        service.check_in(session, 7, booking.id, CheckInIn(seat_id=999))
    assert error.value.status_code == 409
    assert booking.status == E.ReservationStatus.RESERVED


def test_checkin_before_window_fails(session, booking, service_env):
    with pytest.raises(BookingError) as error:
        service.check_in(session, 7, booking.id, CheckInIn(seat_id=11))
    assert error.value.status_code == 409
    assert booking.status == E.ReservationStatus.RESERVED


def test_repeated_qr_checkin_is_idempotent(session, booking, service_env):
    booking.status = E.ReservationStatus.ACTIVE
    assert service.check_in(session, 7, booking.id, CheckInIn(seat_id=11)) is booking
    service_env._sync_seat.assert_not_called()


@pytest.mark.parametrize("offset, expected", [(900, False), (901, True)])
def test_no_show_grace_boundary(booking, offset, expected):
    assert service._overdue(booking, booking.start_time + timedelta(seconds=offset), 15) is expected


def test_booking_end_is_overdue_even_within_grace(booking):
    booking.end_time = booking.start_time + timedelta(minutes=5)
    assert service._overdue(booking, booking.end_time, 15) is True


def test_late_checkin_expires_booking(monkeypatch, session, booking, moment, service_env):
    booking.start_time = moment - timedelta(minutes=16)
    expire = Mock()
    monkeypatch.setattr(service, "_expire_one", expire)
    with pytest.raises(BookingError) as error:
        service.check_in(session, 7, booking.id, CheckInIn(seat_id=11))
    assert error.value.status_code == 409
    expire.assert_called_once_with(session, booking, moment)


def test_expiry_records_no_show_and_releases_seat(monkeypatch, session, booking, moment):
    violation = Mock()
    monkeypatch.setattr(service, "_record_violation", violation)
    booking.seat.status = E.SeatStatus.RESERVED
    session.scalars.return_value = []

    service._expire_one(session, booking, moment)

    assert booking.status == E.ReservationStatus.EXPIRED
    assert booking.expire_reason == "no_show"
    assert booking.seat.status == E.SeatStatus.AVAILABLE
    violation.assert_called_once_with(session, booking, E.ViolationType.NO_SHOW, moment)


def test_expiry_preserves_maintenance_status(monkeypatch, session, booking, moment):
    monkeypatch.setattr(service, "_record_violation", Mock())
    booking.seat.status = E.SeatStatus.MAINTENANCE
    service._expire_one(session, booking, moment)
    assert booking.seat.status == E.SeatStatus.MAINTENANCE


@pytest.mark.parametrize("count", [0, 2])
def test_expiry_sweep_processes_candidates(monkeypatch, session, booking, moment, count):
    monkeypatch.setattr(
        service, "get_business_settings", lambda _: SimpleNamespace(no_show_after_minutes=15),
    )
    candidates = [booking, SimpleNamespace(id=22)][:count]
    session.scalars.return_value = candidates
    expire = Mock()
    monkeypatch.setattr(service, "_expire_one", expire)

    assert service._expire_due(session, moment) == count
    assert [call.args for call in expire.call_args_list] == [
        (session, item, moment) for item in candidates
    ]
