"""并发控制的事务策略与重复提交分支；不模拟真实数据库并发。"""

from contextlib import nullcontext
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app.schemas.reservations import ReservationIn
from app.services import reservations as service
from app.services.availability import BookingError


def test_same_key_and_payload_replays_without_writing(session, booking, service_env):
    body = ReservationIn(seat_id=11, start_time=booking.start_time, end_time=booking.end_time)
    first, replay = service.create(session, 7, body, "unit-key")
    assert replay is False
    session.scalar.return_value = first
    session.add.reset_mock()
    service_env._check_slot.reset_mock()
    service_env.create_notification.reset_mock()

    result, replay = service.create(session, 7, body, "unit-key")

    assert result is first
    assert replay is True
    session.add.assert_not_called()
    service_env._check_slot.assert_not_called()
    service_env.create_notification.assert_not_called()


@pytest.mark.parametrize("other_user, other_payload", [(True, False), (False, True)])
def test_key_cannot_be_reused_for_different_request(
    session,
    booking,
    service_env,
    other_user,
    other_payload,
):
    body = ReservationIn(seat_id=11, start_time=booking.start_time, end_time=booking.end_time)
    previous, _ = service.create(session, 7, body, "unit-key")
    session.scalar.return_value = previous
    session.add.reset_mock()
    if other_payload:
        body = body.model_copy(update={"seat_id": 12})
    with pytest.raises(BookingError) as error:
        service.create(session, 8 if other_user else 7, body, "unit-key")
    assert error.value.status_code == 409
    session.add.assert_not_called()


def test_write_transaction_requests_immediate_lock(monkeypatch, session):
    factory = Mock(return_value=nullcontext(session))
    transaction = Mock(return_value=nullcontext())
    monkeypatch.setattr(service, "Session", factory)
    monkeypatch.setattr(service, "transaction", transaction)

    with service.write_transaction(session) as actual:
        assert actual is session

    factory.assert_called_once_with(
        session.get_bind.return_value,
        expire_on_commit=False,
        autoflush=False,
    )
    transaction.assert_called_once_with(session, immediate=True)


@pytest.mark.parametrize(
    "failure, code",
    [
        (OperationalError("write", {}, Exception("database is locked")), 503),
        (OperationalError("write", {}, Exception("database is busy")), 503),
        (IntegrityError("write", {}, Exception("unique constraint")), 409),
    ],
)
def test_write_errors_become_booking_errors(monkeypatch, session, failure, code):
    monkeypatch.setattr(service, "Session", Mock(return_value=nullcontext(session)))
    monkeypatch.setattr(service, "transaction", Mock(return_value=nullcontext()))
    with pytest.raises(BookingError) as error, service.write_transaction(session):
        raise failure
    assert error.value.status_code == code


def test_unrelated_database_error_is_preserved(monkeypatch, session):
    monkeypatch.setattr(service, "Session", Mock(return_value=nullcontext(session)))
    monkeypatch.setattr(service, "transaction", Mock(return_value=nullcontext()))
    failure = OperationalError("read", {}, Exception("no such table"))
    with pytest.raises(OperationalError) as error, service.write_transaction(session):
        raise failure
    assert error.value is failure
