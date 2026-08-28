import inspect
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from common.user_grading import (
    _load_grade_rows,
    calculate_user_grades,
    normalize_platform_level,
    percentile_scores,
)
from common.user_labels import build_first_order_profile


ROOT = Path(__file__).resolve().parents[1]


def grade_row(user_id, *, high=False):
    return {
        "platform_id": 1,
        "user_id": user_id,
        "platform_level": "钻石" if high else "青铜",
        "orders7d": 8 if high else 1,
        "self_buy7d": 10000 if high else 10,
        "followers7d": 1000 if high else 0,
        "settled7d": 7 if high else 0,
        "wins7d": 6 if high else 0,
        "settled_stake7d": 5000 if high else 0,
        "settled_prize7d": 10000 if high else 0,
        "total_prize": 500000 if high else 0,
        "last5": ["赢", "赢", "赢", "输", "赢"] if high else [],
    }


class GradeCalculationTests(unittest.TestCase):
    def test_level_normalization_and_single_user_percentile(self):
        self.assertEqual(normalize_platform_level("钻石"), 100)
        self.assertEqual(normalize_platform_level("5级"), 50)
        self.assertEqual(normalize_platform_level("unknown"), 35)
        rows = [grade_row(1, high=True)]
        self.assertEqual(percentile_scores(rows, "orders7d")[(1, 1)], 50)

    def test_tied_percentiles_are_equal(self):
        rows = [grade_row(1), grade_row(2)]
        scores = percentile_scores(rows, "orders7d")
        self.assertEqual(scores[(1, 1)], scores[(1, 2)])

    def test_s_and_b_hard_gates(self):
        rows = calculate_user_grades([grade_row(1), grade_row(2, high=True)])
        by_user = {row["user_id"]: row for row in rows}
        self.assertEqual(by_user[2]["grade"], "S")
        self.assertEqual(by_user[1]["grade"], "B")
        self.assertLessEqual(by_user[2]["score"], 100)

    def test_manual_grade_has_priority(self):
        rows = calculate_user_grades(
            [grade_row(1)],
            {(1, 1): "S"},
        )
        self.assertEqual(rows[0]["auto_grade"], "B")
        self.assertEqual(rows[0]["grade"], "S")

    def test_grade_loader_uses_two_batch_queries(self):
        source = inspect.getsource(_load_grade_rows)
        self.assertEqual(source.count("cursor.execute("), 2)
        self.assertIn("LEFT JOIN user_statistics", source)
        self.assertNotIn("GROUP_CONCAT", source)


class FirstOrderLabelTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 28, 12, 0, 0)

    def test_confirmed_first_100(self):
        profile = build_first_order_profile(
            "100.00",
            self.now,
            1,
            history_complete=True,
            now=self.now,
        )
        self.assertEqual(
            profile["auto_tags"],
            [
                "NEW_FIRST_ORDER_100",
                "NEW_FIRST_ORDER_LOW_AMOUNT",
                "NEW_ACCOUNT_OBSERVE",
            ],
        )

    def test_confirmed_first_200(self):
        profile = build_first_order_profile(
            200,
            self.now - timedelta(days=3),
            2,
            history_complete=True,
            now=self.now,
        )
        self.assertIn("NEW_FIRST_ORDER_200", profile["auto_tags"])
        self.assertIn("NEW_ACCOUNT_OBSERVE", profile["auto_tags"])

    def test_large_first_order_only_observe(self):
        profile = build_first_order_profile(
            500,
            self.now,
            1,
            history_complete=True,
            now=self.now,
        )
        self.assertEqual(profile["auto_tags"], ["NEW_ACCOUNT_OBSERVE"])

    def test_old_active_history_keeps_fact_not_observe(self):
        profile = build_first_order_profile(
            100,
            self.now - timedelta(days=30),
            10,
            history_complete=True,
            now=self.now,
        )
        self.assertIn("NEW_FIRST_ORDER_100", profile["auto_tags"])
        self.assertNotIn("NEW_ACCOUNT_OBSERVE", profile["auto_tags"])

    def test_incomplete_history_is_suspected(self):
        profile = build_first_order_profile(
            100,
            self.now,
            1,
            history_complete=False,
            now=self.now,
        )
        self.assertEqual(profile["first_order_confidence"], "suspected")
        self.assertIn("SUSPECTED_FIRST_ORDER_100", profile["auto_tags"])
        self.assertNotIn("NEW_FIRST_ORDER_100", profile["auto_tags"])


class UserDirectoryContractTests(unittest.TestCase):
    def test_user_center_contains_requested_filters_and_columns(self):
        source = (ROOT / "frontend" / "src" / "views" / "UserCenter.vue").read_text(
            encoding="utf-8"
        )
        for marker in (
            "真实盈利",
            "擅长玩法",
            "当前连红",
            "近期红黑",
            "历史命中率",
            "历史回报率",
            "近10场黑红",
            "跟单总额",
            "localStorage",
            "AbortController",
            "role=\"dialog\"",
            "SP赔率",
        ):
            self.assertIn(marker, source)

    def test_active_frontend_has_no_manual_refresh_copy(self):
        for path in (ROOT / "frontend" / "src").rglob("*.vue"):
            if ".bak" in path.name:
                continue
            source = path.read_text(encoding="utf-8")
            for marker in ("刷新", "重新加载", "重试"):
                self.assertNotIn(marker, source, f"{path}: {marker}")


if __name__ == "__main__":
    unittest.main()
