import unittest
from pathlib import Path
from unittest.mock import patch

from api import hub
from spider.build_order_matches import build_structured_legs
from spider.magicangle_contract import build_option_detail


ROOT = Path(__file__).resolve().parents[1]


class ArchiveQueryTests(unittest.TestCase):
    def test_archive_date_uses_one_grouped_match_join(self):
        def columns(_cursor, table):
            if table == "orders":
                return {"publish_time", "created_time", "plan_date"}
            return {"deadline_time", "match_date"}

        with patch.object(hub, "table_columns", side_effect=columns):
            expression, join_sql = hub.archive_date_source(object(), "o")

        self.assertIn("archive_match.deadline_date", expression)
        self.assertIn("archive_match.match_date", expression)
        self.assertIn("GROUP BY order_id", join_sql)
        self.assertNotIn("SELECT DATE", expression)


class VerifiedSpTests(unittest.TestCase):
    def fixture(self):
        return {
            "market_name": "胜平负",
            "selection_code": "31",
            "labels": ["主胜", "平"],
            "team": "甲队:乙队",
            "day": "20260827",
            "match_id": "2041001",
            "team_id": "005",
            "peilvs": [
                {"type": "v3", "peilv": "1.82"},
                {"type": "v1", "peilv": "3.15"},
            ],
        }

    def test_verified_prices_map_to_selected_options(self):
        self.assertEqual(
            build_option_detail(self.fixture()),
            [
                {"name": "主胜", "odds": "1.82"},
                {"name": "平", "odds": "3.15"},
            ],
        )

    def test_caizhanyun_leg_keeps_option_detail(self):
        legs = build_structured_legs([self.fixture()])
        self.assertEqual(legs[0]["option_detail"][0]["odds"], "1.82")


class FrontendReliabilityTests(unittest.TestCase):
    def source(self, name):
        return (ROOT / "frontend" / "src" / "views" / name).read_text(
            encoding="utf-8"
        )

    def test_user_center_renders_real_recent_metrics(self):
        source = self.source("UserCenter.vue")
        for marker in ("item.self_buy7d", "item.orders7d", "item.recent5"):
            self.assertIn(marker, source)

    def test_hover_does_not_replace_ranking_detail(self):
        self.assertNotIn('@mouseenter="select(person)"', self.source("Home.vue"))

    def test_heatmap_play_tabs_are_centered(self):
        source = self.source("Heatmap.vue")
        self.assertIn(".play-tabs{justify-content:center}", source)


if __name__ == "__main__":
    unittest.main()
