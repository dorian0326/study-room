# ruff: noqa: F811
"""Course regression: SRS constraints and CHG-01/02/03, real file SQLite."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import AuditLog, Reservation, ViolationRecord
from app.models import enums as E
from app.services import reservations as service
from tests.test_gaps import clock, room_seats  # noqa: F401


@pytest.fixture
def case(client, make_user, login, clock, room_seats):
    owner = login(*make_user("COURSE01"))
    other = login(*make_user("COURSE02"))
    admin = login(*make_user("COURSEAD", roles=("admin",)))
    ops = login(*make_user("COURSEOP", roles=("ops",)))
    start = clock.at + timedelta(hours=1)
    end = start + timedelta(hours=1)
    r = client.post(
        "/api/reservations",
        headers=owner,
        json={
            "seat_id": room_seats.q1,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "request_key": "course-request-001",
        },
    )
    assert r.status_code == 201, r.text
    return dict(
        owner=owner,
        other=other,
        admin=admin,
        ops=ops,
        start=start,
        end=end,
        rid=r.json()["id"],
        seat=room_seats.q1,
        room=room_seats.room,
    )


def check_in(client, case, clock):
    clock.at = case["start"]
    r = client.post(
        f"/api/reservations/{case['rid']}/check-in",
        headers=case["owner"],
        json={"seat_id": case["seat"]},
    )
    assert r.status_code == 200, r.text


def test_checkout_grace_releases_seat_and_preserves_next_user(client, case, clock, api_db):
    check_in(client, case, clock)
    clock.at = case["end"]
    with api_db() as session:
        result = service.sweep_reservations(session, clock.at)
        assert result["no_checkout"] == 0
        assert session.get(Reservation, case["rid"]).status == E.ReservationStatus.ACTIVE
    seat = client.get(f"/api/seats/{case['seat']}", headers=case["other"]).json()
    assert seat["status"] == "available"
    pending = client.get("/api/reservations?scope=pending-confirmation", headers=case["owner"])
    assert [r["id"] for r in pending.json()] == [case["rid"]]
    created = client.post(
        "/api/reservations",
        headers=case["other"],
        json={
            "seat_id": case["seat"],
            "start_time": case["end"].isoformat(),
            "end_time": (case["end"] + timedelta(hours=1)).isoformat(),
            "request_key": "course-next-user-001",
        },
    )
    assert created.status_code == 201, created.text
    next_id = created.json()["id"]
    assert (
        client.post(
            f"/api/reservations/{next_id}/check-in",
            headers=case["other"],
            json={"seat_id": case["seat"]},
        ).status_code
        == 200
    )
    clock.at = case["end"] + timedelta(minutes=29, seconds=59)
    ended = client.post(
        f"/api/reservations/{case['rid']}/end", headers=case["owner"], json={"confirm": True}
    )
    assert ended.status_code == 200, ended.text
    assert ended.json()["duration_minutes"] == 60
    with api_db() as session:
        assert session.get(Reservation, next_id).status == E.ReservationStatus.ACTIVE
        assert not list(session.scalars(select(ViolationRecord)))


def test_checkout_timeout_at_30_minutes_is_deduplicated(client, case, clock, api_db):
    check_in(client, case, clock)
    clock.at = case["end"] + timedelta(minutes=29, seconds=59)
    with api_db() as session:
        assert service.sweep_reservations(session, clock.at)["no_checkout"] == 0
    clock.at += timedelta(seconds=1)
    with api_db() as session:
        assert service.sweep_reservations(session, clock.at)["no_checkout"] == 1
        assert service.sweep_reservations(session, clock.at)["no_checkout"] == 0
        violations = list(session.scalars(select(ViolationRecord)))
        assert len(violations) == 1
        assert violations[0].violation_type == E.ViolationType.NO_CHECKOUT
        assert violations[0].is_offset  # first raw event is not a full warning
    assert (
        client.post(
            f"/api/reservations/{case['rid']}/end", headers=case["owner"], json={"confirm": True}
        ).status_code
        == 409
    )


def test_early_checkin_then_end_is_completed_not_cancelled(client, case, clock, api_db):
    clock.at = case["start"] - timedelta(minutes=10)
    response = client.post(
        f"/api/reservations/{case['rid']}/check-in",
        headers=case["owner"],
        json={"seat_id": case["seat"]},
    )
    assert response.status_code == 200, response.text
    ended = client.post(
        f"/api/reservations/{case['rid']}/end", headers=case["owner"], json={"confirm": True}
    )
    assert ended.status_code == 200, ended.text
    with api_db() as session:
        assert session.get(Reservation, case["rid"]).status == E.ReservationStatus.COMPLETED
        assert not list(session.scalars(select(ViolationRecord)))


@pytest.mark.parametrize("entry", ["patch", "put", "csv"])
@pytest.mark.parametrize("state", ["maintenance", "closed", "disabled"])
def test_blocked_states_cancel_pending_in_all_entrypoints(client, case, api_db, entry, state):
    base = f"/api/admin/rooms/{case['room']}/seats"
    if entry == "patch":
        response = client.patch(
            f"{base}/{case['seat']}/status",
            headers=case["admin"],
            json={"status": state, "reason": "课程隔离维护"},
        )
    elif entry == "put":
        response = client.put(
            f"{base}/{case['seat']}",
            headers=case["admin"],
            json={"code": "Q01", "zone_type": "quiet", "status": state},
        )
    else:
        response = client.post(
            f"{base}/import",
            headers=case["admin"],
            json={"content": f"code,zone_type,status\nQ01,quiet,{state}"},
        )
    assert response.status_code == 200, response.text
    with api_db() as session:
        assert session.get(Reservation, case["rid"]).status == E.ReservationStatus.ADMIN_CANCELLED
        assert not list(session.scalars(select(ViolationRecord)))


def test_admin_reservations_pagination_and_roles(client, case):
    r = client.get("/api/admin/reservations?page=1&size=1", headers=case["admin"])
    assert r.status_code == 200
    assert r.json()["total"] == 1 and len(r.json()["items"]) == 1
    for role in ("owner", "ops"):
        assert client.get("/api/admin/reservations", headers=case[role]).status_code == 403
    assert client.get("/api/appeals", headers=case["ops"]).status_code == 403


def test_gate_read_is_audited_and_private(client, case, api_db):
    for role in ("owner", "admin"):
        assert client.get("/api/ops/entry-exit/records", headers=case[role]).status_code == 403
    assert client.get("/api/ops/entry-exit/records", headers=case["ops"]).status_code == 200
    with api_db() as session:
        assert (
            len(
                list(
                    session.scalars(
                        select(AuditLog).where(AuditLog.target_type == "entry_exit_read")
                    )
                )
            )
            == 1
        )


def test_no_blank_checkin_and_no_manual_return(client, case, clock):
    clock.at = case["start"]
    assert (
        client.post(f"/api/reservations/{case['rid']}/check-in", headers=case["owner"]).status_code
        == 422
    )
    check_in(client, case, clock)
    assert (
        client.post(
            f"/api/reservations/{case['rid']}/temporary-leave", headers=case["owner"]
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/reservations/{case['rid']}/return", headers=case["owner"]).status_code
        == 409
    )


def test_success_resets_consecutive_login_failures(client, make_user, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "login_max_failures", 3)
    make_user("COURSE99")

    def attempt(password):
        return client.post("/api/auth/login", json={"student_no": "COURSE99", "password": password})

    assert attempt("wrong123").status_code == 401
    assert attempt("wrong123").status_code == 401
    assert attempt("secret123").status_code == 200
    assert attempt("wrong123").status_code == 401
    assert attempt("secret123").status_code == 200


def test_static_spa_and_unknown_api(client):
    page = client.get("/workflows")
    assert page.status_code == 200 and '<div id="app">' in page.text
    missing = client.get("/api/does-not-exist")
    assert missing.status_code == 404 and "application/json" in missing.headers["content-type"]
