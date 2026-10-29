"""需求缺口验收：BR-093/062/065/094a、区域自动分配、暂离超时类型、设施筛选。"""

from datetime import datetime, time, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app import timeutil
from app.models import (
    Notification,
    OpeningSchedule,
    Reservation,
    Seat,
    StudyRoom,
    User,
    ViolationRecord,
)
from app.models import enums as E
from app.services.reservations import sweep_reservations
from app.services.violations import archive_expired_violations, record_violation


@pytest.fixture
def clock(monkeypatch):
    clock = SimpleNamespace(at=datetime(2026, 11, 2, 8, tzinfo=timeutil.tz()))
    monkeypatch.setattr(timeutil, "now", lambda: clock.at)
    return clock


@pytest.fixture
def room_seats(api_db, clock):
    with api_db() as s:
        room = StudyRoom(name="缺口自习室", location="图书馆", floor="3层", capacity=10)
        seats = [
            Seat(room=room, code="Q01", zone_type=E.ZoneType.QUIET, has_power=True, by_window=True),
            Seat(room=room, code="Q02", zone_type=E.ZoneType.QUIET, accessible=True),
            Seat(room=room, code="D01", zone_type=E.ZoneType.DISCUSSION, has_power=True),
        ]
        s.add_all([room, *seats])
        s.flush()
        for kind in E.DayType:
            s.add(
                OpeningSchedule(
                    room_id=room.id, day_type=kind, open_time=time(8), close_time=time(22)
                )
            )
        s.commit()
        return SimpleNamespace(
            room=room.id,
            q1=seats[0].id,
            q2=seats[1].id,
            d1=seats[2].id,
        )


def _hdr(login, make_user, sno="20260001", roles=("user",)):
    return login(*make_user(student_no=sno, roles=roles))


def test_br093_no_checkout_merge(api_db, make_user, clock):
    """两次未签退合并为 1 次计入警告；第三次再合并。"""
    make_user()
    with api_db() as s:
        user = s.scalar(select(User))
        uid = user.id
        v1 = record_violation(
            s,
            user_id=uid,
            violation_type=E.ViolationType.NO_CHECKOUT,
            reservation_id=None,
            description="第一次未结束",
            occurred_at=clock.at,
        )
        s.commit()
        assert v1.is_offset is True
        assert v1.period_seq == 0

        v2 = record_violation(
            s,
            user_id=uid,
            violation_type=E.ViolationType.NO_CHECKOUT,
            reservation_id=None,
            description="第二次未结束",
            occurred_at=clock.at + timedelta(hours=1),
        )
        s.commit()
        assert v2.is_offset is False
        assert v2.period_seq == 1

        v3 = record_violation(
            s,
            user_id=uid,
            violation_type=E.ViolationType.NO_CHECKOUT,
            reservation_id=None,
            description="第三次未结束",
            occurred_at=clock.at + timedelta(hours=2),
        )
        s.commit()
        assert v3.is_offset is True
        assert v3.period_seq == 0

        counted = list(
            s.scalars(
                select(ViolationRecord).where(
                    ViolationRecord.user_id == uid, ViolationRecord.is_offset.is_(False)
                )
            )
        )
        assert len(counted) == 1


def test_temp_leave_timeout_type(api_db, make_user, clock, room_seats):
    make_user()
    with api_db() as s:
        user = s.scalar(select(User))
        seat = s.get(Seat, room_seats.q1)
        start = clock.at + timedelta(hours=1)
        end = start + timedelta(hours=2)
        reservation = Reservation(
            reservation_no="SRTEST1",
            user_id=user.id,
            room_id=seat.room_id,
            seat_id=seat.id,
            start_time=start,
            end_time=end,
            status=E.ReservationStatus.TEMP_LEAVE,
            temp_leave_at=clock.at - timedelta(minutes=31),
            temp_leave_state=E.TempLeaveState.WAITING,
        )
        s.add(reservation)
        s.commit()
        rid = reservation.id

    with api_db() as s:
        counts = sweep_reservations(s, clock.at)
        assert counts["temp_leave"] == 1
        v = s.scalar(select(ViolationRecord).where(ViolationRecord.reservation_id == rid))
        assert v is not None
        assert v.violation_type == E.ViolationType.TEMP_LEAVE_TIMEOUT


