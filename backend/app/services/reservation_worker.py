"""未签到预约的自动释放；可由多个进程运行，写锁与状态条件保证去重。"""

import asyncio
import logging

from app.config import get_settings
from app.db import SessionLocal
from app.services.reservations import expire_due, sweep_reservations

logger = logging.getLogger(__name__)


def sweep() -> int:
    """兼容 #34 测试：执行 expire_due，返回失效条数。"""
    with SessionLocal() as session:
        return expire_due(session)


def full_sweep() -> dict[str, int]:
    """完整扫尾（超窗、暂离超时、提醒）。"""
    with SessionLocal() as session:
        return sweep_reservations(session)


async def run(stop: asyncio.Event) -> None:
    interval = get_settings().reservation_sweep_interval_seconds
    while not stop.is_set():
        try:
            await asyncio.to_thread(full_sweep)
        except Exception:
            # 服务启动早于迁移、临时写锁等情况不会杀死循环；下一轮会补做。
            logger.exception("预约自动处理失败，将在下一轮重试")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            pass
