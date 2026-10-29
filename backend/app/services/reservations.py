"""预约事务、幂等与签到（#12–#16）。

认证依赖已开启只读事务，因此业务使用同一引擎的独立会话，先 BEGIN IMMEDIATE 再查写；
不升级认证会话的读锁，也不提交认证会话中的任何状态。
"""

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import uuid4

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
from app.services.settings import get_business_settings


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
    days = get_business_settings(session).violation_window_days
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
    violation = ViolationRecord(
        user_id=reservation.user_id,
        reservation_id=reservation.id,
        violation_type=kind,
        occurred_at=at,
        period_start=previous.period_start if previous else at,
        period_seq=previous.period_seq + 1 if previous else 1,
        description="开始前15分钟内取消" if kind == E.ViolationType.LATE_CANCEL else "超窗未签到",
    )
    session.add(violation)
    session.flush()
    audit.record(
        session,
        operator=None,
        op_type=E.AuditOpType.VIOLATION,
        target_type="violation_record",
        target_id=violation.id,
        after={"type": kind, "reservation_id": reservation.id, "warnings": 1},
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
        at = timeutil.now()
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
        return _expire_due(session, timeutil.now())


def create(
    source: Session, user_id: int, body: ReservationIn, key: str
) -> tuple[ReservationOut, bool]:
    fingerprint = hashlib.sha256(
        json.dumps(
            [user_id, body.seat_id, body.start_time.isoformat(), body.end_time.isoformat()]
        ).encode()
    ).hexdigest()
    with write_transaction(source) as session:
        _user(session, user_id)
        at = timeutil.now()
        _expire_due(session, at)
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
        seat = _seat(session, body.seat_id)
        _check_slot(session, seat, body.start_time, body.end_time, user_id)
        reservation = Reservation(
            reservation_no=uuid4().hex,
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
        _sync_seat(session, seat, at)
        return reservation_out(session, reservation), False


def change_seat(source: Session, user_id: int, rid: int, sid: int) -> ReservationOut:
    with write_transaction(source) as session:
        _user(session, user_id)
        at = timeutil.now()
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
        at = timeutil.now()
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
        if late:
            _record_violation(session, reservation, E.ViolationType.LATE_CANCEL, at)
        _sync_seat(session, reservation.seat, at)
        return reservation_out(session, reservation)


def check_in(source: Session, user_id: int, rid: int, body: CheckInIn) -> ReservationOut:
    expired = False
    with write_transaction(source) as session:
        _user(session, user_id)
        at = timeutil.now()
        reservation = _owned(session, user_id, rid)
        seat = reservation.seat
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
            arrival.arrived_at, arrival.arrival_method = at, E.ArrivalMethod.QR
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
