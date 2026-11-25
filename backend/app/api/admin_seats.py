"""管理员座位布局、批量导入和维修停用接口。"""

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import timeutil
from app.db import transaction
from app.deps import SessionDep, client_ip, require_permission
from app.models import Reservation, Seat, StudyRoom, User
from app.models import enums as E
from app.models.enums import AuditOpType
from app.schemas.workflows import SeatImportIn, SeatIn, SeatMaintenanceIn, SeatOut, SeatStatusOut
from app.services import audit
from app.services.notifications import create_notification


def now():
    return timeutil.now()


router = APIRouter(prefix="/admin/rooms", tags=["admin-seats"])
RoomAdmin = Annotated[User, Depends(require_permission("room:manage"))]


def _room(session: SessionDep, room_id: int) -> StudyRoom:
    """检查目标自习室存在，统一生成清晰的 404 响应。"""
    room = session.get(StudyRoom, room_id)
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "自习室不存在")
    return room


def _log(
    session: SessionDep,
    request: Request,
    operator: User,
    target_id: int,
    before: dict | None,
    after: dict | None,
) -> None:
    """为座位新增、修改和停用操作写入审计日志。"""
    # 维修停用会批量取消预约，审计字段记录操作者、时间和修改前后状态。
    audit.record(
        session,
        operator=operator,
        op_type=AuditOpType.ADMIN_ACTION,
        target_type="seat",
        target_id=target_id,
        before=before,
        after=after,
        ip=client_ip(request),
    )


def _dump_seat(seat: Seat) -> dict:
    """以 JSON 兼容格式序列化座位属性供审计和 API 响应使用。"""
    return SeatOut.model_validate(seat).model_dump(mode="json")


def _cancel_for_maintenance(session: SessionDep, seat: Seat, operator: User, reason: str) -> int:
    """维修座位时强制取消所有未开始预约并通知用户，不生成补偿记录。"""
    moment = now()
    # 仅取消尚未签到且开始时间在未来的预约，不中断正在使用的座位。
    pending = list(
        session.scalars(
            select(Reservation).where(
                Reservation.seat_id == seat.id,
                Reservation.status == E.ReservationStatus.RESERVED,
                Reservation.end_time > moment,
            )
        )
    )
    for reservation in pending:
        reservation.status = E.ReservationStatus.ADMIN_CANCELLED
        reservation.cancel_type = E.CancelType.SYSTEM
        reservation.cancelled_at = moment
        reservation.cancel_reason = "座位进入维护，系统强制取消（不补偿）"
        create_notification(
            session,
            user_id=reservation.user_id,
            notification_type=E.NotificationType.MAINTENANCE,
            content=(
                f"座位 {seat.code} 已进入维护，你的预约 {reservation.reservation_no} "
                "已取消；本次不提供补偿。"
            ),
            idempotency_key=f"reservation:{reservation.id}:maintenance-cancelled",
        )
    # 维护原因写入独立审计事件，避免仅凭状态变更丢失操作背景。
    audit.record(
        session,
        operator=operator,
        op_type=AuditOpType.ADMIN_ACTION,
        target_type="seat_maintenance",
        target_id=seat.id,
        before=None,
        after={"reason": reason, "cancelled_reservations": len(pending)},
    )
    return len(pending)


@router.get("/{room_id}/seats", response_model=list[SeatOut])
def list_seats(room_id: int, _: RoomAdmin, session: SessionDep):
    """按座位编号列出指定自习室的布局和设施属性。"""
    _room(session, room_id)
    return list(session.scalars(select(Seat).where(Seat.room_id == room_id).order_by(Seat.code)))


@router.post("/{room_id}/seats", response_model=SeatOut, status_code=status.HTTP_201_CREATED)
def create_seat(
    room_id: int,
    body: SeatIn,
    operator: RoomAdmin,
    session: SessionDep,
    request: Request,
):
    """新增座位并保存靠窗、电源、无障碍和区域等属性。"""
    _room(session, room_id)
    try:
        with transaction(session):
            seat = Seat(room_id=room_id, **body.model_dump())
            seat.status_changed_at = now()
            session.add(seat)
            session.flush()
            _log(session, request, operator, seat.id, None, _dump_seat(seat))
    except IntegrityError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "该自习室已存在相同编号的座位") from error
    return seat


@router.put("/{room_id}/seats/{seat_id}", response_model=SeatOut)
def update_seat(
    room_id: int,
    seat_id: int,
    body: SeatIn,
    operator: RoomAdmin,
    session: SessionDep,
    request: Request,
):
    """更新座位编号、区域偏好和设备状态，并保持修改审计。"""
    seat = session.get(Seat, seat_id)
    if seat is None or seat.room_id != room_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "座位不存在")
    before = _dump_seat(seat)
    try:
        with transaction(session):
            for field, value in body.model_dump().items():
                setattr(seat, field, value)
            seat.status_changed_at = now()
            # 完整更新接口若直接将座位置为维护，也执行与状态专用接口相同的预约取消流程。
            if body.status in (
                E.SeatStatus.MAINTENANCE,
                E.SeatStatus.CLOSED,
                E.SeatStatus.DISABLED,
            ):
                _cancel_for_maintenance(session, seat, operator, "管理员通过座位编辑设为维护")
            session.flush()
            _log(session, request, operator, seat.id, before, _dump_seat(seat))
    except IntegrityError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "该自习室已存在相同编号的座位") from error
    return seat


