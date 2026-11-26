"""修改预约仅换座的单元测试。"""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.models import Seat
from app.models import enums as E
from app.schemas.reservations import ChangeSeatIn
from app.services import reservations as service
from app.services.availability import BookingError


def test_change_seat_preserves_reservation_times(session, seat, booking, service_env):
    target = Seat(id=12, room_id=1, room=seat.room, code="A02")
    service_env._seat.return_value = target
    original_times = (booking.start_time, booking.end_time)

    result = service.change_seat(session, 7, booking.id, target.id)

    assert result.seat_id == 12
    assert (result.start_time, result.end_time) == original_times
    service_env._check_slot.assert_called_once_with(
        session, target, *original_times, 7, booking.id,
    )
    assert service_env._sync_seat.call_count == 2


@pytest.mark.parametrize("status", [E.ReservationStatus.ACTIVE, E.ReservationStatus.CANCELLED])
def test_only_reserved_booking_can_change(session, booking, service_env, status):
    booking.status = status
    with pytest.raises(BookingError) as error:
        service.change_seat(session, 7, booking.id, 12)
    assert error.value.status_code == 409
    assert booking.seat_id == 11


def test_overdue_booking_cannot_change(session, booking, moment, service_env):
    booking.start_time = moment - timedelta(minutes=16)
    with pytest.raises(BookingError) as error:
        service.change_seat(session, 7, booking.id, 12)
    assert error.value.status_code == 409


def test_conflicting_target_preserves_original_seat(session, booking, service_env):
    original = booking.seat
    service_env._check_slot.side_effect = BookingError(409, "目标座位已被预约")
    with pytest.raises(BookingError):
        service.change_seat(session, 7, booking.id, 12)
    assert booking.seat is original
    service_env._sync_seat.assert_not_called()


def test_change_request_rejects_time_modification(moment):
    with pytest.raises(ValidationError):
        ChangeSeatIn(seat_id=12, start_time=moment)
