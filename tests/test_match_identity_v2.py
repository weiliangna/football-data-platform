from pathlib import Path
import re
import sys
import types
import unittest


try:
    import pymysql  # noqa: F401
except ModuleNotFoundError:
    pymysql_stub = types.ModuleType("pymysql")
    pymysql_stub.cursors = types.SimpleNamespace(
        DictCursor=object,
        Cursor=object,
    )
    pymysql_stub.connect = None
    sys.modules["pymysql"] = pymysql_stub


from api.portal import (
    load_order_matches,
    portal_match_group_key,
)
from api.settlement import select_order_matches
from common.match_identity import (
    build_alias_map,
    build_match_identity,
    canonical_team,
    identity_match_strategy,
    normalize_match_date,
)
from spider.build_order_matches import build_structured_legs


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "database"
    / "migrations"
    / "20260825_match_identity_v2.sql"
)
ROLLBACK = (
    ROOT
    / "database"
    / "migrations"
    / "20260825_match_identity_v2_rollback.sql"
)


class MatchIdentityBuilderTests(unittest.TestCase):
    def test_same_teams_on_different_dates_do_not_collide(self):
        first = build_match_identity(
            1,
            match_date="20260825",
            source_match_code="2041053",
            match_name="甲队:乙队",
        )
        second = build_match_identity(
            1,
            match_date="20260826",
            source_match_code="2041053",
            match_name="甲队:乙队",
        )

        self.assertNotEqual(
            first["match_identity"],
            second["match_identity"],
        )

    def test_same_source_code_on_two_platforms_does_not_collide(self):
        first = build_match_identity(
            1,
            match_date="2026-08-25",
            source_match_code="001",
            match_name="甲队:乙队",
        )
        second = build_match_identity(
            3,
            match_date="2026-08-25",
            source_match_code="001",
            match_name="甲队:乙队",
        )

        self.assertNotEqual(
            first["match_identity"],
            second["match_identity"],
        )

    def test_caizhanyun_identity_is_verified_primary(self):
        legs = build_structured_legs(
            [
                {
                    "match_id": "2041053",
                    "day": "20260825",
                    "team": "甲队:乙队",
                    "market_name": "胜平负",
                    "labels": ["主胜"],
                    "letpoint": "-1",
                }
            ]
        )
        leg = legs[0]

        self.assertEqual(
            leg["match_identity"],
            "1|2026-08-25|2041053",
        )
        self.assertEqual(leg["identity_quality"], "exact")
        self.assertEqual(
            str(leg["match_date"]),
            "2026-08-25",
        )

    def test_hongrui_without_date_is_incomplete_but_usable(self):
        identity = build_match_identity(
            3,
            match_date=None,
            source_match_code="周二005",
            match_name="甲队:乙队",
        )

        self.assertEqual(
            identity["identity_quality"],
            "incomplete",
        )
        self.assertIsNone(identity["match_date"])
        self.assertTrue(
            identity["match_identity"].startswith(
                "3|incomplete|周二005|"
            )
        )

        strategy = identity_match_strategy(
            {
                "platform_id": 3,
                "match_date": None,
                "match_code": "周二005",
                "match_key": identity["match_key"],
                "match_name": "甲队:乙队",
            },
            {
                "platform_id": 3,
                "match_date": None,
                "match_code": "周二005",
                "match_key": identity["match_key"],
                "match_name": "甲队:乙队",
            },
        )
        self.assertEqual(strategy, "legacy_match_name")

    def test_null_match_date_never_raises(self):
        self.assertIsNone(normalize_match_date(None))
        self.assertIsNone(normalize_match_date(""))
        self.assertIsNone(normalize_match_date("unknown"))


