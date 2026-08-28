import inspect
import unittest

from spider import update_statistics


class StatisticsPerformanceTests(unittest.TestCase):
    def test_group_results_preserves_id_desc_order_per_user(self):
        rows = [
            {"platform_id": 1, "user_id": 10, "id": 9, "result": "赢"},
            {"platform_id": 1, "user_id": 10, "id": 8, "result": "待开奖"},
            {"platform_id": 2, "user_id": 10, "id": 7, "result": "输"},
        ]
        self.assertEqual(update_statistics.group_results(rows)[(1, 10)], ["赢", "待开奖"])
        self.assertEqual(update_statistics.group_results(rows)[(2, 10)], ["输"])

    def test_streak_and_recent_results_keep_legacy_definitions(self):
        self.assertEqual(update_statistics.calculate_streaks(["赢", "赢", "输", "赢"]), (2, 2))
        user = {
            "platform_id": 1,
            "user_id": 10,
            "nickname": "demo",
            "total_orders": 4,
            "settled_orders": 3,
            "win_orders": 2,
            "lose_orders": 1,
            "pending_orders": 1,
            "total_stake": 100,
            "total_profit": 20,
            "follow_num": 3,
            "last_order_time": None,
        }
        values = update_statistics._upsert_values(user, {(1, 10): ["赢", "待开奖", "输", "赢"]})
        self.assertEqual(values[15], "赢,待开奖,输,赢")
        self.assertEqual(values[13:15], (1, 1))

    def test_statistics_no_longer_contains_match_key_backfill(self):
        source = inspect.getsource(update_statistics)
        self.assertNotIn("UPDATE order_matches", source)
        self.assertNotIn("UPDATE match_results", source)
        self.assertIn("executemany", source)
        self.assertIn("statistics already running, skip", source)

    def test_backfill_is_a_separate_module(self):
        from spider import backfill_match_keys

        source = inspect.getsource(backfill_match_keys)
        self.assertIn("UPDATE order_matches", source)
        self.assertIn("UPDATE match_results", source)


if __name__ == "__main__":
    unittest.main()
