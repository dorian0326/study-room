"""docs/分阶段实现与测试计划.md 中 TC-LOCAL-001 ~ TC-LOCAL-010 的可执行案例测试。

每个测试用 ``@pytest.mark.case("<编号>")`` 标注对应案例。
``tests/test_case_traceability.py`` 会校验案例编号与文档保持同步。
这些用例走公开 API 和真实迁移数据库，作为案例层；纯函数见 test_units.py。
"""

from datetime import datetime, time, timedelta
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from openpyxl import load_workbook
from sqlalchemy import func, select

from app import timeutil
from app.models import (
    AuditLog,
    EntryExitRecord,
    Notification,
    OpeningSchedule,
    Reservation,
    Restriction,
    Seat,
    StudyRoom,
    User,
    ViolationRecord,
)
from app.models import enums as E
from app.schemas.workflows import GateEventIn
from app.services import gate as gate_service
from app.services.backup import create_backup, list_backups, restore_backup
from app.services.reservations import sweep_reservations
from app.services.violations import record_violation


@pytest.fixture
def clock(monkeypatch):
    """把服务端“现在”固定到 2026-11-02 08:00，便于断言时间边界。"""
    clock = SimpleNamespace(at=datetime(2026, 11, 2, 8, tzinfo=timeutil.tz()))
    monkeypatch.setattr(timeutil, "now", lambda: clock.at)
    return clock


@pytest.fixture
def seats(api_db, clock):
    """两间自习室、三个座位和全天开放时段。"""
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
                        room_id=room.id,
                        day_type=kind,
                        open_time=time(6),
                        close_time=time(23, 30),
                    )
                )
        s.commit()
        return SimpleNamespace(
            room=rooms[0].id,
            other_room=rooms[1].id,
            a=rows[0].id,
            b=rows[1].id,
            c=rows[2].id,
        )


@pytest.fixture
def actors(client, api_db, make_user, login):
    """两个普通学生账号，返回各自的请求头和用户 ID。"""
    a = login(*make_user())
    b = login(*make_user(student_no="20260002"))
    with api_db() as s:
        users = list(s.scalars(select(User).order_by(User.id)))
    return SimpleNamespace(a=a, b=b, a_id=users[0].id, b_id=users[1].id)


@pytest.fixture
def admin(client, make_user, login):
    make_user("A0000001", roles=("admin",))
    return login("A0000001", "secret123")


def payload(seat, start="2026-11-02T09:00:00+08:00", end="2026-11-02T10:00:00+08:00"):
    return {"seat_id": seat, "start_time": start, "end_time": end}


def reserve(client, headers, seat, **kwargs):
    body = kwargs.pop("body", payload(seat))
    key = kwargs.pop("key", uuid4().hex)
    return client.post(
        "/api/reservations",
        headers={**headers, "Idempotency-Key": key},
        json=body,
    )


def count(api_db, model):
    with api_db() as s:
        return s.scalar(select(func.count()).select_from(model))


@pytest.mark.case("TC-LOCAL-001")
def test_case_001_overlapping_slot_conflicts_and_adjacent_slot_succeeds(client, actors, seats):
    """同一座位重叠时段不能并行成功；相邻区间允许。"""
    first = reserve(client, actors.a, seats.a)
    assert first.status_code == 201, first.text
    assert reserve(client, actors.b, seats.a).status_code == 409
    assert reserve(client, actors.a, seats.c).status_code == 409
    adjacent = payload(seats.a, "2026-11-02T10:00:00+08:00", "2026-11-02T11:00:00+08:00")
    assert reserve(client, actors.b, seats.a, body=adjacent).status_code == 201


@pytest.mark.case("TC-LOCAL-001")
def test_case_001_idempotency_key_replays_same_reservation(client, actors, seats, api_db):
    """同键同请求重放返回同一预约；不同载荷或用户复用同键返回冲突。"""
    key = uuid4().hex
    first = reserve(client, actors.a, seats.a, key=key)
    replay = reserve(client, actors.a, seats.a, key=key)
    assert first.status_code == 201 and replay.status_code == 200
    assert replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json()["id"] == first.json()["id"]
    assert count(api_db, Reservation) == 1
    assert reserve(client, actors.a, seats.b, key=key).status_code == 409
    assert reserve(client, actors.b, seats.a, key=key).status_code == 409


