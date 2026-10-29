"""核心数据对象（DO-001 ~ DO-016，DO-005 区域与 DO-012 候补不单独建表）。"""

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import enums as E
from app.models.base import Base, LocalDateTime, TimestampMixin, str_enum

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


# DO-001 用户
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # HD-45
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    department: Mapped[str | None] = mapped_column(String(128))
    contact: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[E.AccountStatus] = mapped_column(
        str_enum(E.AccountStatus, "account_status"), default=E.AccountStatus.NORMAL, nullable=False
    )

    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users")

    __table_args__ = (CheckConstraint("length(trim(student_no)) > 0", name="student_no_not_blank"),)


# DO-002 角色
class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[E.RoleName] = mapped_column(str_enum(E.RoleName, "role_name"), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permissions)


# DO-003 权限
class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)  # 如 reservation:cancel
    description: Mapped[str | None] = mapped_column(String(255))
    resource: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(32))


# DO-004 自习室（单一校区，HD-48）
class StudyRoom(TimestampMixin, Base):
    __tablename__ = "study_rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    location: Mapped[str | None] = mapped_column(String(128))
    floor: Mapped[str | None] = mapped_column(String(32))
    capacity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    facilities: Mapped[str | None] = mapped_column(Text)
    status: Mapped[E.RoomStatus] = mapped_column(
        str_enum(E.RoomStatus, "room_status"), default=E.RoomStatus.OPEN, nullable=False
    )
    remark: Mapped[str | None] = mapped_column(Text)

    seats: Mapped[list["Seat"]] = relationship(back_populates="room")

    __table_args__ = (CheckConstraint("capacity >= 0", name="capacity_non_negative"),)


# DO-006 座位（区域为座位属性 zone_type，HD-47/48）
class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("study_rooms.id", ondelete="RESTRICT"))
    code: Mapped[str] = mapped_column(String(32))  # 座位编号
    zone_type: Mapped[E.ZoneType] = mapped_column(str_enum(E.ZoneType, "zone_type"))
    has_power: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    by_window: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accessible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[E.SeatStatus] = mapped_column(
        str_enum(E.SeatStatus, "seat_status"), default=E.SeatStatus.AVAILABLE, nullable=False
    )
    status_changed_at: Mapped[datetime | None] = mapped_column(LocalDateTime)

    room: Mapped[StudyRoom] = relationship(back_populates="seats")

    __table_args__ = (UniqueConstraint("room_id", "code"),)


# DO-007 开放时段（06:00–23:30，不跨零点，HD-37）
class OpeningSchedule(Base):
    __tablename__ = "opening_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("study_rooms.id", ondelete="CASCADE"))
    day_type: Mapped[E.DayType] = mapped_column(str_enum(E.DayType, "day_type"))
    open_time: Mapped[time] = mapped_column(Time)
    close_time: Mapped[time] = mapped_column(Time)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint("open_time < close_time", name="open_before_close"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_from <= effective_to",
            name="effective_range",
        ),
    )


# DO-008 预约单
class Reservation(TimestampMixin, Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_no: Mapped[str] = mapped_column(String(32), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    room_id: Mapped[int] = mapped_column(ForeignKey("study_rooms.id", ondelete="RESTRICT"))
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="RESTRICT"))
    start_time: Mapped[datetime] = mapped_column(LocalDateTime)
    end_time: Mapped[datetime] = mapped_column(LocalDateTime)
    status: Mapped[E.ReservationStatus] = mapped_column(
        str_enum(E.ReservationStatus, "reservation_status"),
        default=E.ReservationStatus.RESERVED,
        nullable=False,
    )
    cancel_type: Mapped[E.CancelType | None] = mapped_column(str_enum(E.CancelType, "cancel_type"))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column(LocalDateTime)
    expire_reason: Mapped[str | None] = mapped_column(String(64))
    remark: Mapped[str | None] = mapped_column(Text)
    temp_leave_at: Mapped[datetime | None] = mapped_column(LocalDateTime)
    temp_leave_state: Mapped[E.TempLeaveState] = mapped_column(
        str_enum(E.TempLeaveState, "temp_leave_state"),
        default=E.TempLeaveState.NONE,
        nullable=False,
    )
    # 幂等键：重复提交去重（#13 使用）
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    request_fingerprint: Mapped[str | None] = mapped_column(String(64))

    user: Mapped[User] = relationship()
    seat: Mapped[Seat] = relationship()

    __table_args__ = (
        CheckConstraint("start_time < end_time", name="start_before_end"),
        # 同一座位同一开始时间最多一条活跃预约；时段重叠检测由业务层在 BEGIN IMMEDIATE 事务中完成
        Index(
            "uq_reservations_active_seat_start",
            "seat_id",
            "start_time",
            unique=True,
            sqlite_where=text("status IN ('RESERVED', 'ACTIVE', 'TEMP_LEAVE')"),
        ),
        Index("ix_reservations_user_start", "user_id", "start_time"),
    )


# DO-009 到达记录（独立对象，HD-47）
class ArrivalRecord(Base):
    __tablename__ = "arrival_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="RESTRICT"))
    arrival_status: Mapped[E.ArrivalStatus] = mapped_column(
        str_enum(E.ArrivalStatus, "arrival_status"), default=E.ArrivalStatus.ABSENT
    )
    arrived_at: Mapped[datetime | None] = mapped_column(LocalDateTime)
    arrival_method: Mapped[E.ArrivalMethod | None] = mapped_column(
        str_enum(E.ArrivalMethod, "arrival_method")
    )
    ended_at: Mapped[datetime | None] = mapped_column(LocalDateTime)
    end_method: Mapped[E.EndMethod | None] = mapped_column(str_enum(E.EndMethod, "end_method"))
    sync_delay_seconds: Mapped[int | None] = mapped_column(Integer)  # HD-52


