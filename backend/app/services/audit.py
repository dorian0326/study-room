"""操作日志写入（BR-105：管理动作、违规认定、权限变更均须留痕）。调用方负责事务。"""

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User
from app.models.enums import AuditOpType
from app.timeutil import now


def _dump(v: Any) -> str | None:
    return None if v is None else json.dumps(v, ensure_ascii=False, default=str)


def record(
    session: Session,
    *,
    operator: User | None,
    op_type: AuditOpType,
    target_type: str,
    target_id: Any = None,
    before: Any = None,
    after: Any = None,
    ip: str | None = None,
    result: str = "success",
) -> AuditLog:
    log = AuditLog(
        operator_id=operator.id if operator else None,
        op_type=op_type,
        target_type=target_type,
        target_id=None if target_id is None else str(target_id),
        occurred_at=now(),
        before_value=_dump(before),
        after_value=_dump(after),
        ip_address=ip,
        result=result,
    )
    session.add(log)
    return log
