"""新增暂离超时违规类型 temp_leave_timeout（BR-071）。

修订编号：0008
依赖编号：0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD = ("left_undeclared", "no_show", "no_checkout", "late_cancel")
_NEW = (*_OLD, "temp_leave_timeout")


def upgrade() -> None:
    with op.batch_alter_table("violation_records") as batch:
        batch.alter_column(
            "violation_type",
            existing_type=sa.Enum(*_OLD, name="violation_type", native_enum=False, length=32),
            type_=sa.Enum(
                *_NEW,
                name="violation_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            existing_nullable=False,
        )


def downgrade() -> None:
    op.execute(
        "UPDATE violation_records SET violation_type = 'left_undeclared' "
        "WHERE violation_type = 'temp_leave_timeout'"
    )
    with op.batch_alter_table("violation_records") as batch:
        batch.alter_column(
            "violation_type",
            existing_type=sa.Enum(*_NEW, name="violation_type", native_enum=False, length=32),
            type_=sa.Enum(
                *_OLD,
                name="violation_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            existing_nullable=False,
        )
