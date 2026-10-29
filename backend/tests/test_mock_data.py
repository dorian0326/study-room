"""演示 Mock 数据：幂等、规则一致性、可登录，以及 dev.py 的导入决策。"""

import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app import mock_data
from app.config import get_settings
from app.models import (
    Appeal,
    Reservation,
    Restriction,
    Seat,
    StudyRoom,
    User,
    ViolationRecord,
)
from app.models import enums as E
from app.services.availability import covers
from app.services.reservations import sweep_reservations
from app.timeutil import tz

# 固定在工作日上午，保证“进行中 / 暂离”状态也能生成
MOMENT = datetime(2026, 10, 28, 10, 40, tzinfo=tz())
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def seeded(api_db):
    with api_db() as s:
        assert mock_data.seed(s, moment=MOMENT) is True
    return api_db


def _count(s, model):
    return s.scalar(select(func.count()).select_from(model))


def test_seed_is_idempotent_and_reset_rebuilds(seeded):
    with seeded() as s:
        before = mock_data.summary(s)
        assert mock_data.seed(s, moment=MOMENT) is False
        assert mock_data.summary(s) == before
        assert mock_data.seed(s, reset=True, moment=MOMENT) is True
        assert mock_data.summary(s) == before


def test_counts_and_states(seeded):
    with seeded() as s:
        assert _count(s, User) == 17
        assert _count(s, StudyRoom) == 4
        assert _count(s, Seat) == 40
        assert _count(s, Reservation) >= 150
        statuses = set(s.scalars(select(Reservation.status).distinct()))
        assert {
            E.ReservationStatus.RESERVED,
            E.ReservationStatus.ACTIVE,
            E.ReservationStatus.TEMP_LEAVE,
            E.ReservationStatus.COMPLETED,
            E.ReservationStatus.CANCELLED,
            E.ReservationStatus.EXPIRED,
            E.ReservationStatus.TIMED_OUT,
        } <= statuses
        assert s.scalar(select(func.count()).where(Reservation.cancel_type == E.CancelType.LATE))
        appeals = set(s.scalars(select(Appeal.result)))
        assert {None, E.AppealResult.APPROVED, E.AppealResult.REJECTED} <= appeals
        assert s.scalar(select(func.count()).where(Seat.status == E.SeatStatus.MAINTENANCE)) == 1
        disabled = s.scalar(select(User).where(User.student_no == mock_data.DISABLED_NO))
        assert disabled.status == E.AccountStatus.DISABLED
        banned = s.scalar(select(User).where(User.student_no == mock_data.BANNED_NO))
        r = s.scalar(select(Restriction).where(Restriction.user_id == banned.id))
        assert r.status == E.RestrictionStatus.ACTIVE and r.end_at > MOMENT


def test_no_overlaps_and_within_opening_hours(seeded):
    with seeded() as s:
        rows = list(s.scalars(select(Reservation).order_by(Reservation.start_time)))
        for key in ("seat_id", "user_id"):
            last_end: dict[int, datetime] = {}
            for r in rows:
                k = getattr(r, key)
                assert k not in last_end or last_end[k] <= r.start_time, (key, r.reservation_no)
                last_end[k] = max(last_end.get(k, r.end_time), r.end_time)
        for r in rows:
            assert covers(s, r.room_id, r.start_time, r.end_time), r.reservation_no
        live = (
            E.ReservationStatus.RESERVED,
            E.ReservationStatus.ACTIVE,
            E.ReservationStatus.TEMP_LEAVE,
        )
        per_user = s.execute(
            select(Reservation.user_id, func.count())
            .where(Reservation.status.in_(live))
            .group_by(Reservation.user_id)
        ).all()
        assert all(n <= 1 for _, n in per_user)
        for r in rows:
            if r.status == E.ReservationStatus.RESERVED:
                assert r.start_time > MOMENT
            if r.status in (E.ReservationStatus.ACTIVE, E.ReservationStatus.TEMP_LEAVE):
                assert r.start_time <= MOMENT < r.end_time
            if r.status in (E.ReservationStatus.COMPLETED, E.ReservationStatus.EXPIRED):
                assert r.end_time <= MOMENT
            assert r.created_at <= MOMENT


def test_sweeper_finds_nothing_due(seeded):
    with seeded() as s:
        counts = sweep_reservations(s, MOMENT + timedelta(seconds=1))
        assert counts["no_show"] == counts["no_checkout"] == counts["temp_leave"] == 0
        assert counts["archived_violations"] == 0
        assert _count(s, ViolationRecord) >= 5


def test_demo_accounts_can_log_in(seeded, client):
    for no, pw, _role, _ in mock_data.demo_accounts():
        r = client.post("/api/auth/login", json={"student_no": no, "password": pw})
        if no == mock_data.DISABLED_NO:
            assert r.status_code == 403
        else:
            assert r.status_code == 200, (no, r.text)


def test_refuses_outside_dev(api_db, monkeypatch):
    monkeypatch.setattr(get_settings(), "env", "prod")
    with api_db() as s, pytest.raises(mock_data.MockDataError):
        mock_data.seed(s)


def _load_dev():
    spec = importlib.util.spec_from_file_location("dev_script", ROOT / "scripts" / "dev.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dev_script_prepare_db(monkeypatch):
    dev = _load_dev()
    calls = []
    runner = lambda cmd, cwd: calls.append([str(c) for c in cmd])  # noqa: E731
    monkeypatch.setenv("STUDYROOM_ENV", "dev")
    assert dev.prepare_db(Path("py"), runner=runner) is True
    assert calls[0][-3:] == ["alembic", "upgrade", "head"]
    assert calls[1][-1] == "seed-mock"
    calls.clear()
    assert dev.prepare_db(Path("py"), mock=False, runner=runner) is False
    assert len(calls) == 1
    calls.clear()
    assert dev.prepare_db(Path("py"), reset=True, runner=runner) is True
    assert calls[1][-1] == "--reset"
    calls.clear()
    monkeypatch.setenv("STUDYROOM_ENV", "prod")
    assert dev.prepare_db(Path("py"), runner=runner) is False
    assert len(calls) == 1  # 只迁移，不导入


def test_dev_script_flags():
    dev = _load_dev()
    a = dev.build_parser().parse_args(["--no-mock"])
    assert a.no_mock and a.cmd is None
    a = dev.build_parser().parse_args(["dev", "--reset-mock"])
    assert a.reset_mock
