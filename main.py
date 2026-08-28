from collections import defaultdict, deque
from math import ceil
from threading import Lock
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.admin import router as admin_router
from api.dashboard import router as dashboard_router
from api.expert import router as expert_router
from api.expert_detail import router as expert_detail_router
from api.hub import router as hub_router
from api.match import router as match_router
from api.order import router as order_router
from api.platform import router as platform_router
from api.portal import router as portal_router
from api.ranking import router as ranking_router
from api.result import router as result_router
from api.scpai import router as scpai_router
from api.settlement import router as settlement_router
from api.sync import router as sync_router
from api.user import router as user_router


class RequestTimingMiddleware:
    """Log bounded request timings without logging query strings or credentials."""

    def __init__(self, app, sample_size=256):
        self.app = app
        self.sample_size = sample_size
        self.samples = defaultdict(lambda: deque(maxlen=sample_size))
        self.lock = Lock()

    def _record(self, method, path, status, elapsed_ms):
        key = f"{method} {path}"
        with self.lock:
            values = self.samples[key]
            values.append(elapsed_ms)
            ordered = sorted(values)
            p95 = ordered[max(0, ceil(len(ordered) * 0.95) - 1)]
            average = sum(ordered) / len(ordered)
            maximum = ordered[-1]
            count = len(ordered)
        print(
            "[api-perf] method=%s path=%s status=%s elapsed_ms=%.2f "
            "calls=%d avg_ms=%.2f p95_ms=%.2f max_ms=%.2f"
            % (method, path, status, elapsed_ms, count, average, p95, maximum),
            flush=True,
        )

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "?")
        path = scope.get("path", "/")
        status = 500

        async def send_timed(message):
            nonlocal status
            if message.get("type") == "http.response.start":
                status = int(message.get("status", 500))
            await send(message)

        started = perf_counter()
        try:
            await self.app(scope, receive, send_timed)
        finally:
            self._record(method, path, status, (perf_counter() - started) * 1000)


app = FastAPI(title="足球 AI 数据系统", version="6.1")

app.add_middleware(RequestTimingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def index():
    return {"message": "足球 AI 数据系统运行正常", "version": "6.1"}


for router in (
    order_router,
    expert_router,
    match_router,
    expert_detail_router,
    dashboard_router,
    user_router,
    sync_router,
    result_router,
    settlement_router,
    ranking_router,
    platform_router,
    admin_router,
    hub_router,
    portal_router,
    scpai_router,
):
    app.include_router(router)
