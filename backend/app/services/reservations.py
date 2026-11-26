"""预约事务、幂等与签到（#12–#16）。

认证依赖已开启只读事务，因此业务使用同一引擎的独立会话，先 BEGIN IMMEDIATE 再查写；
不升级认证会话的读锁，也不提交认证会话中的任何状态。
"""

import hashlib
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app import timeutil
from app.db import transaction
from app.models import ArrivalRecord, Reservation, Restriction, Seat, User, ViolationRecord
from app.models import enums as E
from app.schemas.reservations import CheckInIn, ReservationIn, ReservationOut
from app.services import audit
from app.services.availability import BLOCKED_SEAT_STATUSES, BookingError, covers, overlapping
from app.services.notifications import create_notification
from app.services.settings import get_business_settings
from app.services.violations import archive_expired_violations, record_violation

logger = logging.getLogger(__name__)


def now():
    """可被测试替换；默认转发到 timeutil.now（clock 夹具会 patch 后者）。"""
    return timeutil.now()


@contextmanager
def write_transaction(source: Session) -> Iterator[Session]:
    try:
        with Session(source.get_bind(), expire_on_commit=False, autoflush=False) as session:
            with transaction(session, immediate=True):
                yield session
    except OperationalError as exc:
        if "locked" in str(exc.orig).lower() or "busy" in str(exc.orig).lower():
            raise BookingError(503, "预约服务繁忙，请稍后使用相同请求重试") from exc
        raise
    except IntegrityError as exc:
        raise BookingError(409, "预约发生冲突，请刷新座位后重试") from exc


def _owned(session: Session, user_id: int, rid: int) -> Reservation:
    reservation = session.scalar(
        select(Reservation).where(Reservation.id == rid, Reservation.user_id == user_id)
    )
    if reservation is None:
        raise BookingError(404, "预约不存在")
    return reservation


def _user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None or user.status != E.AccountStatus.NORMAL:
        raise BookingError(403, "账户不可用")
    if not any(r.name in (E.RoleName.USER, E.RoleName.ADMIN) for r in user.roles):
        raise BookingError(403, "无权限执行此操作")
    return user


def _restriction(session: Session, user_id: int, at: datetime) -> None:
    ban = session.scalar(
        select(Restriction)
        .where(
            Restriction.user_id == user_id,
            Restriction.status == E.RestrictionStatus.ACTIVE,
            Restriction.start_at <= at,
            Restriction.end_at > at,
        )
        .order_by(Restriction.end_at.desc())
    )
    if ban is not None:
        raise BookingError(403, f"当前处于禁约期，解除时间：{ban.end_at.isoformat()}")


def _seat(session: Session, sid: int) -> Seat:
    seat = session.get(Seat, sid)
    if seat is None:
        raise BookingError(404, "座位不存在")
    if seat.status in BLOCKED_SEAT_STATUSES or seat.room.status != E.RoomStatus.OPEN:
        raise BookingError(409, "座位维护中或已关闭，请选择其他座位")
    return seat


def _check_slot(
    session: Session,
    seat: Seat,
    start: datetime,
    end: datetime,
    user_id: int,
    excluding: int | None = None,
) -> None:
    if not covers(session, seat.room_id, start, end):
        raise BookingError(422, "时段须完整落在自习室开放时间内（06:00–23:30，不跨零点）")
    if any(r.id != excluding for r in overlapping(session, seat.id, start, end)):
        raise BookingError(409, "该座位在所选时段已被预约，请重新选择")
    # HD-35：同一用户同一时段只可占用一个座位；相邻、不重叠时段可以预约。
    if (
        session.scalar(
            select(Reservation.id)
            .where(
                Reservation.user_id == user_id,
                Reservation.status.in_(E.ACTIVE_RESERVATION_STATUSES),
                Reservation.start_time < end,
                Reservation.end_time > start,
                Reservation.id != excluding if excluding is not None else True,
            )
            .limit(1)
        )
        is not None
    ):
        raise BookingError(409, "你在该时段已有有效预约")


