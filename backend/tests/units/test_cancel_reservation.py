"""取消预约与迟取消违规边界的单元测试。"""

from datetime import timedelta

import pytest

from app.models import enums as E
from app.services import reservations as service
from app.services.availability import BookingError


@pytest.mark.parametrize("seconds, late", [(901, False), (900, True), (899, True)])
def test_cancel_classifies_fifteen_minute_boundary(
    session,
    booking,
    moment,
    service_env,
    seconds,
    late,
):
    booking.start_time = moment + timedelta(seconds=seconds)

    result = service.cancel(session, 7, booking.id)

    assert result.status == E.ReservationStatus.CANCELLED
    assert result.cancel_type == (E.CancelType.LATE if late else E.CancelType.NORMAL)
    assert result.cancelled_at == moment
    if late:
        service_env._record_violation.assert_called_once_with(
            session,
            booking,
            E.ViolationType.LATE_CANCEL,
            moment,
        )
    else:
        service_env._record_violation.assert_not_called()
    service_env._sync_seat.assert_called_once_with(session, booking.seat, moment)
    service_env._restriction.assert_not_called()


def test_repeated_cancel_does_not_repeat_violation_or_notification(session, booking, service_env):
    service.cancel(session, 7, booking.id)
    service_env.create_notification.reset_mock()
    service_env._record_violation.reset_mock()
    service_env._sync_seat.reset_mock()

    assert service.cancel(session, 7, booking.id) is booking

    service_env.create_notification.assert_not_called()
    service_env._record_violation.assert_not_called()
    service_env._sync_seat.assert_not_called()


@pytest.mark.parametrize("status", [E.ReservationStatus.ACTIVE, E.ReservationStatus.EXPIRED])
def test_cancel_rejects_non_reserved_booking(session, booking, service_env, status):
    booking.status = status
    with pytest.raises(BookingError) as error:
        service.cancel(session, 7, booking.id)
    assert error.value.status_code == 409
    assert booking.status == status


@pytest.mark.parametrize("seconds", [0, -1])
def test_cancel_rejects_started_booking(session, booking, moment, service_env, seconds):
    booking.start_time = moment + timedelta(seconds=seconds)
    with pytest.raises(BookingError) as error:
        service.cancel(session, 7, booking.id)
    assert error.value.status_code == 409
    service_env._record_violation.assert_not_called()
