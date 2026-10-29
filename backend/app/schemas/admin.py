# ruff: noqa: E501
from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import DayType, RoomStatus


class BusinessSettings(BaseModel):
    """可配置业务参数（Q-014 清单未定，先覆盖 05 业务规则中 P-003~P-021 的核心项）。"""

    model_config = ConfigDict(extra="forbid")

    advance_booking_days: int = Field(1, ge=0, le=30, description="最多提前几天预约（P-003）")
    max_active_reservations: int = Field(1, ge=1, le=10, description="同时有效预约上限（P-004）")
    checkin_open_before_minutes: int = Field(
        15, ge=0, le=120, description="开始前多久可签到（P-006）"
    )
    no_show_after_minutes: int = Field(
        15, ge=1, le=120, description="开始后多久未签到记爽约（P-007）"
    )
    late_cancel_minutes: int = Field(
        15, ge=0, le=120, description="开始前多久内取消记违规（P-017）"
    )
    temp_leave_minutes: int = Field(30, ge=5, le=240, description="临时离开时长（P-021）")
    missed_checkout_merge: int = Field(
        2, ge=1, le=10, description="几次未结束使用合并为 1 次警告（P-009）"
    )
    violation_window_days: int = Field(14, ge=1, le=180, description="违规累计窗口天数（P-016）")
    penalty_base_threshold: int = Field(
        3, ge=1, le=50, description="第 1 档处罚的违规次数阈值（P-014）"
    )
    penalty_threshold_step: int = Field(2, ge=0, le=50, description="每升一档阈值增加（P-014）")
    penalty_days_per_tier: int = Field(1, ge=1, le=30, description="第 k 档禁约 k×该值 天（P-014）")
    opening_earliest: time = Field(time(6, 0), description="开放时段最早开始（BR-006）")
    opening_latest: time = Field(time(23, 30), description="开放时段最晚结束（BR-006）")

    @model_validator(mode="after")
    def _check(self):
        if self.opening_earliest >= self.opening_latest:
            raise ValueError("开放时段最早开始须早于最晚结束")
        return self


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    location: str | None = Field(None, max_length=128)
    floor: str | None = Field(None, max_length=32)
    capacity: int = Field(0, ge=0)
    facilities: str | None = None
    remark: str | None = None


class RoomOut(RoomIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: RoomStatus


class RoomStatusIn(BaseModel):
    status: RoomStatus


class ScheduleIn(BaseModel):
    day_type: DayType
    open_time: time
    close_time: time
    effective_from: date | None = None
    effective_to: date | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def _check(self):
        if self.open_time >= self.close_time:
            raise ValueError("开放时间须早于关闭时间（不跨零点）")
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError("生效开始日期不能晚于结束日期")
        return self


class ScheduleOut(ScheduleIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int


class CalendarDayIn(BaseModel):
    day: date
    day_type: DayType
    note: str | None = Field(None, max_length=128)

    @model_validator(mode="after")
    def _check(self):
        if self.day_type not in (DayType.HOLIDAY, DayType.EXAM_WEEK):
            raise ValueError("特殊日期只能标为 holiday 或 exam_week")
        return self


class CalendarDayOut(CalendarDayIn):
    model_config = ConfigDict(from_attributes=True)
