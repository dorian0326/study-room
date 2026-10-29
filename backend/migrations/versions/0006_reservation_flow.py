"""可选楼层与创建预约请求指纹（#10、#13）。已有数据保持不变。"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("study_rooms", sa.Column("floor", sa.String(32), nullable=True))
    op.add_column("reservations", sa.Column("request_fingerprint", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("reservations") as batch:
        batch.drop_column("request_fingerprint")
    with op.batch_alter_table("study_rooms") as batch:
        batch.drop_column("floor")
