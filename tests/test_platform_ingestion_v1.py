import sys
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path


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

try:
    import fastapi  # noqa: F401
except ModuleNotFoundError:
    fastapi_stub = types.ModuleType("fastapi")

    class OfflineAPIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return lambda function: function

    fastapi_stub.APIRouter = OfflineAPIRouter
    sys.modules["fastapi"] = fastapi_stub


from api.portal import resolve_order_deadline
from common.match_utils import parse_match_name
from spider import pipeline
from spider.caizhanyun_pipeline import build_enrichment_steps
from spider.build_order_matches import (
    parse_selection_legs,
    upsert_order_matches,
)
from spider.run_job import redact_sensitive_text


ROOT = Path(__file__).resolve().parents[1]


class FakeOrderMatchCursor:
    def __init__(self):
        self.rows = []
        self.current = None
        self.next_id = 1

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())

        if (
            normalized.startswith("select id,result from order_matches")
            and "for update" in normalized
        ):
            order_id, match_name, play_type, handicap = params
            self.current = next(
                (
                    row
                    for row in self.rows
                    if row["order_id"] == order_id
                    and row["match_name"] == match_name
                    and row["play_type"] == play_type
                    and int(row.get("handicap") or 0) == handicap
                ),
                None,
            )
            return

        if normalized.startswith("update order_matches set"):
            (
                match_code,
                match_key,
                league,
                selection,
                handicap,
                row_id,
            ) = params
            row = next(
                row
                for row in self.rows
                if row["id"] == row_id
            )
            row.update(
                {
                    "match_code": match_code,
                    "match_key": match_key,
                    "league": league,
                    "selection": selection,
                    "handicap": handicap,
                }
            )
            self.current = None
            return

        if normalized.startswith("insert into order_matches"):
            (
                order_id,
                match_code,
                match_name,
                match_key,
                league,
                play_type,
                selection,
                handicap,
                deadline_time,
            ) = params
            self.rows.append(
                {
                    "id": self.next_id,
                    "order_id": order_id,
                    "match_code": match_code,
                    "match_name": match_name,
                    "match_key": match_key,
                    "league": league,
                    "play_type": play_type,
                    "selection": selection,
                    "handicap": handicap,
                    "deadline_time": deadline_time,
                    "result": "待开奖",
                    "profit": 0,
                }
            )
            self.next_id += 1
            self.current = None
            return

        raise AssertionError(f"Unexpected SQL in fake cursor: {normalized}")

    def fetchone(self):
        return self.current


class OrderMatchTests(unittest.TestCase):
    def test_two_leg_parlay_is_idempotent_and_preserves_result(self):
        cursor = FakeOrderMatchCursor()
        order = {
            "id": 101,
            "league": "测试联赛",
            "handicap": -1,
            "selection": (
                "主队甲:客队甲→胜平负：主胜；"
                "主队乙：客队乙→让球胜平负：让胜"
            ),
        }

        first = upsert_order_matches(cursor, order)
        self.assertEqual(first["inserted"], 2)
        self.assertEqual(len(cursor.rows), 2)

        cursor.rows[0]["result"] = "赢"
        cursor.rows[0]["profit"] = 12.5

        second = upsert_order_matches(cursor, order)
        self.assertEqual(second["inserted"], 0)
        self.assertEqual(second["updated"], 2)
        self.assertEqual(len(cursor.rows), 2)
        self.assertEqual(cursor.rows[0]["result"], "赢")
        self.assertEqual(cursor.rows[0]["profit"], 12.5)

    def test_handicap_only_applies_to_handicap_play(self):
        selection = "；".join(
            (
                "甲:乙→胜平负：主胜",
                "丙:丁→让球胜平负：让胜",
                "戊:己→总进球：3球",
                "庚:辛→比分：1:0",
                "壬:癸→半全场：胜胜",
            )
        )
        legs = parse_selection_legs(
            selection,
            order_handicap=-2,
        )
        self.assertEqual(len(legs), 5)

        by_play = {
            leg["play_type"]: leg["handicap"]
            for leg in legs
        }
        self.assertEqual(by_play["胜平负"], 0)
        self.assertEqual(by_play["总进球"], 0)
        self.assertEqual(by_play["比分"], 0)
        self.assertEqual(by_play["半全场"], 0)
        self.assertEqual(by_play["让球胜平负"], -2)


