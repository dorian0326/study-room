"""管理员配置（#22）：业务参数与校历（节假日/考试周）。"""

from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import enums as E
from app.models.base import Base, LocalDateTime, str_enum


class SystemSetting(Base):
    """键值形式的业务参数，value 为 JSON。"""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(LocalDateTime)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class CalendarDay(Base):
    """特殊日期：把某天标为节假日或考试周，覆盖按星期推算的工作日/周末。"""

    __tablename__ = "calendar_days"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    day_type: Mapped[E.DayType] = mapped_column(str_enum(E.DayType, "day_type"))
    note: Mapped[str | None] = mapped_column(String(128))