@pytest.mark.case("TC-LOCAL-002")
def test_case_002_unauthenticated_requests_are_rejected(client):
    """未登录访问受保护接口返回 401。"""
    for path in ("/api/auth/me", "/api/reservations/current", "/api/notifications"):
        assert client.get(path).status_code == 401


@pytest.mark.case("TC-LOCAL-002")
def test_case_002_missing_permission_returns_403(client, actors):
    """普通学生访问管理接口返回 403。"""
    assert client.get("/api/admin/settings", headers=actors.a).status_code == 403
    assert client.get("/api/admin/users", headers=actors.a).status_code == 403
    created = client.post(
        "/api/admin/rooms",
        headers=actors.a,
        json={"name": "越权自习室", "location": "图书馆", "capacity": 10},
    )
    assert created.status_code == 403


@pytest.mark.case("TC-LOCAL-002")
def test_case_002_other_users_reservation_is_invisible(client, actors, seats, api_db):
    """使用他人预约或通知 ID 不能读取或修改数据，列表也只返回本人记录。"""
    rid = reserve(client, actors.a, seats.a).json()["id"]
    assert client.get(f"/api/reservations/{rid}", headers=actors.b).status_code == 404
    assert client.post(f"/api/reservations/{rid}/cancel", headers=actors.b).status_code == 404
    changed = client.patch(
        f"/api/reservations/{rid}/seat",
        headers=actors.b,
        json={"seat_id": seats.b},
    )
    assert changed.status_code == 404
    current = client.get("/api/reservations", headers=actors.b).json()
    assert all(row["id"] != rid for row in current)

    with api_db() as s:
        note = Notification(
            user_id=actors.a_id,
            type=E.NotificationType.SYSTEM,
            content="只给甲的通知",
            sent_at=timeutil.now(),
            channel="in_app",
            idempotency_key="case-002-private",
        )
        s.add(note)
        s.commit()
        note_id = note.id
    listed = client.get("/api/notifications", headers=actors.b).json()
    assert all(item["id"] != note_id for item in listed)
    denied = client.post(f"/api/notifications/{note_id}/read", headers=actors.b)
    assert denied.status_code == 404


@pytest.mark.case("TC-LOCAL-003")
@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-11-02T05:59:00+08:00", "2026-11-02T08:00:00+08:00"),
        ("2026-11-02T22:00:00+08:00", "2026-11-02T23:31:00+08:00"),
        ("2026-11-02T23:00:00+08:00", "2026-11-03T01:00:00+08:00"),
        ("2026-11-01T09:00:00+08:00", "2026-11-01T10:00:00+08:00"),
        ("2026-11-02T09:00:00+08:00", "2026-11-02T09:00:00+08:00"),
        ("2026-11-02T09:00:00", "2026-11-02T10:00:00"),
    ],
)
def test_case_003_invalid_times_are_rejected(client, actors, seats, clock, start, end):
    """关闭时间以外、跨日、过去时间、零长度和无时区时间应拒绝。"""
    clock.at = clock.at.replace(hour=5)
    response = reserve(client, actors.a, seats.a, body=payload(seats.a, start, end))
    assert response.status_code == 422, response.text


@pytest.mark.case("TC-LOCAL-003")
def test_case_003_short_but_valid_interval_is_allowed(client, actors, seats, clock):
    """短于 30 分钟的合法时段不应被时长规则拒绝。"""
    clock.at = clock.at.replace(hour=5)
    short = payload(seats.a, "2026-11-02T09:00:00+08:00", "2026-11-02T09:10:00+08:00")
    assert reserve(client, actors.a, seats.a, body=short).status_code == 201