class MatchNameTests(unittest.TestCase):
    def assert_match(self, raw):
        parsed = parse_match_name(raw)
        self.assertEqual(parsed["raw_name"], raw)
        self.assertEqual(parsed["home_team"], "主队")
        self.assertEqual(parsed["away_team"], "客队")

    def test_english_colon(self):
        self.assert_match("主队:客队")

    def test_chinese_colon(self):
        self.assert_match("主队：客队")

    def test_uppercase_vs(self):
        self.assert_match("主队 VS 客队")

    def test_lowercase_vs(self):
        self.assert_match("主队 vs 客队")

    def test_invalid_match_name_does_not_raise(self):
        parsed = parse_match_name("无法解析")
        self.assertEqual(parsed["raw_name"], "无法解析")
        self.assertIsNone(parsed["home_team"])
        self.assertIsNone(parsed["away_team"])


class PipelineTests(unittest.TestCase):
    def test_caizhanyun_enrichment_uses_package_modules(self):
        steps = build_enrichment_steps(1174, "python")
        commands = [command for _title, command in steps]

        self.assertEqual(
            [command[1:3] for command in commands],
            [
                ["-m", "spider.caizhanyun_enrich"],
                ["-m", "spider.caizhanyun_pass_enrich"],
                ["-m", "spider.build_order_matches"],
            ],
        )
        self.assertEqual(commands[2][-2:], ["--id", "1174"])

    def test_caizhanyun_failure_does_not_hide_other_statuses(self):
        records = []

        def fail_caizhanyun():
            raise RuntimeError("offline failure")

        statuses = pipeline.run(
            caizhanyun_runner=fail_caizhanyun,
            status_recorder=records.append,
        )

        self.assertEqual(records, statuses)
        by_id = {
            item["platform_id"]: item["status"]
            for item in statuses
        }
        self.assertEqual(by_id[1], "failed")
        self.assertEqual(by_id[3], "external_scheduler")
        self.assertEqual(by_id[2], "waiting_config")
        self.assertEqual(by_id[4], "waiting_config")


class RedactionTests(unittest.TestCase):
    def test_token_is_redacted(self):
        value = redact_sensitive_text(
            "to" + "ken=" + "offline-token-value"
        )
        self.assertNotIn("offline-token-value", value)
        self.assertIn("[REDACTED]", value)

    def test_cookie_is_redacted(self):
        value = redact_sensitive_text(
            "Cookie: session=offline-cookie-value"
        )
        self.assertNotIn("offline-cookie-value", value)
        self.assertIn("[REDACTED]", value)

    def test_jwt_is_redacted(self):
        value = redact_sensitive_text(
            "Authorization: Bearer eyJabc.def.ghi"
        )
        self.assertNotIn("eyJabc.def.ghi", value)
        self.assertIn("[REDACTED", value)

    def test_password_secret_and_bearer_are_redacted(self):
        value = redact_sensitive_text(
            "pass" + "word=offline-password "
            + "pass" + "wd=offline-pass "
            + "se" + "cret=offline-secret "
            + "Bearer offline-bearer"
        )
        for secret in (
            "offline-password",
            "offline-pass",
            "offline-secret",
            "offline-bearer",
        ):
            self.assertNotIn(secret, value)


class DeadlineTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 25, 12, 0, 0)

    def test_null_deadline_pending_fallback(self):
        result = resolve_order_deadline(
            {"result": "待开奖"},
            [{"deadline_time": None}],
            self.now,
            {},
            {},
        )
        self.assertTrue(result["unexpired"])
        self.assertIsNone(result["deadline_time"])
        self.assertEqual(
            result["deadline_source"],
            "pending_fallback",
        )
        self.assertFalse(result["deadline_exact"])

    def test_direct_deadline_is_exact(self):
        deadline = self.now + timedelta(minutes=10)
        result = resolve_order_deadline(
            {"result": "待开奖"},
            [{"deadline_time": deadline}],
            self.now,
            {},
            {},
        )
        self.assertEqual(result["deadline_source"], "deadline")
        self.assertTrue(result["deadline_exact"])

    def test_kickoff_proxy_is_not_exact(self):
        kickoff = self.now + timedelta(hours=2)
        result = resolve_order_deadline(
            {"result": "待开奖"},
            [{"match_code": "周一001", "deadline_time": None}],
            self.now,
            {
                "周一001": {
                    "deadline_time": kickoff,
                    "deadline_source": "kickoff_proxy",
                    "deadline_exact": False,
                }
            },
            {},
        )
        self.assertEqual(
            result["deadline_source"],
            "kickoff_proxy",
        )
        self.assertFalse(result["deadline_exact"])


class DeploymentTemplateTests(unittest.TestCase):
    def test_hongrui_service_enables_write_mode(self):
        service = (
            ROOT
            / "deploy"
            / "systemd"
            / "hongrui-spider.service"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "--module spider.hongrui "
            "--args --limit 50 --write",
            service,
        )


if __name__ == "__main__":
    unittest.main()