def test_archive_expired_violations(api_db, make_user, clock):
    make_user()
    with api_db() as s:
        user = s.scalar(select(User))
        old = clock.at - timedelta(days=20)
        v = record_violation(
            s,
            user_id=user.id,
            violation_type=E.ViolationType.NO_SHOW,
            reservation_id=None,
            description="过期违规",
            occurred_at=old,
        )
        # 强制把 period_start 推到窗口外
        v.period_start = old
        s.commit()
        n = archive_expired_violations(s, clock.at)
        s.commit()
        assert n == 1
        s.refresh(v)
        assert v.state == E.ViolationState.ARCHIVED


def test_zone_auto_assign(client, make_user, login, room_seats, clock):
    h = _hdr(login, make_user)
    body = {
        "room_id": room_seats.room,
        "zone_type": "quiet",
        "start_time": "2026-11-02T09:00:00+08:00",
        "end_time": "2026-11-02T10:00:00+08:00",
        "request_key": uuid4().hex,
    }
    r = client.post("/api/reservations", headers=h, json=body)
    assert r.status_code == 201, r.text
    assert r.json()["seat_id"] == room_seats.q1  # 按编号 Q01 优先

    # 再约同一区域应分到 Q02
    h2 = _hdr(login, make_user, sno="20260002")
    body["request_key"] = uuid4().hex
    r2 = client.post("/api/reservations", headers=h2, json=body)
    assert r2.status_code == 201, r2.text
    assert r2.json()["seat_id"] == room_seats.q2


def test_facility_filters(client, make_user, login, room_seats, clock):
    h = _hdr(login, make_user)
    params = {
        "date": "2026-11-02",
        "start_time": "09:00",
        "end_time": "10:00",
        "room_id": room_seats.room,
        "has_power": True,
    }
    ids = {x["id"] for x in client.get("/api/seats", headers=h, params=params).json()}
    assert ids == {room_seats.q1, room_seats.d1}
    params = {
        "date": "2026-11-02",
        "start_time": "09:00",
        "end_time": "10:00",
        "room_id": room_seats.room,
        "accessible": True,
    }
    ids = {x["id"] for x in client.get("/api/seats", headers=h, params=params).json()}
    assert ids == {room_seats.q2}


def test_close_room_cancels_reservations(client, make_user, login, room_seats, clock, api_db):
    user_h = _hdr(login, make_user)
    admin = _hdr(login, make_user, sno="A0000001", roles=("admin",))
    body = {
        "seat_id": room_seats.q1,
        "start_time": "2026-11-02T09:00:00+08:00",
        "end_time": "2026-11-02T10:00:00+08:00",
        "request_key": uuid4().hex,
    }
    r = client.post("/api/reservations", headers=user_h, json=body)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    resp = client.patch(
        f"/api/admin/rooms/{room_seats.room}/status",
        headers=admin,
        json={"status": "closed"},
    )
    assert resp.status_code == 200, resp.text

    with api_db() as s:
        reservation = s.get(Reservation, rid)
        assert reservation.status == E.ReservationStatus.ADMIN_CANCELLED
        notes = list(
            s.scalars(select(Notification).where(Notification.user_id == reservation.user_id))
        )
        assert any("已关闭" in n.content for n in notes)


def test_schedule_change_cancels_conflicting(client, make_user, login, room_seats, clock, api_db):
    user_h = _hdr(login, make_user)
    admin = _hdr(login, make_user, sno="A0000001", roles=("admin",))
    body = {
        "seat_id": room_seats.q1,
        "start_time": "2026-11-02T20:00:00+08:00",
        "end_time": "2026-11-02T21:00:00+08:00",
        "request_key": uuid4().hex,
    }
    r = client.post("/api/reservations", headers=user_h, json=body)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    # 找到 weekday schedule id
    schedules = client.get(f"/api/admin/rooms/{room_seats.room}/schedules", headers=admin).json()
    # 2026-11-02 is Monday -> weekday
    sch = next(x for x in schedules if x["day_type"] == "weekday")
    # 把关闭时间提前到 18:00，使 20-21 的预约冲突
    resp = client.put(
        f"/api/admin/rooms/{room_seats.room}/schedules/{sch['id']}",
        headers=admin,
        json={
            "day_type": "weekday",
            "open_time": "08:00:00",
            "close_time": "18:00:00",
            "enabled": True,
        },
    )
    assert resp.status_code == 200, resp.text

    with api_db() as s:
        reservation = s.get(Reservation, rid)
        assert reservation.status == E.ReservationStatus.ADMIN_CANCELLED
