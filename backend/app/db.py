"""SQLite 引擎与会话。每个连接启用外键约束、WAL 模式与 busy_timeout。"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings


def _ensure_sqlite_dir(url: str) -> None:
    prefix = "sqlite:///"
    if url.startswith(prefix) and ":memory:" not in url:
        Path(url[len(prefix) :]).parent.mkdir(parents=True, exist_ok=True)


def make_engine(url: str | None = None) -> Engine:
    settings = get_settings()
    url = url or settings.database_url
    _ensure_sqlite_dir(url)
    # Requests may retain an authentication session while opening a write session.
    # A small bounded pool can deadlock those nested acquisitions under HTTP load.
    # SQLite connections are cheap; do not hold a scarce pool slot across layers.
    engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=NullPool)
    # 关闭 pysqlite 的隐式事务处理，由下面的 begin 事件统一发 BEGIN，
    # 这样 transaction(immediate=True) 才能用 BEGIN IMMEDIATE 拿写锁

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record) -> None:  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute(f"PRAGMA busy_timeout={int(settings.sqlite_busy_timeout_ms)}")
        cur.close()
        dbapi_conn.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin(conn) -> None:  # noqa: ANN001
        conn.exec_driver_sql(conn.get_execution_options().get("sqlite_begin", "BEGIN"))

    return engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI 依赖：请求结束时关闭会话。"""
    with SessionLocal() as session:
        yield session


@contextmanager
def transaction(session: Session, *, immediate: bool = False) -> Iterator[Session]:
    """事务边界（FR-083 数据回滚）：块内任何异常都会整体回滚并重新抛出。

    immediate=True 时以 BEGIN IMMEDIATE 开始，提前拿到 SQLite 写锁，
    用于“先查冲突再写入”的场景（如创建预约），避免并发写入时的检查-写入竞态。
    非 immediate 时允许接续此前查询自动开启的（只读）事务。
    """
    if immediate:
        if session.in_transaction():
            raise RuntimeError("会话中已有未结束的事务，无法以 BEGIN IMMEDIATE 开始")
        session.connection(execution_options={"sqlite_begin": "BEGIN IMMEDIATE"})
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
