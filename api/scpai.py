import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from service.scpai.adapter import ScpaiAdapterError, ScpaiNotFoundError, ScpaiPublicAdapter


router = APIRouter(prefix="/api/matches", tags=["public-match-data"])
_adapter = None
_scpai_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="scpai-api")
_scpai_slots = asyncio.Semaphore(8)


def get_adapter():
    global _adapter
    if _adapter is None:
        _adapter = ScpaiPublicAdapter()
    return _adapter


async def _run_adapter(method_name, *args):
    method = getattr(get_adapter(), method_name)
    loop = asyncio.get_running_loop()
    async with _scpai_slots:
        return await loop.run_in_executor(_scpai_executor, partial(method, *args))


def _error_response(exc):
    status_code = 404 if isinstance(exc, ScpaiNotFoundError) else 503
    return JSONResponse(status_code=status_code, content={"code": status_code, "msg": str(exc), "data": {}})


@router.get("")
async def list_matches():
    try:
        return {"code": 200, "data": await _run_adapter("get_matches")}
    except ScpaiAdapterError as exc:
        return _error_response(exc)


@router.get("/{external_id}/context")
async def match_context(external_id: str):
    try:
        return {"code": 200, "data": await _run_adapter("get_match_context", external_id)}
    except ScpaiAdapterError as exc:
        return _error_response(exc)


@router.get("/{external_id}/news")
async def match_news(external_id: str):
    try:
        return {"code": 200, "data": await _run_adapter("get_match_news", external_id)}
    except ScpaiAdapterError as exc:
        return _error_response(exc)


@router.get("/{external_id}")
async def match_detail(external_id: str):
    try:
        return {"code": 200, "data": await _run_adapter("get_match_detail", external_id)}
    except ScpaiAdapterError as exc:
        return _error_response(exc)