class AliasAndMatchingTests(unittest.TestCase):
    def test_team_aliases_are_applied_before_identity(self):
        alias_map = build_alias_map(
            [
                {
                    "platform_id": 0,
                    "alias_name": "巴黎圣日耳曼",
                    "canonical_name": "巴黎圣日曼",
                },
                {
                    "platform_id": 1,
                    "alias_name": "PSG",
                    "canonical_name": "巴黎圣日曼",
                },
            ]
        )

        self.assertEqual(
            canonical_team(alias_map, 1, "PSG"),
            "巴黎圣日曼",
        )
        identity = build_match_identity(
            1,
            match_date="2026-08-25",
            match_name="PSG:里昂",
            alias_map=alias_map,
        )
        self.assertEqual(
            identity["normalized_home"],
            "巴黎圣日曼",
        )

    def test_settlement_matching_priority(self):
        exact = identity_match_strategy(
            {
                "platform_id": 1,
                "match_date": "2026-08-25",
                "match_code": "2041053",
                "match_key": "甲|乙",
                "match_name": "甲:乙",
            },
            {
                "platform_id": 1,
                "match_date": "2026-08-25",
                "match_code": "2041053",
                "match_key": "不同|队名",
                "match_name": "旧名:旧名",
            },
        )
        fallback = identity_match_strategy(
            {
                "platform_id": 1,
                "match_date": "2026-08-25",
                "match_code": "",
                "match_key": "甲|乙",
                "match_name": "甲:乙",
            },
            {
                "platform_id": 1,
                "match_date": "2026-08-25",
                "match_code": "",
                "match_key": "甲|乙",
                "match_name": "旧名:旧名",
            },
        )
        legacy = identity_match_strategy(
            {"match_name": "甲:乙"},
            {"match_name": "甲:乙"},
        )

        self.assertEqual(exact, "identity_v2")
        self.assertEqual(fallback, "identity_fallback")
        self.assertEqual(legacy, "legacy_match_name")

    def test_different_platforms_never_match_by_code(self):
        strategy = identity_match_strategy(
            {
                "platform_id": 1,
                "match_date": "2026-08-25",
                "match_code": "001",
                "match_name": "甲:乙",
            },
            {
                "platform_id": 3,
                "match_date": "2026-08-25",
                "match_code": "001",
                "match_name": "甲:乙",
            },
        )
        self.assertIsNone(strategy)

    def test_portal_prefers_identity_v2_group_key(self):
        key = portal_match_group_key(
            {
                "platform_id": 1,
                "match_identity": "1|2026-08-25|2041053",
                "match_code": "2041053",
                "match_name": "甲 VS 乙",
            }
        )
        self.assertEqual(
            key,
            "identity:1|2026-08-25|2041053",
        )


class RecordingSettlementCursor:
    def __init__(self):
        self.sql = ""
        self.params = ()

    def execute(self, sql, params=()):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return []


class LegacyPortalCursor:
    def __init__(self):
        self.rows = []
        self.final_query_seen = False

    def execute(self, sql, params=()):
        if "information_schema.COLUMNS" in sql:
            table_name = params[0]
            columns = {
                "order_matches": {
                    "id",
                    "order_id",
                    "match_code",
                    "match_name",
                    "match_key",
                    "league",
                    "play_type",
                    "selection",
                    "option_detail",
                    "handicap",
                    "deadline_time",
                    "result",
                },
                "match_results": {
                    "id",
                    "match_code",
                    "match_name",
                    "match_key",
                    "home_score",
                    "away_score",
                    "half_home_score",
                    "half_away_score",
                    "status",
                },
            }[table_name]
            self.rows = [
                {"COLUMN_NAME": value}
                for value in columns
            ]
            return

        self.final_query_seen = True
        self.rows = []

    def fetchall(self):
        return self.rows


class CompatibilityQueryTests(unittest.TestCase):
    def test_settlement_v2_sql_placeholder_count_matches(self):
        cursor = RecordingSettlementCursor()
        rows = select_order_matches(
            cursor,
            {
                "platform_id": 1,
                "match_date": normalize_match_date(
                    "2026-08-25"
                ),
                "source_match_code": "2041053",
                "match_key": "甲|乙",
            },
            "甲:乙",
            True,
        )

        self.assertEqual(rows, [])
        self.assertEqual(
            cursor.sql.count("%s"),
            len(cursor.params),
        )
        self.assertLess(
            cursor.sql.index("'identity_v2'"),
            cursor.sql.index("'identity_fallback'"),
        )
        self.assertLess(
            cursor.sql.index("'identity_fallback'"),
            cursor.sql.index("'legacy_match_name'"),
        )

    def test_portal_works_before_migration(self):
        cursor = LegacyPortalCursor()
        grouped = load_order_matches(cursor, [1])

        self.assertEqual(dict(grouped), {})
        self.assertTrue(cursor.final_query_seen)


class MigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = MIGRATION.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")

    def test_migration_has_repeatable_guards(self):
        self.assertIn(
            "information_schema.COLUMNS",
            self.forward,
        )
        self.assertIn(
            "information_schema.STATISTICS",
            self.forward,
        )
        self.assertIn(
            "IF NOT EXISTS",
            self.forward,
        )
        self.assertIn(
            "DROP PROCEDURE IF EXISTS",
            self.forward,
        )

    def test_forward_migration_never_deletes_business_data(self):
        destructive_dml = re.compile(
            r"(?i)\b(?:DELETE\s+FROM|TRUNCATE\s+TABLE|DROP\s+TABLE)\b"
        )
        self.assertIsNone(
            destructive_dml.search(self.forward)
        )

    def test_forward_migration_adds_no_unique_constraint(self):
        unique_ddl = re.compile(
            r"(?i)\bADD\s+(?:CONSTRAINT\s+\w+\s+)?UNIQUE\b"
        )
        self.assertIsNone(unique_ddl.search(self.forward))

    def test_rollback_sql_exists_and_is_guarded(self):
        self.assertTrue(ROLLBACK.is_file())
        self.assertIn(
            "rollback_match_identity_v2",
            self.rollback,
        )
        self.assertIn("Rollback blocked", self.rollback)


if __name__ == "__main__":
    unittest.main()
