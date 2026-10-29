"""预约历史、临时离开、结束使用和后台超时处理。"""

from datetime import datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import transaction
from app.models import (
    ArrivalRecord,
    CalendarDay,
    OpeningSchedule,
    Reservation,
    Restriction,
    Seat,
    StudyRoom,
    User,
)
from app.models import enums as E
from app.schemas.admin import BusinessSettings
from app.schemas.workflows import ReservationCreate
from app.services.notifications import create_notification
from app.services.settings import get_business_settings
from app.services.violations import record_violation
from app.timeutil import now, tz


def _day_type(session: Session, day) -> E.DayType:
    """根据校历或星期推算开放类型，节假日校历优先覆盖默认日历。"""
    special = session.get(CalendarDay, day)
    if special is not None:
        return special.day_type
    return E.DayType.WEEKEND if day.weekday() >= 5 else E.DayType.WEEKDAY


def _is_open(session: Session, room_id: int, start: datetime, end: datetime) -> bool:
    """要求预约完整落在同一天的一条有效开放时段内。"""
    local_start = start.astimezone(tz())
    local_end = end.astimezone(tz())
    if local_start.date() != local_end.date():
        return False
    schedules = session.scalars(
        select(OpeningSchedule).where(
            OpeningSchedule.room_id == room_id,
            OpeningSchedule.day_type == _day_type(session, local_start.date()),
            OpeningSchedule.enabled.is_(True),
            (OpeningSchedule.effective_from.is_(None))
            | (OpeningSchedule.effective_from <= local_start.date()),
            (OpeningSchedule.effective_to.is_(None))
            | (OpeningSchedule.effective_to >= local_start.date()),
        )
    )
    start_time = local_start.time().replace(tzinfo=None)
    end_time = local_end.time().replace(tzinfo=None)
    return any(slot.open_time <= start_time and end_time <= slot.close_time for slot in schedules)


def _validate_window(
    session: Session,
    body: ReservationCreate,
    settings: BusinessSettings,
    moment: datetime,
) -> tuple[datetime, datetime]:
    """校验预约粒度、时间方向、提前范围与房间开放时段。"""
    start = body.start_time.astimezone(tz())
    end = body.end_time.astimezone(tz())
    if start >= end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "预约开始时间必须早于结束时间")
    if start.date() != end.date():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "预约暂不支持跨日")
    if any(value.minute % 30 or value.second or value.microsecond for value in (start, end)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "预约时间须按 30 分钟粒度设置")
    if start < moment:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "不能预约已经开始的时段")
    if (start.date() - moment.astimezone(tz()).date()).days > settings.advance_booking_days:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "预约日期超出可提前预约范围")
    return start, end


