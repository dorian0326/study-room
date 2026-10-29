"""业务枚举。取值对应 requirements/08_data_dictionary.md 与 10_state_transitions.md。"""

from enum import StrEnum


class AccountStatus(StrEnum):
    NORMAL = "normal"  # 正常
    DISABLED = "disabled"  # 禁用


class RoleName(StrEnum):
    USER = "user"  # 用户
    ADMIN = "admin"  # 管理员
    OPS = "ops"  # 运维


class RoomStatus(StrEnum):
    OPEN = "open"  # 正常
    CLOSED = "closed"  # 关闭


class ZoneType(StrEnum):
    QUIET = "quiet"  # 静音区
    DISCUSSION = "discussion"  # 讨论区
    EXAM_PREP = "exam_prep"  # 考研区


class SeatStatus(StrEnum):
    AVAILABLE = "available"  # 可用
    RESERVED = "reserved"  # 已被预约
    IN_USE = "in_use"  # 使用中
    MAINTENANCE = "maintenance"  # 维护中
    CLOSED = "closed"  # 暂不可用 / 已关闭
    DISABLED = "disabled"  # 永久停用 / 已禁用


class DayType(StrEnum):
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"
    EXAM_WEEK = "exam_week"


class ReservationStatus(StrEnum):
    RESERVED = "RESERVED"  # 已预约
    ACTIVE = "ACTIVE"  # 已签到
    TEMP_LEAVE = "TEMP_LEAVE"  # 临时离开
    COMPLETED = "COMPLETED"  # 已完成
    CANCELLED = "CANCELLED"  # 已取消
    ADMIN_CANCELLED = "ADMIN_CANCELLED"  # 管理员强制取消
    EXPIRED = "EXPIRED"  # 预约失效
    TIMED_OUT = "TIMED_OUT"  # 超时结束


ACTIVE_RESERVATION_STATUSES = (
    ReservationStatus.RESERVED,
    ReservationStatus.ACTIVE,
    ReservationStatus.TEMP_LEAVE,
)


class CancelType(StrEnum):
    NORMAL = "normal"  # 正常取消（>15min）
    LATE = "late"  # 违规取消（≤15min）
    SYSTEM = "system"  # 系统取消


class TempLeaveState(StrEnum):
    NONE = "none"  # 未声明
    WAITING = "waiting"  # 等待返回
    RETURNED = "returned"  # 已返回
    TIMED_OUT = "timed_out"  # 超时释放


class ArrivalStatus(StrEnum):
    ABSENT = "absent"  # 未到
    ON_TIME = "on_time"  # 准时到
    LATE = "late"  # 迟到
    EARLY = "early"  # 提前到


class ArrivalMethod(StrEnum):
    QR = "qr"  # 扫码（HD-43 唯一签到方式）
    MANUAL = "manual"  # 手动


class EndMethod(StrEnum):
    BUTTON = "button"  # 显式按钮
    AUTO_TIMEOUT = "auto_timeout"  # 超时自动
    ADMIN_RELEASE = "admin_release"  # 管理员释放


class ViolationType(StrEnum):
    LEFT_UNDECLARED = "left_undeclared"  # 离开图书馆超时未声明
    NO_SHOW = "no_show"  # 预约未到达
    NO_CHECKOUT = "no_checkout"  # 未签退
    LATE_CANCEL = "late_cancel"  # 预约开始前≤15min取消


class ViolationState(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ViolationResult(StrEnum):
    WARNING = "warning"
    RESTRICTED = "restricted"  # 触发禁约


class AppealStatus(StrEnum):
    NONE = "none"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AppealResult(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class RestrictionStatus(StrEnum):
    ACTIVE = "active"  # 生效中
    LIFTED = "lifted"  # 已解除
    EXPIRED = "expired"  # 已过期


class NotificationType(StrEnum):
    RESERVATION_CONFIRMED = "reservation_confirmed"
    CHECKIN_REMINDER = "checkin_reminder"
    VIOLATION = "violation"
    MAINTENANCE = "maintenance"
    SYSTEM = "system"
    TEMP_LEAVE = "temp_leave"


class AuditOpType(StrEnum):
    ADMIN_ACTION = "admin_action"  # 管理动作
    VIOLATION = "violation"  # 违规认定
    PERMISSION_CHANGE = "permission_change"  # 权限变更


class EntryExitType(StrEnum):
    ENTRY = "entry"
    EXIT = "exit"


class RecognitionMethod(StrEnum):
    FACE = "face"
    CARD = "card"
