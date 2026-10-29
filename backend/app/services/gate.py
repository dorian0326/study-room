"""脱敏门禁事件 mock 接口与五分钟延迟降级逻辑。"""

import hashlib
import hmac
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import transaction
from app.models import ArrivalRecord, EntryExitRecord, Reservation, User
from app.models import enums as E
from app.schemas.workflows import GateEventIn
from app.services.notifications import create_notification
from app.services.settings import get_business_settings
from app.services.violations import record_violation
from app.timeutil import now


def user_key_for_gate(student_no: str) -> str:
    """用部署私钥生成稳定的脱敏用户键，避免门禁接口暴露学号。"""
    # HMAC 使相同学号无法通过裸哈希字典轻易反查，密钥由环境变量配置。
    secret = get_settings().gate_hmac_secret.encode("utf-8")
    return hmac.new(secret, student_no.encode("utf-8"), hashlib.sha256).hexdigest()


def _find_user(session: Session, masked_user_key: str) -> User | None:
    """按 keyed hash 在用户表中定位账号，不保存或返回原始学号。"""
    # 用户规模受学校账号数量限制；恒定时间比较避免提前退出的字符串比较。
    for user in session.scalars(select(User)):
        if hmac.compare_digest(user_key_for_gate(user.student_no), masked_user_key):
            return user
    return None


def process_gate_event(session: Session, body: GateEventIn) -> dict:
    """持久化 mock 门禁事件，延迟超过五分钟时要求人工申诉核验。"""
    moment = now()
    recorded_at = body.recorded_at.astimezone(moment.tzinfo)
    delay_seconds = int((moment - recorded_at).total_seconds())
    delayed = delay_seconds > 300

    # 同一来源事件号只处理一次；重复回调直接返回首次同步结果。
    session.commit()
    with transaction(session, immediate=True):
        existing = session.scalar(
            select(EntryExitRecord).where(
                EntryExitRecord.source_system == body.source_system,
                EntryExitRecord.external_id == body.external_id,
            )
        )
        if existing is not None:
            return {
                "record_id": existing.id,
                "duplicate": True,
                "sync_status": existing.sync_status,
                "sync_delay_seconds": existing.sync_delay_seconds,
                "manual_appeal_required": existing.sync_status != "synced",
            }

        # 门禁原始事件无论是否超时都落库，便于事后追溯和管理员核验。
        user = _find_user(session, body.masked_user_key)
        # 即使需要人工复核，也尽量关联用户本人和事件时间对应的预约。
        reservation = _matching_reservation(session, body, user, recorded_at)
        record = EntryExitRecord(
            external_id=body.external_id,
            source_system=body.source_system,
            masked_user_key=body.masked_user_key,
            record_type=body.record_type,
            recorded_at=recorded_at,
            received_at=moment,
            expires_at=moment + timedelta(days=get_settings().log_retention_days),
            sync_delay_seconds=delay_seconds,
            sync_status="pending",
        )
        session.add(record)
        session.flush()

        # 超过 300 秒的回调不改变预约状态；关联记录并通知用户申请人工核验。
        if delayed:
            record.sync_status = "late"
            if reservation is not None:
                record.reservation_id = reservation.id
            if user is not None:
                create_notification(
                    session,
                    user_id=user.id,
                    notification_type=E.NotificationType.SYSTEM,
                    content=(
                        f"门禁{_event_label(body.record_type)}记录延迟超过 5 分钟，"
                        "未自动变更预约状态；请提交人工核验申请。"
                    ),
                    idempotency_key=f"gate:{body.source_system}:{body.external_id}:late",
                )
            return {
                "record_id": record.id,
                "duplicate": False,
                "sync_status": "late",
                "sync_delay_seconds": delay_seconds,
                "reservation_id": reservation.id if reservation is not None else None,
                "manual_appeal_required": True,
            }

        # 脱敏身份、预约时间或预约状态不匹配时保留原始事件并转入人工处理。
        if user is None or reservation is None or not _state_matches(body, reservation):
            record.sync_status = "unmatched"
            if reservation is not None:
                record.reservation_id = reservation.id
            if user is not None:
                create_notification(
                    session,
                    user_id=user.id,
                    notification_type=E.NotificationType.SYSTEM,
                    content=(
                        f"门禁{_event_label(body.record_type)}记录无法自动匹配有效预约，"
                        "请检查预约记录或提交人工核验申请。"
                    ),
                    idempotency_key=f"gate:{body.source_system}:{body.external_id}:unmatched",
                )
            return {
                "record_id": record.id,
                "duplicate": False,
                "sync_status": "unmatched",
                "sync_delay_seconds": delay_seconds,
                "reservation_id": reservation.id if reservation is not None else None,
                "manual_appeal_required": True,
            }

        # 命中有效预约后只更新到达或签退事实，不依据门禁进出判定违规。
        arrival = session.scalar(
            select(ArrivalRecord).where(ArrivalRecord.reservation_id == reservation.id)
        )
        if arrival is None:
            arrival = ArrivalRecord(
                reservation_id=reservation.id,
                user_id=user.id,
                seat_id=reservation.seat_id,
            )
            session.add(arrival)
        if body.record_type == E.EntryExitType.ENTRY:
            if reservation.status == E.ReservationStatus.TEMP_LEAVE:
                # 临时离开 30 分钟内经门禁返回，恢复为使用中（HD-15/HD-31）。
                reservation.status = E.ReservationStatus.ACTIVE
                reservation.temp_leave_state = E.TempLeaveState.RETURNED
                notice = "门禁入馆记录已同步：临时离开已结束，座位恢复使用中。"
            else:
                arrival.arrival_status = E.ArrivalStatus.ON_TIME
                arrival.arrived_at = recorded_at
                arrival.arrival_method = E.ArrivalMethod.MANUAL
                reservation.status = E.ReservationStatus.ACTIVE
                notice = "门禁入馆记录已同步到你的预约。"
        elif reservation.status == E.ReservationStatus.TEMP_LEAVE:
            # 已声明临时离开后出馆：保留座位，沿用临时离开计时，超时由定时任务释放。
            notice = "门禁出馆记录已同步：座位将为你保留至临时离开期限结束。"
        else:
            # 使用中未声明临时离开即出馆：按状态文档记为超时结束并登记未声明离开违规。
            arrival.ended_at = recorded_at
            arrival.end_method = E.EndMethod.AUTO_TIMEOUT
            reservation.status = E.ReservationStatus.TIMED_OUT
            reservation.expire_reason = "left_undeclared"
            record_violation(
                session,
                user_id=user.id,
                violation_type=E.ViolationType.LEFT_UNDECLARED,
                reservation_id=reservation.id,
                description="使用中未声明临时离开即通过门禁出馆，座位已释放，可提交申诉。",
                occurred_at=recorded_at,
            )
            notice = "你未声明临时离开即出馆，预约已超时结束并记录违规，可提交申诉。"
        record.reservation_id = reservation.id
        record.sync_status = "synced"
        create_notification(
            session,
            user_id=user.id,
            notification_type=E.NotificationType.SYSTEM,
            content=notice,
            idempotency_key=f"gate:{body.source_system}:{body.external_id}:synced",
        )
        return {
            "record_id": record.id,
            "duplicate": False,
            "sync_status": "synced",
            "sync_delay_seconds": delay_seconds,
            "reservation_id": reservation.id,
            "manual_appeal_required": False,
        }