# DO-011 限制措施（禁止预约）
class Restriction(TimestampMixin, Base):
    __tablename__ = "restrictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    ban_days: Mapped[int] = mapped_column(Integer)  # ⌊(警告次数-1)÷2⌋（HD-17）
    warning_count: Mapped[int] = mapped_column(Integer)
    trigger_condition: Mapped[str] = mapped_column(String(32))  # 满3次 / 满5次 / …
    start_at: Mapped[datetime] = mapped_column(LocalDateTime)
    end_at: Mapped[datetime] = mapped_column(LocalDateTime)
    status: Mapped[E.RestrictionStatus] = mapped_column(
        str_enum(E.RestrictionStatus, "restriction_status"), default=E.RestrictionStatus.ACTIVE
    )
    lifted_at: Mapped[datetime | None] = mapped_column(LocalDateTime)
    lift_reason: Mapped[str | None] = mapped_column(Text)
    lifted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    __table_args__ = (
        CheckConstraint("ban_days >= 1", name="ban_days_positive"),
        CheckConstraint("start_at < end_at", name="start_before_end"),
    )


# DO-010 违规记录
class ViolationRecord(TimestampMixin, Base):
    __tablename__ = "violation_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    violation_type: Mapped[E.ViolationType] = mapped_column(
        str_enum(E.ViolationType, "violation_type")
    )
    occurred_at: Mapped[datetime] = mapped_column(LocalDateTime)
    reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL")
    )
    arrival_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("arrival_records.id", ondelete="SET NULL")
    )
    description: Mapped[str | None] = mapped_column(Text)
    state: Mapped[E.ViolationState] = mapped_column(
        str_enum(E.ViolationState, "violation_state"), default=E.ViolationState.ACTIVE
    )
    period_start: Mapped[datetime] = mapped_column(LocalDateTime)  # 首次违规日起 14 天（HD-28）
    period_seq: Mapped[int] = mapped_column(Integer, default=1)  # HD-18
    archived_at: Mapped[datetime | None] = mapped_column(LocalDateTime)
    determined_by: Mapped[str] = mapped_column(String(16), default="system")  # 系统自动
    result: Mapped[E.ViolationResult] = mapped_column(
        str_enum(E.ViolationResult, "violation_result"), default=E.ViolationResult.WARNING
    )
    restriction_id: Mapped[int | None] = mapped_column(
        ForeignKey("restrictions.id", ondelete="SET NULL")
    )
    appeal_status: Mapped[E.AppealStatus] = mapped_column(
        str_enum(E.AppealStatus, "appeal_status"), default=E.AppealStatus.NONE
    )
    is_offset: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否折算

    __table_args__ = (Index("ix_violation_records_user_period", "user_id", "period_start"),)


# DO-014 申诉（7 天时限，HD-51）
class Appeal(TimestampMixin, Base):
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    violation_id: Mapped[int] = mapped_column(
        ForeignKey("violation_records.id", ondelete="CASCADE")
    )
    restriction_id: Mapped[int | None] = mapped_column(
        ForeignKey("restrictions.id", ondelete="SET NULL")
    )
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(LocalDateTime)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    result: Mapped[E.AppealResult | None] = mapped_column(str_enum(E.AppealResult, "appeal_result"))
    reviewed_at: Mapped[datetime | None] = mapped_column(LocalDateTime)
    review_comment: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (CheckConstraint("length(trim(reason)) > 0", name="reason_not_blank"),)


# DO-013 通知（仅站内，HD-38）
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[E.NotificationType] = mapped_column(
        str_enum(E.NotificationType, "notification_type")
    )
    content: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(LocalDateTime)
    channel: Mapped[str] = mapped_column(String(16), default="in_app")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint("channel = 'in_app'", name="in_app_only"),
        Index("ix_notifications_user_read", "user_id", "is_read"),
    )


# DO-015 操作日志（保留 1 学期，HD-47）
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    op_type: Mapped[E.AuditOpType] = mapped_column(str_enum(E.AuditOpType, "audit_op_type"))
    target_type: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(LocalDateTime)
    before_value: Mapped[str | None] = mapped_column(Text)  # JSON
    after_value: Mapped[str | None] = mapped_column(Text)  # JSON
    ip_address: Mapped[str | None] = mapped_column(String(45))
    result: Mapped[str] = mapped_column(String(16), default="success")

    __table_args__ = (Index("ix_audit_logs_occurred_at", "occurred_at"),)


# DO-016 入馆/出馆记录（仅脱敏三元组 + 去重键，不存人脸/卡号；与用户为逻辑关联）
class EntryExitRecord(Base):
    __tablename__ = "entry_exit_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64))
    source_system: Mapped[str] = mapped_column(String(64))
    masked_user_key: Mapped[str] = mapped_column(String(64), index=True)
    record_type: Mapped[E.EntryExitType] = mapped_column(
        str_enum(E.EntryExitType, "entry_exit_type")
    )
    recorded_at: Mapped[datetime] = mapped_column(LocalDateTime)
    recognition: Mapped[E.RecognitionMethod | None] = mapped_column(
        str_enum(E.RecognitionMethod, "recognition_method")
    )
    received_at: Mapped[datetime] = mapped_column(LocalDateTime)
    expires_at: Mapped[datetime] = mapped_column(LocalDateTime)

    __table_args__ = (UniqueConstraint("source_system", "external_id"),)
