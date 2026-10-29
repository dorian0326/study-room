from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin_config, admin_users, auth, health, ops_logs
from app.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name)
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
    return app


app = create_app()
