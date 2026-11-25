"""Requirement-based defect probes, intentionally kept outside backend/tests.

Run from backend with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and:
python -m pytest ../docs/audit/evidence/test_audit_findings.py --import-mode=importlib
Failing assertions document current defects; no production database is used.
"""
from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import select

# Import the existing isolation fixtures BEFORE application imports.
from tests.conftest import api_db, client, login, make_user  # noqa: F401
from app import timeutil
from app.models import ArrivalRecord, EntryExitRecord, OpeningSchedule, Reservation, Restriction, Seat, StudyRoom, User, ViolationRecord
from app.models import enums as E
from app.services import reservations as service
from app.services.violations import record_violation


@pytest.fixture
def scenario(api_db, client, make_user, login, monkeypatch):
    current = [datetime(2026, 11, 2, 8, tzinfo=timeutil.tz())]
    monkeypatch.setattr(timeutil, "now", lambda: current[0])
    owner = login(*make_user("AUDIT001"))
    admin = login(*make_user("AUDADMIN", roles=("admin",)))
    ops = login(*make_user("AUDITOPS", roles=("ops",)))
    with api_db() as session:
        room = StudyRoom(name="审计隔离自习室", capacity=2)
        seats = [Seat(room=room, code=str(i), zone_type=E.ZoneType.QUIET) for i in (1, 2)]
        session.add_all([room, *seats])
        session.flush()
        for kind in E.DayType:
            session.add(OpeningSchedule(room_id=room.id, day_type=kind, open_time=time(6), close_time=time(23)))
        session.commit()
        uid = session.scalar(select(User.id).where(User.student_no == "AUDIT001"))
        ids = (room.id, seats[0].id, seats[1].id)
    start = current[0].replace(hour=9)
    response = client.post("/api/reservations", headers=owner, json={"seat_id": ids[1], "start_time": start.isoformat(), "end_time": (start + timedelta(hours=2)).isoformat(), "request_key": "audit-request-001"})
    assert response.status_code == 201, response.text
    return {"clock": current, "owner": owner, "admin": admin, "ops": ops, "uid": uid, "room": ids[0], "seat": ids[1], "other": ids[2], "rid": response.json()["id"], "start": start}


def seed_two_warnings(api_db, case):
    with api_db() as session:
        for i in (2, 1):
            record_violation(session, user_id=case["uid"], violation_type=E.ViolationType.NO_SHOW, reservation_id=None, description="审计合成既有违规", occurred_at=case["start"] - timedelta(days=i))
        session.commit()


def test_AUD01_third_late_cancel_must_trigger_restriction(api_db, client, scenario):
    """BR-031/095: the third counted warning must create a one-day ban."""
    c = scenario
    seed_two_warnings(api_db, c)
    c["clock"][0] = c["start"] - timedelta(minutes=10)
    assert client.post(f"/api/reservations/{c['rid']}/cancel", headers=c["owner"]).status_code == 200
    with api_db() as session:
        assert len(list(session.scalars(select(ViolationRecord)))) == 3
        ban = session.scalar(select(Restriction).where(Restriction.user_id == c["uid"]))
        assert ban is not None, "Third late-cancel warning created no restriction"


def test_AUD02_lazy_expiry_must_trigger_restriction(api_db, client, scenario):
    """BR-092/095: request-triggered expiry must use the penalty pipeline."""
    c = scenario
    seed_two_warnings(api_db, c)
    c["clock"][0] = c["start"] + timedelta(minutes=16)
    assert client.get("/api/reservations/current", headers=c["owner"]).status_code == 200
    with api_db() as session:
        assert session.get(Reservation, c["rid"]).status == E.ReservationStatus.EXPIRED
        assert session.scalar(select(Restriction).where(Restriction.user_id == c["uid"])) is not None, "Lazy expiry bypassed the third-warning penalty"


def test_AUD03_sweep_must_preserve_inclusive_checkin_endpoint(api_db, client, scenario):
    """BR-020: exactly +15 minutes remains inside the check-in window."""
    c = scenario
    c["clock"][0] = c["start"] + timedelta(minutes=15)
    with api_db() as session:
        service.sweep_reservations(session, c["clock"][0])
    response = client.post(f"/api/reservations/{c['rid']}/check-in", headers=c["owner"], json={"seat_id": c["seat"]})
    assert response.status_code == 200, response.text