@pytest.mark.case("TC-LOCAL-004")
def test_case_004_temp_leave_timeout_releases_once_with_one_violation(
    client, actors, seats, clock, api_db
):
    """临时离开超时只释放一次，并至多生成一条违规和一条通知。"""
    rid = reserve(client, actors.a, seats.a).json()["id"]
    clock.at = datetime(2026, 11, 2, 9, tzinfo=timeutil.tz())
    assert client.post(f"/api/reservations/{rid}/check-in", headers=actors.a).status_code == 200
    left = client.post(f"/api/reservations/{rid}/temporary-leave", headers=actors.a)
    assert left.status_code == 200
    moment = clock.at + timedelta(minutes=31)
    with api_db() as s:
        first = sweep_reservations(s, moment)
        second = sweep_reservations(s, moment + timedelta(minutes=1))
        saved = s.get(Reservation, rid)
        violations = list(
            s.scalars(select(ViolationRecord).where(ViolationRecord.reservation_id == rid))
        )
        notice = s.scalar(
            select(Notification).where(
                Notification.idempotency_key == f"reservation:{rid}:timeout-released"
            )
        )
    assert first["temp_leave"] == 1
    assert second["temp_leave"] == 0
    assert saved.status == E.ReservationStatus.TIMED_OUT
    assert [row.violation_type for row in violations] == [E.ViolationType.TEMP_LEAVE_TIMEOUT]
    assert notice is not None


@pytest.mark.case("TC-LOCAL-005")
@pytest.mark.parametrize("minutes,late", [(16, False), (15, True), (1, True)])
def test_case_005_cancel_boundary_records_late_violation(
    client, actors, seats, clock, api_db, minutes, late
):
    """开始前 15 分钟边界内取消记违规，边界外为正常取消。"""
    rid = reserve(client, actors.a, seats.a).json()["id"]
    clock.at = datetime(2026, 11, 2, 9, tzinfo=timeutil.tz()) - timedelta(minutes=minutes)
    response = client.post(f"/api/reservations/{rid}/cancel", headers=actors.a)
    assert response.status_code == 200
    assert response.json()["cancel_type"] == ("late" if late else "normal")
    with api_db() as s:
        rows = list(s.scalars(select(ViolationRecord).where(ViolationRecord.reservation_id == rid)))
        assert s.get(Seat, seats.a).status == E.SeatStatus.AVAILABLE
    assert len(rows) == int(late)
    if late:
        assert rows[0].violation_type == E.ViolationType.LATE_CANCEL


@pytest.mark.case("TC-LOCAL-005")
def test_case_005_restricted_user_may_cancel_but_not_book(client, actors, seats, clock, api_db):
    """被禁约用户仍可取消已有预约，但不能新建或改座。"""
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
    changed = client.patch(
        f"/api/reservations/{rid}/seat",
        headers=actors.a,
        json={"seat_id": seats.b},
    )
    assert changed.status_code == 403
    assert client.post(f"/api/reservations/{rid}/cancel", headers=actors.a).status_code == 200
    assert reserve(client, actors.a, seats.b).status_code == 403


@pytest.mark.case("TC-LOCAL-005")
def test_case_005_appeal_is_owner_only_and_within_deadline(client, actors, api_db, clock):
    """申诉只能关联本人，并受期限限制。"""
    with api_db() as s:
        fresh = record_violation(
            s,
            user_id=actors.a_id,
            violation_type=E.ViolationType.NO_SHOW,
            reservation_id=None,
            description="合成违规",
            occurred_at=clock.at,
        )
        stale = record_violation(
            s,
            user_id=actors.a_id,
            violation_type=E.ViolationType.LATE_CANCEL,
            reservation_id=None,
            description="过期违规",
            occurred_at=clock.at - timedelta(days=8),
        )
        s.commit()
        fresh_id, stale_id = fresh.id, stale.id
    foreign = client.post(
        "/api/appeals",
        headers=actors.b,
        json={"violation_id": fresh_id, "reason": "不是我的记录"},
    )
    assert foreign.status_code == 404
    expired = client.post(
        "/api/appeals",
        headers=actors.a,
        json={"violation_id": stale_id, "reason": "已经超过七天"},
    )
    assert expired.status_code == 409
    own = client.post(
        "/api/appeals",
        headers=actors.a,
        json={"violation_id": fresh_id, "reason": "门禁设备异常导致签到失败"},
    )
    assert own.status_code == 201, own.text


