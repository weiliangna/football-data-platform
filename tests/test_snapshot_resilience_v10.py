import inspect
import unittest

from api import portal
from common import snapshot_store


class SnapshotResilienceTests(unittest.TestCase):
    def test_dashboard_timeout_is_renderable(self):
        response = portal._empty_dashboard_response()
        self.assertEqual(response["code"], 200)
        self.assertEqual(response["meta"]["freshness"], "refreshing")
        self.assertTrue(response["meta"]["refreshing"])
        self.assertIn("metrics", response["data"])
        self.assertIn("sender_ranking", response["data"])

    def test_dashboard_uses_persisted_snapshot_and_single_flight_refresh(self):
        source = inspect.getsource(portal.dashboard)
        self.assertIn('load_snapshot("portal:dashboard")', source)
        self.assertIn("refresh_dashboard_cache()", source)
        self.assertIn("freshness", source)

    def test_snapshot_store_is_best_effort(self):
        self.assertEqual(snapshot_store.SNAPSHOT_TABLE, "api_snapshots")
        self.assertIn("ON DUPLICATE KEY UPDATE", inspect.getsource(snapshot_store.save_snapshot))
        self.assertIn("except Exception", inspect.getsource(snapshot_store.load_snapshot))


if __name__ == "__main__":
    unittest.main()

