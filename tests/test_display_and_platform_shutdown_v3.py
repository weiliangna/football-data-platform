import unittest
from pathlib import Path

from api.portal import format_match_row, selection_odds
from common.pass_utils import normalize_pass_summary
from common.platform_registry import (
    ACTIVE_PLATFORM_IDS,
    STOPPED_PLATFORM_IDS,
)
from scripts.purge_stopped_platforms import main as purge_main


ROOT = Path(__file__).resolve().parents[1]


class BettingDisplayTests(unittest.TestCase):
    def test_selected_option_odds_are_exposed_as_sp(self):
        row = {
            "selection": "主胜/平",
            "option_detail": (
                '[{"name":"主胜","odds":1.85},'
                '{"name":"平","odds":3.2}]'
            ),
        }
        self.assertEqual(selection_odds(row), "1.85 / 3.2")

    def test_caizhanyun_reference_controls_public_match_display(self):
        row = {
            "match_name": "曼联:阿森纳",
            "match_code": "source-100",
            "match_date": "2026-08-27",
            "selection": "主胜",
        }
        references = {
            "by_date": {
                "2026-08-27": [{
                    "match_code": "008",
                    "home": "曼联",
                    "away": "阿森纳",
                    "match_name": "曼联 VS 阿森纳",
                    "event_day": "2026-08-27",
                    "canonical_display_key": "2026-08-27|曼联|阿森纳",
                }]
            },
            "all": [],
        }
        result = format_match_row(row, {}, 2, references)
        self.assertEqual(result["match_code"], "008")
        self.assertEqual(result["match_name"], "曼联 VS 阿森纳")

    def test_zhouyunbao_pass_codes_follow_caizhanyun_wording(self):
        self.assertEqual(normalize_pass_summary("501"), "单关")
        self.assertEqual(normalize_pass_summary("502"), "2串1")
        self.assertEqual(normalize_pass_summary("503/502"), "3串1/2串1")
        self.assertEqual(normalize_pass_summary("500"), "500")


class PlatformShutdownTests(unittest.TestCase):
    def test_only_four_platforms_are_public_and_two_are_stopped(self):
        self.assertEqual(ACTIVE_PLATFORM_IDS, (1, 2, 3, 4))
        self.assertEqual(STOPPED_PLATFORM_IDS, frozenset({5, 6}))

    def test_purge_requires_explicit_confirmation(self):
        with self.assertRaises(SystemExit):
            purge_main([])

    def test_frontend_does_not_offer_stopped_platforms(self):
        source = (
            ROOT / "frontend" / "src" / "views" / "Experts.vue"
        ).read_text(encoding="utf-8")
        self.assertNotIn('name: "好店主"', source)
        self.assertNotIn('name: "启示录"', source)


class RequestedUiTests(unittest.TestCase):
    def test_home_uses_real_today_amount(self):
        source = (
            ROOT / "frontend" / "src" / "views" / "Home.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("metrics.today_amount", source)
        self.assertNotIn("接口暂未提供跟单金额", source)

    def test_heatmap_has_no_manual_refresh_label_or_yellow_fill(self):
        source = (
            ROOT / "frontend" / "src" / "views" / "Heatmap.vue"
        ).read_text(encoding="utf-8")
        self.assertNotIn("刷新热力图", source)
        self.assertNotIn("rgba(217,255,53", source)

    def test_results_have_compact_calendar_without_destructive_tools(self):
        source = (
            ROOT / "frontend" / "src" / "views" / "Results.vue"
        ).read_text(encoding="utf-8")
        for marker in ("calendarCells", "返回方案大厅", "前一日", "后一日"):
            self.assertIn(marker, source)
        for marker in ("刷新赛果", "保存图片", "保存 Excel", "一键清空", "DELETE_RESULTS_"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
