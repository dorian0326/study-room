"""未签到预约的自动释放；可由多个进程运行，写锁与状态条件保证去重。"""

import asyncio
import logging

from app.config import get_settings
from app.db import SessionLocal
from app.services.reservations import expire_due

logger = logging.getLogger(__name__)


def sweep() -> int:
    with SessionLocal() as session:
        return expire_due(session)


async def run(stop: asyncio.Event) -> None:
    interval = get_settings().reservation_sweep_interval_seconds
    while not stop.is_set():
        try:
            await asyncio.to_thread(sweep)
        except Exception:
            # 服务启动早于迁移、临时写锁等情况不会杀死循环；下一轮会补做。
            logger.exception("未签到预约自动释放失败，将在下一轮重试")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            pass
