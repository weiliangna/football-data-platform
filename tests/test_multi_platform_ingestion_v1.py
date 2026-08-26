import copy
import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


try:
    import pymysql  # noqa: F401
except ModuleNotFoundError:
    pymysql_stub = types.ModuleType("pymysql")
    pymysql_stub.cursors = types.SimpleNamespace(
        DictCursor=object,
        Cursor=object,
    )

    def forbidden_connect(*args, **kwargs):
        raise AssertionError("offline test attempted database connection")

    pymysql_stub.connect = forbidden_connect
    sys.modules["pymysql"] = pymysql_stub


try:
    import requests  # noqa: F401
except ModuleNotFoundError:
    requests_stub = types.ModuleType("requests")

    class OfflineSession:
        created = 0
        post_calls = 0

        def __init__(self):
            type(self).created += 1
            self.headers = {}

        def post(self, *args, **kwargs):
            type(self).post_calls += 1
            raise AssertionError("offline test attempted HTTP")

    requests_stub.Session = OfflineSession
    requests_stub.post = (
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("offline test attempted HTTP")
        )
    )
    sys.modules["requests"] = requests_stub


from config.caizhanyun_config import get_caizhanyun_config
from spider import caizhanyun, haodianzhu, qishilu, yuncai, zhouyunbao
from spider.unified_ingestion import (
    DatabaseRepository,
    PlatformOrderCollision,
)


ROOT = Path(__file__).resolve().parents[1]


class RecordingRepository:
    def __init__(self):
        self.records = {}
        self.calls = []

    def save(self, record):
        key = (
            int(record["platform_id"]),
            str(record["order"]["platform_order_id"]),
        )
        inserted = key not in self.records
        self.records[key] = copy.deepcopy(record)
        self.calls.append(key)
        return {
            "order_id": len(self.records),
            "inserted_order": inserted,
            "inserted_legs": len(record.get("legs") or []),
            "updated_legs": 0 if inserted else len(record.get("legs") or []),
            "saved_results": len(record.get("match_results") or []),
            "skipped_results": 0,
        }


def magicangle_list_response():
    return {
        "errorCode": "0",
        "value": "成功",
        "data": {
            "rankList": [
                {
                    "id": "P-100",
                    "starterId": "75049",
                    "staterName": "测试用户",
                    "staterPhoto": "https://img.example/avatar.jpg",
                    "selfBuyAmt": 20000,
                    "fansNumber": 7,
                    "profitRate": 12,
                }
            ],
            "recommendList": [],
        },
    }


def magicangle_detail_response():
    return {
        "errorCode": "0",
        "value": "成功",
        "data": {
            "starterInfo": {
                "id": 75049,
                "nickname": "测试用户",
                "headPic": "https://img.example/detail-avatar.jpg",
                "militaryInfo": {
                    "hitRate": "80.00",
                    "earningsRate": "25.00",
                },
            },
            "prescientInfo": {
                "id": "P-100",
                "lotNo": "MIX",
                "playType": "MIX",
                "createTime": 1787627709000,
                "winFlag": 2,
                "description": "离线样本",
                "selfBuyAmt": 20000,
                "followerNumber": 9,
                "allPrizeAmt": 50000,
                "commission": 1000,
                "betCodeForResult": (
                    "502@20260825|2|005|J00001|3^"
                    "20260825|2|006|J00013|1"
                ),
                "jingcaiResultList": [
                    {
                        "team": "主队甲:客队甲",
                        "teamId": "005",
                        "week": "2",
                        "day": "20260825",
                        "enddate": "08-25 22:00",
                        "league": "测试联赛",
                        "matchId": "2041053",
                        "letpoint": None,
                        "result": "2:1",
                        "firsthalfresult": "1:0",
                        "peilvs": [
                            {
                                "type": "v3",
                                "peilv": "1.80",
                                "isHit": "true",
                            }
                        ],
                    },
                    {
                        "team": "主队乙：客队乙",
                        "teamId": "006",
                        "week": "2",
                        "day": "20260825",
                        "enddate": "08-25 22:00",
                        "league": "测试联赛",
                        "matchId": "2041054",
                        "letpoint": "-1",
                        "result": "1:1",
                        "firsthalfresult": "0:0",
                        "peilvs": [
                            {
                                "type": "letVs_v1",
                                "peilv": "3.20",
                                "isHit": "false",
                            }
                        ],
                    },
                ],
            },
        },
    }


