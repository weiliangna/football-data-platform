import unittest
from datetime import datetime
from pathlib import Path

from api.portal import aggregate_today_hot_plays, format_match_row
from common.bet_aggregation import (
    normalize_selection_combination,
    resolve_archive_date,
)
from common.match_utils import match_pair_similarity, parse_match_name


ROOT = Path(__file__).resolve().parents[1]


def references():
    return {
        "by_date": {
            "2026-08-27": [{
                "match_code": "005",
                "home": "贝尔格莱德红星",
                "away": "阿拉木图凯拉特",
                "match_name": "贝尔格莱德红星 VS 阿拉木图凯拉特",
                "league": "欧冠",
                "event_day": "2026-08-27",
                "canonical_display_key": "2026-08-27|贝尔格莱德红星|阿拉木图凯拉特",
            }]
        },
        "all": [],
    }


class MatchDisplayTests(unittest.TestCase):
    def test_caizhanyun_team_id_and_names_win_cross_platform_display(self):
        row = {
            "id": 1,
            "match_name": "贝红星 VS 阿拉木图",
            "match_code": "周三009",
            "match_date": "2026-08-27",
            "play_type": "胜平负",
            "selection": "胜",
        }
        value = format_match_row(row, {}, 3, references())
        self.assertEqual(value["match_code"], "005")
        self.assertEqual(value["home"], "贝尔格莱德红星")
        self.assertEqual(value["away"], "阿拉木图凯拉特")

    def test_home_and_away_reversal_is_supported(self):
        score, reversed_order = match_pair_similarity(
            "阿拉木图",
            "贝红星",
            "贝尔格莱德红星",
            "阿拉木图凯拉特",
        )
        self.assertGreater(score, 0.62)
        self.assertTrue(reversed_order)

    def test_match_parser_accepts_v_hyphen_and_slash(self):
        for value in ("甲队 V 乙队", "甲队-乙队", "甲队／乙队"):
            parsed = parse_match_name(value)
            self.assertEqual(parsed["home_team"], "甲队")
            self.assertEqual(parsed["away_team"], "乙队")


class HotPlayTests(unittest.TestCase):
    def test_selection_standardization(self):
        self.assertEqual(normalize_selection_combination("胜平负", "胜/1/客胜"), "主胜/主负/平")
        self.assertEqual(normalize_selection_combination("让球胜平负", "让主胜"), "让胜")
        self.assertEqual(normalize_selection_combination("比分", "2-1"), "2:1")
        self.assertEqual(normalize_selection_combination("半全场", "主胜/客胜"), "胜负")

    def test_same_order_duplicate_counts_once_and_other_order_adds_one(self):
        deadline = {"deadline_time": datetime(2026, 8, 27, 20, 0)}
        row = {
            "id": 1,
            "match_name": "贝红星 VS 阿拉木图",
            "match_code": "周三009",
            "match_date": "2026-08-27",
            "play_type": "胜平负",
            "selection": "胜",
        }
        context = {
            "alias_map": {},
            "match_references": references(),
            "today_hot_legs": [
                ({"id": 10, "platform_id": 3}, row, deadline),
                ({"id": 10, "platform_id": 3}, row, deadline),
                ({"id": 11, "platform_id": 2}, row, deadline),
            ],
        }
        groups = aggregate_today_hot_plays(context)
        spf = next(item for item in groups if item["play_type"] == "胜平负")
        self.assertEqual(spf["items"][0]["count"], 2)
        self.assertEqual(spf["items"][0]["selection"], "主胜")

    def test_archive_date_priority(self):
        order = {
            "betEndTime": "2026-08-27 20:00:00",
            "planDate": "2026-08-26",
            "firstViewedAt": "2026-08-25 10:00:00",
        }
        self.assertEqual(
            resolve_archive_date(order, [{"day": "2026-08-24"}]),
            "2026-08-27",
        )


class UiContractTests(unittest.TestCase):
    def test_heatmap_has_match_filter_without_platform_cards(self):
        source = (ROOT / "frontend/src/views/Heatmap.vue").read_text(encoding="utf-8")
        self.assertIn("赛事筛选", source)
        self.assertNotIn("platform-strip", source)

    def test_home_has_four_hot_play_cards_and_auto_refresh(self):
        source = (ROOT / "frontend/src/views/Home.vue").read_text(encoding="utf-8")
        self.assertIn("今日热门玩法", source)
        self.assertIn("setInterval", source)
        self.assertIn("30000", source)


if __name__ == "__main__":
    unittest.main()