@pytest.mark.case("TC-LOCAL-005")
def test_case_005_approved_appeal_lifts_restriction_and_notifies(client, actors, admin, api_db):
    """审核通过时解除禁约，并在同一流程里通知申请人。"""
    with api_db() as s:
        records = [
            record_violation(
                s,
                user_id=actors.a_id,
                violation_type=E.ViolationType.NO_SHOW,
                reservation_id=None,
                description="预约开始后未签到。",
                occurred_at=timeutil.now() + timedelta(minutes=index),
            )
            for index in range(3)
        ]
        s.commit()
        violation_id = records[-1].id
        restriction_id = records[-1].restriction_id
    submitted = client.post(
        "/api/appeals",
        headers=actors.a,
        json={"violation_id": violation_id, "reason": "门禁设备异常导致签到失败"},
    )
    assert submitted.status_code == 201, submitted.text
    reviewed = client.patch(
        f"/api/admin/appeals/{submitted.json()['id']}",
        headers=admin,
        json={"result": "approved", "review_comment": "核验后确认设备异常"},
    )
    assert reviewed.status_code == 200, reviewed.text
    with api_db() as s:
        restriction = s.get(Restriction, restriction_id)
        notice = s.scalar(
            select(Notification).where(
                Notification.idempotency_key == f"appeal:{submitted.json()['id']}:reviewed"
            )
        )
    assert restriction.status == E.RestrictionStatus.LIFTED
    assert notice is not None
    assert "已通过" in notice.content


@pytest.mark.case("TC-LOCAL-006")
def test_case_006_maintenance_cancels_pending_but_not_active(
    client, actors, seats, clock, admin, api_db, monkeypatch
):
    """座位进入维护后取消尚未开始的预约；正在使用的预约不被中断。"""
    import app.api.admin_seats as seat_api

    active_id = reserve(client, actors.a, seats.a).json()["id"]
    later = payload(seats.b, "2026-11-02T12:00:00+08:00", "2026-11-02T13:00:00+08:00")
    pending_id = reserve(client, actors.b, seats.b, body=later).json()["id"]
    clock.at = datetime(2026, 11, 2, 8, 50, tzinfo=timeutil.tz())
    # 座位接口绑定了自己的 now，测试时钟要打到那一处才会按设定时间取消。
    monkeypatch.setattr(seat_api, "now", lambda: clock.at)
    assert (
        client.post(f"/api/reservations/{active_id}/check-in", headers=actors.a).status_code == 200
    )

    for seat_id in (seats.a, seats.b):
        response = client.patch(
            f"/api/admin/rooms/{seats.room}/seats/{seat_id}/status",
            headers=admin,
            json={"status": "maintenance", "reason": "设备检修"},
        )
        assert response.status_code == 200, response.text

    with api_db() as s:
        active = s.get(Reservation, active_id)
        pending = s.get(Reservation, pending_id)
        notice = s.scalar(
            select(Notification).where(
                Notification.idempotency_key == f"reservation:{pending_id}:maintenance-cancelled"
            )
        )
        audits = list(s.scalars(select(AuditLog).where(AuditLog.target_type == "seat_maintenance")))
    assert active.status == E.ReservationStatus.ACTIVE
    assert pending.status == E.ReservationStatus.ADMIN_CANCELLED
    assert notice is not None
    assert "不提供补偿" in notice.content
    assert {row.target_id for row in audits} == {str(seats.a), str(seats.b)}


@pytest.mark.case("TC-LOCAL-007")
def test_case_007_only_admin_can_change_config_and_invalid_input_is_noop(client, actors, admin):
    """只有授权角色可管理；非法开放时间或参数不改变已保存值。"""
    assert client.get("/api/admin/settings", headers=actors.a).status_code == 403
    before = client.get("/api/admin/settings", headers=admin).json()
    rejected = client.put(
        "/api/admin/settings",
        headers=admin,
        json={**before, "temp_leave_minutes": 0},
    )
    assert rejected.status_code == 422
    assert client.get("/api/admin/settings", headers=admin).json() == before

    room = client.post(
        "/api/admin/rooms",
        headers=admin,
        json={"name": "配置自习室", "location": "图书馆", "capacity": 20},
    )
    assert room.status_code == 201, room.text
    url = f"/api/admin/rooms/{room.json()['id']}/schedules"
    bad = client.post(
        url,
        headers=admin,
        json={"day_type": "weekday", "open_time": "05:30", "close_time": "22:00"},
    )
    assert bad.status_code == 422
    assert client.get(url, headers=admin).json() == []
    ok = client.post(
        url,
        headers=admin,
        json={"day_type": "weekday", "open_time": "08:00", "close_time": "22:00"},
    )
    assert ok.status_code == 201


