import inspect
import unittest
from pathlib import Path

from api import settlement
from api import portal
from common import match_identity
from spider import auto_settlement, caizhanyun_pipeline, caizhanyun_enrich, sync_avatars


ROOT = Path(__file__).resolve().parents[1]


class P0DatabaseOptimizationTests(unittest.TestCase):
    def test_settlement_filters_pending_and_skips_unchanged_updates(self):
        source = inspect.getsource(settlement.select_order_matches)
        self.assertIn("result='待开奖'", source)
        source = inspect.getsource(settlement.settle_match_with_connection)
        self.assertIn("changed_match_updates", source)
        self.assertIn("executemany", source)
        self.assertIn("rows_skipped", source)

    def test_settlement_batches_order_refresh(self):
        source = inspect.getsource(settlement.refresh_order_results_batch)
        self.assertIn("GROUP BY om.order_id", source)
        self.assertIn("executemany", source)
        self.assertIn("result<>%s", source)

    def test_settlement_uses_bounded_transactions(self):
        source = inspect.getsource(auto_settlement)
        self.assertIn("SETTLEMENT_BATCH_SIZE = 50", source)
        self.assertIn("SAVEPOINT settlement_match", source)
        self.assertIn("commit_count", source)
        self.assertIn("pending_found", source)

    def test_schema_checks_are_cached_in_runtime_modules(self):
        self.assertIn("_schema_cache", inspect.getsource(match_identity.table_columns))
        self.assertIn("_orders_columns_cache", inspect.getsource(caizhanyun_pipeline.check_columns))
        self.assertIn("_orders_columns_cache", inspect.getsource(caizhanyun_enrich.check_columns))
        self.assertIn("_schema_cache", inspect.getsource(sync_avatars.table_columns))

    def test_statistics_timer_is_five_minutes(self):
        timer = (ROOT / "deploy/systemd/football-statistics.timer").read_text(encoding="utf-8")
        self.assertIn("OnUnitActiveSec=300s", timer)
        self.assertNotIn("OnUnitActiveSec=30s", timer)

    def test_dashboard_cache_and_top30_pipeline_contract(self):
        self.assertEqual(portal.DASHBOARD_CACHE_SECONDS, 60.0)
        self.assertEqual(portal.DASHBOARD_STALE_SECONDS, 300.0)
        self.assertEqual(portal.DASHBOARD_FIRST_RESPONSE_TIMEOUT, 8.0)
        source = inspect.getsource(portal.build_dashboard_response)
        self.assertIn("get_current_context(cursor, include_profiles=False)", source)
        self.assertIn("candidate_ranking[:30]", source)
        self.assertIn("load_platform_day_metrics", source)
        self.assertIn("load_day_metrics", source)


if __name__ == "__main__":
    unittest.main()