def _arrival(session: Session, rid: int) -> ArrivalRecord | None:
    return session.scalar(
        select(ArrivalRecord).where(ArrivalRecord.reservation_id == rid).order_by(ArrivalRecord.id)
    )


def reservation_out(session: Session, reservation: Reservation) -> ReservationOut:
    settings = get_business_settings(session)
    arrival = _arrival(session, reservation.id)
    return ReservationOut(
        id=reservation.id,
        reservation_no=reservation.reservation_no,
        user_id=reservation.user_id,
        room_id=reservation.room_id,
        room_name=reservation.seat.room.name,
        seat_id=reservation.seat_id,
        seat_code=reservation.seat.code,
        start_time=reservation.start_time,
        end_time=reservation.end_time,
        status=reservation.status,
        cancel_type=reservation.cancel_type,
        cancelled_at=reservation.cancelled_at,
        expire_reason=reservation.expire_reason,
        arrived_at=arrival.arrived_at if arrival else None,
        checkin_opens_at=reservation.start_time
        - timedelta(minutes=settings.checkin_open_before_minutes),
        checkin_closes_at=min(
            reservation.end_time,
            reservation.start_time + timedelta(minutes=settings.no_show_after_minutes),
        ),
    )


def _sync_seat(session: Session, seat: Seat, at: datetime) -> None:
    if seat.status in BLOCKED_SEAT_STATUSES:
        return
    session.flush()
    bookings = list(
        session.scalars(
            select(Reservation).where(
                Reservation.seat_id == seat.id,
                Reservation.status.in_(E.ACTIVE_RESERVATION_STATUSES),
            )
        )
    )
    if any(r.status != E.ReservationStatus.RESERVED for r in bookings):
        new = E.SeatStatus.IN_USE
    elif any(r.start_time <= at < r.end_time for r in bookings):
        new = E.SeatStatus.RESERVED
    else:
        new = E.SeatStatus.AVAILABLE
    if seat.status != new:
        seat.status, seat.status_changed_at = new, at


def _record_violation(
    session: Session, reservation: Reservation, kind: E.ViolationType, at: datetime
) -> None:
    # 唯一行为去重在同一个写事务内完成；#19 可消费这些记录执行处罚与申诉。
    if (
        session.scalar(
            select(ViolationRecord.id)
            .where(
                ViolationRecord.reservation_id == reservation.id,
                ViolationRecord.violation_type == kind,
            )
            .limit(1)
        )
        is not None
    ):
        return
    settings = get_business_settings(session)
    days = settings.violation_window_days
    previous = session.scalar(
        select(ViolationRecord)
        .where(
            ViolationRecord.user_id == reservation.user_id,
            ViolationRecord.state == E.ViolationState.ACTIVE,
            ViolationRecord.period_start <= at,
            ViolationRecord.period_start > at - timedelta(days=days),
        )
        .order_by(ViolationRecord.period_start.desc(), ViolationRecord.period_seq.desc())
    )
    sequence = previous.period_seq + 1 if previous else 1
    first_threshold = getattr(settings, "penalty_base_threshold", 3)
    tier_step = max(1, getattr(settings, "penalty_threshold_step", 2))
    days_per_tier = getattr(settings, "penalty_days_per_tier", 1)
    restriction = None
    if sequence >= first_threshold and (sequence - first_threshold) % tier_step == 0:
        tier = (sequence - first_threshold) // tier_step + 1
        ban_days = tier * days_per_tier
        restriction = Restriction(
            user_id=reservation.user_id,
            ban_days=ban_days,
            warning_count=sequence,
            trigger_condition=f"满{sequence}次",
            start_at=at,
            end_at=at + timedelta(days=ban_days),
            status=E.RestrictionStatus.ACTIVE,
        )
        session.add(restriction)
        session.flush()
    violation = ViolationRecord(
        user_id=reservation.user_id,
        reservation_id=reservation.id,
        violation_type=kind,
        occurred_at=at,
        period_start=previous.period_start if previous else at,
        period_seq=sequence,
        description="开始前15分钟内取消" if kind == E.ViolationType.LATE_CANCEL else "超窗未签到",
        result=E.ViolationResult.RESTRICTED if restriction else E.ViolationResult.WARNING,
        restriction_id=restriction.id if restriction else None,
    )
    session.add(violation)
    session.flush()
    create_notification(
        session,
        user_id=reservation.user_id,
        notification_type=E.NotificationType.VIOLATION,
        content=(
            f"你在 14 天累计窗口内达到第 {sequence} 次违规，禁约 {restriction.ban_days} 天。"
            if restriction
            else f"你有一条新的违规记录（{kind.value}），当前累计第 {sequence} 次。"
        ),
    )
    audit.record(
        session,
        operator=None,
        op_type=E.AuditOpType.VIOLATION,
        target_type="violation_record",
        target_id=violation.id,
        after={"type": kind, "reservation_id": reservation.id, "warnings": sequence},
    )


