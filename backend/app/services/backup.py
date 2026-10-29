"""SQLite 在线备份与恢复（#9，NFR 可恢复性）。

备份用 sqlite3 的 online backup API，服务运行中、WAL 模式下也能拿到一致快照。
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import Engine

from app.config import get_settings

PREFIX = "study_room-"


def backup_dir() -> Path:
    d = Path(get_settings().backup_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _db_path(engine: Engine) -> Path:
    db = engine.url.database
    if engine.url.get_backend_name() != "sqlite" or not db or db == ":memory:":
        raise RuntimeError("仅支持文件型 SQLite 数据库备份")
    return Path(db)


def create_backup(engine: Engine) -> Path:
    keep = get_settings().backup_keep
    name = f"{PREFIX}{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.db"
    target = backup_dir() / name
    src = engine.raw_connection()
    try:
        dst = sqlite3.connect(target)
        try:
            src.driver_connection.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    for old in list_backups()[keep:]:
        old.unlink(missing_ok=True)
    return target


def list_backups() -> list[Path]:
    """新到旧。"""
    return sorted(backup_dir().glob(f"{PREFIX}*.db"), reverse=True)


def restore_backup(engine: Engine, name: str) -> Path:
    """用备份覆盖当前库。只应在服务停止时通过 CLI 调用。"""
    src_path = backup_dir() / Path(name).name
    if not src_path.is_file():
        raise FileNotFoundError(name)
    check = sqlite3.connect(src_path)
    try:
        if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("备份文件校验失败")
    finally:
        check.close()
    _db_path(engine)
    engine.dispose()
    src = sqlite3.connect(src_path)
    dst = engine.raw_connection()
    try:
        src.backup(dst.driver_connection)
    finally:
        dst.close()
        src.close()
    return src_path
