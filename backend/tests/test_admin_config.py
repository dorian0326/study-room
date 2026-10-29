# ruff: noqa: E501
"""#22：自习室增删改关、开放时间、节假日、业务参数，以及操作留痕。"""

import json

import pytest
from sqlalchemy import select

from app.models import AuditLog, Seat
from app.models.enums import ZoneType


@pytest.fixture
def admin(client, make_user, login):
    make_user("A0000001", roles=("admin",))
    return login("A0000001", "secret123")


ROOM = {"name": "图书馆 301", "location": "图书馆三楼", "capacity": 80, "facilities": "插座"}


def _logs(api_db, target):
    with api_db() as s:
        return list(s.scalars(select(AuditLog).where(AuditLog.target_type == target)))


def test_non_admin_forbidden(client, make_user, login):
    make_user("20260001")
    make_user("20260002", roles=("ops",))
    for sno in ("20260001", "20260002"):
        h = login(sno, "secret123")
        assert client.post("/api/admin/rooms", headers=h, json=ROOM).status_code == 403
        assert client.get("/api/admin/settings", headers=h).status_code == 403


def test_room_crud_and_close(client, admin, api_db):
    r = client.post("/api/admin/rooms", headers=admin, json=ROOM)
    assert r.status_code == 201 and r.json()["status"] == "open"
    rid = r.json()["id"]
    assert client.post("/api/admin/rooms", headers=admin, json=ROOM).status_code == 409

    r = client.put(f"/api/admin/rooms/{rid}", headers=admin, json={**ROOM, "capacity": 60})
    assert r.json()["capacity"] == 60
    r = client.patch(f"/api/admin/rooms/{rid}/status", headers=admin, json={"status": "closed"})
    assert r.json()["status"] == "closed"
    assert [x["id"] for x in client.get("/api/admin/rooms", headers=admin).json()] == [rid]
    assert client.delete(f"/api/admin/rooms/{rid}", headers=admin).status_code == 204
    assert client.delete(f"/api/admin/rooms/{rid}", headers=admin).status_code == 404

    logs = _logs(api_db, "study_room")
    assert len(logs) == 3 and all(log.op_type == "admin_action" for log in logs)
    assert json.loads(logs[1].before_value)["capacity"] == 80
    assert json.loads(logs[1].after_value)["capacity"] == 60
    assert len(_logs(api_db, "study_room_status")) == 1


def test_room_with_seats_cannot_be_deleted(client, admin, api_db):
    rid = client.post("/api/admin/rooms", headers=admin, json=ROOM).json()["id"]
    with api_db() as s:
        s.add(Seat(room_id=rid, code="A01", zone_type=ZoneType.QUIET))
        s.commit()
    r = client.delete(f"/api/admin/rooms/{rid}", headers=admin)
    assert r.status_code == 409 and "关闭" in r.json()["detail"]


def test_opening_schedules(client, admin, api_db):
    rid = client.post("/api/admin/rooms", headers=admin, json=ROOM).json()["id"]
    url = f"/api/admin/rooms/{rid}/schedules"
    ok = {"day_type": "weekday", "open_time": "08:00", "close_time": "22:00"}
    r = client.post(url, headers=admin, json=ok)
    assert r.status_code == 201
    sid = r.json()["id"]

    # 超出 06:00–23:30 或跨零点
    assert client.post(url, headers=admin, json={**ok, "open_time": "05:30"}).status_code == 422
    assert client.post(url, headers=admin, json={**ok, "close_time": "23:45"}).status_code == 422
    assert client.post(url, headers=admin, json={**ok, "close_time": "07:00"}).status_code == 422

    holiday = {
        **ok,
        "day_type": "holiday",
        "effective_from": "2026-10-01",
        "effective_to": "2026-10-07",
    }
    assert client.post(url, headers=admin, json=holiday).status_code == 201
    r = client.put(f"{url}/{sid}", headers=admin, json={**ok, "close_time": "23:00"})
    assert r.json()["close_time"] == "23:00:00"
    assert len(client.get(url, headers=admin).json()) == 2
    assert client.delete(f"{url}/{sid}", headers=admin).status_code == 204
    assert client.put(f"{url}/{sid}", headers=admin, json=ok).status_code == 404
    assert len(_logs(api_db, "opening_schedule")) == 4


def test_calendar_days(client, admin):
    body = {"day": "2026-10-01", "day_type": "holiday", "note": "国庆"}
    assert client.put("/api/admin/calendar/2026-10-01", headers=admin, json=body).status_code == 200
    body2 = {**body, "day_type": "weekday"}
    assert (
        client.put("/api/admin/calendar/2026-10-01", headers=admin, json=body2).status_code == 422
    )
    assert client.get("/api/admin/calendar", headers=admin).json()[0]["note"] == "国庆"
    assert client.delete("/api/admin/calendar/2026-10-01", headers=admin).status_code == 204


def test_business_settings(client, admin, api_db):
    s = client.get("/api/admin/settings", headers=admin).json()
    assert s["no_show_after_minutes"] == 15 and s["penalty_base_threshold"] == 3
    assert s["opening_earliest"] == "06:00:00"

    s["no_show_after_minutes"] = 20
    r = client.put("/api/admin/settings", headers=admin, json=s)
    assert r.status_code == 200 and r.json()["no_show_after_minutes"] == 20
    assert client.get("/api/admin/settings", headers=admin).json()["no_show_after_minutes"] == 20

    assert (
        client.put(
            "/api/admin/settings", headers=admin, json={**s, "temp_leave_minutes": 0}
        ).status_code
        == 422
    )
    assert (
        client.put("/api/admin/settings", headers=admin, json={**s, "unknown": 1}).status_code
        == 422
    )

    (log,) = _logs(api_db, "system_settings")
    assert json.loads(log.before_value) == {"no_show_after_minutes": 15}
    assert json.loads(log.after_value) == {"no_show_after_minutes": 20}

    # 收窄开放窗口后，新时段受新边界约束
    client.put("/api/admin/settings", headers=admin, json={**s, "opening_earliest": "07:00:00"})
    rid = client.post("/api/admin/rooms", headers=admin, json=ROOM).json()["id"]
    r = client.post(
        f"/api/admin/rooms/{rid}/schedules",
        headers=admin,
        json={"day_type": "weekday", "open_time": "06:30", "close_time": "22:00"},
    )
    assert r.status_code == 422 and "07:00" in r.json()["detail"]
