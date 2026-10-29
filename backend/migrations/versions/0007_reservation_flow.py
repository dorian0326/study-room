"""可选楼层与创建预约请求指纹（#10、#13）。已有数据保持不变。

修订编号：0007
依赖编号：0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("study_rooms", sa.Column("floor", sa.String(32), nullable=True))
    op.add_column("reservations", sa.Column("request_fingerprint", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("reservations") as batch:
        batch.drop_column("request_fingerprint")
    with op.batch_alter_table("study_rooms") as batch:
        batch.drop_column("floor")