def yuncai_list_response():
    return {
        "code": 200,
        "data": {
            "total": 1,
            "rows": [
                {
                    "orderId": 11704985,
                    "userId": 60352,
                    "nickName": "云彩用户",
                    "imgUrl": "https://img.example/yuncai.jpg",
                    "amount": 2888.0,
                    "passType": "2串1",
                    "followNum": 12,
                    "hitRate": 0.8,
                    "profitability": 9.56,
                }
            ],
        },
    }


def yuncai_detail_response():
    return {
        "code": 200,
        "data": {
            "userId": 60352,
            "nickName": "云彩用户",
            "imgUrl": "https://img.example/yuncai-detail.jpg",
            "declaration": "离线样本",
            "amount": 2888.0,
            "winStatus": 2,
            "ticketStatus": 3,
            "returnAmount": 35002.56,
            "commission": 100.0,
            "orderId": 11704985,
            "orderNo": "ORDER-NO-1",
            "lotteryName": "竞彩足球",
            "bettingString": "2串1",
            "betFreePass": "2串1",
            "buyEndTime": "2026-08-23 22:45:00",
            "trackingOrderUserCount": 20,
            "totalHitRate": 0.5172,
            "totalProfitability": 4.6796,
            "betContentJZCDtoList": [
                {
                    "competitionSessions": "周日014",
                    "matchScore": "2:5",
                    "halfMatchScore": "0:4",
                    "home": "主队甲",
                    "away": "客队甲",
                    "betPlayListList": [
                        {
                            "betPlay": "进球数",
                            "betHandicap": "",
                            "betItem": "7+",
                            "betOdds": "9.25",
                            "result": "7+",
                            "hasHit": 1,
                        }
                    ],
                },
                {
                    "competitionSessions": "周日018",
                    "matchScore": "0:1",
                    "halfMatchScore": "0:1",
                    "home": "主队乙",
                    "away": "客队乙",
                    "betPlayListList": [
                        {
                            "betPlay": "让球胜平负",
                            "betHandicap": "-1",
                            "betItem": "让负",
                            "betOdds": "2.40",
                            "result": "让负",
                            "hasHit": 1,
                        }
                    ],
                },
            ],
        },
    }


def haodianzhu_list_response():
    return {
        "code": "0000",
        "message": "ok",
        "result": [
            {
                "memberId": 1065442,
                "headImage": "https://img.example/hdz.jpg",
                "name": "好店主用户",
                "lottery_type": "竞彩足球",
                "pass_type": "固定单关",
                "amount": 20,
                "follow": 3,
                "status": 3,
                "planId": 14849617,
                "createTime": "2026-08-23 21:47:16",
                "description": "离线样本",
                "recentHitRateValue": 80,
                "overallReturnRateValue": 2.1,
                "daShenStatistics": {},
            }
        ],
    }


def haodianzhu_history_response(option_text="胜-胜"):
    return {
        "code": "0000",
        "message": "ok",
        "result": [
            {
                "planId": 14849617,
                "passType": "固定单关",
                "lottery_type_name": "竞彩足球",
                "memberId": 1065442,
                "status": 4,
                "win_status": 3,
                "postax_prize": 48.0,
                "create_time": "2026-08-23 21:47:16",
                "multiple": 10,
                "myself_amount": 20,
                "deduct_amount": 0,
                "contentList": [
                    {
                        "raceNo": "260823012",
                        "bet_concede": None,
                        "itemList": [
                            {
                                "val": "33",
                                "text": option_text,
                                "sp": "2.40",
                                "hit": True,
                            }
                        ],
                        "race": {
                            "race_no": "260823012",
                            "league_name": "葡超",
                            "home_team": "主队",
                            "guest_team": "客队",
                            "match_time": "2026-08-23 22:30:00",
                            "sell_stop_time": "2026-08-23 22:00:00",
                            "zcrace": {
                                "concede": -1,
                                "final_score": "1:0",
                                "half_score": "1:0",
                            },
                        },
                    }
                ],
            }
        ],
    }