def _overdue(reservation: Reservation, at: datetime, grace: int) -> bool:
    return at >= reservation.end_time or at > reservation.start_time + timedelta(minutes=grace)


def _expire_one(session: Session, reservation: Reservation, at: datetime) -> None:
    reservation.status = E.ReservationStatus.EXPIRED
    reservation.expire_reason = "no_show"
    _record_violation(session, reservation, E.ViolationType.NO_SHOW, at)
    _sync_seat(session, reservation.seat, at)


def _expire_due(session: Session, at: datetime) -> int:
    grace = get_business_settings(session).no_show_after_minutes
    candidates = list(
        session.scalars(
            select(Reservation).where(
                Reservation.status == E.ReservationStatus.RESERVED,
                (Reservation.start_time < at - timedelta(minutes=grace))
                | (Reservation.end_time <= at),
            )
        )
    )
    for reservation in candidates:
        _expire_one(session, reservation, at)
    return len(candidates)


def expire_due(source: Session) -> int:
    """后台与请求补偿共用；只有确实存在到期预约时才申请写锁。"""
    with Session(source.get_bind()) as check:
        at = now()
        grace = get_business_settings(check).no_show_after_minutes
        candidate = check.scalar(
            select(Reservation.id)
            .where(
                Reservation.status == E.ReservationStatus.RESERVED,
                (Reservation.start_time < at - timedelta(minutes=grace))
                | (Reservation.end_time <= at),
            )
            .limit(1)
        )
    if candidate is None:
        return 0
    with write_transaction(source) as session:
        return _expire_due(session, now())


def _pick_seat_for_zone(
    session: Session,
    room_id: int,
    zone_type: E.ZoneType,
    start: datetime,
    end: datetime,
    user_id: int,
) -> Seat:
    """BR-012：在指定房间与区域内按编号顺序挑第一个可用座位。"""
    from app.models import StudyRoom as _StudyRoom

    room = session.get(_StudyRoom, room_id)
    if room is None:
        raise BookingError(404, "自习室不存在")
    if room.status != E.RoomStatus.OPEN:
        raise BookingError(409, "自习室已关闭，无法预约")
    seats = list(
        session.scalars(
            select(Seat)
            .where(
                Seat.room_id == room_id,
                Seat.zone_type == zone_type,
                Seat.status == E.SeatStatus.AVAILABLE,
            )
            .order_by(Seat.code)
        )
    )
    if not seats:
        raise BookingError(409, "该区域暂无可用座位")
    for seat in seats:
        try:
            _check_slot(session, seat, start, end, user_id)
            return seat
        except BookingError:
            continue
    raise BookingError(409, "该区域在所选时段已约满，请换时段或区域")


