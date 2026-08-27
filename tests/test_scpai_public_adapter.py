import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import requests

from service.scpai.adapter import ScpaiNotFoundError, ScpaiPublicAdapter
from service.scpai.client import ScpaiPublicClient
from service.scpai.config import ScpaiSettings
from service.scpai.mapper import map_context, map_news, normalize_market_series


MATCH_ID = "sporttery:2041077"


def dashboard_payload(selected=False):
    match = {
        "id": MATCH_ID,
        "code": "周四001",
        "competition": "公开赛事",
        "kickoffAt": "2026-08-27T19:30:00+08:00",
        "home": "主队",
        "away": "客队",
        "marketCount": 5,
    }
    return {
        "queue": [match],
        "selectedMatch": match if selected else None,
        "series": [
            {
                "id": "win",
                "name": "胜平负",
                "selection": "主胜",
                "labels": ["10:00", "10:15"],
                "values": [2.1, 2.05],
            }
        ] if selected else [],
        "summary": {"matches": 1, "markets": 5},
        "updatedAt": "2026-08-27T10:00:00+08:00",
    }


def context_payload(absences=None):
    return {
        "match": {"id": MATCH_ID, "home": "主队", "away": "客队"},
        "home": {"team": "主队", "position": 1},
        "away": {"team": "客队", "position": None, "league": ""},
        "absences": [] if absences is None else absences,
        "absenceStatus": "verified-empty" if not absences else "synced",
    }


class FakeResponse:
    def __init__(self, status_code=200, data=None, headers=None):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.headers = headers or {}

    def json(self):
        return self._data


class EndpointSession:
    def __init__(self, responses, delay=0):
        self.responses = {key: list(value) for key, value in responses.items()}
        self.delay = delay
        self.calls = []
        self.lock = threading.Lock()

    def get(self, url, **kwargs):
        if self.delay:
            time.sleep(self.delay)
        endpoint = next(key for key in self.responses if url.endswith(key))
        with self.lock:
            self.calls.append((endpoint, kwargs))
            result = self.responses[endpoint].pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def settings():
    return ScpaiSettings(
        base_url="https://example.invalid",
        enabled=True,
        dashboard_cache_seconds=15,
        context_cache_seconds=300,
        news_cache_seconds=300,
        connect_timeout=1,
        request_timeout=1,
    )


