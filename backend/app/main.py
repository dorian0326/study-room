import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin_config,
    admin_seats,
    admin_users,
    admin_violations,
    auth,
    gate,
    health,
    ops_logs,
    ops_system,
    reports,
    reservations,
)
from app.config import get_settings
from app.db import SessionLocal
from app.metrics import MetricsMiddleware
from app.services.reservations import sweep_reservations

logger = logging.getLogger(__name__)


def _run_reservation_sweep() -> None:
    """在独立数据库会话中执行一次预约超时、提醒和违规扫描。"""
    # 后台作业独立管理会话，异常回滚并关闭连接，不影响 API 请求事务。
    with SessionLocal() as session:
        sweep_reservations(session)


async def _reservation_worker() -> None:
    """每分钟处理预约生命周期事件，应用关闭时由 lifespan 取消任务。"""
    await asyncio.sleep(60)
    while True:
        try:
            # SQLAlchemy 同步会话放入线程池，避免阻塞 FastAPI 事件循环。
            await asyncio.to_thread(_run_reservation_sweep)
        except Exception:
            logger.exception("预约自动处理任务失败")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """管理预约后台任务的创建和关闭。"""
    # 首次扫描延后一分钟，避免测试或刚启动的迁移过程出现并发读写。
    task = asyncio.create_task(_reservation_worker())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    """组装 API 路由、中间件和预约自动任务。"""
    # Router 路径统一由 /api 前缀暴露，后台 worker 随应用生命周期启动。
    app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(admin_users.router, prefix="/api")
    app.include_router(admin_config.router, prefix="/api")
    app.include_router(ops_logs.router, prefix="/api")
    app.include_router(ops_system.router, prefix="/api")
    app.include_router(reservations.router, prefix="/api")
    app.include_router(gate.router, prefix="/api")
    app.include_router(admin_seats.router, prefix="/api")
    app.include_router(admin_violations.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    return app


app = create_app()