def create(
    source: Session, user_id: int, body: ReservationIn, key: str | None
) -> tuple[ReservationOut, bool]:
    # 指纹包含座位或区域，便于幂等比对自动分配结果。
    fingerprint = hashlib.sha256(
        json.dumps(
            [
                user_id,
                body.seat_id,
                body.room_id,
                body.zone_type.value if body.zone_type else None,
                body.start_time.isoformat(),
                body.end_time.isoformat(),
            ]
        ).encode()
    ).hexdigest()
    with write_transaction(source) as session:
        _user(session, user_id)
        at = now()
        _expire_due(session, at)
        if key:
            previous = session.scalar(select(Reservation).where(Reservation.idempotency_key == key))
            if previous is not None:
                if previous.user_id != user_id or previous.request_fingerprint != fingerprint:
                    raise BookingError(409, "幂等键已被不同请求使用，请重新提交")
                return reservation_out(session, previous), True
        if body.start_time < at:
            raise BookingError(422, "预约开始时间不能早于当前时间")
        settings = get_business_settings(session)
        advance = min(settings.advance_booking_days, 1)  # HD-34 的本期上限
        if body.start_time.date() > at.date() + timedelta(days=advance):
            raise BookingError(422, "最多提前1天预约，请调整日期")
        _restriction(session, user_id, at)
        if body.seat_id is not None:
            seat = _seat(session, body.seat_id)
            _check_slot(session, seat, body.start_time, body.end_time, user_id)
        else:
            seat = _pick_seat_for_zone(
                session, body.room_id, body.zone_type, body.start_time, body.end_time, user_id
            )
        # 与 #33 一致：预约号带时间前缀，便于人工排查。
        reservation = Reservation(
            reservation_no=f"SR{at:%Y%m%d%H%M%S}{uuid4().hex[:6].upper()}",
            user_id=user_id,
            room_id=seat.room_id,
            seat=seat,
            start_time=body.start_time,
            end_time=body.end_time,
            idempotency_key=key,
            request_fingerprint=fingerprint,
        )
        session.add(reservation)
        session.flush()
        # 预先占位到达记录，供签到与门禁更新。
        session.add(
            ArrivalRecord(
                reservation_id=reservation.id,
                user_id=user_id,
                seat_id=seat.id,
                arrival_status=E.ArrivalStatus.ABSENT,
            )
        )
        create_notification(
            session,
            user_id=user_id,
            notification_type=E.NotificationType.RESERVATION_CONFIRMED,
            content=(
                f"预约成功：{seat.room.name} {seat.code}，"
                f"{body.start_time:%Y-%m-%d %H:%M}–{body.end_time:%H:%M}。"
            ),
            idempotency_key=f"reservation:{reservation.id}:confirmed",
        )
        _sync_seat(session, seat, at)
        return reservation_out(session, reservation), False


def change_seat(source: Session, user_id: int, rid: int, sid: int) -> ReservationOut:
    with write_transaction(source) as session:
        _user(session, user_id)
        at = now()
        reservation = _owned(session, user_id, rid)
        if reservation.status != E.ReservationStatus.RESERVED:
            raise BookingError(409, "仅未签到的有效预约可换座")
        if _overdue(reservation, at, get_business_settings(session).no_show_after_minutes):
            raise BookingError(409, "预约已超过签到窗口，无法换座")
        _restriction(session, user_id, at)
        seat = _seat(session, sid)
        _check_slot(session, seat, reservation.start_time, reservation.end_time, user_id, rid)
        original = reservation.seat
        reservation.seat = seat
        reservation.seat_id, reservation.room_id = seat.id, seat.room_id
        _sync_seat(session, original, at)
        _sync_seat(session, seat, at)
        return reservation_out(session, reservation)


def cancel(source: Session, user_id: int, rid: int) -> ReservationOut:
    with write_transaction(source) as session:
        _user(session, user_id)  # 禁约不影响取消权限（HD-40）
        at = now()
        reservation = _owned(session, user_id, rid)
        if reservation.status == E.ReservationStatus.CANCELLED:
            return reservation_out(session, reservation)
        if reservation.status != E.ReservationStatus.RESERVED:
            raise BookingError(409, "仅未签到的有效预约可取消")
        if at >= reservation.start_time:
            raise BookingError(409, "预约已开始，未签到将按超窗规则处理")
        late = reservation.start_time - at <= timedelta(
            minutes=get_business_settings(session).late_cancel_minutes
        )
        reservation.status = E.ReservationStatus.CANCELLED
        reservation.cancel_type = E.CancelType.LATE if late else E.CancelType.NORMAL
        reservation.cancelled_at = at
        reservation.cancel_reason = "本人取消预约"
        try:
            create_notification(
                session,
                user_id=user_id,
                notification_type=E.NotificationType.SYSTEM,
                content=f"预约 {reservation.reservation_no} 已取消。",
                idempotency_key=f"reservation:{reservation.id}:cancelled",
            )
        except Exception:
            logger.exception("预约已取消，但取消通知创建失败")
        if late:
            _record_violation(session, reservation, E.ViolationType.LATE_CANCEL, at)
        _sync_seat(session, reservation.seat, at)
        return reservation_out(session, reservation)


