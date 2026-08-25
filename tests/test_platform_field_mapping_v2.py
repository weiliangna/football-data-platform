import sys
import types
import unittest
from unittest.mock import patch


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
    import requests  # noqa: F401
except ModuleNotFoundError:
    requests_stub = types.ModuleType("requests")

    class OfflineSession:
        def __init__(self):
            self.headers = {}

        def post(self, *args, **kwargs):
            raise AssertionError("offline test attempted HTTP")

    requests_stub.Session = OfflineSession
    requests_stub.post = (
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("offline test attempted HTTP")
        )
    )
    sys.modules["requests"] = requests_stub


import database.save_user as save_user_module
from common.platform_field_mapping import (
    extract_caizhanyun_order_fields,
    extract_hongrui_source_fields,
    parse_epoch_milliseconds_beijing,
    resolve_hongrui_handicap,
    select_avatar,
)
from spider.build_order_matches import (
    build_structured_legs,
    choose_legs,
)
from spider.caizhanyun_enrich import (
    build_selection_text,
    save_user_avatar as save_caizhanyun_avatar,
)
from spider.hongrui import (
    parse_detail,
    save_user_avatar as save_hongrui_avatar,
)


class RecordingCursor:
    def __init__(self):
        self.calls = []
        self.closed = False

    def execute(self, sql, params=()):
        self.calls.append((sql, params))

    def close(self):
        self.closed = True


class RecordingConnection:
    def __init__(self):
        self.cursor_instance = RecordingCursor()
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, *args, **kwargs):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def caizhanyun_fixture():
    matches = [
        {
            "matchId": "2041053",
            "teamId": "005",
            "day": "20260825",
            "week": "2",
            "team": "甲队:乙队",
            "league": "测试联赛",
            "letpoint": "-1",
            "enddate": "08-25 22:00",
        },
        {
            "matchId": "2041054",
            "teamId": "006",
            "day": "20260825",
            "week": "2",
            "team": "丙队:丁队",
            "league": "测试联赛",
            "letpoint": "+1",
            "enddate": "08-25 23:00",
        },
    ]
    info = {
        "createTime": 1787560615000,
        "endTime": 1787665800000,
        "lotNo": "J00013",
        "betCodeForResult": (
            "502@"
            "20260825|2|005|J00013|3^"
            "20260825|2|006|J00013|0"
        ),
        "jingcaiResultList": matches,
    }
    return info, matches


def decoded_caizhanyun_fixture():
    info, matches = caizhanyun_fixture()
    _, _, decoded = build_selection_text(
        info,
        matches,
    )
    return info, decoded


def hongrui_fixture():
    return {
        "code": 1,
        "data": {
            "head": {
                "user_id": 301,
                "user_name": "测试用户",
                "user_pic": "detail-avatar",
                "expire_time": "08-25 21:50",
                "fans_count": 88,
                "profit": "12.5",
                "bonus_num": 7,
                "status": 1,
                "status_msg": "进行中",
                "bonus": "0",
                "commission_total": "0",
            },
            "order_message": {
                "field_count": 2,
                "lottery_list": [
                    {
                        "week_name": "周二005",
                        "home": "甲队",
                        "away": "乙队",
                        "playing": [
                            {
                                "name": "让球胜平负",
                                "rq_number": "-1",
                                "odds_name": "胜",
                                "odds": "1.80",
                            },
                            {
                                "name": "胜平负",
                                "rq_number": "-1",
                                "odds_name": "平",
                                "odds": "3.20",
                            },
                        ],
                    },
                    {
                        "week_name": "周二006",
                        "home": "丙队",
                        "away": "丁队",
                        "playing": [
                            {
                                "name": "让球胜平负",
                                "rq_number": "+1",
                                "odds_name": "负",
                                "odds": "2.10",
                            }
                        ],
                    },
                ],
            },
            "follow_count": 10,
        },
    }