class ScpaiPublicAdapterTests(unittest.TestCase):
    def make_adapter(self, responses, delay=0):
        session = EndpointSession(responses, delay=delay)
        client = ScpaiPublicClient(settings(), session=session, sleeper=lambda _x: None)
        return ScpaiPublicAdapter(settings(), client=client), session

    def test_dashboard_200_and_cache_hit(self):
        adapter, session = self.make_adapter(
            {"/api/dashboard": [FakeResponse(200, dashboard_payload(), {"ETag": "v1"})]}
        )
        first = adapter.get_matches()
        second = adapter.get_matches()
        self.assertEqual(first["status"], "fresh")
        self.assertEqual(second["status"], "cached")
        self.assertEqual(first["matches"][0]["externalId"], MATCH_ID)
        self.assertEqual(len(session.calls), 1)

    def test_dashboard_304_reuses_cached_data(self):
        adapter, session = self.make_adapter(
            {"/api/dashboard": [FakeResponse(200, dashboard_payload(), {"ETag": "v1"}), FakeResponse(304)]}
        )
        adapter.get_matches()
        adapter.cache.get("dashboard:-").expires_at = datetime.now() - timedelta(seconds=1)
        result = adapter.get_matches()
        self.assertEqual(result["status"], "cached")
        self.assertEqual(result["matches"][0]["externalId"], MATCH_ID)
        self.assertEqual(session.calls[1][1]["headers"]["If-None-Match"], "v1")

    def test_context_empty_absences_is_valid(self):
        mapped = map_context(context_payload())
        self.assertEqual(mapped["absences"], [])
        self.assertEqual(mapped["absenceStatus"], "verified-empty")

    def test_context_with_absences(self):
        mapped = map_context(context_payload([{"player": "球员甲", "reason": "伤病"}]))
        self.assertEqual(mapped["absences"][0]["player"], "球员甲")
        self.assertEqual(mapped["absenceStatus"], "synced")

    def test_news_empty_and_dynamic_categories(self):
        self.assertEqual(map_news({"items": []})["categories"], [])
        mapped = map_news({"items": [{"category": "官方消息"}, {"category": "国际资讯"}, {"category": "官方消息"}]})
        self.assertEqual(mapped["categories"], ["国际资讯", "官方消息"])

    def test_unknown_market_is_preserved(self):
        mapped = normalize_market_series({"id": "future-market", "name": "未来盘口"})
        self.assertEqual(mapped["type"], "UNKNOWN")
        self.assertEqual(mapped["rawMarketId"], "future-market")
        self.assertEqual(mapped["rawMarketName"], "未来盘口")

    def test_timeout_is_retried(self):
        adapter, session = self.make_adapter(
            {"/api/dashboard": [requests.Timeout(), FakeResponse(200, dashboard_payload())]}
        )
        self.assertEqual(adapter.get_matches()["status"], "fresh")
        self.assertEqual(len(session.calls), 2)

    def test_429_and_500_are_retried(self):
        for status_code in (429, 500):
            with self.subTest(status_code=status_code):
                adapter, session = self.make_adapter(
                    {"/api/dashboard": [FakeResponse(status_code), FakeResponse(200, dashboard_payload())]}
                )
                self.assertEqual(adapter.get_matches()["matches"][0]["externalId"], MATCH_ID)
                self.assertEqual(len(session.calls), 2)

    def test_single_flight_coalesces_concurrent_dashboard_calls(self):
        adapter, session = self.make_adapter(
            {"/api/dashboard": [FakeResponse(200, dashboard_payload())]}, delay=0.03
        )
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda _index: adapter.get_matches(), range(10)))
        self.assertTrue(all(result["matches"] for result in results))
        self.assertEqual(len(session.calls), 1)

    def test_detail_and_context_are_independent(self):
        adapter, _session = self.make_adapter(
            {
                "/api/dashboard": [FakeResponse(200, dashboard_payload()), FakeResponse(200, dashboard_payload(selected=True))],
                "/api/context": [FakeResponse(200, context_payload())],
            }
        )
        result = adapter.get_match_detail(MATCH_ID)
        self.assertEqual(result["match"]["externalId"], MATCH_ID)
        self.assertEqual(result["markets"][0]["type"], "WIN_DRAW_LOSS")
        self.assertNotIn("context", result)
        context = adapter.get_match_context(MATCH_ID)
        self.assertEqual(context["absences"], [])

    def test_match_id_must_come_from_dashboard_queue(self):
        adapter, _session = self.make_adapter(
            {"/api/dashboard": [FakeResponse(200, dashboard_payload())]}
        )
        with self.assertRaises(ScpaiNotFoundError):
            adapter.get_match_news("sporttery:9999999")
        with self.assertRaises(ScpaiNotFoundError):
            adapter.get_match_news("https://example.com")

    def test_frontend_navigation_and_external_link_safety(self):
        with open("frontend/src/components/layout/AppSidebar.vue", encoding="utf-8") as handle:
            sidebar = handle.read()
        with open("frontend/src/views/ScpaiNews.vue", encoding="utf-8") as handle:
            news_page = handle.read()
        expected = ["今日总览", "方案大厅", "赛事分析", "赛事数据", "投注热力", "赛果统计", "用户中心"]
        positions = [sidebar.index(name) for name in expected]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("水位看板", sidebar)
        self.assertIn("比赛新闻", sidebar)
        self.assertIn('rel="noopener noreferrer"', news_page)

    def test_scpai_routes_are_lazy_and_do_not_change_global_axios(self):
        with open("frontend/src/router/index.js", encoding="utf-8") as handle:
            router = handle.read()
        with open("frontend/src/views/ScpaiMatches.vue", encoding="utf-8") as handle:
            dashboard = handle.read()
        with open("frontend/src/views/ScpaiNews.vue", encoding="utf-8") as handle:
            news = handle.read()
        self.assertIn('() => import("../views/ScpaiMatches.vue")', router)
        self.assertNotIn('import * as echarts', dashboard)
        self.assertNotIn("axios.defaults", router + dashboard + news)
        self.assertNotIn("https://scpai.top", dashboard + news)

    def test_scpai_pages_refresh_locally_every_30_seconds(self):
        for path in (
            "frontend/src/views/ScpaiMatches.vue",
            "frontend/src/views/ScpaiNews.vue",
        ):
            with self.subTest(path=path), open(path, encoding="utf-8") as handle:
                source = handle.read()
                self.assertIn("REFRESH_MS=30000", source)
                self.assertIn("setInterval", source)
                self.assertIn("clearInterval", source)

    def test_backend_uses_a_dedicated_bounded_executor(self):
        with open("api/scpai.py", encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("ThreadPoolExecutor(max_workers=4", source)
        self.assertIn("run_in_executor(_scpai_executor", source)
        self.assertIn("async def list_matches", source)

    def test_public_dashboard_information_hierarchy_is_preserved(self):
        with open("frontend/src/views/ScpaiMatches.vue", encoding="utf-8") as handle:
            source = handle.read()
        for contract in (
            "scpai-report-head",
            "scpai-summary-grid",
            "scpai-focus-grid",
            "scpai-workspace-grid",
            "scpai-match-panel",
            "scpai-detail-panel",
            "scpai-market-grid",
            "scpai-priority-panel",
        ):
            self.assertIn(contract, source)
        self.assertIn("loadContext", source)
        self.assertNotIn("loadNews", source)

    def test_contact_and_provider_brand_are_not_rendered(self):
        for path in (
            "frontend/src/views/ScpaiMatches.vue",
            "frontend/src/views/ScpaiNews.vue",
        ):
            with self.subTest(path=path), open(path, encoding="utf-8") as handle:
                template = handle.read().split("<script", 1)[0]
                self.assertNotIn("联系方式", template)
                self.assertNotIn("数据来源", template)
                self.assertNotIn("scpai.top", template.lower())

    def test_existing_auto_refresh_pages_do_not_overlap_requests(self):
        for path in (
            "frontend/src/views/Home.vue",
            "frontend/src/views/Heatmap.vue",
        ):
            with self.subTest(path=path), open(path, encoding="utf-8") as handle:
                source = handle.read()
                self.assertIn("requestInFlight", source)
                self.assertIn("timeout: 25000", source)


if __name__ == "__main__":
    unittest.main()