def qishilu_list_response():
    return {
        "total": 1,
        "rows": [
            {
                "proId": 4011854,
                "userId": 2000043004,
                "userName": "启示录用户",
                "avatar": "https://img.example/qsl.jpg",
                "proGameCodeName": "竞足",
                "stopSaleTime": 20260823230000,
                "payTime": "20260821152912",
                "proClaim": "离线样本",
                "bets": 200000,
                "hitRate": 4,
                "profitMargin": 129,
                "oneMultiple": 2.0,
            }
        ],
        "code": 200,
    }


def qishilu_detail_response(market_key="g501"):
    match = {
        "group": "西甲",
        "guest": "客队",
        "home": "主队",
        "matchId": "2041021",
        "openingDate": "2026-08-23",
        "proCon": {
            market_key: [
                {"is": True, "na": "胜", "o": "3", "s": "1.93"},
                {"is": False, "na": "平", "o": "1", "s": "2.88"},
            ]
        },
        "score": "1:0",
        "halfScore": "0:0",
        "p501": "胜",
    }
    return {
        "code": 200,
        "data": {
            "id": 4011854,
            "userId": 2000043004,
            "userName": "启示录用户",
            "proCalState": 1,
            "proTicketAward": 2,
            "bets": 200000,
            "manner": "单关",
            "matchContent": __import__("json").dumps(
                [match],
                ensure_ascii=False,
            ),
            "dataContent": "501//3;1.93",
            "stopSaleTime": 20260823230000,
            "proAwardMoney": 386000,
            "proCommission": 23887.36,
            "proGameCodeName": "竞足",
            "proClaim": "离线样本",
            "createTime": "2026-08-21T15:27:23",
            "proAwardDistributionTime": 20260824095740,
        },
    }


