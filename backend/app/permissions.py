# ruff: noqa: E501, E741
"""权限矩阵（FR-005、HD-14、SRS §4.2 PERM-001~027）。

按 BR-106 采用粗粒度「模块 × 动作」，行级隔离（“仅限本人”）由各接口的查询过滤实现。
本文件是唯一权威来源；迁移 0003 把同一份快照写入 permissions / role_permissions 表供查看，
tests/test_permissions.py 校验两者一致。
"""

from app.models.enums import RoleName as R

U, A, O = R.USER, R.ADMIN, R.OPS

# code: (resource, action, 说明, 允许的角色)
PERMISSIONS: dict[str, tuple[str, str, str, frozenset[R]]] = {
    "room:read": ("room", "read", "查看自习室/座位公开信息与可用状态（PERM-004/005）", frozenset({U, A, O})),
    "reservation:own": ("reservation", "own", "本人预约、签到、结束、临时离开、历史、申诉（PERM-006~014）", frozenset({U, A})),
    "reservation:read_all": ("reservation", "read_all", "查看全部用户预约明细（PERM-015）", frozenset({A})),
    "room:manage": ("room", "manage", "管理自习室、座位、开放时间（PERM-017~019）", frozenset({A})),
    "settings:manage": ("settings", "manage", "配置业务参数（PERM-020）", frozenset({A})),
    "violation:manage": ("violation", "manage", "查看/认定/撤销违规、执行处罚（PERM-016/021）", frozenset({A})),
    "appeal:manage": ("appeal", "manage", "处理申诉（PERM-022）", frozenset({A})),
    "stats:read": ("stats", "read", "查看统计报表（PERM-023）", frozenset({A})),
    "data:export": ("data", "export", "数据导出（PERM-026）", frozenset({A})),
    "user:manage": ("user", "manage", "管理用户角色、账户状态、签发重置码（FR-005/007）", frozenset({A})),
    "system_log:read": ("system_log", "read", "查看系统运行状态与日志（PERM-024）", frozenset({O})),
    "audit_log:read": ("audit_log", "read", "查看操作审计日志（PERM-025）", frozenset({A, O})),
    "entry_exit:read": ("entry_exit", "read", "读取入馆/出馆记录（PERM-027）", frozenset({O})),
    "system:backup": ("system", "backup", "数据备份与恢复（US-403）", frozenset({O})),
}  # fmt: skip


def roles_for(code: str) -> frozenset[R]:
    return PERMISSIONS[code][3]


def permissions_of(roles) -> set[str]:  # noqa: ANN001
    roles = set(roles)
    return {code for code, (*_, allowed) in PERMISSIONS.items() if allowed & roles}
