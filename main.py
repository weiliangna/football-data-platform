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


app = FastAPI(title="足球 AI 数据系统", version="6.1")

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
