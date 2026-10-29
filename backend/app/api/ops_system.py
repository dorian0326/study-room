"""运维：数据库备份与运行状态（#9，仅运维 system:backup / system_log:read）。"""

import os
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.db import transaction
from app.deps import SessionDep, require_permission
from app.metrics import METRICS, STARTED_AT
from app.models import AuthSession, User
from app.models.enums import AuditOpType
from app.services import audit
from app.services.backup import create_backup, list_backups
from app.timeutil import now

router = APIRouter(prefix="/ops", tags=["ops-system"])
Backup = Annotated[User, Depends(require_permission("system:backup"))]
Monitor = Annotated[User, Depends(require_permission("system_log:read"))]


def _info(p: Path) -> dict:
    st = p.stat()
    return {"name": p.name, "size_bytes": st.st_size, "created_at": st.st_mtime}


@router.get("/backups")
def backups(_: Backup) -> list[dict]:
    return [_info(p) for p in list_backups()]


@router.post("/backups", status_code=status.HTTP_201_CREATED)
def backup_now(user: Backup, session: SessionDep) -> dict:
    try:
        path = create_backup(session.get_bind())
    except RuntimeError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    with transaction(session):
        audit.record(
            session,
            operator=user,
            op_type=AuditOpType.ADMIN_ACTION,
            target_type="backup",
            target_id=path.name,
        )
    return _info(path)


@router.get("/status")
def system_status(_: Monitor, session: SessionDep) -> dict:
    engine = session.get_bind()
    db = engine.url.database
    size = lambda p: os.path.getsize(p) if p and os.path.exists(p) else 0  # noqa: E731
    latest = list_backups()[:1]
    return {
        "uptime_seconds": int(time.time() - STARTED_AT),
        "database": {"size_bytes": size(db), "wal_bytes": size(f"{db}-wal") if db else 0},
        "users": session.scalar(select(func.count()).select_from(User)),
        "active_sessions": session.scalar(
            select(func.count())
            .select_from(AuthSession)
            .where(AuthSession.revoked_at.is_(None), AuthSession.expires_at > now())
        ),
        "latest_backup": _info(latest[0]) if latest else None,
        "requests": METRICS.snapshot(),
    }