@pytest.mark.case("TC-LOCAL-008")
def test_case_008_report_json_and_xlsx_share_the_same_scope(client, admin):
    """JSON 与 XLSX 使用一致的统计区间和口径；日期倒置或超范围拒绝。"""
    room = client.post(
        "/api/admin/rooms",
        headers=admin,
        json={"name": "报表自习室", "location": "图书馆", "capacity": 20},
    )
    assert room.status_code == 201, room.text
    room_id = room.json()["id"]
    day = timeutil.now().date() + timedelta(days=2)
    day_type = "weekend" if day.weekday() >= 5 else "weekday"
    schedule = client.post(
        f"/api/admin/rooms/{room_id}/schedules",
        headers=admin,
        json={"day_type": day_type, "open_time": "06:00", "close_time": "23:00"},
    )
    assert schedule.status_code == 201, schedule.text
    seat = client.post(
        f"/api/admin/rooms/{room_id}/seats",
        headers=admin,
        json={"code": "A01", "zone_type": "quiet", "status": "available"},
    )
    assert seat.status_code == 201, seat.text
    closed = client.post(
        f"/api/admin/rooms/{room_id}/seats",
        headers=admin,
        json={"code": "A02", "zone_type": "quiet", "status": "maintenance"},
    )
    assert closed.status_code == 201, closed.text

    params = {"start": day.isoformat(), "end": day.isoformat()}
    report = client.get("/api/admin/reports", headers=admin, params=params)
    assert report.status_code == 200, report.text
    body = report.json()
    # 维护中的座位不计入可用时长，因此分母仍是一个座位的 17 小时。
    assert body["utilization"]["available_hours"] == 17.0
    exported = client.get("/api/admin/reports/export.xlsx", headers=admin, params=params)
    assert exported.status_code == 200
    sheet = load_workbook(BytesIO(exported.content))["利用率概览"]
    rows = {row[0]: row[1] for row in sheet.iter_rows(values_only=True)}
    assert rows["开始日期"] == body["period"]["start"]
    assert rows["结束日期"] == body["period"]["end"]
    assert rows["可用时长（座位小时）"] == body["utilization"]["available_hours"]
    assert rows["利用率"] == body["utilization"]["rate"]

    inverted = client.get(
        "/api/admin/reports",
        headers=admin,
        params={"start": "2026-11-05", "end": "2026-11-01"},
    )
    assert inverted.status_code == 422
    too_long = client.get(
        "/api/admin/reports",
        headers=admin,
        params={"start": "2025-01-01", "end": "2026-02-01"},
    )
    assert too_long.status_code == 422


@pytest.mark.case("TC-LOCAL-009")
def test_case_009_backup_requires_ops_role(client, make_user, login, tmp_path, monkeypatch):
    """只有运维角色可以创建和查看备份。"""
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "backup_dir", str(tmp_path / "bk"))
    make_user("20260001")
    make_user("A0000001", roles=("admin",))
    make_user("O0000001", roles=("ops",))
    student = login("20260001", "secret123")
    admin = login("A0000001", "secret123")
    ops = login("O0000001", "secret123")
    assert client.post("/api/ops/backups", headers=student).status_code == 403
    assert client.post("/api/ops/backups", headers=admin).status_code == 403
    created = client.post("/api/ops/backups", headers=ops)
    assert created.status_code == 201
    assert client.get("/api/ops/backups", headers=student).status_code == 403
    names = [item["name"] for item in client.get("/api/ops/backups", headers=ops).json()]
    assert names == [created.json()["name"]]


@pytest.mark.case("TC-LOCAL-009")
def test_case_009_backup_rotation_restore_and_status(
    client, api_db, make_user, login, tmp_path, monkeypatch
):
    """备份轮换后仍可完整性恢复；监控接口只返回定义字段。"""
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "backup_dir", str(tmp_path / "bk"))
    monkeypatch.setattr(get_settings(), "backup_keep", 2)
    make_user("20260001")
    engine = api_db.kw["bind"]
    first = create_backup(engine)
    make_user("20260002")
    create_backup(engine)
    latest = create_backup(engine)
    assert first not in list_backups()
    assert latest in list_backups()
    make_user("20260003")
    restore_backup(engine, latest.name)
    with api_db() as s:
        assert s.scalar(select(func.count()).select_from(User)) == 2

    make_user("O0000001", roles=("ops",))
    status = client.get("/api/ops/status", headers=login("O0000001", "secret123"))
    assert status.status_code == 200, status.text
    assert set(status.json()) == {
        "uptime_seconds",
        "database",
        "users",
        "active_sessions",
        "latest_backup",
        "requests",
    }


