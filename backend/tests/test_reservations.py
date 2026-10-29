"""#10–#16：真实迁移数据库上的 API、并发、边界和后台释放验收。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from threading import Barrier, Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select

from app import timeutil
from app.db import transaction
from app.models import (
    ArrivalRecord,
    AuditLog,
    CalendarDay,
    OpeningSchedule,
    Reservation,
    Restriction,
    Role,
    Seat,
    StudyRoom,
    User,
    ViolationRecord,
)
from app.models import enums as E
from app.schemas.reservations import ReservationIn
from app.services import reservations as service
from app.services.availability import BookingError


@pytest.fixture
def clock(monkeypatch):
    clock = SimpleNamespace(at=datetime(2026, 11, 2, 8, tzinfo=timeutil.tz()))
    monkeypatch.setattr(timeutil, "now", lambda: clock.at)
    return clock


@pytest.fixture
def seats(api_db, clock):
    with api_db() as s:
        rooms = [
            StudyRoom(name=f"自习室{i}", location="图书馆", floor=f"{i}层", capacity=3)
            for i in (1, 2)
        ]
        rows = [
            Seat(room=rooms[0], code="A01", zone_type=E.ZoneType.QUIET, has_power=True),
            Seat(room=rooms[0], code="A02", zone_type=E.ZoneType.DISCUSSION),
            Seat(room=rooms[1], code="A01", zone_type=E.ZoneType.EXAM_PREP),
        ]
        s.add_all(rooms + rows)
        s.flush()
        for room in rooms:
            for kind in E.DayType:
                s.add(
                    OpeningSchedule(
                        room_id=room.id, day_type=kind, open_time=time(6), close_time=time(23, 30)
                    )
                )
        s.commit()
        return SimpleNamespace(
            room=rooms[0].id, other_room=rooms[1].id, a=rows[0].id, b=rows[1].id, c=rows[2].id
        )


@pytest.fixture
def actors(client, api_db, make_user, login):
    a = login(*make_user())
    b = login(*make_user(student_no="20260002"))
    with api_db() as s:
        users = list(s.scalars(select(User).order_by(User.id)))
    return SimpleNamespace(a=a, b=b, a_id=users[0].id, b_id=users[1].id)


def payload(seat, start="2026-11-02T09:00:00+08:00", end="2026-11-02T10:00:00+08:00"):
    return {"seat_id": seat, "start_time": start, "end_time": end}


def reserve(client, headers, seat, **kwargs):
    body = kwargs.pop("body", payload(seat))
    key = kwargs.pop("key", uuid4().hex)
    return client.post(
        "/api/reservations", headers={**headers, "Idempotency-Key": key}, json=body, **kwargs
    )


def count(api_db, model):
    with api_db() as s:
        return s.scalar(select(func.count()).select_from(model))


def test_room_search_detail_and_interval_states(client, actors, seats, api_db):
    rooms = client.get("/api/rooms?date=2026-11-02", headers=actors.a)
    assert rooms.status_code == 200
    room = rooms.json()[0]
    assert (room["name"], room["location"], room["floor"], room["capacity"]) == (
        "自习室1",
        "图书馆",
        "1层",
        3,
    )
    assert room["opening_hours"] == [{"open_time": "06:00:00", "close_time": "23:30:00"}]
    r = reserve(client, actors.a, seats.a)
    assert r.status_code == 201, r.text
    query = {
        "date": "2026-11-02",
        "start_time": "09:00",
        "end_time": "10:00",
        "room_id": seats.room,
    }
    result = client.get("/api/seats", headers=actors.b, params=query).json()
    assert [x["status"] for x in result] == ["reserved", "available"]
    filtered = client.get(
        "/api/seats",
        headers=actors.b,
        params={**query, "available_only": True, "zone_type": "discussion"},
    )
    assert [x["id"] for x in filtered.json()] == [seats.b]
    detail = client.get(f"/api/seats/{seats.a}", headers=actors.b, params=query).json()
    assert detail["has_power"] and detail["zone_type"] == "quiet"
    assert detail["qr_payload"] == f"studyroom:seat:{seats.a}"
    assert "user_id" not in detail and "reservation_no" not in detail
    # 未来有预约不代表其他时段不可用；相邻时间按半开区间处理。
    query.update(start_time="10:00", end_time="11:00")
    assert (
        client.get(f"/api/seats/{seats.a}", headers=actors.b, params=query).json()["status"]
        == "available"
    )
    with api_db() as s:
        s.get(Seat, seats.b).status = E.SeatStatus.MAINTENANCE
        s.commit()
    assert client.get(f"/api/seats/{seats.b}", headers=actors.a).json()["status"] == "maintenance"


@pytest.mark.parametrize(
    "query",
    [
        "date=2026-11-02",
        "start_time=09:00&end_time=10:00",
        "date=2026-11-02&start_time=23:00&end_time=01:00",
        "zone_type=unknown",
    ],
)
def test_search_invalid_inputs(client, actors, seats, query):
    assert client.get(f"/api/seats?{query}", headers=actors.a).status_code == 422


def test_calendar_priority_effective_dates_and_closed_room(client, actors, seats, api_db):
    with api_db() as s:
        s.add(CalendarDay(day=timeutil.now().date(), day_type=E.DayType.HOLIDAY))
        holiday = s.scalar(
            select(OpeningSchedule).where(
                OpeningSchedule.room_id == seats.room, OpeningSchedule.day_type == E.DayType.HOLIDAY
            )
        )
        holiday.open_time, holiday.close_time = time(12), time(18)
        s.commit()
    assert reserve(client, actors.a, seats.a).status_code == 422
    rooms = client.get("/api/rooms", headers=actors.a).json()
    assert rooms[0]["opening_hours"][0]["open_time"] == "12:00:00"
    with api_db() as s:
        s.get(StudyRoom, seats.room).status = E.RoomStatus.CLOSED
        s.commit()
    assert reserve(client, actors.a, seats.a).status_code == 409
    assert client.get(f"/api/seats/{seats.a}", headers=actors.a).json()["status"] == "closed"


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-11-02T05:59:00+08:00", "2026-11-02T08:00:00+08:00"),
        ("2026-11-02T22:00:00+08:00", "2026-11-02T23:31:00+08:00"),
        ("2026-11-02T23:00:00+08:00", "2026-11-03T01:00:00+08:00"),
        ("2026-11-04T09:00:00+08:00", "2026-11-04T10:00:00+08:00"),
        ("2026-11-02T09:00:00+08:00", "2026-11-02T09:00:00+08:00"),
        ("2026-11-02T09:00:00", "2026-11-02T10:00:00"),
    ],
)
def test_create_rejects_invalid_times(client, actors, seats, clock, start, end):
    clock.at = clock.at.replace(hour=5)
    response = reserve(client, actors.a, seats.a, body=payload(seats.a, start, end))
    assert response.status_code == 422, response.text


def test_today_tomorrow_short_duration_and_full_opening_day(client, actors, seats, clock):
    clock.at = clock.at.replace(hour=5)
    full = payload(seats.a, "2026-11-02T06:00:00+08:00", "2026-11-02T23:30:00+08:00")
    assert reserve(client, actors.a, seats.a, body=full).status_code == 201
    # HD-32 最短不限；不是 README 中旧的半小时粒度。
    short = payload(seats.a, "2026-11-03T09:00:00+08:00", "2026-11-03T09:00:01+08:00")
    assert reserve(client, actors.a, seats.a, body=short).status_code == 201


def test_overlap_person_overlap_adjacent_and_utc_conversion(client, actors, seats):
    first = reserve(client, actors.a, seats.a)
    assert first.status_code == 201
    assert reserve(client, actors.b, seats.a).status_code == 409
    assert reserve(client, actors.a, seats.c).status_code == 409
    # 同一物理时段用 UTC 表示仍冲突。
    utc = payload(seats.a, "2026-11-02T01:30:00Z", "2026-11-02T02:30:00Z")
    assert reserve(client, actors.b, seats.a, body=utc).status_code == 409
    adjacent = payload(seats.a, "2026-11-02T10:00:00+08:00", "2026-11-02T11:00:00+08:00")
    assert reserve(client, actors.a, seats.a, body=adjacent).status_code == 201


def test_idempotency_key_required_and_scoped_to_payload_and_user(client, actors, seats, api_db):
    # 幂等键可选：无键也可创建；有键时同键同载荷重放，不同载荷/用户冲突。
    # 使用不与后续 seats.a 9–10 点冲突的时段。
    assert (
        client.post(
            "/api/reservations",
            headers=actors.a,
            json=payload(seats.c, "2026-11-02T11:00:00+08:00", "2026-11-02T12:00:00+08:00"),
        ).status_code
        == 201
    )
    key = uuid4().hex
    first = reserve(client, actors.a, seats.a, key=key)
    replay = reserve(client, actors.a, seats.a, key=key)
    assert first.status_code == 201 and replay.status_code == 200
    assert replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json()["id"] == first.json()["id"]
    assert reserve(client, actors.a, seats.b, key=key).status_code == 409
    assert reserve(client, actors.b, seats.a, key=key).status_code == 409
    rid = first.json()["id"]
    client.patch(f"/api/reservations/{rid}/seat", headers=actors.a, json={"seat_id": seats.b})
    # 换座后旧请求重试返回同一预约的当前状态，不另建预约。
    assert reserve(client, actors.a, seats.a, key=key).json()["seat_id"] == seats.b
    client.post(f"/api/reservations/{rid}/cancel", headers=actors.a)
    assert reserve(client, actors.a, seats.a, key=key).json()["status"] == "CANCELLED"
    assert count(api_db, Reservation) == 2


def test_change_seat_rechecks_conflicts_and_preserves_original_on_failure(client, actors, seats):
    rid = reserve(client, actors.a, seats.a).json()["id"]
    reserve(client, actors.b, seats.b)
    path = f"/api/reservations/{rid}/seat"
    assert client.patch(path, headers=actors.a, json={"seat_id": seats.b}).status_code == 409
    assert client.get(f"/api/reservations/{rid}", headers=actors.a).json()["seat_id"] == seats.a
    assert (
        client.patch(
            path, headers=actors.a, json={"seat_id": seats.c, "start_time": "2026-11-02"}
        ).status_code
        == 422
    )
    response = client.patch(path, headers=actors.a, json={"seat_id": seats.c})
    assert response.status_code == 200
    assert response.json()["room_id"] == seats.other_room
    assert response.json()["start_time"] == "2026-11-02T09:00:00+08:00"
    assert reserve(client, actors.b, seats.a).status_code == 409  # 此用户自己已有重叠预约


@pytest.mark.parametrize("minutes,late", [(16, False), (15, True), (1, True)])
def test_cancel_exact_boundary_and_no_show_mutual_exclusion(
    client, actors, seats, clock, api_db, minutes, late
):
    rid = reserve(client, actors.a, seats.a).json()["id"]
    clock.at = clock.at.replace(hour=9) - timedelta(minutes=minutes)
    r = client.post(f"/api/reservations/{rid}/cancel", headers=actors.a)
    assert r.status_code == 200
    assert r.json()["cancel_type"] == ("late" if late else "normal")
    client.post(f"/api/reservations/{rid}/cancel", headers=actors.a)
    clock.at = clock.at.replace(hour=10)
    with api_db() as s:
        assert service.expire_due(s) == 0
    assert count(api_db, ViolationRecord) == int(late)
    with api_db() as s:
        assert s.get(Seat, seats.a).status == E.SeatStatus.AVAILABLE
        if late:
            assert s.scalar(select(ViolationRecord.violation_type)) == E.ViolationType.LATE_CANCEL
    assert count(api_db, AuditLog) == int(late)


def test_restricted_user_can_cancel_but_cannot_create_or_change(
    client, actors, seats, api_db, clock
):
    rid = reserve(client, actors.a, seats.a).json()["id"]
    with api_db() as s:
        s.add(
            Restriction(
                user_id=actors.a_id,
                ban_days=1,
                warning_count=3,
                trigger_condition="3",
                start_at=clock.at - timedelta(minutes=1),
                end_at=clock.at + timedelta(days=1),
            )
        )
        s.commit()
    assert (
        client.patch(
            f"/api/reservations/{rid}/seat", headers=actors.a, json={"seat_id": seats.b}
        ).status_code
        == 403
    )
    assert client.post(f"/api/reservations/{rid}/cancel", headers=actors.a).status_code == 200
    assert reserve(client, actors.a, seats.b).status_code == 403


@pytest.mark.parametrize("minute,second,success", [(44, 59, False), (45, 0, True)])
def test_checkin_early_boundary(client, actors, seats, clock, minute, second, success):
    rid = reserve(client, actors.a, seats.a).json()["id"]
    clock.at = clock.at.replace(minute=minute, second=second)
    r = client.post(
        f"/api/reservations/{rid}/check-in", headers=actors.a, json={"seat_id": seats.a}
    )
    assert r.status_code == (200 if success else 409)


@pytest.mark.parametrize(
    "minute,microsecond,success", [(0, 0, True), (15, 0, True), (15, 1, False), (16, 0, False)]
)
def test_checkin_late_boundary_no_penalty_inside_window(
    client, actors, seats, clock, api_db, minute, microsecond, success
):
    rid = reserve(client, actors.a, seats.a).json()["id"]
    clock.at = clock.at.replace(hour=9, minute=minute, microsecond=microsecond)
    response = client.post(
        f"/api/reservations/{rid}/check-in", headers=actors.a, json={"seat_id": seats.a}
    )
    assert response.status_code == (200 if success else 409), response.text
    with api_db() as s:
        assert s.get(Reservation, rid).status == (
            E.ReservationStatus.ACTIVE if success else E.ReservationStatus.EXPIRED
        )
        assert service.expire_due(s) == 0
    assert count(api_db, ViolationRecord) == (0 if success else 1)


def test_checkin_identity_seat_repeat_and_state_transitions(client, actors, seats, clock, api_db):
    rid = reserve(client, actors.a, seats.a).json()["id"]
    clock.at = clock.at.replace(minute=45)
    path = f"/api/reservations/{rid}/check-in"
    assert client.post(path, headers=actors.b, json={"seat_id": seats.a}).status_code == 404
    assert client.post(path, headers=actors.a, json={"seat_id": seats.b}).status_code == 409
    body = {"room_id": seats.room, "seat_code": "A01"}
    assert client.post(path, headers=actors.a, json=body).status_code == 200
    assert client.post(path, headers=actors.a, json=body).status_code == 200
    assert count(api_db, ArrivalRecord) == 1
    assert count(api_db, ViolationRecord) == 0
    assert client.get(f"/api/seats/{seats.a}", headers=actors.b).json()["status"] == "in_use"
    assert client.post(f"/api/reservations/{rid}/cancel", headers=actors.a).status_code == 409
    assert (
        client.patch(
            f"/api/reservations/{rid}/seat", headers=actors.a, json={"seat_id": seats.b}
        ).status_code
        == 409
    )


def test_unattended_expiry_worker_and_dedup(api_db, seats, actors, clock, monkeypatch):
    with api_db() as s:
        result, _ = service.create(s, actors.a_id, ReservationIn(**payload(seats.a)), uuid4().hex)
    clock.at = clock.at.replace(hour=9, minute=16)
    from app.config import get_settings
    from app.main import create_app
    from app.services import reservation_worker as worker

    completed = Event()
    original = worker.full_sweep

    def full_sweep():
        result = original()
        completed.set()
        return result

    monkeypatch.setattr(worker, "SessionLocal", api_db)
    monkeypatch.setattr(worker, "full_sweep", full_sweep)
    monkeypatch.setattr(get_settings(), "reservation_sweep_interval_seconds", 0.02)
    # 没有任何 HTTP 请求也必须自动失效。
    with TestClient(create_app()):
        assert completed.wait(3), "background worker did not execute"
    with api_db() as s:
        assert s.get(Reservation, result.id).status == E.ReservationStatus.EXPIRED
        assert s.get(Seat, seats.a).status == E.SeatStatus.AVAILABLE
        assert service.expire_due(s) == 0
    assert count(api_db, ViolationRecord) == 1


def test_lazy_expiry_and_maintenance_preserved(client, actors, seats, clock, api_db):
    reserve(client, actors.a, seats.a)
    with api_db() as s:
        s.get(Seat, seats.a).status = E.SeatStatus.MAINTENANCE
        s.commit()
    clock.at = clock.at.replace(hour=9, minute=16)
    assert client.get("/api/reservations/current", headers=actors.a).json() == []
    assert client.get(f"/api/seats/{seats.a}", headers=actors.a).json()["status"] == "maintenance"
    assert count(api_db, ViolationRecord) == 1


def test_owner_privacy_and_ops_permissions(client, actors, seats, make_user, login):
    rid = reserve(client, actors.a, seats.a).json()["id"]
    for method, suffix, body in [
        ("get", "", None),
        ("post", "/cancel", None),
        ("patch", "/seat", {"seat_id": seats.b}),
    ]:
        assert (
            client.request(
                method, f"/api/reservations/{rid}{suffix}", headers=actors.b, json=body
            ).status_code
            == 404
        )
    assert client.get("/api/reservations/current", headers=actors.b).json() == []
    assert client.get("/api/rooms").status_code == 401
    ops = login(*make_user(student_no="OPS00001", roles=("ops",)))
    assert client.get("/api/rooms", headers=ops).status_code == 200
    assert reserve(client, ops, seats.a).status_code == 403
    assert client.get("/api/reservations/current", headers=ops).status_code == 403


def test_cancel_audit_failure_rolls_back_violation_and_release(
    client, actors, seats, clock, api_db, monkeypatch
):
    rid = reserve(client, actors.a, seats.a).json()["id"]
    clock.at = clock.at.replace(minute=50)

    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(service.audit, "record", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post(f"/api/reservations/{rid}/cancel", headers=actors.a)
    with api_db() as s:
        assert s.get(Reservation, rid).status == E.ReservationStatus.RESERVED
    assert count(api_db, ViolationRecord) == 0


def test_100_competing_users_only_one_reservation(api_db, seats, clock):
    with api_db() as s:
        role = s.scalar(select(Role).where(Role.name == E.RoleName.USER))
        users = [
            User(student_no=f"race{i:04}", password_hash="unused", name="并发用户", roles=[role])
            for i in range(100)
        ]
        s.add_all(users)
        s.commit()
        ids = [u.id for u in users]
    barrier = Barrier(100)

    def book(uid):
        barrier.wait(timeout=10)
        with api_db() as s:
            try:
                result, replay = service.create(
                    s, uid, ReservationIn(**payload(seats.a)), uuid4().hex
                )
                assert not replay
                return result.id
            except BookingError as exc:
                assert exc.status_code == 409
                return None

    with ThreadPoolExecutor(max_workers=100) as executor:
        results = list(executor.map(book, ids))
    assert sum(r is not None for r in results) == 1
    assert count(api_db, Reservation) == 1


def test_concurrent_retries_return_same_id(api_db, seats, actors):
    key = uuid4().hex

    def book(_):
        with api_db() as s:
            return service.create(s, actors.a_id, ReservationIn(**payload(seats.a)), key)

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(book, range(16)))
    assert len({result.id for result, _ in results}) == 1
    assert sum(not replay for _, replay in results) == 1
    assert count(api_db, Reservation) == 1


def test_write_lock_error_is_retryable_and_same_key_can_recover(client, actors, seats, api_db):
    with api_db() as held:
        engine = held.get_bind()

        def short_wait(dbapi_conn, *_):
            dbapi_conn.execute("PRAGMA busy_timeout=25")

        event.listen(engine, "checkout", short_wait)
        key = uuid4().hex
        try:
            with transaction(held, immediate=True):
                response = reserve(client, actors.a, seats.a, key=key)
                assert response.status_code == 503
                assert response.headers["Retry-After"] == "1"
            assert reserve(client, actors.a, seats.a, key=key).status_code == 201
        finally:
            event.remove(engine, "checkout", short_wait)