@router.patch("/{room_id}/seats/{seat_id}/status", response_model=SeatStatusOut)
def set_seat_status(
    room_id: int,
    seat_id: int,
    body: SeatMaintenanceIn,
    operator: RoomAdmin,
    session: SessionDep,
    request: Request,
):
    """变更座位状态；维护中会取消待生效预约并发送站内通知。"""
    # 结束鉴权查询留下的只读事务，再拿写锁读取座位和待取消预约，避免与并发预约之间的检查-写入竞态。
    session.commit()
    with transaction(session, immediate=True):
        seat = session.get(Seat, seat_id)
        if seat is None or seat.room_id != room_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "座位不存在")
        before = _dump_seat(seat)
        seat.status = body.status
        seat.status_changed_at = now()
        cancelled = 0
        if body.status in (E.SeatStatus.MAINTENANCE, E.SeatStatus.CLOSED, E.SeatStatus.DISABLED):
            cancelled = _cancel_for_maintenance(session, seat, operator, body.reason)
        after = _dump_seat(seat)
        after["cancelled_reservations"] = cancelled
        _log(session, request, operator, seat.id, before, after)
    return {**_dump_seat(seat), "cancelled_reservations": cancelled}


@router.delete("/{room_id}/seats/{seat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_seat(
    room_id: int,
    seat_id: int,
    operator: RoomAdmin,
    session: SessionDep,
    request: Request,
):
    """仅删除从未产生预约历史的座位，避免破坏业务追溯。"""
    seat = session.get(Seat, seat_id)
    if seat is None or seat.room_id != room_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "座位不存在")
    used = session.scalar(select(Reservation.id).where(Reservation.seat_id == seat.id).limit(1))
    if used is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "该座位已有预约历史，请改为关闭或维护")
    with transaction(session):
        before = _dump_seat(seat)
        session.delete(seat)
        _log(session, request, operator, seat_id, before, None)


def _parse_row(row: dict[str, str], line_number: int) -> SeatIn:
    """将 CSV 行转换为经过字段校验的座位结构。"""
    # 配置文件使用英文列名，与接口 JSON 字段一一对应；布尔值仅接受明确值。
    values = {key: value.strip() for key, value in row.items() if key}
    for key in ("has_power", "by_window", "accessible"):
        if key in values:
            normalized = values[key].lower()
            if normalized not in {"true", "false", "1", "0", "yes", "no"}:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    f"CSV 第 {line_number} 行 {key} 只能为 true/false 或 1/0",
                )
            values[key] = normalized in {"true", "1", "yes"}
    try:
        return SeatIn.model_validate(values)
    except ValueError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"CSV 第 {line_number} 行字段不合法：{error}",
        ) from error


@router.post("/{room_id}/seats/import")
def import_seats(
    room_id: int,
    body: SeatImportIn,
    operator: RoomAdmin,
    session: SessionDep,
    request: Request,
):
    """原子导入 CSV 座位清单；按编号新增或更新座位属性。"""
    # 先完整解析和验证全部行，任何错误都在事务开始前返回，避免半份导入。
    try:
        reader = csv.DictReader(io.StringIO(body.content.lstrip("\ufeff")))
        if not reader.fieldnames or "code" not in reader.fieldnames:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "CSV 必须包含 code 列")
        parsed = [_parse_row(row, index) for index, row in enumerate(reader, start=2)]
    except csv.Error as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "CSV 格式无法解析") from error
    if not parsed:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "CSV 中没有可导入的座位行")
    codes = [seat.code for seat in parsed]
    if len(codes) != len(set(codes)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "CSV 中座位编号重复")

    created = 0
    updated = 0
    session.commit()
    with transaction(session, immediate=True):
        _room(session, room_id)
        # 编号冲突时更新已有座位；不会覆盖座位所属房间或既有预约记录。
        current = {
            seat.code: seat for seat in session.scalars(select(Seat).where(Seat.room_id == room_id))
        }
        for values in parsed:
            seat = current.get(values.code)
            if seat is None:
                seat = Seat(room_id=room_id, **values.model_dump())
                session.add(seat)
                created += 1
            else:
                for field, value in values.model_dump().items():
                    setattr(seat, field, value)
                updated += 1
            seat.status_changed_at = now()
            if values.status in (
                E.SeatStatus.MAINTENANCE,
                E.SeatStatus.CLOSED,
                E.SeatStatus.DISABLED,
            ):
                _cancel_for_maintenance(
                    session,
                    seat,
                    operator,
                    "批量导入将座位设为维护中",
                )
        session.flush()
        _log(
            session,
            request,
            operator,
            room_id,
            {"seat_count": len(current)},
            {"created": created, "updated": updated},
        )
    return {"created": created, "updated": updated, "total": len(parsed)}