def _gate_event(session, reservation_id, *, external_id, recorded_at, record_type):
    reservation = session.get(Reservation, reservation_id)
    user = session.get(User, reservation.user_id)
    body = GateEventIn(
        external_id=external_id,
        source_system="mock-gate-case",
        masked_user_key=gate_service.user_key_for_gate(user.student_no),
        record_type=record_type,
        recorded_at=recorded_at,
        reservation_id=reservation_id,
    )
    return gate_service.process_gate_event(session, body)


@pytest.mark.case("TC-LOCAL-010")
def test_case_010_duplicate_gate_event_is_not_counted_twice(
    client, actors, seats, api_db, monkeypatch
):
    """同一外部事件重放不重复入账。"""
    rid = reserve(client, actors.a, seats.a).json()["id"]
    moment = datetime(2026, 11, 2, 9, tzinfo=timeutil.tz())
    monkeypatch.setattr(gate_service, "now", lambda: moment)
    with api_db() as s:
        first = _gate_event(
            s,
            rid,
            external_id="case-gate-001",
            recorded_at=moment,
            record_type=E.EntryExitType.ENTRY,
        )
        duplicate = _gate_event(
            s,
            rid,
            external_id="case-gate-001",
            recorded_at=moment,
            record_type=E.EntryExitType.ENTRY,
        )
        records = list(
            s.scalars(select(EntryExitRecord).where(EntryExitRecord.external_id == "case-gate-001"))
        )
    assert first["duplicate"] is False
    assert duplicate["duplicate"] is True
    assert len(records) == 1


@pytest.mark.case("TC-LOCAL-010")
def test_case_010_delayed_and_unmatched_events_need_manual_review(
    client, actors, seats, api_db, monkeypatch
):
    """延迟事件和已结束预约上的事件只关联记录，不复活或结束预约。"""
    rid = reserve(client, actors.a, seats.a).json()["id"]
    start = datetime(2026, 11, 2, 9, tzinfo=timeutil.tz())
    monkeypatch.setattr(gate_service, "now", lambda: start + timedelta(minutes=10))
    with api_db() as s:
        late = _gate_event(
            s,
            rid,
            external_id="case-gate-late",
            recorded_at=start,
            record_type=E.EntryExitType.ENTRY,
        )
        saved = s.get(Reservation, rid)
    assert late["sync_status"] == "late"
    assert late["manual_appeal_required"] is True
    assert saved.status == E.ReservationStatus.RESERVED

    monkeypatch.setattr(gate_service, "now", lambda: start)
    with api_db() as s:
        saved = s.get(Reservation, rid)
        saved.status = E.ReservationStatus.COMPLETED
        s.commit()
        unmatched = _gate_event(
            s,
            rid,
            external_id="case-gate-unmatched",
            recorded_at=start,
            record_type=E.EntryExitType.ENTRY,
        )
        s.refresh(saved)
    assert unmatched["sync_status"] == "unmatched"
    assert unmatched["manual_appeal_required"] is True
    assert saved.status == E.ReservationStatus.COMPLETED


@pytest.mark.case("TC-LOCAL-010")
def test_case_010_entry_after_temp_leave_window_is_not_applied(
    client, actors, seats, api_db, clock, monkeypatch
):
    """超过临时离开期限后的入馆事件不恢复使用中状态。"""
    rid = reserve(client, actors.a, seats.a).json()["id"]
    clock.at = datetime(2026, 11, 2, 9, tzinfo=timeutil.tz())
    assert client.post(f"/api/reservations/{rid}/check-in", headers=actors.a).status_code == 200
    assert (
        client.post(f"/api/reservations/{rid}/temporary-leave", headers=actors.a).status_code == 200
    )
    late = clock.at + timedelta(minutes=35)
    monkeypatch.setattr(gate_service, "now", lambda: late)
    with api_db() as s:
        result = _gate_event(
            s,
            rid,
            external_id="case-gate-tl-late",
            recorded_at=late,
            record_type=E.EntryExitType.ENTRY,
        )
        saved = s.get(Reservation, rid)
    assert result["sync_status"] == "unmatched"
    assert saved.status == E.ReservationStatus.TEMP_LEAVE