def check_in(
    source: Session, user_id: int, rid: int, body: CheckInIn | None = None
) -> ReservationOut:
    expired = False
    with write_transaction(source) as session:
        _user(session, user_id)
        at = now()
        reservation = _owned(session, user_id, rid)
        seat = reservation.seat
        if body is not None:
            matched = (
                body.seat_id == seat.id
                if body.seat_id is not None
                else body.room_id == seat.room_id and body.seat_code == seat.code
            )
            if not matched:
                raise BookingError(409, "扫码座位与本人预约不一致")
        if reservation.status == E.ReservationStatus.ACTIVE:
            return reservation_out(session, reservation)  # 重复扫码幂等
        if reservation.status != E.ReservationStatus.RESERVED:
            raise BookingError(409, "预约已失效、取消或已结束，无法签到")
        settings = get_business_settings(session)
        if _overdue(reservation, at, settings.no_show_after_minutes):
            _expire_one(session, reservation, at)
            expired = True
        else:
            _seat(session, seat.id)
            if at < reservation.start_time - timedelta(
                minutes=settings.checkin_open_before_minutes
            ):
                raise BookingError(409, "签到窗口尚未开放")
            occupied = session.scalar(
                select(Reservation.id)
                .where(
                    Reservation.seat_id == seat.id,
                    Reservation.id != rid,
                    Reservation.status.in_(
                        (E.ReservationStatus.ACTIVE, E.ReservationStatus.TEMP_LEAVE)
                    ),
                )
                .limit(1)
            )
            if occupied is not None:
                raise BookingError(409, "座位仍有人使用，请等待释放或联系管理员")
            reservation.status = E.ReservationStatus.ACTIVE
            arrival = _arrival(session, rid)
            if arrival is None:
                arrival = ArrivalRecord(reservation_id=rid, user_id=user_id, seat_id=seat.id)
                session.add(arrival)
            arrival.arrived_at = at
            arrival.arrival_method = (
                E.ArrivalMethod.QR if body is not None else E.ArrivalMethod.MANUAL
            )
            # 窗内均不违规；到达分类仅用于记录，不触发处罚。
            arrival.arrival_status = (
                E.ArrivalStatus.EARLY
                if at < reservation.start_time
                else (
                    E.ArrivalStatus.ON_TIME
                    if at == reservation.start_time
                    else E.ArrivalStatus.LATE
                )
            )
            _sync_seat(session, seat, at)
        result = reservation_out(session, reservation)
    if expired:
        # 必须在提交失效/违规后再返回错误，不能被异常回滚。
        raise BookingError(409, "签到窗口已关闭，预约已失效并记录1次违规")
    return result


# ---- #33 暂离 / 结束使用 / 全量扫描（与 #34 预约核心并存）----


def create_reservation(session: Session, user: User, body) -> Reservation:
    """#33 API 兼容：把 request_key 映射为幂等键后复用 create。"""
    key = None
    if getattr(body, "request_key", None):
        key = hashlib.sha256(f"{user.id}:{body.request_key}".encode()).hexdigest()
    result, _replay = create(session, user.id, body, key)
    with Session(session.get_bind()) as read:
        return read.get(Reservation, result.id)


