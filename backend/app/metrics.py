"""进程内请求计数中间件（#9 运行监控）。多进程部署时各进程独立计数。"""

import time
from collections import Counter

from starlette.middleware.base import BaseHTTPMiddleware

STARTED_AT = time.time()


class Metrics:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.requests = 0
        self.by_status: Counter[str] = Counter()
        self.total_ms = 0.0
        self.max_ms = 0.0

    def snapshot(self) -> dict:
        return {
            "requests": self.requests,
            "by_status": dict(self.by_status),
            "avg_ms": round(self.total_ms / self.requests, 2) if self.requests else 0,
            "max_ms": round(self.max_ms, 2),
        }


METRICS = Metrics()


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):  # noqa: ANN001, ANN201
        start = time.perf_counter()
        status = 500
        try:
            resp = await call_next(request)
            status = resp.status_code
            return resp
        finally:
            ms = (time.perf_counter() - start) * 1000
            METRICS.requests += 1
            METRICS.by_status[f"{status // 100}xx"] += 1
            METRICS.total_ms += ms
            METRICS.max_ms = max(METRICS.max_ms, ms)