def test_AUD04_sweep_must_preserve_temp_leave_endpoint(api_db, client, scenario):
    """ST-07: a return at exactly 30 minutes is allowed."""
    c = scenario
    c["clock"][0] = c["start"]
    assert client.post(f"/api/reservations/{c['rid']}/check-in", headers=c["owner"], json={"seat_id": c["seat"]}).status_code == 200
    assert client.post(f"/api/reservations/{c['rid']}/temporary-leave", headers=c["owner"]).status_code == 200
    c["clock"][0] += timedelta(minutes=30)
    with api_db() as session:
        service.sweep_reservations(session, c["clock"][0])
        assert session.get(Reservation, c["rid"]).status == E.ReservationStatus.TEMP_LEAVE, "Sweeper released the seat at the inclusive return endpoint"


@pytest.mark.parametrize("status", ["closed", "disabled"])
def test_AUD05_blocked_seat_must_cancel_future_booking(api_db, client, scenario, status):
    """BR-060/061: blocked seat states must handle existing reservations."""
    c = scenario
    response = client.patch(f"/api/admin/rooms/{c['room']}/seats/{c['seat']}/status", headers=c["admin"], json={"status": status, "reason": "审计隔离状态测试"})
    assert response.status_code == 200, response.text
    with api_db() as session:
        assert session.get(Reservation, c["rid"]).status == E.ReservationStatus.ADMIN_CANCELLED, f"Seat {status} retained a future reservation"


def test_AUD06_change_seat_must_update_arrival_reference(api_db, client, scenario):
    """Data consistency: arrival fact must refer to the booked physical seat."""
    c = scenario
    assert client.patch(f"/api/reservations/{c['rid']}/seat", headers=c["owner"], json={"seat_id": c["other"]}).status_code == 200
    c["clock"][0] = c["start"]
    assert client.post(f"/api/reservations/{c['rid']}/check-in", headers=c["owner"], json={"seat_id": c["other"]}).status_code == 200
    with api_db() as session:
        arrival = session.scalar(select(ArrivalRecord).where(ArrivalRecord.reservation_id == c["rid"]))
        assert arrival.seat_id == c["other"], "Arrival record still points at the old seat after change and check-in"


def test_AUD07_return_without_entry_evidence_must_be_rejected(api_db, client, scenario):
    """BR-071: ordinary return requires a re-entry event."""
    c = scenario
    c["clock"][0] = c["start"]
    assert client.post(f"/api/reservations/{c['rid']}/check-in", headers=c["owner"], json={"seat_id": c["seat"]}).status_code == 200
    assert client.post(f"/api/reservations/{c['rid']}/temporary-leave", headers=c["owner"]).status_code == 200
    with api_db() as session:
        assert list(session.scalars(select(EntryExitRecord))) == []
    response = client.post(f"/api/reservations/{c['rid']}/return", headers=c["owner"])
    assert response.status_code in (403, 409, 422), "Manual return succeeded with no gate entry evidence"


def test_AUD08_checkin_without_seat_identifier_must_be_rejected(client, scenario):
    """HD-02/UC-010: QR or damaged-label seat-identifier fallback is required."""
    c = scenario
    c["clock"][0] = c["start"]
    response = client.post(f"/api/reservations/{c['rid']}/check-in", headers=c["owner"])
    assert response.status_code in (409, 422), "Check-in succeeded without any seat identifier"


def test_AUD09_ops_must_not_access_personal_appeal_workflow(client, scenario):
    """PERM-013/014: ops role has no personal reservation/appeal workflow."""
    response = client.get("/api/appeals", headers=scenario["ops"])
    assert response.status_code == 403, "Ops role was permitted to enter the personal appeal workflow"


def test_AUD10_room_close_with_consistent_test_clock(api_db, client, scenario, monkeypatch):
    """Control: an imported clock must be patched as well as timeutil.now."""
    from app.services import admin_force_cancel
    c = scenario
    monkeypatch.setattr(admin_force_cancel, "now", lambda: c["clock"][0])
    response = client.patch(f"/api/admin/rooms/{c['room']}/status", headers=c["admin"], json={"status": "closed"})
    assert response.status_code == 200, response.text
    with api_db() as session:
        assert session.get(Reservation, c["rid"]).status == E.ReservationStatus.ADMIN_CANCELLED


def test_AUD11_schedule_change_with_consistent_test_clock(api_db, client, scenario, monkeypatch):
    from app.services import admin_force_cancel
    c = scenario
    monkeypatch.setattr(admin_force_cancel, "now", lambda: c["clock"][0])
    rows = client.get(f"/api/admin/rooms/{c['room']}/schedules", headers=c["admin"]).json()
    schedule = next(row for row in rows if row["day_type"] == "weekday")
    response = client.put(f"/api/admin/rooms/{c['room']}/schedules/{schedule['id']}", headers=c["admin"], json={"day_type": "weekday", "open_time": "06:00", "close_time": "08:30"})
    assert response.status_code == 200, response.text
    with api_db() as session:
        assert session.get(Reservation, c["rid"]).status == E.ReservationStatus.ADMIN_CANCELLED
