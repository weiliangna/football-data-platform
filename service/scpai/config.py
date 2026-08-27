import os
from dataclasses import dataclass
from urllib.parse import urlparse


def _boolean(value, default=False):
    text = str(value or "").strip().lower()
    if not text:
        return default
    return text in {"1", "true", "yes", "on"}


def _integer(value, default, minimum=1, maximum=3600):
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _number(value, default, minimum=0.1, maximum=60.0):
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


@dataclass(frozen=True)
class ScpaiSettings:
    base_url: str
    enabled: bool
    dashboard_cache_seconds: int
    context_cache_seconds: int
    news_cache_seconds: int
    connect_timeout: float
    request_timeout: float


def load_settings(environment=None):
    values = os.environ if environment is None else environment
    base_url = str(values.get("SCPAI_BASE_URL") or "https://scpai.top").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("SCPAI_BASE_URL 必须是有效的 HTTP(S) 地址")
    return ScpaiSettings(
        base_url=base_url,
        enabled=_boolean(values.get("SCPAI_ENABLED"), True),
        dashboard_cache_seconds=_integer(values.get("SCPAI_DASHBOARD_CACHE_SECONDS"), 15),
        context_cache_seconds=_integer(values.get("SCPAI_CONTEXT_CACHE_SECONDS"), 300),
        news_cache_seconds=_integer(values.get("SCPAI_NEWS_CACHE_SECONDS"), 300),
        connect_timeout=_number(values.get("SCPAI_CONNECT_TIMEOUT"), 5),
        request_timeout=_number(values.get("SCPAI_REQUEST_TIMEOUT"), 10),
    )
