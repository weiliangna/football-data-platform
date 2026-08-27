from fastapi import APIRouter
from fastapi.responses import JSONResponse

from service.scpai.adapter import (
    ScpaiAdapterError,
    ScpaiNotFoundError,
    ScpaiPublicAdapter,
)


router = APIRouter(prefix="/api/matches", tags=["public-match-data"])
_adapter = None


def get_adapter():
    global _adapter
    if _adapter is None:
        _adapter = ScpaiPublicAdapter()
    return _adapter


def _error_response(exc):
    status_code = 404 if isinstance(exc, ScpaiNotFoundError) else 503
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "msg": str(exc), "data": {}},
    )


@router.get("")
def list_matches():
    try:
        return {"code": 200, "data": get_adapter().get_matches()}
    except ScpaiAdapterError as exc:
        return _error_response(exc)


@router.get("/{external_id}/news")
def match_news(external_id: str):
    try:
        return {"code": 200, "data": get_adapter().get_match_news(external_id)}
    except ScpaiAdapterError as exc:
        return _error_response(exc)


@router.get("/{external_id}")
def match_detail(external_id: str):
    try:
        return {"code": 200, "data": get_adapter().get_match_detail(external_id)}
    except ScpaiAdapterError as exc:
        return _error_response(exc)