def start_temporary_leave(session: Session, user: User, reservation_id: int) -> Reservation:
    """声明临时离开并保存 30 分钟返回期限起点。"""
    session.commit()
    with transaction(session, immediate=True):
        moment = now()
        reservation = session.scalar(
            select(Reservation).where(
                Reservation.id == reservation_id, Reservation.user_id == user.id
            )
        )
        if reservation is None:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "预约不存在")
        if reservation.status != E.ReservationStatus.ACTIVE:
            raise HTTPException(http_status.HTTP_409_CONFLICT, "只有正在使用的预约可以临时离开")
        if reservation.end_time <= moment:
            raise HTTPException(http_status.HTTP_409_CONFLICT, "预约时段已结束，不能再登记临时离开")
        reservation.status = E.ReservationStatus.TEMP_LEAVE
        reservation.temp_leave_at = moment
        reservation.temp_leave_state = E.TempLeaveState.WAITING
        create_notification(
            session,
            user_id=user.id,
            notification_type=E.NotificationType.TEMP_LEAVE,
            content="已登记临时离开，请在 30 分钟内返回；超时后预约将释放并记违规。",
            idempotency_key=f"reservation:{reservation.id}:leave:{moment.isoformat()}",
        )
    return reservation


def return_from_temporary_leave(session: Session, user: User, reservation_id: int) -> Reservation:
    """在登记后的 30 分钟内返回并恢复预约使用状态。"""
    settings = get_business_settings(session)
    session.commit()
    with transaction(session, immediate=True):
        moment = now()
        reservation = session.scalar(
            select(Reservation).where(
                Reservation.id == reservation_id, Reservation.user_id == user.id
            )
        )
        if reservation is None:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "预约不存在")
        if (
            reservation.status != E.ReservationStatus.TEMP_LEAVE
            or reservation.temp_leave_at is None
            or reservation.temp_leave_state != E.TempLeaveState.WAITING
        ):
            raise HTTPException(http_status.HTTP_409_CONFLICT, "该预约没有待返回的临时离开记录")
        deadline = reservation.temp_leave_at + timedelta(minutes=settings.temp_leave_minutes)
        if moment > deadline:
            raise HTTPException(
                http_status.HTTP_409_CONFLICT, "临时离开已超时，预约正在等待系统释放"
            )
        if reservation.end_time <= moment:
            raise HTTPException(http_status.HTTP_409_CONFLICT, "预约时段已结束，不能再恢复使用")
        reservation.status = E.ReservationStatus.ACTIVE
        reservation.temp_leave_state = E.TempLeaveState.RETURNED
        create_notification(
            session,
            user_id=user.id,
            notification_type=E.NotificationType.TEMP_LEAVE,
            content="已记录你返回自习室。",
            idempotency_key=f"reservation:{reservation.id}:returned:{reservation.temp_leave_at.isoformat()}",
        )
    return reservation


