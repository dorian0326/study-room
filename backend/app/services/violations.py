"""违规候选记录、阶梯禁约和申诉审核业务逻辑。"""

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


def record_violation(
    session: Session,
    *,
    user_id: int,
    violation_type: ViolationType,
    reservation_id: int | None,
    description: str,
    occurred_at=None,
) -> ViolationRecord:
    """记录违规并按 14 天首次违规窗口计算警告或阶梯禁约。"""
    # 预约触发的定时任务可能重复执行，先按预约与违规类型返回已有记录。
    if reservation_id is not None:
        existing = session.scalar(
            select(ViolationRecord).where(
                ViolationRecord.reservation_id == reservation_id,
                ViolationRecord.violation_type == violation_type,
            )
        )
        if existing is not None:
            return existing

    # 累计窗口固定从首次违规开始，不滚动延长；窗口过期后新违规重新计数。
    settings = get_business_settings(session)
    moment = occurred_at or now()
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
        sequence = (
            int(
                session.scalar(
                    select(func.count(ViolationRecord.id)).where(
                        ViolationRecord.user_id == user_id,
                        ViolationRecord.state == ViolationState.ACTIVE,
                        ViolationRecord.period_start == period_start,
                    )
                )
                or 0
            )
            + 1
        )
    else:
        period_start = moment
        sequence = 1

    # 每次违规先记警告；仅在达到 3、5、7……次时新建对应天数的禁约。
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

    # 保存可复核的原始违规候选，处罚和通知都不执行扣分逻辑。
    violation = ViolationRecord(
        user_id=user_id,
        violation_type=violation_type,
        occurred_at=moment,
        reservation_id=reservation_id,
        description=description,
        state=ViolationState.ACTIVE,
        period_start=period_start,
        period_seq=sequence,
        determined_by="system",
        result=result,
        restriction_id=restriction.id if restriction else None,
    )
    session.add(violation)
    session.flush()
    content = (
        f"你有一条新的违规记录（{violation_type.value}），当前累计第 {sequence} 次。"
        if restriction is None
        else f"你在 14 天累计窗口内达到第 {sequence} 次违规，禁约 {restriction.ban_days} 天。"
    )
    create_notification(
        session,
        user_id=user_id,
        notification_type=NotificationType.VIOLATION,
        content=content,
        idempotency_key=f"violation:{violation.id}:created",
    )
    return violation
