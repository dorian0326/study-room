"""FastAPI 应用入口：路由、中间件、预约扫尾与业务异常处理。"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from app.metrics import MetricsMiddleware
from app.services.availability import BookingError
from app.services.reservations import sweep_reservations
from app.db import SessionLocal

logger = logging.getLogger(__name__)


def _run_full_sweep() -> None:
    """跑完整预约扫尾（超窗、暂离超时、提醒）；#33 与 #34 能力合并。"""
    with SessionLocal() as session:
        sweep_reservations(session)


async def _legacy_interval_worker(interval: float) -> None:
    """按配置间隔执行扫尾；关闭时由 lifespan 取消。"""
    await asyncio.sleep(min(interval, 60.0))
    while True:
        try:
            await asyncio.to_thread(_run_full_sweep)
        except Exception:
            logger.exception("预约自动处理任务失败")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """管理预约后台任务：interval>0 时启动；测试可设为 0 关闭。"""
    settings = get_settings()
    task = None
    stop = asyncio.Event()
    if settings.reservation_sweep_interval_seconds > 0:
        # 优先用完整 sweep；若仅需 expire_due 也可走 reservation_worker。
        task = asyncio.create_task(
            _legacy_interval_worker(settings.reservation_sweep_interval_seconds)
        )
    try:
        yield
    finally:
        stop.set()
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


def create_app() -> FastAPI:
    """组装 API 路由、中间件、BookingError 映射与预约自动任务。"""
    app = FastAPI(title=get_settings().app_name, lifespan=lifespan)

    @app.exception_handler(BookingError)
    async def booking_error(_: Request, exc: BookingError):
        headers = {"Retry-After": "1"} if exc.status_code == 503 else None
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message}, headers=headers
        )

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