class CaizhanyunLegTests(unittest.TestCase):
    def test_two_match_handicaps_are_independent(self):
        _, decoded = decoded_caizhanyun_fixture()
        legs = build_structured_legs(decoded)

        self.assertEqual(
            [leg["handicap"] for leg in legs],
            [-1, 1],
        )

    def test_non_handicap_play_ignores_letpoint(self):
        legs = build_structured_legs(
            [
                {
                    "team": "甲队:乙队",
                    "market_name": "胜平负",
                    "labels": ["主胜"],
                    "letpoint": "-2",
                }
            ]
        )
        self.assertEqual(legs[0]["handicap"], 0)

    def test_null_letpoint_does_not_raise_or_fallback(self):
        legs = build_structured_legs(
            [
                {
                    "team": "甲队:乙队",
                    "market_name": "让球胜平负",
                    "labels": ["让胜"],
                    "letpoint": None,
                }
            ]
        )
        self.assertEqual(legs[0]["handicap"], 0)
        self.assertFalse(legs[0]["used_legacy_fallback"])

    def test_legacy_fallback_is_explicit_and_logged(self):
        logs = []
        order = {
            "id": 9,
            "selection": "甲队:乙队→让球胜平负：让胜",
            "handicap": -2,
            "league": "旧数据",
        }

        legs = choose_legs(
            order,
            detail_response=None,
            logger=logs.append,
            allow_legacy_fallback=True,
        )

        self.assertEqual(legs[0]["handicap"], -2)
        self.assertTrue(legs[0]["used_legacy_fallback"])
        self.assertTrue(
            any("legacy fallback" in line for line in logs)
        )

    def test_online_default_rejects_unverified_legacy_fallback(self):
        order = {
            "id": 9,
            "selection": "甲队:乙队→让球胜平负：让胜",
            "handicap": -2,
            "league": "旧数据",
        }

        with self.assertRaises(RuntimeError):
            choose_legs(
                order,
                detail_response=None,
                logger=lambda _: None,
                allow_legacy_fallback=False,
            )

    def test_match_code_uses_match_id_not_team_id(self):
        _, decoded = decoded_caizhanyun_fixture()
        legs = build_structured_legs(decoded)

        self.assertEqual(legs[0]["match_code"], "2041053")
        self.assertNotEqual(legs[0]["match_code"], "005")
        self.assertEqual(legs[0]["team_id"], "005")

    def test_day_and_identity_candidate_are_retained(self):
        _, decoded = decoded_caizhanyun_fixture()
        legs = build_structured_legs(decoded)

        self.assertEqual(legs[0]["day"], "20260825")
        self.assertEqual(
            legs[0]["identity_candidate"],
            "1:20260825:2041053",
        )
        self.assertFalse(
            legs[0]["match_key"].startswith("20260825|")
        )

    def test_enddate_is_kickoff_proxy_not_deadline(self):
        _, decoded = decoded_caizhanyun_fixture()
        leg = build_structured_legs(decoded)[0]

        self.assertEqual(leg["enddate"], "08-25 22:00")
        self.assertEqual(
            leg["kickoff_time"].strftime(
                "%Y-%m-%d %H:%M"
            ),
            "2026-08-25 22:00",
        )
        self.assertEqual(
            leg["kickoff_source"],
            "kickoff_proxy",
        )
        self.assertFalse(leg["kickoff_exact"])
        self.assertIsNone(leg["deadline_time"])

    def test_end_time_is_not_written_to_each_leg(self):
        info, decoded = decoded_caizhanyun_fixture()
        fields = extract_caizhanyun_order_fields(info)
        legs = build_structured_legs(decoded)

        self.assertEqual(
            fields["end_time_candidate"].strftime(
                "%Y-%m-%d %H:%M"
            ),
            "2026-08-25 21:50",
        )
        self.assertFalse(
            fields["end_time_deadline_exact"]
        )
        self.assertTrue(
            all(
                leg["deadline_time"] is None
                for leg in legs
            )
        )


