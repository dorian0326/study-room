"""seed permissions：写入权限矩阵快照（#7，BR-106 模块 × 动作）

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (code, resource, action, 说明, 角色) —— 与 app/permissions.py 同步（有测试校验）
ROWS = [
    (
        "room:read",
        "room",
        "read",
        "查看自习室/座位公开信息与可用状态（PERM-004/005）",
        ["admin", "ops", "user"],
    ),
    (
        "reservation:own",
        "reservation",
        "own",
        "本人预约、签到、结束、临时离开、历史、申诉（PERM-006~014）",
        ["admin", "user"],
    ),
    (
        "reservation:read_all",
        "reservation",
        "read_all",
        "查看全部用户预约明细（PERM-015）",
        ["admin"],
    ),
    ("room:manage", "room", "manage", "管理自习室、座位、开放时间（PERM-017~019）", ["admin"]),
    ("settings:manage", "settings", "manage", "配置业务参数（PERM-020）", ["admin"]),
    (
        "violation:manage",
        "violation",
        "manage",
        "查看/认定/撤销违规、执行处罚（PERM-016/021）",
        ["admin"],
    ),
    ("appeal:manage", "appeal", "manage", "处理申诉（PERM-022）", ["admin"]),
    ("stats:read", "stats", "read", "查看统计报表（PERM-023）", ["admin"]),
    ("data:export", "data", "export", "数据导出（PERM-026）", ["admin"]),
    (
        "user:manage",
        "user",
        "manage",
        "管理用户角色、账户状态、签发重置码（FR-005/007）",
        ["admin"],
    ),
    ("system_log:read", "system_log", "read", "查看系统运行状态与日志（PERM-024）", ["ops"]),
    ("audit_log:read", "audit_log", "read", "查看操作审计日志（PERM-025）", ["admin", "ops"]),
    ("entry_exit:read", "entry_exit", "read", "读取入馆/出馆记录（PERM-027）", ["ops"]),
    ("system:backup", "system", "backup", "数据备份与恢复（US-403）", ["ops"]),
]


def upgrade() -> None:
    conn = op.get_bind()
    role_ids = dict(conn.execute(sa.text("SELECT name, id FROM roles")).all())
    for code, resource, action, desc, roles in ROWS:
        pid = conn.execute(
            sa.text(
                "INSERT INTO permissions (code, description, resource, action) "
                "VALUES (:c, :d, :r, :a) RETURNING id"
            ),
            {"c": code, "d": desc, "r": resource, "a": action},
        ).scalar_one()
        for role in roles:
            conn.execute(
                sa.text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r, :p)"),
                {"r": role_ids[role], "p": pid},
            )


def downgrade() -> None:
    codes = [r[0] for r in ROWS]
    conn = op.get_bind()
    ids = sa.bindparam("codes", expanding=True)
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code IN :codes)"
        ).bindparams(ids),
        {"codes": codes},
    )
    conn.execute(
        sa.text("DELETE FROM permissions WHERE code IN :codes").bindparams(ids), {"codes": codes}
    )
