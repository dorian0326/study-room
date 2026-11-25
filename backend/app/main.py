"""FastAPI 应用入口：路由、中间件、预约扫尾与业务异常处理。"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
from app.services import ops_worker, reservation_worker
from app.services.availability import BookingError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """管理预约扫尾、备份与日志清理后台任务；interval=0 时不启动（测试默认）。"""
    settings = get_settings()
    stop = asyncio.Event()
    tasks = []
    if settings.reservation_sweep_interval_seconds > 0:
        tasks.append(asyncio.create_task(reservation_worker.run(stop)))
    if settings.backup_interval_seconds > 0 or settings.log_purge_interval_seconds > 0:
        tasks.append(asyncio.create_task(ops_worker.run(stop)))
    try:
        yield
    finally:
        stop.set()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


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
    # Optional built SPA: all API routes are registered first, no /api fallback.
    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.is_dir() and (dist / "index.html").is_file():
        if (dist / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path == "api" or path.startswith("api/"):
                raise HTTPException(404, "接口不存在")
            candidate = (dist / path).resolve()
            if not candidate.is_relative_to(dist.resolve()):
                raise HTTPException(404, "文件不存在")
            if candidate.is_file():
                return FileResponse(candidate)
            if Path(path).suffix:
                raise HTTPException(404, "文件不存在")
            return FileResponse(dist / "index.html")

    return app


app = create_app()