def end_use(
    session: Session, user: User, reservation_id: int, *, confirmed: bool
) -> tuple[list[Reservation], int]:
    """经显式确认结束连续预约，并把连续时段合并为一次操作。"""
    if not confirmed:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_CONTENT, "结束使用前必须明确确认")
    settings = get_business_settings(session)
    session.commit()
    with transaction(session, immediate=True):
        moment = now()
        first = session.scalar(
            select(Reservation).where(
                Reservation.id == reservation_id, Reservation.user_id == user.id
            )
        )
        if first is None:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "预约不存在")
        if first.status not in (E.ReservationStatus.ACTIVE, E.ReservationStatus.TEMP_LEAVE):
            raise HTTPException(http_status.HTTP_409_CONFLICT, "该预约当前不能结束使用")
        if (
            first.status == E.ReservationStatus.TEMP_LEAVE
            and first.temp_leave_at is not None
            and moment > first.temp_leave_at + timedelta(minutes=settings.temp_leave_minutes)
        ):
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                "临时离开已超时，不能通过结束操作绕过处理",
            )
        chain = [first]
        cursor = first.end_time
        while True:
            next_reservation = session.scalar(
                select(Reservation)
                .where(
                    Reservation.user_id == user.id,
                    Reservation.seat_id == first.seat_id,
                    Reservation.start_time == cursor,
                    Reservation.status.in_(
                        (
                            E.ReservationStatus.RESERVED,
                            E.ReservationStatus.ACTIVE,
                            E.ReservationStatus.TEMP_LEAVE,
                        )
                    ),
                )
                .limit(1)
            )
            if next_reservation is None:
                break
            chain.append(next_reservation)
            cursor = next_reservation.end_time

        total_seconds = 0
        for reservation in chain:
            if (
                reservation.status == E.ReservationStatus.RESERVED
                or reservation.start_time > moment
            ):
                reservation.status = E.ReservationStatus.CANCELLED
                reservation.cancel_type = E.CancelType.NORMAL
                reservation.cancelled_at = moment
                reservation.cancel_reason = "结束连续使用并释放后续预约"
                create_notification(
                    session,
                    user_id=user.id,
                    notification_type=E.NotificationType.SYSTEM,
                    content=f"连续使用已结束，后续预约 {reservation.reservation_no} 已释放。",
                    idempotency_key=f"reservation:{reservation.id}:released-after-end",
                )
                _sync_seat(session, reservation.seat, moment)
                continue
            arrival = session.scalar(
                select(ArrivalRecord).where(ArrivalRecord.reservation_id == reservation.id)
            )
            if arrival is not None:
                arrival.ended_at = moment
                arrival.end_method = E.EndMethod.BUTTON
                if arrival.arrived_at is not None:
                    total_seconds += max(
                        0,
                        int(
                            (min(moment, reservation.end_time) - arrival.arrived_at).total_seconds()
                        ),
                    )
            reservation.status = E.ReservationStatus.COMPLETED
            reservation.temp_leave_state = (
                E.TempLeaveState.RETURNED
                if reservation.temp_leave_state == E.TempLeaveState.WAITING
                else reservation.temp_leave_state
            )
            _sync_seat(session, reservation.seat, moment)
        create_notification(
            session,
            user_id=user.id,
            notification_type=E.NotificationType.SYSTEM,
            content=f"已结束本次连续使用，共计约 {total_seconds // 60} 分钟。",
            idempotency_key=f"reservation:{first.id}:ended:{moment.isoformat()}",
        )
        return chain, total_seconds // 60