def create_reservation(session: Session, user: User, body: ReservationCreate) -> Reservation:
    """原子创建预约、阻止座位冲突并写入确认通知。"""
    settings = get_business_settings(session)
    moment = now()
    start, end = _validate_window(session, body, settings, moment)
    # 登录鉴权已读取用户并打开只读事务；先结束该事务，再用 SQLite 写锁执行检查与插入。
    session.commit()
    with transaction(session, immediate=True):
        seat = session.get(Seat, body.seat_id)
        if seat is None or seat.status != E.SeatStatus.AVAILABLE:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "座位不存在或暂不可预约")
        room = session.get(StudyRoom, seat.room_id)
        if room is None or room.status != E.RoomStatus.OPEN:
            raise HTTPException(status.HTTP_409_CONFLICT, "自习室当前未开放")
        if not _is_open(session, room.id, start, end):
            raise HTTPException(status.HTTP_409_CONFLICT, "预约时段不在自习室开放时间内")

        # 违规阶梯产生的禁约在新预约写入前检查，过期措施不会继续阻止预约。
        restriction = session.scalar(
            select(Restriction.id)
            .where(
                Restriction.user_id == user.id,
                Restriction.status == E.RestrictionStatus.ACTIVE,
                Restriction.start_at <= moment,
                Restriction.end_at > moment,
            )
            .limit(1)
        )
        if restriction is not None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "你当前处于禁约期，暂不能创建预约")

        # 客户端重试使用同一请求键时返回原预约，不重复占用座位。
        if body.request_key:
            key = sha256(f"{user.id}:{body.request_key}".encode()).hexdigest()
            existing = session.scalar(select(Reservation).where(Reservation.idempotency_key == key))
            if existing is not None:
                return existing
        else:
            key = None

        # 按配置限制用户尚未结束的预约数量，避免通过不同座位绕过资源上限。
        active_count = session.scalar(
            select(func.count(Reservation.id)).where(
                Reservation.user_id == user.id,
                Reservation.status.in_(E.ACTIVE_RESERVATION_STATUSES),
                Reservation.end_time > moment,
            )
        )
        if active_count >= settings.max_active_reservations:
            raise HTTPException(status.HTTP_409_CONFLICT, "当前有效预约数量已达到上限")

        # 半开区间冲突判断：相接边界允许连续预约，重叠区间只能有一个成功。
        conflict = session.scalar(
            select(Reservation.id)
            .where(
                Reservation.seat_id == seat.id,
                Reservation.status.in_(E.ACTIVE_RESERVATION_STATUSES),
                Reservation.start_time < end,
                Reservation.end_time > start,
            )
            .limit(1)
        )
        if conflict is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "该座位在所选时段已被预约")

        # 创建预约和签到占位记录处于同一事务，避免出现无记录的预约。
        reservation = Reservation(
            reservation_no=f"SR{moment:%Y%m%d%H%M%S}{uuid4().hex[:6].upper()}",
            user_id=user.id,
            room_id=room.id,
            seat_id=seat.id,
            start_time=start,
            end_time=end,
            status=E.ReservationStatus.RESERVED,
            idempotency_key=key,
        )
        session.add(reservation)
        session.flush()
        session.add(
            ArrivalRecord(
                reservation_id=reservation.id,
                user_id=user.id,
                seat_id=seat.id,
                arrival_status=E.ArrivalStatus.ABSENT,
            )
        )
        create_notification(
            session,
            user_id=user.id,
            notification_type=E.NotificationType.RESERVATION_CONFIRMED,
            content=f"预约成功：{room.name} {seat.code}，{start:%Y-%m-%d %H:%M}–{end:%H:%M}。",
            idempotency_key=f"reservation:{reservation.id}:confirmed",
        )
        return reservation


def _owned_reservation(session: Session, user: User, reservation_id: int) -> Reservation:
    """只读取当前用户自己的预约，避免以对象编号越权访问。"""
    reservation = session.get(Reservation, reservation_id)
    if reservation is None or reservation.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预约不存在")
    return reservation


def check_in(session: Session, user: User, reservation_id: int) -> Reservation:
    """在签到窗口内将本人预约转为使用中并记录到达时间。"""
    settings = get_business_settings(session)
    reservation = _owned_reservation(session, user, reservation_id)
    # 状态检查与到达记录更新在同一写事务中，重复签到会保持原状态并返回冲突。
    session.commit()
    with transaction(session, immediate=True):
        moment = now()
        reservation = _owned_reservation(session, user, reservation_id)
        if reservation.status != E.ReservationStatus.RESERVED:
            raise HTTPException(status.HTTP_409_CONFLICT, "该预约当前不能签到")
        if not (
            reservation.start_time - timedelta(minutes=settings.checkin_open_before_minutes)
            <= moment
            <= reservation.start_time + timedelta(minutes=settings.no_show_after_minutes)
        ):
            raise HTTPException(status.HTTP_409_CONFLICT, "当前时间不在允许签到窗口内")
        arrival = session.scalar(
            select(ArrivalRecord).where(ArrivalRecord.reservation_id == reservation.id)
        )
        if arrival is None:
            arrival = ArrivalRecord(
                reservation_id=reservation.id,
                user_id=user.id,
                seat_id=reservation.seat_id,
                arrival_status=E.ArrivalStatus.ON_TIME,
            )
            session.add(arrival)
        arrival.arrival_status = (
            E.ArrivalStatus.LATE if moment > reservation.start_time else E.ArrivalStatus.ON_TIME
        )
        arrival.arrived_at = moment
        arrival.arrival_method = E.ArrivalMethod.MANUAL
        reservation.status = E.ReservationStatus.ACTIVE
        create_notification(
            session,
            user_id=user.id,
            notification_type=E.NotificationType.SYSTEM,
            content=f"预约 {reservation.reservation_no} 已签到。",
            idempotency_key=f"reservation:{reservation.id}:checked-in",
        )
        return reservation


