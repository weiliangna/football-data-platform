import inspect
import unittest
from datetime import date
from unittest.mock import patch

import api.hub as hub
import api.portal as portal


class RecordingCursor:
    def __init__(self):
        self.statements = []

    def execute(self, statement, params=()):
        self.statements.append((statement, tuple(params)))

    def fetchall(self):
        return []


class MysqlFormattingRegressionTests(unittest.TestCase):
    def test_user_metrics_escape_mysql_date_format_for_pymysql(self):
        source = inspect.getsource(portal.load_recent_user_metrics)
        self.assertIn("DATE_FORMAT(CURDATE(),'%%Y-%%m-01')", source)
        self.assertNotIn("DATE_FORMAT(CURDATE(),'%Y-%m-01')", source)

    def test_results_escape_parameterized_month_formats(self):
        source = inspect.getsource(hub.hub_results)
        self.assertGreaterEqual(source.count("'%%Y-%%m'"), 3)


class SharedContextRegressionTests(unittest.TestCase):
    def setUp(self):
        portal._current_context_cache.update({
            "data": None,
            "created_at": 0.0,
            "has_profiles": False,
        })

    def tearDown(self):
        portal._current_context_cache.update({
            "data": None,
            "created_at": 0.0,
            "has_profiles": False,
        })

    def test_analysis_heatmap_and_dashboard_can_share_context(self):
        with patch.object(
            portal,
            "build_current_context",
            return_value={"profiles": {}},
        ) as build:
            first = portal.get_current_context(object())
            second = portal.get_current_context(object())
        self.assertIs(first, second)
        build.assert_called_once()

    def test_profile_request_upgrades_profileless_context(self):
        with patch.object(
            portal,
            "build_current_context",
            side_effect=[{"profiles": {}}, {"profiles": {(1, 2): {}}}],
        ) as build:
            portal.get_current_context(object())
            upgraded = portal.get_current_context(object(), include_profiles=True)
        self.assertEqual(build.call_count, 2)
        self.assertIn((1, 2), upgraded["profiles"])

    def test_today_pending_candidates_do_not_scan_all_history(self):
        cursor = RecordingCursor()
        with patch.object(
            portal,
            "table_columns",
            return_value={"deadline_time", "match_date"},
        ):
            portal.load_pending_orders(cursor, date(2026, 8, 28))
        sql, params = cursor.statements[-1]
        self.assertIn("COALESCE(o.publish_time,o.created_time)>=%s", sql)
        self.assertIn("deadline_match.deadline_time>=%s", sql)
        self.assertIn("dated_match.match_date=%s", sql)
        self.assertEqual(len(params), 4)


if __name__ == "__main__":
    unittest.main()
