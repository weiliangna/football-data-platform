import asyncio
import time
import unittest
from unittest.mock import patch

import api.portal as portal


class RecordingCursor:
    def __init__(self):
        self.statements = []

    def execute(self, statement, params=()):
        self.statements.append((statement, tuple(params)))

    def fetchall(self):
        return [{
            "id": 10,
            "order_id": 1,
            "platform_id": 1,
            "match_date": None,
            "match_key": "home|away",
            "match_code": "001",
            "match_name": "主队 VS 客队",
            "league": "测试联赛",
            "play_type": "胜平负",
            "selection": "主胜",
            "option_detail": "[]",
            "handicap": 0,
            "deadline_time": None,
            "bet_result": "待开奖",
        }]


class HotPlayQueryTests(unittest.TestCase):
    def test_hot_play_loader_does_not_join_settlement_results(self):
        cursor = RecordingCursor()
        with patch.object(portal, "table_columns", return_value={
            "id",
            "order_id",
            "match_key",
            "match_code",
            "match_name",
            "league",
            "play_type",
            "selection",
            "option_detail",
            "handicap",
            "deadline_time",
            "result",
        }):
            grouped = portal.load_hot_play_matches(cursor, [1])

        sql = "\n".join(statement for statement, _params in cursor.statements)
        self.assertIn("FROM order_matches", sql)
        self.assertNotIn("match_results", sql)
        self.assertEqual(grouped[1][0]["match_code"], "001")

    def test_hot_play_loader_chunks_large_order_sets(self):
        cursor = RecordingCursor()
        with patch.object(portal, "table_columns", return_value=set()):
            portal.load_hot_play_matches(cursor, list(range(1, 2002)))
        self.assertEqual(len(cursor.statements), 3)
        self.assertEqual(len(cursor.statements[0][1]), 1000)
        self.assertEqual(len(cursor.statements[-1][1]), 1)


class DashboardIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        portal._dashboard_cache["data"] = None
        portal._dashboard_cache["created_at"] = 0.0
        portal._dashboard_refresh_task = None

    async def asyncTearDown(self):
        task = portal._dashboard_refresh_task
        if task is not None and not task.done():
            await task
        portal._dashboard_refresh_task = None
        portal._dashboard_cache["data"] = None
        portal._dashboard_cache["created_at"] = 0.0

    async def test_concurrent_requests_share_one_dashboard_build(self):
        calls = 0

        def build():
            nonlocal calls
            calls += 1
            time.sleep(0.02)
            return {"code": 200, "data": {"value": calls}}

        with patch.object(portal, "build_dashboard_response", side_effect=build):
            results = await asyncio.gather(*[
                portal.dashboard()
                for _ in range(10)
            ])

        self.assertEqual(calls, 1)
        self.assertTrue(all(item["code"] == 200 for item in results))

    async def test_fresh_cache_avoids_database_work(self):
        portal._dashboard_cache["data"] = {"code": 200, "data": {"cached": True}}
        portal._dashboard_cache["created_at"] = portal.monotonic()

        with patch.object(portal, "build_dashboard_response") as build:
            result = await portal.dashboard()

        self.assertTrue(result["data"]["cached"])
        build.assert_not_called()

    async def test_stale_cache_returns_while_refresh_runs(self):
        portal._dashboard_cache["data"] = {"code": 200, "data": {"stale": True}}
        portal._dashboard_cache["created_at"] = (
            portal.monotonic() - portal.DASHBOARD_CACHE_SECONDS - 1
        )

        def build():
            time.sleep(0.02)
            return {"code": 200, "data": {"stale": False}}

        with patch.object(portal, "build_dashboard_response", side_effect=build):
            result = await portal.dashboard()
            await portal._dashboard_refresh_task

        self.assertTrue(result["data"]["stale"])
        self.assertFalse(portal._dashboard_cache["data"]["data"]["stale"])


if __name__ == "__main__":
    unittest.main()
