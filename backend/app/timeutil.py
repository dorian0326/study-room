"""统一时间基准：Asia/Shanghai UTC+8（HD-39）。业务代码一律通过 now() 取时间。"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_settings


def tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def now() -> datetime:
    """返回带时区（Asia/Shanghai）的当前时间。"""
    return datetime.now(tz())