def sweep_reservations(session: Session, moment: datetime | None = None) -> dict[str, int]:
    """幂等释放未签到、未签退和临时离开超时预约，并投递提醒通知。"""
    moment = moment or now()
    settings = get_business_settings(session)
    counts = {
        "no_show": 0,
        "no_checkout": 0,
        "temp_leave": 0,
        "reminders": 0,
        "archived_violations": 0,
    }
    session.commit()
    with transaction(session, immediate=True):
        expired_restrictions = list(
            session.scalars(
                select(Restriction).where(
                    Restriction.status == E.RestrictionStatus.ACTIVE,
                    Restriction.end_at <= moment,
                )
            )
        )
        for restriction in expired_restrictions:
            restriction.status = E.RestrictionStatus.EXPIRED

        pending = list(
            session.scalars(
                select(Reservation).where(
                    Reservation.status == E.ReservationStatus.RESERVED,
                    Reservation.start_time
                    < moment - timedelta(minutes=settings.no_show_after_minutes),
                )
            )
        )
        for reservation in pending:
            reservation.status = E.ReservationStatus.EXPIRED
            reservation.expire_reason = "no_show"
            arrival = session.scalar(
                select(ArrivalRecord).where(ArrivalRecord.reservation_id == reservation.id)
            )
            if arrival is not None:
                arrival.arrival_status = E.ArrivalStatus.ABSENT
            record_violation(
                session,
                user_id=reservation.user_id,
                violation_type=E.ViolationType.NO_SHOW,
                reservation_id=reservation.id,
                description="预约开始后未在签到期限内到达，系统自动释放时段。",
                occurred_at=moment,
            )
            create_notification(
                session,
                user_id=reservation.user_id,
                notification_type=E.NotificationType.SYSTEM,
                content=f"预约 {reservation.reservation_no} 因未签到已自动释放。",
                idempotency_key=f"reservation:{reservation.id}:no-show-released",
            )
            _sync_seat(session, reservation.seat, moment)
            counts["no_show"] += 1

        active = list(
            session.scalars(
                select(Reservation).where(
                    Reservation.status.in_(
                        (E.ReservationStatus.ACTIVE, E.ReservationStatus.TEMP_LEAVE)
                    ),
                    Reservation.end_time <= moment,
                )
            )
        )
        away = list(
            session.scalars(
                select(Reservation).where(
                    Reservation.status == E.ReservationStatus.TEMP_LEAVE,
                    Reservation.temp_leave_at.is_not(None),
                    Reservation.temp_leave_at
                    <= moment - timedelta(minutes=settings.temp_leave_minutes),
                )
            )
        )
        timeout_ids = {row.id: row for row in active}
        timeout_ids.update({row.id: row for row in away})
        for reservation in timeout_ids.values():
            left_too_long = reservation.id in {row.id for row in away}
            reservation.status = E.ReservationStatus.TIMED_OUT
            reservation.expire_reason = "temp_leave_timeout" if left_too_long else "period_end"
            if left_too_long:
                reservation.temp_leave_state = E.TempLeaveState.TIMED_OUT
                violation_type = E.ViolationType.TEMP_LEAVE_TIMEOUT
                counts["temp_leave"] += 1
            else:
                violation_type = E.ViolationType.NO_CHECKOUT
                counts["no_checkout"] += 1
            arrival = session.scalar(
                select(ArrivalRecord).where(ArrivalRecord.reservation_id == reservation.id)
            )
            if arrival is not None and arrival.ended_at is None:
                arrival.ended_at = moment
                arrival.end_method = E.EndMethod.AUTO_TIMEOUT
            record_violation(
                session,
                user_id=reservation.user_id,
                violation_type=violation_type,
                reservation_id=reservation.id,
                description="系统按预约结束或临时离开期限释放座位，违规记录可提交申诉。",
                occurred_at=moment,
            )
            create_notification(
                session,
                user_id=reservation.user_id,
                notification_type=E.NotificationType.SYSTEM,
                content=f"预约 {reservation.reservation_no} 已由系统超时释放。",
                idempotency_key=f"reservation:{reservation.id}:timeout-released",
            )
            _sync_seat(session, reservation.seat, moment)

        reminder_end = moment + timedelta(minutes=settings.checkin_open_before_minutes)
        reminders = list(
            session.scalars(
                select(Reservation).where(
                    Reservation.status == E.ReservationStatus.RESERVED,
                    Reservation.start_time >= moment,
                    Reservation.start_time <= reminder_end,
                )
            )
        )
        for reservation in reminders:
            create_notification(
                session,
                user_id=reservation.user_id,
                notification_type=E.NotificationType.CHECKIN_REMINDER,
                content=f"预约 {reservation.reservation_no} 即将开始，请在允许窗口内签到。",
                idempotency_key=f"reservation:{reservation.id}:checkin-reminder",
            )
            counts["reminders"] += 1

        leave_reminders = list(
            session.scalars(
                select(Reservation).where(
                    Reservation.status == E.ReservationStatus.TEMP_LEAVE,
                    Reservation.temp_leave_at.is_not(None),
                    Reservation.temp_leave_at
                    <= moment - timedelta(minutes=max(0, settings.temp_leave_minutes - 5)),
                    Reservation.temp_leave_at
                    > moment - timedelta(minutes=settings.temp_leave_minutes),
                )
            )
        )
        for reservation in leave_reminders:
            create_notification(
                session,
                user_id=reservation.user_id,
                notification_type=E.NotificationType.TEMP_LEAVE,
                content="临时离开即将到 30 分钟期限，请尽快返回；到期后系统会释放预约。",
                idempotency_key=f"reservation:{reservation.id}:leave-expiry-reminder",
            )
            counts["reminders"] += 1
        counts["archived_violations"] = archive_expired_violations(session, moment)

    return counts