class SourceContractTests(unittest.TestCase):
    def test_zhouyunbao_complete_normalized_chain(self):
        record = zhouyunbao.build_record(
            magicangle_list_response()["data"]["rankList"][0],
            magicangle_detail_response(),
        )
        self.assertEqual(record["platform_id"], 2)
        self.assertEqual(record["user"]["user_id"], 75049)
        self.assertEqual(
            record["user"]["avatar_url"],
            "https://img.example/detail-avatar.jpg",
        )
        self.assertEqual(record["order"]["result"], "赢")
        self.assertEqual(len(record["legs"]), 2)
        self.assertEqual(record["legs"][0]["handicap"], 0)
        self.assertEqual(record["legs"][1]["handicap"], -1)
        self.assertEqual(record["legs"][0]["result"], "赢")
        self.assertEqual(record["legs"][1]["result"], "输")
        self.assertEqual(record["legs"][0]["match_date"], "20260825")
        self.assertEqual(record["legs"][0]["source_match_code"], "2041053")
        self.assertEqual(len(record["match_results"]), 2)

    def test_zhouyunbao_ingestion_is_idempotent_and_logs_status(self):
        repository = RecordingRepository()
        statuses = []
        fetcher = lambda _source_id, _item: magicangle_detail_response()
        first = zhouyunbao.ingest_responses(
            magicangle_list_response(),
            fetcher,
            repository=repository,
            status_recorder=statuses.append,
        )
        second = zhouyunbao.ingest_responses(
            magicangle_list_response(),
            fetcher,
            repository=repository,
            status_recorder=statuses.append,
        )
        self.assertEqual(first["new_count"], 1)
        self.assertEqual(second["duplicate_count"], 1)
        self.assertEqual(len(repository.records), 1)
        self.assertEqual([item["status"] for item in statuses], ["success", "success"])

    def test_yuncai_maps_verified_legs_results_deadline_and_avatar(self):
        item = yuncai.parse_list_response(yuncai_list_response())[0]
        record = yuncai.build_record(item, yuncai_detail_response())
        self.assertEqual(record["platform_id"], 4)
        self.assertEqual(record["user"]["avatar_source"], "yuncai_response")
        self.assertEqual(record["order"]["result"], "赢")
        self.assertEqual(len(record["legs"]), 2)
        self.assertEqual(record["legs"][0]["play_type"], "总进球")
        self.assertEqual(record["legs"][0]["handicap"], 0)
        self.assertEqual(record["legs"][1]["play_type"], "让球胜平负")
        self.assertEqual(record["legs"][1]["handicap"], -1)
        self.assertTrue(record["legs"][0]["deadline_exact"])
        self.assertIsNone(record["legs"][0]["match_date"])
        self.assertEqual(len(record["match_results"]), 2)
        self.assertTrue(any("match_date_unavailable" in value for value in record["issues"]))

    def test_haodianzhu_requires_assigned_platform_id(self):
        item = haodianzhu.parse_list_response(
            haodianzhu_list_response()
        )[0]
        history = haodianzhu.parse_history_response(
            haodianzhu_history_response()
        )[0]
        with self.assertRaisesRegex(ValueError, "platform_id"):
            haodianzhu.build_record(item, history, 0)

    def test_haodianzhu_verified_half_full_leg_and_result(self):
        item = haodianzhu.parse_list_response(
            haodianzhu_list_response()
        )[0]
        history = haodianzhu.parse_history_response(
            haodianzhu_history_response()
        )[0]
        record = haodianzhu.build_record(item, history, 5)
        self.assertEqual(record["order"]["result"], "赢")
        self.assertEqual(len(record["legs"]), 1)
        self.assertEqual(record["legs"][0]["play_type"], "半全场")
        self.assertEqual(record["legs"][0]["handicap"], 0)
        self.assertTrue(record["legs"][0]["deadline_exact"])
        self.assertEqual(str(record["legs"][0]["match_date"]), "2026-08-23")
        self.assertEqual(len(record["match_results"]), 1)

    def test_haodianzhu_ambiguous_play_is_not_guessed(self):
        item = haodianzhu.parse_list_response(
            haodianzhu_list_response()
        )[0]
        history = haodianzhu.parse_history_response(
            haodianzhu_history_response(option_text="胜")
        )[0]
        record = haodianzhu.build_record(item, history, 5)
        self.assertEqual(record["legs"], [])
        self.assertTrue(any("ambiguous_play_type" in value for value in record["issues"]))
        self.assertEqual(len(record["match_results"]), 1)

    def test_qishilu_verified_501_market_identity_result_and_avatar(self):
        item = qishilu.parse_list_response(qishilu_list_response())[0]
        record = qishilu.build_record(
            item,
            qishilu_detail_response(),
            6,
        )
        self.assertEqual(record["user"]["avatar_source"], "qishilu_list")
        self.assertEqual(record["order"]["result"], "赢")
        self.assertEqual(len(record["legs"]), 1)
        self.assertEqual(record["legs"][0]["play_type"], "胜平负")
        self.assertEqual(record["legs"][0]["selection"], "主胜")
        self.assertEqual(record["legs"][0]["source_match_code"], "2041021")
        self.assertEqual(record["legs"][0]["match_date"], "2026-08-23")
        self.assertEqual(record["legs"][0]["result"], "赢")
        self.assertEqual(len(record["match_results"]), 1)

    def test_qishilu_unknown_market_is_not_guessed(self):
        item = qishilu.parse_list_response(qishilu_list_response())[0]
        record = qishilu.build_record(
            item,
            qishilu_detail_response(market_key="g999"),
            6,
        )
        self.assertEqual(record["legs"], [])
        self.assertTrue(any("unverified_market:g999" in value for value in record["issues"]))

    def test_one_failed_detail_does_not_stop_other_orders_or_status(self):
        response = magicangle_list_response()
        response["data"]["rankList"].append(
            {
                **response["data"]["rankList"][0],
                "id": "P-FAIL",
            }
        )
        repository = RecordingRepository()
        statuses = []

        def fetch(source_id, _item):
            if source_id == "P-FAIL":
                raise RuntimeError("offline detail failure")
            return magicangle_detail_response()

        summary = zhouyunbao.ingest_responses(
            response,
            fetch,
            repository=repository,
            status_recorder=statuses.append,
        )
        self.assertEqual(summary["new_count"], 1)
        self.assertEqual(summary["failed_count"], 1)
        self.assertEqual(summary["status"], "partial")
        self.assertEqual(statuses[0]["status"], "partial")