def start_temporary_leave(session: Session, user: User, reservation_id: int) -> Reservation:
    """声明临时离开并保存 30 分钟返回期限起点。"""
    # 离开状态、时间戳及站内提醒一起提交，超时扫描据此执行一次性释放。
    session.commit()
    with transaction(session, immediate=True):
        moment = now()
        reservation = _owned_reservation(session, user, reservation_id)
        if reservation.status != E.ReservationStatus.ACTIVE:
            raise HTTPException(status.HTTP_409_CONFLICT, "只有正在使用的预约可以临时离开")
        if reservation.end_time <= moment:
            raise HTTPException(status.HTTP_409_CONFLICT, "预约时段已结束，不能再登记临时离开")
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
    # 返回操作和后台超时任务竞争同一写锁，最终只会有一个状态转换成功。
    session.commit()
    with transaction(session, immediate=True):
        moment = now()
        reservation = _owned_reservation(session, user, reservation_id)
        if (
            reservation.status != E.ReservationStatus.TEMP_LEAVE
            or reservation.temp_leave_at is None
            or reservation.temp_leave_state != E.TempLeaveState.WAITING
        ):
            raise HTTPException(status.HTTP_409_CONFLICT, "该预约没有待返回的临时离开记录")
        # 超时后不复活已释放的时段；后台扫描负责记录违规和发出通知。
        deadline = reservation.temp_leave_at + timedelta(minutes=settings.temp_leave_minutes)
        if moment > deadline:
            raise HTTPException(status.HTTP_409_CONFLICT, "临时离开已超时，预约正在等待系统释放")
        if reservation.end_time <= moment:
            raise HTTPException(status.HTTP_409_CONFLICT, "预约时段已结束，不能再恢复使用")
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
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "结束使用前必须明确确认")
    initial = _owned_reservation(session, user, reservation_id)
    if initial.status not in (E.ReservationStatus.ACTIVE, E.ReservationStatus.TEMP_LEAVE):
        raise HTTPException(status.HTTP_409_CONFLICT, "只有已签到的预约可以结束使用")
    settings = get_business_settings(session)
    # 查找同一用户、同一座位且首尾相接的时段；一次确认覆盖当前段并释放后续待用段。
    session.commit()
    with transaction(session, immediate=True):
        moment = now()
        first = _owned_reservation(session, user, reservation_id)
        # 获取写锁后重新核对状态，避免与自动超时扫描并发时复活已释放的预约。
        if first.status not in (E.ReservationStatus.ACTIVE, E.ReservationStatus.TEMP_LEAVE):
            raise HTTPException(status.HTTP_409_CONFLICT, "该预约当前不能结束使用")
        if (
            first.status == E.ReservationStatus.TEMP_LEAVE
            and first.temp_leave_at is not None
            and moment > first.temp_leave_at + timedelta(minutes=settings.temp_leave_minutes)
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
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

        # 当前已签到时段记为完成，紧接的未来预约取消释放；操作由单一事务提交。
        total_seconds = 0
        for reservation in chain:
            if reservation.status == E.ReservationStatus.RESERVED:
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
                continue
            # 连续预约下一段尚未到开始时间时，不允许提前结束它或扩大学习时长。
            if reservation.start_time > moment:
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
    counts = {"no_show": 0, "no_checkout": 0, "temp_leave": 0, "reminders": 0}
    # 以一个写事务包住状态转换、违规和通知，重复运行不会重复处罚或提醒。
    session.commit()
    with transaction(session, immediate=True):
        # 已过结束时刻的限制自动转为过期，用户历史记录仍保留供审计。
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
                    <= moment - timedelta(minutes=settings.no_show_after_minutes),
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
            counts["no_show"] += 1

        # 已签到预约在预约时段结束时释放；离开超时按离开期限释放。
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
                violation_type = E.ViolationType.LEFT_UNDECLARED
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

        # 进入签到提醒窗口时每条预约只写入一条站内提醒。
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

        # 临时离开进入最后五分钟时发送一次到期提示，超时任务仍负责最终释放。
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
    return counts
