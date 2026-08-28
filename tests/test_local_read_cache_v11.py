import asyncio
import unittest
from unittest.mock import patch

from api import portal


class LocalReadCacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        portal._local_read_cache.clear()
        portal._local_read_tasks.clear()

    async def asyncTearDown(self):
        tasks = [task for task in portal._local_read_tasks.values() if not task.done()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        portal._local_read_cache.clear()
        portal._local_read_tasks.clear()

    async def test_concurrent_cold_reads_are_single_flight(self):
        calls = 0

        async def fake_execute(_key, _function, _args):
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)
            return {"code": 200, "data": [calls]}

        with patch.object(portal, "_execute_local_read", side_effect=fake_execute):
            results = await asyncio.gather(*[
                portal._serve_local_read("users:test", lambda: None, (), [])
                for _ in range(8)
            ])

        self.assertEqual(calls, 1)
        self.assertTrue(all(item["code"] == 200 for item in results))

    async def test_stale_read_returns_without_waiting_for_refresh(self):
        portal._local_read_cache["analysis"] = {
            "payload": {"code": 200, "data": {"cached": True}},
            "created_at": portal.monotonic() - 61,
            "updated_at": "2026-08-28T00:00:00",
        }

        async def slow_execute(_key, _function, _args):
            await asyncio.sleep(0.05)
            return {"code": 200, "data": {"cached": False}}

        with patch.object(portal, "_execute_local_read", side_effect=slow_execute):
            result = await portal._serve_local_read("analysis", lambda: None, (), {})

        self.assertEqual(result["data"]["cached"], True)
        self.assertEqual(result["meta"]["freshness"], "stale")
        await portal._local_read_tasks["analysis"]


if __name__ == "__main__":
    unittest.main()
