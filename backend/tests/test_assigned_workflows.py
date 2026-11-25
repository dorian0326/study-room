"""#17、#18、#19、#20、#21、#23 与 #24 的预约流程验收测试。"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models import (
    Appeal,
    EntryExitRecord,
    Notification,
    Reservation,
    Restriction,
    User,
    ViolationRecord,
)
from app.models import enums as E
from app.schemas.workflows import GateEventIn
from app.services import gate as gate_service
from app.services.reservations import sweep_reservations
from app.services.violations import record_violation
from app.timeutil import now

SHANGHAI = ZoneInfo("Asia/Shanghai")
ROOM = {"name": "流程验收自习室", "location": "图书馆", "capacity": 20}


def _create_room_and_seat(client, admin):
    """通过管理员接口建立一间测试自习室和一个可预约座位。"""
    room_response = client.post("/api/admin/rooms", headers=admin, json=ROOM)
    assert room_response.status_code == 201, room_response.text
    room_id = room_response.json()["id"]
    seat_response = client.post(
        f"/api/admin/rooms/{room_id}/seats",
        headers=admin,
        json={"code": "A01", "zone_type": "quiet", "status": "available"},
    )
    assert seat_response.status_code == 201, seat_response.text
    return room_id, seat_response.json()["id"]


def _create_reservation(client, admin, headers, *, day_offset=1, request_key=None):
    """创建带开放时段的测试预约，并返回房间、座位和预约响应。"""
    room_id, seat_id = _create_room_and_seat(client, admin)
    booking_day = now().date() + timedelta(days=day_offset)
    day_type = "weekend" if booking_day.weekday() >= 5 else "weekday"
    schedule = client.post(
        f"/api/admin/rooms/{room_id}/schedules",
        headers=admin,
        json={"day_type": day_type, "open_time": "06:00", "close_time": "23:00"},
    )
    assert schedule.status_code == 201, schedule.text
    # 预约校验按 Asia/Shanghai 的当前分钟判断；测试固定到半小时边界。
    current = now()
    start_day = booking_day if booking_day > current.date() else current.date()
    start_hour = 8 if start_day > current.date() else ((current.hour + 2) // 2) * 2
    start = datetime.combine(start_day, time(start_hour, 0), SHANGHAI)
    if start <= current:
        start += timedelta(days=1)
    body = {
        "seat_id": seat_id,
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=1)).isoformat(),
    }
    if request_key:
        body["request_key"] = request_key
    response = client.post("/api/reservations", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return room_id, seat_id, start, response.json()


@pytest.fixture
def admin_headers(client, make_user, login):
    """创建并登录具有自习室管理权限的管理员账号。"""
    make_user("A0000101", roles=("admin",))
    return login("A0000101", "secret123")


def test_reservation_idempotency_ownership_and_user_limit(client, admin_headers, make_user, login):
    """验证预约请求幂等、本人数据隔离以及同一用户的有效预约上限。"""
    make_user("20261001")
    make_user("20261002")
    first_user = login("20261001", "secret123")
    second_user = login("20261002", "secret123")
    room_id, seat_id, start, first = _create_reservation(
        client,
        admin_headers,
        first_user,
        request_key="request-key-001",
    )

    # 相同请求键返回原预约；第二个用户不能占用同一重叠座位时段。
    retry = client.post(
        "/api/reservations",
        headers=first_user,
        json={
            "seat_id": seat_id,
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
            "request_key": "request-key-001",
        },
    )
    assert retry.status_code == 201
    assert retry.json()["id"] == first["id"]
    conflict = client.post(
        "/api/reservations",
        headers=second_user,
        json={
            "seat_id": seat_id,
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
        },
    )
    assert conflict.status_code == 409

    # 第二个座位也不能绕过每位用户同时有效预约数量的系统设置。
    new_seat = client.post(
        f"/api/admin/rooms/{room_id}/seats",
        headers=admin_headers,
        json={"code": "A02", "zone_type": "quiet", "status": "available"},
    )
    assert new_seat.status_code == 201
    other_seat_id = new_seat.json()["id"]
    too_many = client.post(
        "/api/reservations",
        headers=first_user,
        json={
            "seat_id": other_seat_id,
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
        },
    )
    assert too_many.status_code == 409
    hidden = client.get("/api/reservations", headers=second_user)
    assert all(row["user_id"] != first["user_id"] for row in hidden.json())


def test_temporary_leave_timeout_creates_one_violation(
    client, admin_headers, make_user, login, api_db, monkeypatch
):
    """验证临时离开超过 30 分钟后释放预约，且重复扫描不会重复处罚。"""
    make_user("20261003")
    headers = login("20261003", "secret123")
    _, _, start, reservation = _create_reservation(client, admin_headers, headers)
    moment = start
    monkeypatch.setattr("app.services.reservations.now", lambda: moment)

    check_in = client.post(
        f"/api/reservations/{reservation['id']}/check-in",
        headers=headers,
        json={"seat_id": reservation["seat_id"]},
    )
    assert check_in.status_code == 200
    leave = client.post(f"/api/reservations/{reservation['id']}/temporary-leave", headers=headers)
    assert leave.status_code == 200
    assert leave.json()["status"] == E.ReservationStatus.TEMP_LEAVE.value

    with api_db() as session:
        first_scan = sweep_reservations(session, moment + timedelta(minutes=31))
        second_scan = sweep_reservations(session, moment + timedelta(minutes=32))
        saved = session.get(Reservation, reservation["id"])
        violations = list(
            session.scalars(
                select(ViolationRecord).where(ViolationRecord.reservation_id == reservation["id"])
            )
        )
    assert first_scan["temp_leave"] == 1
    assert second_scan["temp_leave"] == 0
    assert saved.status == E.ReservationStatus.TIMED_OUT
    assert len(violations) == 1


def test_late_cancellation_records_violation_and_notice(
    client, admin_headers, make_user, login, api_db, monkeypatch
):
    """验证预约开始前 15 分钟内取消时生成违规和站内结果通知。"""
    make_user("20261009")
    headers = login("20261009", "secret123")
    _, _, start, reservation = _create_reservation(client, admin_headers, headers)
    cancellation_time = start - timedelta(minutes=10)
    monkeypatch.setattr("app.api.reservations.now", lambda: cancellation_time)
    monkeypatch.setattr("app.services.reservations.now", lambda: cancellation_time)

    response = client.post(f"/api/reservations/{reservation['id']}/cancel", headers=headers)
    assert response.status_code == 200, response.text
    with api_db() as session:
        saved = session.get(Reservation, reservation["id"])
        violation = session.scalar(
            select(ViolationRecord).where(ViolationRecord.reservation_id == reservation["id"])
        )
        notice = session.scalar(
            select(Notification).where(
                Notification.idempotency_key == f"reservation:{reservation['id']}:cancelled"
            )
        )
    assert saved.status == E.ReservationStatus.CANCELLED
    assert saved.cancel_type == E.CancelType.LATE
    assert violation.violation_type == E.ViolationType.LATE_CANCEL
    assert notice is not None


def test_late_gate_event_is_linked_not_applied_and_notifies_user(
    client, admin_headers, make_user, login, api_db, monkeypatch
):
    """验证门禁迟到回调关联预约、提醒本人并保持预约状态不变。"""
    make_user("20261004")
    headers = login("20261004", "secret123")
    _, _, start, reservation_data = _create_reservation(client, admin_headers, headers)
    received_at = start + timedelta(minutes=10)
    monkeypatch.setattr("app.services.gate.now", lambda: received_at)

    with api_db() as session:
        user = session.get(User, reservation_data["user_id"])
        body = GateEventIn(
            external_id="gate-event-001",
            source_system="mock-gate-test",
            masked_user_key=gate_service.user_key_for_gate(user.student_no),
            record_type=E.EntryExitType.ENTRY,
            recorded_at=start,
            reservation_id=reservation_data["id"],
        )
        result = gate_service.process_gate_event(session, body)
        duplicate = gate_service.process_gate_event(session, body)
        saved_reservation = session.get(Reservation, reservation_data["id"])
        gate_record = session.scalar(
            select(EntryExitRecord).where(EntryExitRecord.external_id == body.external_id)
        )
        notices = list(
            session.scalars(
                select(Notification).where(
                    Notification.user_id == user.id,
                    Notification.idempotency_key.endswith(":late"),
                )
            )
        )

    assert result["sync_status"] == "late"
    assert result["reservation_id"] == reservation_data["id"]
    assert result["manual_appeal_required"] is True
    assert duplicate["duplicate"] is True
    assert saved_reservation.status == E.ReservationStatus.RESERVED
    assert gate_record.reservation_id == reservation_data["id"]
    assert len(notices) == 1


def test_gate_entry_cannot_reactivate_completed_reservation(
    client, admin_headers, make_user, login, api_db, monkeypatch
):
    """验证状态不匹配的门禁入馆事件进入人工处理而不复活已完成预约。"""
    make_user("20261005")
    headers = login("20261005", "secret123")
    _, _, start, reservation_data = _create_reservation(client, admin_headers, headers)
    monkeypatch.setattr("app.services.gate.now", lambda: start)

    with api_db() as session:
        reservation = session.get(Reservation, reservation_data["id"])
        reservation.status = E.ReservationStatus.COMPLETED
        session.commit()
        user = session.get(User, reservation.user_id)
        body = GateEventIn(
            external_id="gate-event-002",
            source_system="mock-gate-test",
            masked_user_key=gate_service.user_key_for_gate(user.student_no),
            record_type=E.EntryExitType.ENTRY,
            recorded_at=start,
            reservation_id=reservation.id,
        )
        result = gate_service.process_gate_event(session, body)
        session.refresh(reservation)
        record = session.scalar(
            select(EntryExitRecord).where(EntryExitRecord.external_id == body.external_id)
        )

    assert result["sync_status"] == "unmatched"
    assert result["manual_appeal_required"] is True
    assert reservation.status == E.ReservationStatus.COMPLETED
    assert record.reservation_id == reservation.id


def test_approved_appeal_lifts_restriction_and_notifies_user(
    client, admin_headers, make_user, login, api_db
):
    """验证管理员批准申诉后解除有效禁约并向申请人发送站内通知。"""
    make_user("20261007")
    headers = login("20261007", "secret123")
    moment = now()
    with api_db() as session:
        user = session.scalar(select(User).where(User.student_no == "20261007"))
        records = [
            record_violation(
                session,
                user_id=user.id,
                violation_type=E.ViolationType.NO_SHOW,
                reservation_id=None,
                description="预约开始后未签到。",
                occurred_at=moment + timedelta(minutes=index),
            )
            for index in range(3)
        ]
        session.flush()
        violation_id = records[-1].id
        restriction_id = records[-1].restriction_id
        session.commit()

    submitted = client.post(
        "/api/appeals",
        headers=headers,
        json={"violation_id": violation_id, "reason": "门禁设备异常导致签到失败"},
    )
    assert submitted.status_code == 201, submitted.text
    appeal_id = submitted.json()["id"]
    reviewed = client.patch(
        f"/api/admin/appeals/{appeal_id}",
        headers=admin_headers,
        json={"result": "approved", "review_comment": "核验后确认设备异常"},
    )
    assert reviewed.status_code == 200, reviewed.text

    with api_db() as session:
        appeal = session.get(Appeal, appeal_id)
        violation = session.get(ViolationRecord, violation_id)
        restriction = session.get(Restriction, restriction_id)
        notice = session.scalar(
            select(Notification).where(
                Notification.idempotency_key == f"appeal:{appeal_id}:reviewed"
            )
        )
    assert appeal.result == E.AppealResult.APPROVED
    assert violation.state == E.ViolationState.ARCHIVED
    assert restriction.status == E.RestrictionStatus.LIFTED
    assert notice is not None
    assert "已通过" in notice.content


def test_maintenance_cancels_pending_reservation_and_notifies(
    client, admin_headers, make_user, login, api_db
):
    """验证座位置为维护时会取消未开始预约并向预约人发送站内通知。"""
    make_user("20261006")
    headers = login("20261006", "secret123")
    _, seat_id, _, reservation = _create_reservation(client, admin_headers, headers)
    room_id = reservation["room_id"]

    response = client.patch(
        f"/api/admin/rooms/{room_id}/seats/{seat_id}/status",
        headers=admin_headers,
        json={"status": "maintenance", "reason": "设备检修"},
    )
    assert response.status_code == 200, response.text
    with api_db() as session:
        saved = session.get(Reservation, reservation["id"])
        notice = session.scalar(
            select(Notification).where(
                Notification.idempotency_key
                == f"reservation:{reservation['id']}:maintenance-cancelled"
            )
        )
    assert saved.status == E.ReservationStatus.ADMIN_CANCELLED
    assert notice is not None
    assert "不提供补偿" in notice.content


def test_full_seat_update_to_maintenance_also_cancels_bookings(
    client, admin_headers, make_user, login, api_db
):
    """验证完整座位编辑接口改为维护状态时执行相同的预约取消规则。"""
    make_user("20261008")
    headers = login("20261008", "secret123")
    room_id, seat_id, _, reservation = _create_reservation(client, admin_headers, headers)

    response = client.put(
        f"/api/admin/rooms/{room_id}/seats/{seat_id}",
        headers=admin_headers,
        json={
            "code": "A01",
            "zone_type": "quiet",
            "has_power": False,
            "by_window": False,
            "accessible": False,
            "status": "maintenance",
        },
    )
    assert response.status_code == 200, response.text
    with api_db() as session:
        saved = session.get(Reservation, reservation["id"])
    assert saved.status == E.ReservationStatus.ADMIN_CANCELLED


def test_report_endpoint_returns_supply_hours_and_excel(client, admin_headers):
    """验证管理员报表按开放座位计算计划时长并生成 Excel 文件。"""
    room_response = client.post("/api/admin/rooms", headers=admin_headers, json=ROOM)
    room_id = room_response.json()["id"]
    target_day = now().date() + timedelta(days=2)
    day_type = "weekend" if target_day.weekday() >= 5 else "weekday"
    schedule = client.post(
        f"/api/admin/rooms/{room_id}/schedules",
        headers=admin_headers,
        json={"day_type": day_type, "open_time": "06:00", "close_time": "23:00"},
    )
    assert schedule.status_code == 201
    seat = client.post(
        f"/api/admin/rooms/{room_id}/seats",
        headers=admin_headers,
        json={"code": "A01", "zone_type": "quiet", "status": "available"},
    )
    assert seat.status_code == 201

    params = {"start": target_day.isoformat(), "end": target_day.isoformat()}
    report = client.get("/api/admin/reports", headers=admin_headers, params=params)
    assert report.status_code == 200, report.text
    assert report.json()["utilization"]["available_hours"] == 17.0
    exported = client.get("/api/admin/reports/export.xlsx", headers=admin_headers, params=params)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def _gate_event(session, reservation, *, external_id, record_type, recorded_at):
    """构造指向指定预约的门禁事件并交给门禁服务处理。"""
    user = session.get(User, reservation.user_id)
    body = GateEventIn(
        external_id=external_id,
        source_system="mock-gate-test",
        masked_user_key=gate_service.user_key_for_gate(user.student_no),
        record_type=record_type,
        recorded_at=recorded_at,
        reservation_id=reservation.id,
    )
    return gate_service.process_gate_event(session, body)


def test_gate_exit_while_active_without_leave_times_out_with_violation(
    client, admin_headers, make_user, login, api_db, monkeypatch
):
    """使用中未声明临时离开即出馆：超时结束并记录未声明离开违规。"""
    make_user("20261101")
    headers = login("20261101", "secret123")
    _, _, start, data = _create_reservation(client, admin_headers, headers)
    moment = start + timedelta(minutes=10)
    monkeypatch.setattr("app.services.gate.now", lambda: moment)
    with api_db() as session:
        reservation = session.get(Reservation, data["id"])
        reservation.status = E.ReservationStatus.ACTIVE
        session.commit()
        result = _gate_event(
            session,
            reservation,
            external_id="g-exit-1",
            record_type=E.EntryExitType.EXIT,
            recorded_at=moment,
        )
        session.refresh(reservation)
        violations = list(
            session.scalars(
                select(ViolationRecord).where(ViolationRecord.reservation_id == data["id"])
            )
        )
    assert result["sync_status"] == "synced"
    assert reservation.status == E.ReservationStatus.TIMED_OUT
    assert [v.violation_type for v in violations] == [E.ViolationType.LEFT_UNDECLARED]


def test_gate_exit_during_temp_leave_keeps_seat_and_entry_resumes(
    client, admin_headers, make_user, login, api_db, monkeypatch
):
    """临时离开期间出馆保留座位；30 分钟内入馆恢复使用中，且不产生违规。"""
    make_user("20261102")
    headers = login("20261102", "secret123")
    _, _, start, data = _create_reservation(client, admin_headers, headers)
    monkeypatch.setattr("app.services.reservations.now", lambda: start)
    assert (
        client.post(
            f"/api/reservations/{data['id']}/check-in",
            headers=headers,
            json={"seat_id": data["seat_id"]},
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/reservations/{data['id']}/temporary-leave", headers=headers).status_code
        == 200
    )
    exit_at = start + timedelta(minutes=2)
    back_at = start + timedelta(minutes=20)
    with api_db() as session:
        reservation = session.get(Reservation, data["id"])
        monkeypatch.setattr("app.services.gate.now", lambda: exit_at)
        out = _gate_event(
            session,
            reservation,
            external_id="g-tl-exit",
            record_type=E.EntryExitType.EXIT,
            recorded_at=exit_at,
        )
        session.refresh(reservation)
        assert out["sync_status"] == "synced"
        assert reservation.status == E.ReservationStatus.TEMP_LEAVE
        assert reservation.temp_leave_state == E.TempLeaveState.WAITING
        monkeypatch.setattr("app.services.gate.now", lambda: back_at)
        back = _gate_event(
            session,
            reservation,
            external_id="g-tl-entry",
            record_type=E.EntryExitType.ENTRY,
            recorded_at=back_at,
        )
        session.refresh(reservation)
        violations = list(
            session.scalars(
                select(ViolationRecord).where(ViolationRecord.reservation_id == data["id"])
            )
        )
    assert back["sync_status"] == "synced"
    assert reservation.status == E.ReservationStatus.ACTIVE
    assert reservation.temp_leave_state == E.TempLeaveState.RETURNED
    assert violations == []


def test_gate_entry_after_temp_leave_window_is_not_applied(
    client, admin_headers, make_user, login, api_db, monkeypatch
):
    """超过 30 分钟临时离开期限后的入馆事件不恢复座位，转入人工核验。"""
    make_user("20261103")
    headers = login("20261103", "secret123")
    _, _, start, data = _create_reservation(client, admin_headers, headers)
    monkeypatch.setattr("app.services.reservations.now", lambda: start)
    client.post(
        f"/api/reservations/{data['id']}/check-in",
        headers=headers,
        json={"seat_id": data["seat_id"]},
    )
    client.post(f"/api/reservations/{data['id']}/temporary-leave", headers=headers)
    late = start + timedelta(minutes=35)
    monkeypatch.setattr("app.services.gate.now", lambda: late)
    with api_db() as session:
        reservation = session.get(Reservation, data["id"])
        result = _gate_event(
            session,
            reservation,
            external_id="g-tl-late",
            record_type=E.EntryExitType.ENTRY,
            recorded_at=late,
        )
        session.refresh(reservation)
    assert result["sync_status"] == "unmatched"
    assert reservation.status == E.ReservationStatus.TEMP_LEAVE


def test_current_scope_excludes_cancelled_future_reservation(
    client, admin_headers, make_user, login
):
    """已取消的未来预约只出现在历史列表，不出现在当前预约。"""
    make_user("20261104")
    headers = login("20261104", "secret123")
    _, _, _, data = _create_reservation(client, admin_headers, headers)
    cancel = client.post(f"/api/reservations/{data['id']}/cancel", headers=headers)
    assert cancel.status_code == 200, cancel.text
    current = client.get("/api/reservations?scope=current", headers=headers).json()
    history = client.get("/api/reservations?scope=history", headers=headers).json()
    assert data["id"] not in [row["id"] for row in current]
    assert data["id"] in [row["id"] for row in history]


def test_default_gate_secret_rejected_outside_dev(monkeypatch):
    """生产环境沿用默认门禁密钥时配置校验失败；dev/test 或自定义密钥可通过。"""
    from pydantic import ValidationError

    from app.config import Settings

    monkeypatch.delenv("STUDYROOM_GATE_HMAC_SECRET", raising=False)
    with pytest.raises(ValidationError):
        Settings(env="prod")
    assert Settings(env="test").env == "test"
    assert Settings(env="prod", gate_hmac_secret="x" * 32).env == "prod"
