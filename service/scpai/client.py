import logging
import time
from dataclasses import dataclass
from datetime import datetime

import requests


LOGGER = logging.getLogger("football.scpai")
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
ALLOWED_ENDPOINTS = {
    "dashboard": "/api/dashboard",
    "context": "/api/context",
    "news": "/api/news",
}


class ScpaiClientError(RuntimeError):
    pass


@dataclass
class ClientResponse:
    status_code: int
    data: dict
    etag: str = ""


class ScpaiPublicClient:
    def __init__(self, settings, session=None, sleeper=None, max_attempts=2):
        self.settings = settings
        if session is None:
            session = requests.Session()
            session.trust_env = False
        self.session = session
        self.sleeper = sleeper or time.sleep
        self.max_attempts = max(1, min(int(max_attempts), 3))

    def _get(self, endpoint, match_id=None, etag=""):
        if endpoint not in ALLOWED_ENDPOINTS:
            raise ScpaiClientError("Scpai endpoint is not allowed")
        params = {"match": match_id} if match_id else None
        headers = {"Accept": "application/json"}
        if endpoint == "dashboard" and etag:
            headers["If-None-Match"] = etag
        started = time.monotonic()
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.session.get(
                    self.settings.base_url + ALLOWED_ENDPOINTS[endpoint],
                    params=params,
                    headers=headers,
                    timeout=(self.settings.connect_timeout, self.settings.request_timeout),
                    allow_redirects=False,
                )
                duration = round((time.monotonic() - started) * 1000)
                LOGGER.info(
                    "scpai_request endpoint=%s matchId=%s status=%s durationMs=%s fetchedAt=%s",
                    endpoint,
                    match_id or "",
                    response.status_code,
                    duration,
                    datetime.now().isoformat(timespec="seconds"),
                )
                if response.status_code == 304 and endpoint == "dashboard":
                    return ClientResponse(304, {}, etag)
                if response.status_code in RETRYABLE_STATUS:
                    last_error = ScpaiClientError(f"Scpai temporary HTTP status {response.status_code}")
                    if attempt < self.max_attempts:
                        self.sleeper(min(0.2 * attempt, 0.5))
                        continue
                    raise last_error
                if response.status_code != 200:
                    raise ScpaiClientError(f"Scpai HTTP status {response.status_code}")
                try:
                    data = response.json()
                except (TypeError, ValueError) as exc:
                    raise ScpaiClientError("Scpai returned invalid JSON") from exc
                if not isinstance(data, dict):
                    raise ScpaiClientError("Scpai JSON root must be an object")
                return ClientResponse(200, data, str(response.headers.get("ETag") or ""))
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = ScpaiClientError("Scpai network request failed")
                if attempt < self.max_attempts:
                    self.sleeper(min(0.2 * attempt, 0.5))
                    continue
                raise last_error from exc
        raise last_error or ScpaiClientError("Scpai request failed")

    def get_dashboard(self, match_id=None, etag=""):
        return self._get("dashboard", match_id=match_id, etag=etag)

    def get_context(self, match_id):
        return self._get("context", match_id=match_id)

    def get_news(self, match_id):
        return self._get("news", match_id=match_id)
