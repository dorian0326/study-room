"""登录日志（#8，FR-075 / US-402）。操作日志沿用 audit_logs。"""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, LocalDateTime


class LoginLog(Base):
    __tablename__ = "login_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    student_no: Mapped[str] = mapped_column(String(32))  # 失败时也记录尝试的学号
    event: Mapped[str] = mapped_column(String(16))  # login / logout
    success: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(String(32))  # 失败原因代码
    occurred_at: Mapped[datetime] = mapped_column(LocalDateTime)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        Index("ix_login_logs_occurred_at", "occurred_at"),
        Index("ix_login_logs_student_no", "student_no"),
    )