class ExistingPlatformAuditTests(unittest.TestCase):
    def test_caizhanyun_config_has_verified_fallback_and_env_override(self):
        config = get_caizhanyun_config(
            {
                "CAIZHANYUN_TOKEN": "fixture-token",
                "CAIZHANYUN_COOKIE": "fixture-cookie",
            }
        )
        self.assertEqual(config["store_id"], "ds711")
        self.assertEqual(config["request_user_id"], "260610")
        override = get_caizhanyun_config(
            {
                "CAIZHANYUN_TOKEN": "fixture-token",
                "CAIZHANYUN_COOKIE": "fixture-cookie",
                "CAIZHANYUN_STORE_ID": "fixture-store",
            }
        )
        self.assertEqual(override["store_id"], "fixture-store")

    def test_caizhanyun_import_and_normalization_do_not_use_http_or_db(self):
        module = importlib.reload(caizhanyun)
        order = module.normalize_list_item(
            magicangle_list_response()["data"]["rankList"][0]
        )
        self.assertEqual(order["platform_order_id"], "P-100")
        self.assertEqual(order["user_id"], "75049")

    def test_hongrui_preview_accepts_alias_map(self):
        from spider import hongrui

        raw = {
            "code": 1,
            "data": {
                "head": {
                    "user_id": 1,
                    "user_name": "测试用户",
                    "purchase_amount": "100",
                },
                "order_message": {
                    "customs": "单关",
                    "lottery_list": [],
                },
                "follow_count": "0",
            },
        }
        with patch("builtins.print"):
            hongrui.preview_order(
                {"order_id": 10, "user": {}, "order_detail": {}},
                raw,
                alias_map={},
            )

    def test_hongrui_write_chain_upserts_users(self):
        source = (ROOT / "spider" / "hongrui.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("INSERT INTO users", source)
        self.assertIn("alias_map=alias_map", source)


class DatabaseSafetyTests(unittest.TestCase):
    def test_cross_platform_global_order_id_collision_is_rejected(self):
        class CollisionCursor:
            def execute(self, sql, params=()):
                self.sql = sql

            def fetchone(self):
                return {
                    "id": 9,
                    "platform_id": 1,
                    "result": "待开奖",
                    "profit": 0,
                    "platform_bonus": 0,
                    "commission_total": 0,
                    "settlement_status": "",
                    "settled_time": None,
                }

        repository = DatabaseRepository(
            connection_factory=lambda: None
        )
        record = zhouyunbao.build_record(
            magicangle_list_response()["data"]["rankList"][0],
            magicangle_detail_response(),
        )
        with self.assertRaises(PlatformOrderCollision):
            repository._save_order(CollisionCursor(), record)

    def test_unified_writer_never_deletes_orders_or_order_matches(self):
        source = (
            ROOT / "spider" / "unified_ingestion.py"
        ).read_text(encoding="utf-8").lower()
        self.assertNotIn("delete from orders", source)
        self.assertNotIn("delete from order_matches", source)


if __name__ == "__main__":
    unittest.main()
