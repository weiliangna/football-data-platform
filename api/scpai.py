import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from time import monotonic

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from service.scpai.adapter import ScpaiAdapterError, ScpaiNotFoundError, ScpaiPublicAdapter
from common.snapshot_store import load_snapshot, save_snapshot


router = APIRouter(prefix="/api/matches", tags=["public-match-data"])
_adapter = None
_scpai_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="scpai-api")
_scpai_slots = asyncio.Semaphore(8)
_memory_snapshots = {}
_refresh_tasks = {}
_SNAPSHOT_TTL = 180.0


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


async def _read_snapshot(key):
    cached = _memory_snapshots.get(key)
    if cached and monotonic() - cached["created"] <= _SNAPSHOT_TTL:
        return cached["payload"], {
            "freshness": "fresh",
            "updated_at": cached["updated_at"],
            "age_seconds": round(monotonic() - cached["created"], 3),
            "refreshing": False,
        }
    try:
        payload, meta = await asyncio.wait_for(
            asyncio.to_thread(load_snapshot, key),
            timeout=0.25,
        )
    except asyncio.TimeoutError:
        return None, None
    if payload is not None:
        _memory_snapshots[key] = {
            "payload": payload,
            "created": monotonic(),
            "updated_at": (meta or {}).get("updated_at"),
        }
    return payload, meta


async def _store_snapshot(key, payload):
    _memory_snapshots[key] = {
        "payload": payload,
        "created": monotonic(),
        "updated_at": datetime.now().isoformat(),
    }
    await asyncio.to_thread(save_snapshot, key, payload, "fresh")


async def _refresh_snapshot(key, method_name, args):
    try:
        payload = await asyncio.wait_for(_run_adapter(method_name, *args), timeout=3.0)
        await _store_snapshot(key, payload)
    except Exception:
        pass
    finally:
        _refresh_tasks.pop(key, None)


async def _serve_with_snapshot(key, method_name, *args):
    snapshot, snapshot_meta = await _read_snapshot(key)
    if snapshot is not None:
        if key not in _refresh_tasks:
            _refresh_tasks[key] = asyncio.create_task(
                _refresh_snapshot(key, method_name, args)
            )
        return {
            "code": 200,
            "data": snapshot,
            "meta": {
                **(snapshot_meta or {}),
                "freshness": "stale",
                "refreshing": True,
            },
        }
    try:
        payload = await asyncio.wait_for(
            _run_adapter(method_name, *args),
            timeout=3.0,
        )
        await _store_snapshot(key, payload)
        return {
            "code": 200,
            "data": payload,
            "meta": {
                "freshness": "fresh",
                "updated_at": datetime.now().isoformat(),
                "age_seconds": 0.0,
                "refreshing": False,
            },
        }
    except (asyncio.TimeoutError, ScpaiAdapterError):
        if snapshot is not None:
            return {
                "code": 200,
                "data": snapshot,
                "meta": {
                    **(snapshot_meta or {}),
                    "freshness": "stale",
                    "refreshing": False,
                },
            }
        raise


def _error_response(exc):
    status_code = 404 if isinstance(exc, ScpaiNotFoundError) else 503
    return JSONResponse(status_code=status_code, content={"code": status_code, "msg": str(exc), "data": {}})


@router.get("")
async def list_matches():
    try:
        return await _serve_with_snapshot("matches:list", "get_matches")
    except ScpaiAdapterError as exc:
        return _error_response(exc)


@router.get("/{external_id}/context")
async def match_context(external_id: str):
    try:
        return await _serve_with_snapshot(
            f"match:{external_id}:context", "get_match_context", external_id
        )
    except ScpaiAdapterError as exc:
        return _error_response(exc)


@router.get("/{external_id}/news")
async def match_news(external_id: str):
    try:
        return await _serve_with_snapshot(
            f"match:{external_id}:news", "get_match_news", external_id
        )
    except ScpaiAdapterError as exc:
        return _error_response(exc)


@router.get("/{external_id}")
async def match_detail(external_id: str):
    try:
        return await _serve_with_snapshot(
            f"match:{external_id}:detail", "get_match_detail", external_id
        )
    except ScpaiAdapterError as exc:
        return _error_response(exc)