class CaizhanyunTimeAndAvatarTests(unittest.TestCase):
    def test_create_time_epoch_is_beijing_aware_then_db_naive(self):
        aware = parse_epoch_milliseconds_beijing(
            1787560615000
        )
        fields = extract_caizhanyun_order_fields(
            {"createTime": 1787560615000}
        )

        self.assertEqual(
            aware.isoformat(),
            "2026-08-24T16:36:55+08:00",
        )
        self.assertIsNotNone(aware.tzinfo)
        self.assertEqual(
            fields["publish_time"].strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "2026-08-24 16:36:55",
        )
        self.assertIsNone(
            fields["publish_time"].tzinfo
        )

    def test_head_pic_has_priority(self):
        self.assertEqual(
            select_avatar(
                detail_avatar="detail-head-pic",
                list_avatar="list-photo",
                existing_avatar="old-avatar",
            ),
            "detail-head-pic",
        )

    def test_stater_photo_is_fallback(self):
        self.assertEqual(
            select_avatar(
                detail_avatar="",
                list_avatar="list-photo",
                existing_avatar="old-avatar",
            ),
            "list-photo",
        )

    def test_empty_avatar_does_not_issue_database_update(self):
        caizhanyun_cursor = RecordingCursor()
        hongrui_cursor = RecordingCursor()

        self.assertFalse(
            save_caizhanyun_avatar(
                caizhanyun_cursor,
                1,
                "用户",
                "",
            )
        )
        self.assertFalse(
            save_hongrui_avatar(
                hongrui_cursor,
                1,
                "用户",
                "",
            )
        )
        self.assertEqual(caizhanyun_cursor.calls, [])
        self.assertEqual(hongrui_cursor.calls, [])

    def test_empty_list_avatar_does_not_update_profile(self):
        conn = RecordingConnection()
        order = {
            "platform_id": 1,
            "user_id": 10,
            "nickname": "用户",
            "avatar_url": "",
            "avatar_source": "caizhanyun_list",
        }

        with patch.object(
            save_user_module,
            "get_conn",
            return_value=conn,
        ):
            save_user_module.save_user(order)

        self.assertEqual(
            len(conn.cursor_instance.calls),
            1,
        )
        self.assertTrue(conn.committed)

    def test_detail_avatar_cannot_be_downgraded_by_list(self):
        conn = RecordingConnection()
        order = {
            "platform_id": 1,
            "user_id": 10,
            "nickname": "用户",
            "avatar_url": "list-photo",
            "avatar_source": "caizhanyun_list",
        }

        with patch.object(
            save_user_module,
            "get_conn",
            return_value=conn,
        ):
            save_user_module.save_user(order)

        profile_sql, profile_params = (
            conn.cursor_instance.calls[1]
        )
        normalized_sql = " ".join(
            profile_sql.split()
        )

        self.assertIn(
            "source='caizhanyun_detail'",
            normalized_sql,
        )
        self.assertIn(
            "VALUES(source)='caizhanyun_list'",
            normalized_sql,
        )
        self.assertEqual(
            profile_params[-1],
            "caizhanyun_list",
        )


class HongruiFieldTests(unittest.TestCase):
    def test_rq_number_is_per_play(self):
        parsed = parse_detail(hongrui_fixture())
        by_match = {
            (
                item["week_name"],
                item["market"],
            ): item["handicap"]
            for item in parsed["matches"]
        }

        self.assertEqual(
            by_match[("周二005", "让球胜平负")],
            -1,
        )
        self.assertEqual(
            by_match[("周二006", "让球胜平负")],
            1,
        )

    def test_non_handicap_hongrui_play_is_zero(self):
        self.assertEqual(
            resolve_hongrui_handicap(
                "胜平负",
                "-2",
            ),
            0,
        )
        parsed = parse_detail(hongrui_fixture())
        normal = next(
            item
            for item in parsed["matches"]
            if item["market"] == "胜平负"
        )
        self.assertEqual(normal["handicap"], 0)

    def test_expire_time_remains_unknown_and_not_exact(self):
        fields = extract_hongrui_source_fields(
            hongrui_fixture(),
            {"expire_time": "08-25 22:00"},
        )

        self.assertEqual(
            fields["expire_time_candidate"],
            "08-25 21:50",
        )
        self.assertEqual(
            fields["expire_time_semantic_status"],
            "unknown",
        )
        self.assertFalse(
            fields["expire_time_deadline_exact"]
        )

    def test_confirmed_statistics_are_read_from_real_layers(self):
        fields = extract_hongrui_source_fields(
            hongrui_fixture()
        )

        self.assertEqual(fields["fans_count"], 88)
        self.assertEqual(fields["profit_candidate"], "12.5")
        self.assertEqual(fields["bonus_num_candidate"], 7)
        self.assertEqual(fields["field_count_candidate"], 2)
        self.assertEqual(fields["status"], 1)
        self.assertEqual(fields["status_msg"], "进行中")
        self.assertEqual(fields["bonus"], "0")
        self.assertEqual(fields["commission_total"], "0")

    def test_detail_avatar_precedes_list_avatar(self):
        fields = extract_hongrui_source_fields(
            hongrui_fixture(),
            {
                "user": {
                    "user_pic": "list-avatar"
                }
            },
        )
        self.assertEqual(
            fields["avatar_url"],
            "detail-avatar",
        )

    def test_week_name_identity_is_incomplete(self):
        parsed = parse_detail(hongrui_fixture())
        self.assertTrue(parsed["matches"])
        self.assertTrue(
            all(
                item["identity_candidate"].startswith("周二")
                for item in parsed["matches"]
            )
        )
        self.assertTrue(
            all(
                not item["identity_complete"]
                for item in parsed["matches"]
            )
        )


if __name__ == "__main__":
    unittest.main()


