"""ORM 基类与公共类型。"""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, MetaData, TypeDecorator
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.timeutil import now, tz

# 统一约束命名，便于 Alembic 在 SQLite batch 模式下识别约束
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class LocalDateTime(TypeDecorator):
    """以 Asia/Shanghai 本地时间（无时区）存入 SQLite，读出时附上 UTC+8 时区（HD-39）。"""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):  # noqa: ANN001
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("必须使用带时区的 datetime（请用 app.timeutil.now()）")
        return value.astimezone(tz()).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):  # noqa: ANN001
        return None if value is None else value.replace(tzinfo=tz())


def str_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    """以字符串存储枚举值，并生成 CHECK 约束。"""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(LocalDateTime, default=now, nullable=False)
