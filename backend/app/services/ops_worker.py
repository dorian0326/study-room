"""定时备份与日志清理后台任务（BR-105）。

interval 为 0 时不启动（测试默认）；生产可通过
STUDYROOM_BACKUP_INTERVAL_SECONDS / STUDYROOM_LOG_PURGE_INTERVAL_SECONDS 开启。
CLI（python -m app.cli backup / purge-logs）仍可用。
"""

import asyncio
import logging

from app.config import get_settings
from app.db import SessionLocal, engine
from app.services.backup import create_backup
from app.services.logs import purge_expired

logger = logging.getLogger(__name__)


def run_backup() -> str:
    path = create_backup(engine)
    return str(path)


def run_purge() -> dict[str, int]:
    with SessionLocal() as session:
        return purge_expired(session)


async def _loop(stop: asyncio.Event, interval: float, name: str, fn) -> None:
    while not stop.is_set():
        try:
            result = await asyncio.to_thread(fn)
            logger.info("%s 完成: %s", name, result)
        except Exception:
            logger.exception("%s 失败，将在下一轮重试", name)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            pass


async def run(stop: asyncio.Event) -> None:
    settings = get_settings()
    tasks = []
    if settings.backup_interval_seconds > 0:
        tasks.append(
            asyncio.create_task(
                _loop(stop, settings.backup_interval_seconds, "定时备份", run_backup)
            )
        )
    if settings.log_purge_interval_seconds > 0:
        tasks.append(
            asyncio.create_task(
                _loop(stop, settings.log_purge_interval_seconds, "日志清理", run_purge)
            )
        )
    if not tasks:
        await stop.wait()
        return
    await asyncio.gather(*tasks)
