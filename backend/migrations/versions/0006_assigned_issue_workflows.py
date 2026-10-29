"""为站内通知和门禁事件添加去重与同步状态字段。

修订编号：0006
依赖编号：0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增加可空唯一键，让既有通知保持兼容并为新事件提供幂等保护。"""
    # 既有记录保持 NULL；SQLite 允许多个 NULL，但不允许重复的非空事件键。
    op.add_column("notifications", sa.Column("idempotency_key", sa.String(length=128)))
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.create_unique_constraint("uq_notifications_idempotency_key", ["idempotency_key"])
    # 兼容早期可配置值，Issue 17 将临时离开时限固定为 30 分钟。
    op.execute("UPDATE system_settings SET value = '30' WHERE key = 'temp_leave_minutes'")
    # 保存门禁回调延迟和同步降级状态，便于运维排查与申诉追溯。
    op.add_column(
        "entry_exit_records",
        sa.Column("sync_status", sa.String(length=16), nullable=False, server_default="pending"),
    )
    op.add_column("entry_exit_records", sa.Column("sync_delay_seconds", sa.Integer()))
    op.add_column(
        "entry_exit_records",
        sa.Column("reservation_id", sa.Integer(), nullable=True),
    )
    with op.batch_alter_table("entry_exit_records") as batch_op:
        batch_op.create_foreign_key(
            "fk_entry_exit_records_reservation_id_reservations",
            "reservations",
            ["reservation_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.add_column("entry_exit_records", sa.Column("manual_note", sa.Text()))


def downgrade() -> None:
    """回滚通知事件键字段和唯一约束。"""
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_constraint("uq_notifications_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")
    # 回滚门禁同步状态扩展字段。
    with op.batch_alter_table("entry_exit_records") as batch_op:
        batch_op.drop_constraint(
            "fk_entry_exit_records_reservation_id_reservations", type_="foreignkey"
        )
        batch_op.drop_column("manual_note")
        batch_op.drop_column("reservation_id")
    op.drop_column("entry_exit_records", "sync_delay_seconds")
    op.drop_column("entry_exit_records", "sync_status")
