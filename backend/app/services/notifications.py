"""仅站内通知的创建、去重和用户已读处理。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification
from app.models.enums import NotificationType
from app.timeutil import now


def create_notification(
    session: Session,
    *,
    user_id: int,
    notification_type: NotificationType,
    content: str,
    idempotency_key: str | None = None,
) -> Notification:
    """创建站内通知；事件键已存在时返回原记录以保持任务幂等。"""
    # 重复任务和重复回调共用稳定事件键，避免用户收到重复消息。
    if idempotency_key:
        existing = session.scalar(
            select(Notification).where(Notification.idempotency_key == idempotency_key)
        )
        if existing is not None:
            return existing

    # 通知只写入数据库，模型约束和此处固定 channel 均禁止邮件或短信外发。
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        content=content,
        sent_at=now(),
        channel="in_app",
        idempotency_key=idempotency_key,
    )
    session.add(notification)
    session.flush()
    return notification
