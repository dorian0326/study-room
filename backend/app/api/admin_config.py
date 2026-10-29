"""管理员配置（#22，FR-070/072/073，US-101/107）：自习室、开放时间、节假日、业务参数。

所有写操作都写入操作日志（BR-105）。
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import transaction
from app.deps import SessionDep, client_ip, require_permission
from app.models import CalendarDay, OpeningSchedule, Reservation, Seat, StudyRoom, User
from app.models.enums import AuditOpType
from app.schemas.admin import (
    BusinessSettings,
    CalendarDayIn,
    CalendarDayOut,
    RoomIn,
    RoomOut,
    RoomStatusIn,
    ScheduleIn,
    ScheduleOut,
)
from app.services import audit
from app.services.settings import get_business_settings, save_business_settings

router = APIRouter(prefix="/admin", tags=["admin-config"])
RoomAdmin = Annotated[User, Depends(require_permission("room:manage"))]
SettingsAdmin = Annotated[User, Depends(require_permission("settings:manage"))]


def _log(session: Session, request: Request, op: User, target: str, tid, before=None, after=None):  # noqa: ANN001
    audit.record(
        session,
        operator=op,
        op_type=AuditOpType.ADMIN_ACTION,
        target_type=target,
        target_id=tid,
        before=before,
        after=after,
        ip=client_ip(request),
    )


def _room(session: Session, room_id: int) -> StudyRoom:
    room = session.get(StudyRoom, room_id)
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "自习室不存在")
    return room


def _dump_room(room: StudyRoom) -> dict:
    return RoomOut.model_validate(room).model_dump(mode="json")


# ---------- 自习室 ----------
@router.get("/rooms", response_model=list[RoomOut])
def list_rooms(_: RoomAdmin, session: SessionDep):
    return list(session.scalars(select(StudyRoom).order_by(StudyRoom.id)))


@router.post("/rooms", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(body: RoomIn, op: RoomAdmin, session: SessionDep, request: Request):
    try:
        with transaction(session):
            room = StudyRoom(**body.model_dump())
            session.add(room)
            session.flush()
            _log(session, request, op, "study_room", room.id, after=_dump_room(room))
    except IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, "自习室名称已存在") from e
    return room


@router.put("/rooms/{room_id}", response_model=RoomOut)
def update_room(room_id: int, body: RoomIn, op: RoomAdmin, session: SessionDep, request: Request):
    room = _room(session, room_id)
    before = _dump_room(room)
    try:
        with transaction(session):
            for k, v in body.model_dump().items():
                setattr(room, k, v)
            session.flush()
            _log(session, request, op, "study_room", room.id, before, _dump_room(room))
    except IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, "自习室名称已存在") from e
    return room


@router.patch("/rooms/{room_id}/status", response_model=RoomOut)
def set_room_status(
    room_id: int, body: RoomStatusIn, op: RoomAdmin, session: SessionDep, request: Request
):
    """开放/关闭自习室。关闭后不再接受新预约（BR-065，由预约模块按 status 过滤）。"""
    room = _room(session, room_id)
    before = room.status
    with transaction(session):
        room.status = body.status
        _log(
            session,
            request,
            op,
            "study_room_status",
            room.id,
            {"status": before},
            {"status": body.status},
        )
    return room


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: int, op: RoomAdmin, session: SessionDep, request: Request):
    """仅允许删除没有座位和预约记录的自习室；已有数据的请改用「关闭」。"""
    room = _room(session, room_id)
    in_use = session.scalar(
        select(
            exists().where(Seat.room_id == room_id) | exists().where(Reservation.room_id == room_id)
        )
    )
    if in_use:
        raise HTTPException(status.HTTP_409_CONFLICT, "该自习室已有座位或预约记录，请改为关闭")
    with transaction(session):
        before = _dump_room(room)
        session.delete(room)
        _log(session, request, op, "study_room", room_id, before=before)


# ---------- 开放时间 ----------
def _check_window(session: Session, body: ScheduleIn) -> None:
    s = get_business_settings(session)
    if body.open_time < s.opening_earliest or body.close_time > s.opening_latest:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"开放时段须在 {s.opening_earliest:%H:%M}–{s.opening_latest:%H:%M} 之间",
        )


def _schedule(session: Session, room_id: int, sid: int) -> OpeningSchedule:
    sch = session.get(OpeningSchedule, sid)
    if sch is None or sch.room_id != room_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "开放时段不存在")
    return sch


def _dump_sch(sch: OpeningSchedule) -> dict:
    return ScheduleOut.model_validate(sch).model_dump(mode="json")


@router.get("/rooms/{room_id}/schedules", response_model=list[ScheduleOut])
def list_schedules(room_id: int, _: RoomAdmin, session: SessionDep):
    _room(session, room_id)
    return list(
        session.scalars(
            select(OpeningSchedule)
            .where(OpeningSchedule.room_id == room_id)
            .order_by(OpeningSchedule.day_type, OpeningSchedule.open_time)
        )
    )


@router.post(
    "/rooms/{room_id}/schedules", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED
)
def create_schedule(
    room_id: int, body: ScheduleIn, op: RoomAdmin, session: SessionDep, request: Request
):
    _room(session, room_id)
    _check_window(session, body)
    with transaction(session):
        sch = OpeningSchedule(room_id=room_id, **body.model_dump())
        session.add(sch)
        session.flush()
        _log(session, request, op, "opening_schedule", sch.id, after=_dump_sch(sch))
    return sch


@router.put("/rooms/{room_id}/schedules/{sid}", response_model=ScheduleOut)
def update_schedule(
    room_id: int, sid: int, body: ScheduleIn, op: RoomAdmin, session: SessionDep, request: Request
):
    """修改开放时间：只影响之后的新预约，已有预约不追溯（BR-062，由预约模块执行）。"""
    sch = _schedule(session, room_id, sid)
    _check_window(session, body)
    before = _dump_sch(sch)
    with transaction(session):
        for k, v in body.model_dump().items():
            setattr(sch, k, v)
        session.flush()
        _log(session, request, op, "opening_schedule", sch.id, before, _dump_sch(sch))
    return sch


@router.delete("/rooms/{room_id}/schedules/{sid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(room_id: int, sid: int, op: RoomAdmin, session: SessionDep, request: Request):
    sch = _schedule(session, room_id, sid)
    before = _dump_sch(sch)
    with transaction(session):
        session.delete(sch)
        _log(session, request, op, "opening_schedule", sid, before=before)


# ---------- 节假日 / 考试周 ----------
@router.get("/calendar", response_model=list[CalendarDayOut])
def list_calendar(_: RoomAdmin, session: SessionDep):
    return list(session.scalars(select(CalendarDay).order_by(CalendarDay.day)))


@router.put("/calendar/{day}", response_model=CalendarDayOut)
def upsert_calendar_day(
    day: date, body: CalendarDayIn, op: RoomAdmin, session: SessionDep, request: Request
):
    if body.day != day:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "路径日期与请求体不一致")
    row = session.get(CalendarDay, body.day)
    before = CalendarDayOut.model_validate(row).model_dump(mode="json") if row else None
    with transaction(session):
        row = row or CalendarDay(day=body.day)
        row.day_type, row.note = body.day_type, body.note
        session.add(row)
        _log(session, request, op, "calendar_day", day, before, body.model_dump(mode="json"))
    return row


@router.delete("/calendar/{day}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calendar_day(day: date, op: RoomAdmin, session: SessionDep, request: Request):
    row = session.get(CalendarDay, day)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "该日期未设置")
    before = CalendarDayOut.model_validate(row).model_dump(mode="json")
    with transaction(session):
        session.delete(row)
        _log(session, request, op, "calendar_day", day, before=before)


# ---------- 业务参数 ----------
@router.get("/settings", response_model=BusinessSettings)
def read_settings(_: SettingsAdmin, session: SessionDep):
    return get_business_settings(session)


@router.put("/settings", response_model=BusinessSettings)
def update_settings(
    body: BusinessSettings, op: SettingsAdmin, session: SessionDep, request: Request
):
    with transaction(session):
        changed = save_business_settings(session, body, op)
        if changed:
            _log(
                session,
                request,
                op,
                "system_settings",
                None,
                {k: v[0] for k, v in changed.items()},
                {k: v[1] for k, v in changed.items()},
            )
    return get_business_settings(session)
