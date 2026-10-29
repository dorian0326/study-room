import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin_config, admin_users, auth, health, ops_logs, ops_system, reservations
from app.config import get_settings
from app.metrics import MetricsMiddleware
from app.services import reservation_worker
from app.services.availability import BookingError


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = asyncio.Event()
    task = None
    if get_settings().reservation_sweep_interval_seconds > 0:
        task = asyncio.create_task(reservation_worker.run(stop))
    try:
        yield
    finally:
        stop.set()
        if task is not None:
            await task


def create_app() -> FastAPI:
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
    return app


app = create_app()
