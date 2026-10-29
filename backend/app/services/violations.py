"""违规候选记录、阶梯禁约、周期归档和申诉审核业务逻辑。"""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Restriction, ViolationRecord
from app.models.enums import (
    NotificationType,
    RestrictionStatus,
    ViolationResult,
    ViolationState,
    ViolationType,
)
from app.services.notifications import create_notification
from app.services.settings import get_business_settings
from app.timeutil import now


def archive_expired_violations(session: Session, moment=None) -> int:
    """BR-094a：周期窗口到期后把仍有效的违规记录归档，下一轮重新计数。"""
    moment = moment or now()
    settings = get_business_settings(session)
    window = timedelta(days=settings.violation_window_days)
    rows = list(
        session.scalars(
            select(ViolationRecord).where(
                ViolationRecord.state == ViolationState.ACTIVE,
                ViolationRecord.period_start <= moment - window,
            )
        )
    )
    for row in rows:
        row.state = ViolationState.ARCHIVED
        row.archived_at = moment
    return len(rows)


def record_violation(
    session: Session,
    *,
    user_id: int,
    violation_type: ViolationType,
    reservation_id: int | None,
    description: str,
    occurred_at=None,
) -> ViolationRecord:
    """记录违规并按 14 天首次违规窗口计算警告或阶梯禁约。

    BR-093：未点结束使用（NO_CHECKOUT）按 missed_checkout_merge（默认 2）次合并为 1 次警告。
    未计入阶梯的原始事件写入 is_offset=True，不推进 period_seq。
    """
    if reservation_id is not None:
        existing = session.scalar(
            select(ViolationRecord).where(
                ViolationRecord.reservation_id == reservation_id,
                ViolationRecord.violation_type == violation_type,
            )
        )
        if existing is not None:
            return existing

    settings = get_business_settings(session)
    moment = occurred_at or now()

    # 含 is_offset 记录，避免 BR-093 首条抵消事件无法延续同一周期窗口。
    previous = session.scalar(
        select(ViolationRecord)
        .where(
            ViolationRecord.user_id == user_id,
            ViolationRecord.state == ViolationState.ACTIVE,
            ViolationRecord.occurred_at <= moment,
        )
        .order_by(ViolationRecord.occurred_at.desc())
        .limit(1)
    )
    if previous and moment < previous.period_start + timedelta(days=settings.violation_window_days):
        period_start = previous.period_start
        counted = int(
            session.scalar(
                select(func.count(ViolationRecord.id)).where(
                    ViolationRecord.user_id == user_id,
                    ViolationRecord.state == ViolationState.ACTIVE,
                    ViolationRecord.is_offset.is_(False),
                    ViolationRecord.period_start == period_start,
                )
            )
            or 0
        )
    else:
        period_start = moment
        counted = 0

    is_offset = False
    merge = max(1, settings.missed_checkout_merge)
    raw = 0
    if violation_type == ViolationType.NO_CHECKOUT:
        raw = int(
            session.scalar(
                select(func.count(ViolationRecord.id)).where(
                    ViolationRecord.user_id == user_id,
                    ViolationRecord.state == ViolationState.ACTIVE,
                    ViolationRecord.violation_type == ViolationType.NO_CHECKOUT,
                    ViolationRecord.period_start == period_start,
                )
            )
            or 0
        )
        if (raw + 1) % merge != 0:
            is_offset = True

    if is_offset:
        sequence = counted
        result = ViolationResult.WARNING
        restriction = None
        content = f"已记录一次未结束使用（{raw + 1}/{merge}），满额后才会计入一次违规警告。"
        period_seq = 0
    else:
        sequence = counted + 1
        result = ViolationResult.WARNING
        restriction = None
        first_threshold = settings.penalty_base_threshold
        tier_step = max(1, settings.penalty_threshold_step)
        if sequence >= first_threshold and (sequence - first_threshold) % tier_step == 0:
            tier = (sequence - first_threshold) // tier_step + 1
            ban_days = tier * settings.penalty_days_per_tier
            restriction = Restriction(
                user_id=user_id,
                ban_days=ban_days,
                warning_count=sequence,
                trigger_condition=f"满{sequence}次",
                start_at=moment,
                end_at=moment + timedelta(days=ban_days),
                status=RestrictionStatus.ACTIVE,
            )
            session.add(restriction)
            session.flush()
            result = ViolationResult.RESTRICTED
        content = (
            f"你有一条新的违规记录（{violation_type.value}），当前累计第 {sequence} 次。"
            if restriction is None
            else f"你在 14 天累计窗口内达到第 {sequence} 次违规，禁约 {restriction.ban_days} 天。"
        )
        period_seq = sequence

    violation = ViolationRecord(
        user_id=user_id,
        violation_type=violation_type,
        occurred_at=moment,
        reservation_id=reservation_id,
        description=description,
        state=ViolationState.ACTIVE,
        period_start=period_start,
        period_seq=period_seq,
        determined_by="system",
        result=result,
        restriction_id=restriction.id if restriction else None,
        is_offset=is_offset,
    )
    session.add(violation)
    session.flush()
    create_notification(
        session,
        user_id=user_id,
        notification_type=NotificationType.VIOLATION,
        content=content,
        idempotency_key=f"violation:{violation.id}:created",
    )
    return violation