def _matching_reservation(
    session: Session,
    body: GateEventIn,
    user: User | None,
    recorded_at: datetime,
) -> Reservation | None:
    """按脱敏身份和有效事件时间寻找唯一预约，保留终态记录供延迟核验。"""
    if user is None:
        return None
    settings = get_business_settings(session)

    # 进馆时间须落在签到窗口附近，出馆时间允许在预约结束后短暂补录。
    def matches_time(row: Reservation) -> bool:
        """判断门禁时间是否落在该预约允许核验的签到或签退窗口。"""
        if (
            body.record_type == E.EntryExitType.ENTRY
            and row.status == E.ReservationStatus.TEMP_LEAVE
        ):
            return _within_temp_leave(row, recorded_at, settings.temp_leave_minutes)
        if body.record_type == E.EntryExitType.ENTRY:
            return (
                row.start_time - timedelta(minutes=settings.checkin_open_before_minutes)
                <= recorded_at
                <= row.start_time + timedelta(minutes=settings.no_show_after_minutes)
            )
        return (
            row.start_time
            <= recorded_at
            <= row.end_time + timedelta(minutes=settings.no_show_after_minutes)
        )

    if body.reservation_id is not None:
        reservation = session.get(Reservation, body.reservation_id)
        if reservation is None or reservation.user_id != user.id or not matches_time(reservation):
            return None
        return reservation

    # 多条重叠预约无法安全推断，交由人工核验而不任意挑选一条。
    candidates = [
        row
        for row in session.scalars(select(Reservation).where(Reservation.user_id == user.id))
        if matches_time(row)
    ]
    return candidates[0] if len(candidates) == 1 else None


def _within_temp_leave(row: Reservation, recorded_at: datetime, minutes: int) -> bool:
    """判断入馆时间是否落在临时离开的保留期内且未超过预约结束时间。"""
    if row.temp_leave_at is None or row.temp_leave_state != E.TempLeaveState.WAITING:
        return False
    deadline = min(row.temp_leave_at + timedelta(minutes=minutes), row.end_time)
    return row.temp_leave_at <= recorded_at <= deadline


def _state_matches(body: GateEventIn, reservation: Reservation) -> bool:
    """确认门禁进出事件与预约状态相符，防止旧事件复活或结束预约。"""
    if body.record_type == E.EntryExitType.ENTRY:
        if reservation.status == E.ReservationStatus.TEMP_LEAVE:
            return reservation.temp_leave_state == E.TempLeaveState.WAITING
        return reservation.status == E.ReservationStatus.RESERVED
    return reservation.status in (E.ReservationStatus.ACTIVE, E.ReservationStatus.TEMP_LEAVE)


def _event_label(record_type: E.EntryExitType) -> str:
    """返回用于站内通知的中文门禁事件名称。"""
    return "入馆" if record_type == E.EntryExitType.ENTRY else "出馆"
