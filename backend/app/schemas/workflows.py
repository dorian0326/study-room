"""需求 #17 至 #24 使用的预约、座位、违规、通知和门禁数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    AppealResult,
    AppealStatus,
    EntryExitType,
    NotificationType,
    ReservationStatus,
    SeatStatus,
    ViolationResult,
    ViolationState,
    ViolationType,
    ZoneType,
)


class ReservationCreate(BaseModel):
    """预约提交结构；时间必须带时区，防止跨客户端时区误判。"""

    seat_id: int = Field(gt=0)
    start_time: datetime
    end_time: datetime
    request_key: str | None = Field(None, min_length=8, max_length=64)

    @field_validator("start_time", "end_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """拒绝无时区时间，统一由后端转换到 Asia/Shanghai 存储。"""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("预约时间必须包含时区")
        return value


class ReservationOut(BaseModel):
    """预约历史的最小安全输出，不暴露其他用户资料。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reservation_no: str
    user_id: int
    room_id: int
    seat_id: int
    start_time: datetime
    end_time: datetime
    status: ReservationStatus
    created_at: datetime
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    temp_leave_at: datetime | None = None


class ReservationHistoryOut(ReservationOut):
    """预约历史附带房间和座位标签，供用户端直接展示。"""

    room_name: str
    seat_code: str


class EndUseIn(BaseModel):
    """显式结束使用的确认结构，确认值必须由用户主动提交。"""

    confirm: bool


class SeatIn(BaseModel):
    """座位新增和修改结构，属性与导入配置文件使用相同字段。"""

    code: str = Field(min_length=1, max_length=32)
    zone_type: ZoneType = ZoneType.QUIET
    has_power: bool = False
    by_window: bool = False
    accessible: bool = False
    status: SeatStatus = SeatStatus.AVAILABLE


class SeatOut(SeatIn):
    """管理员座位管理响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int


class SeatStatusOut(SeatOut):
    """座位状态变更结果，包含维护操作取消的预约数量。"""

    cancelled_reservations: int = 0


class SeatStatusIn(BaseModel):
    """座位状态变更结构；maintenance 会触发预约取消和通知。"""

    status: SeatStatus


class SeatImportIn(BaseModel):
    """配置文件导入结构，前端读取 CSV 文本后提交。"""

    content: str = Field(min_length=1, max_length=2_000_000)


class ManualViolationIn(BaseModel):
    """管理员手工登记违规时使用的审计友好请求结构。"""

    user_id: int = Field(gt=0)
    violation_type: ViolationType
    reservation_id: int | None = Field(None, gt=0)
    description: str = Field(min_length=5, max_length=4000)


class ViolationOut(BaseModel):
    """本人或管理员查看违规时使用的响应结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    violation_type: ViolationType
    occurred_at: datetime
    reservation_id: int | None
    description: str | None
    state: ViolationState
    period_start: datetime
    period_seq: int
    result: ViolationResult
    appeal_status: AppealStatus


class AppealCreate(BaseModel):
    """学生申诉结构，理由必填，证据以文本描述保存。"""

    violation_id: int = Field(gt=0)
    reason: str = Field(min_length=5, max_length=4000)
    evidence: str | None = Field(None, max_length=8000)


class AppealOut(BaseModel):
    """申诉查看结构，包含受理期限和审核结果。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    violation_id: int
    reason: str
    evidence: str | None
    deadline: datetime
    reviewer_id: int | None
    result: AppealResult | None
    reviewed_at: datetime | None
    review_comment: str | None


class AppealReviewIn(BaseModel):
    """管理员审核申诉的结论及可见处理说明。"""

    result: AppealResult
    review_comment: str = Field(min_length=2, max_length=4000)


class SeatMaintenanceIn(BaseModel):
    """座位维护状态和管理员操作理由。"""

    status: SeatStatus
    reason: str = Field(default="管理员设置座位状态", min_length=2, max_length=500)


class NotificationOut(BaseModel):
    """站内通知响应结构，不提供外部发送渠道字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: NotificationType
    content: str
    sent_at: datetime
    is_read: bool


class GateEventIn(BaseModel):
    """门禁模拟同步事件；人员标识必须是脱敏后的 keyed hash。"""

    external_id: str = Field(min_length=1, max_length=64)
    source_system: str = Field(default="mock-gate", min_length=1, max_length=64)
    masked_user_key: str = Field(min_length=16, max_length=64)
    record_type: EntryExitType
    recorded_at: datetime
    reservation_id: int | None = Field(None, gt=0)

    @field_validator("recorded_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """要求门禁事件时间包含时区，便于测量同步延迟。"""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("门禁事件时间必须包含时区")
        return value


class ManualGateAppealIn(BaseModel):
    """门禁不可用或回调超时后的人工核验申请。"""

    record_type: EntryExitType
    reason: str = Field(min_length=5, max_length=4000)
    reservation_id: int | None = Field(None, gt=0)
