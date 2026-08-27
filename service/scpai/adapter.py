import logging
import re
from concurrent.futures import ThreadPoolExecutor

from service.scpai.cache import MemoryTtlCache
from service.scpai.client import ScpaiClientError, ScpaiPublicClient
from service.scpai.config import load_settings
from service.scpai.mapper import map_context, map_dashboard, map_news


LOGGER = logging.getLogger("football.scpai")
MATCH_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+$")


class ScpaiAdapterError(RuntimeError):
    pass


class ScpaiNotFoundError(ScpaiAdapterError):
    pass


class ScpaiPublicAdapter:
    def __init__(self, settings=None, client=None, cache=None):
        self.settings = settings or load_settings()
        self.client = client or ScpaiPublicClient(self.settings)
        self.cache = cache or MemoryTtlCache()

    def _log_cache(self, endpoint, match_id, status):
        LOGGER.info(
            "scpai_cache endpoint=%s matchId=%s cacheStatus=%s",
            endpoint,
            match_id or "",
            status,
        )

    def _fetch(self, endpoint, match_id, ttl, loader, mapper, etag_enabled=False):
        key = f"{endpoint}:{match_id or '-'}"
        entry = self.cache.get(key)
        if entry and entry.fresh:
            self._log_cache(endpoint, match_id, "cached")
            return entry.data, "cached", entry.fetched_at.isoformat(timespec="seconds")

        with self.cache.lock_for(key):
            entry = self.cache.get(key)
            if entry and entry.fresh:
                self._log_cache(endpoint, match_id, "cached")
                return entry.data, "cached", entry.fetched_at.isoformat(timespec="seconds")
            try:
                response = loader(entry.etag if entry and etag_enabled else "")
                if response.status_code == 304 and entry:
                    entry = self.cache.touch(key, ttl)
                    self._log_cache(endpoint, match_id, "cached")
                    return entry.data, "cached", entry.fetched_at.isoformat(timespec="seconds")
                mapped = mapper(response.data)
                entry = self.cache.set(key, mapped, ttl, response.etag)
                self._log_cache(endpoint, match_id, "fresh")
                return mapped, "fresh", entry.fetched_at.isoformat(timespec="seconds")
            except ScpaiClientError:
                if entry:
                    self._log_cache(endpoint, match_id, "stale")
                    return entry.data, "stale", entry.fetched_at.isoformat(timespec="seconds")
                self._log_cache(endpoint, match_id, "unavailable")
                return None, "unavailable", ""

    def _dashboard(self, match_id=None):
        return self._fetch(
            "dashboard",
            match_id,
            self.settings.dashboard_cache_seconds,
            lambda etag: self.client.get_dashboard(match_id, etag),
            map_dashboard,
            etag_enabled=True,
        )

    def _context(self, match_id):
        return self._fetch(
            "context",
            match_id,
            self.settings.context_cache_seconds,
            lambda _etag: self.client.get_context(match_id),
            map_context,
        )

    def _news(self, match_id):
        return self._fetch(
            "news",
            match_id,
            self.settings.news_cache_seconds,
            lambda _etag: self.client.get_news(match_id),
            map_news,
        )

    def _validate_available_match(self, external_id):
        external_id = str(external_id or "")
        if not MATCH_ID_PATTERN.fullmatch(external_id):
            raise ScpaiNotFoundError("比赛不存在")
        dashboard, status, _ = self._dashboard()
        if dashboard is None:
            raise ScpaiAdapterError("公开比赛数据暂时不可用")
        allowed = {item.get("externalId") for item in dashboard.get("matches", [])}
        if external_id not in allowed:
            raise ScpaiNotFoundError("比赛不存在")
        return status

    def get_matches(self):
        if not self.settings.enabled:
            return {
                "matches": [],
                "updatedAt": "",
                "status": "unavailable",
                "message": "赛事数据源尚未启用",
            }
        dashboard, status, fetched_at = self._dashboard()
        if dashboard is None:
            return {
                "matches": [],
                "updatedAt": "",
                "status": "unavailable",
                "message": "赛事数据暂时不可用",
            }
        return {
            "matches": dashboard.get("matches", []),
            "summary": dashboard.get("summary", {}),
            "updatedAt": dashboard.get("updatedAt") or fetched_at,
            "status": status,
        }

    def get_match_detail(self, external_id):
        if not self.settings.enabled:
            raise ScpaiAdapterError("赛事数据源尚未启用")
        self._validate_available_match(external_id)
        with ThreadPoolExecutor(max_workers=2) as executor:
            dashboard_future = executor.submit(self._dashboard, external_id)
            context_future = executor.submit(self._context, external_id)
            dashboard, dashboard_status, dashboard_at = dashboard_future.result()
            context, context_status, context_at = context_future.result()
        if dashboard is None and context is None:
            raise ScpaiAdapterError("比赛详情暂时不可用")
        dashboard = dashboard or {}
        return {
            "match": dashboard.get("match") or (context or {}).get("match"),
            "markets": dashboard.get("markets", []),
            "context": context or {},
            "favoriteIndex": dashboard.get("favoriteIndex"),
            "updatedAt": dashboard.get("updatedAt") or context_at or dashboard_at,
            "status": self._combined_status(dashboard_status, context_status),
        }

    def get_match_news(self, external_id):
        if not self.settings.enabled:
            raise ScpaiAdapterError("赛事数据源尚未启用")
        self._validate_available_match(external_id)
        news, status, fetched_at = self._news(external_id)
        if news is None:
            raise ScpaiAdapterError("比赛新闻暂时不可用")
        return {**news, "updatedAt": news.get("generatedAt") or fetched_at, "status": status}

    @staticmethod
    def _combined_status(*statuses):
        if "stale" in statuses:
            return "stale"
        if "unavailable" in statuses:
            return "cached" if "cached" in statuses or "fresh" in statuses else "unavailable"
        if "fresh" in statuses:
            return "fresh"
        return "cached"
