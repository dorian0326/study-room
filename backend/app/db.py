"""SQLite 引擎与会话。每个连接启用外键约束、WAL 模式与 busy_timeout。"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def _ensure_sqlite_dir(url: str) -> None:
    prefix = "sqlite:///"
    if url.startswith(prefix) and ":memory:" not in url:
        Path(url[len(prefix) :]).parent.mkdir(parents=True, exist_ok=True)


def make_engine(url: str | None = None) -> Engine:
    settings = get_settings()
    url = url or settings.database_url
    _ensure_sqlite_dir(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record) -> None:  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute(f"PRAGMA busy_timeout={int(settings.sqlite_busy_timeout_ms)}")
        cur.close()

    return engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI 依赖：请求结束时关闭会话。"""
    with SessionLocal() as session:
        yield session
