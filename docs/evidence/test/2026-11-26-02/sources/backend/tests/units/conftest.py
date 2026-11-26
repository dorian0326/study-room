"""单元测试共用对象：仅使用内存对象和 Mock，不建表、不请求 HTTP 接口。"""

from contextlib import nullcontext
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.models import Reservation, Seat, StudyRoom
from app.models import enums as E
from app.services import reservations
from app.timeutil import tz


@pytest.fixture
def moment():
    return datetime(2026, 11, 26, 10, tzinfo=tz())


@pytest.fixture
def session():
    mocked = Mock(spec=Session)
    mocked.scalar.return_value = None
    mocked.scalars.return_value = []
    return mocked


@pytest.fixture
def seat():
    room = StudyRoom(
        id=1, name="一号自习室", location="图书馆", floor="3",
        capacity=20, facilities="空调", status=E.RoomStatus.OPEN,
    )
    return Seat(
        id=11, room_id=1, room=room, code="A01", zone_type=E.ZoneType.QUIET,
        status=E.SeatStatus.AVAILABLE, has_power=True, by_window=True, accessible=False,
    )


@pytest.fixture
def booking(seat, moment):
    return Reservation(
        id=21, reservation_no="SR-UNIT-21", user_id=7, room_id=seat.room_id,
        seat_id=seat.id, seat=seat, start_time=moment + timedelta(hours=1),
        end_time=moment + timedelta(hours=2), status=E.ReservationStatus.RESERVED,
    )


@pytest.fixture
def service_env(monkeypatch, session, moment, seat, booking):
    """隔离被测业务函数的外部依赖；每个测试只恢复自己要测的真实行为。"""
    monkeypatch.setattr(reservations, "write_transaction", lambda _: nullcontext(session))
    monkeypatch.setattr(reservations, "now", lambda: moment)
    mocks = SimpleNamespace()
    for name in (
        "_user", "_restriction", "_expire_due", "_check_slot", "_sync_seat",
        "_record_violation", "create_notification",
    ):
        mock = Mock()
        monkeypatch.setattr(reservations, name, mock)
        setattr(mocks, name, mock)
    mocks._owned = Mock(return_value=booking)
    mocks._seat = Mock(return_value=seat)
    mocks.reservation_out = Mock(side_effect=lambda _, reservation: reservation)
    for name in ("_owned", "_seat", "reservation_out"):
        monkeypatch.setattr(reservations, name, getattr(mocks, name))
    settings = SimpleNamespace(
        advance_booking_days=1, no_show_after_minutes=15,
        late_cancel_minutes=15, checkin_open_before_minutes=15,
    )
    monkeypatch.setattr(reservations, "get_business_settings", lambda _: settings)
    return mocks
