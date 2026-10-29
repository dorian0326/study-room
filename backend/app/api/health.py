from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.timeutil import now

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: Annotated[Session, Depends(get_session)]) -> dict:
    session.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "sqlite",
        "timezone": get_settings().timezone,
        "server_time": now().isoformat(),
    }
