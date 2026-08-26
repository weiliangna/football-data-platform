import threading
import unittest

from common.platform_registry import (
    PLATFORM_DEFINITIONS,
    ensure_platform_configs,
)
from config.platform_ingestion_config import SourceContractUnavailable
from spider import haodianzhu, pipeline, qishilu, yuncai, zhouyunbao


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("offline HTTP status")

    def json(self):
        return self.payload


class RecordingSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse(self.responses.pop(0))

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse(self.responses.pop(0))


class PlatformConfigCursor:
    def __init__(self, rows):
        self.rows = rows
        self.result = []

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        if normalized.startswith("select platform_id"):
            self.result = [dict(row) for row in self.rows]
            return
        if normalized.startswith("insert into platform_config"):
            platform_id, name = params
            self.rows.append(
                {
                    "platform_id": platform_id,
                    "name": name,
                    "enabled": 1,
                    "spider_enabled": 1,
                    "result_enabled": 1,
                    "settlement_enabled": 1,
                }
            )
            return
        raise AssertionError("unexpected SQL in offline test")

    def fetchall(self):
        return list(self.result)

    def close(self):
        pass


class PlatformConfigConnection:
    def __init__(self, rows):
        self.rows = rows
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return PlatformConfigCursor(self.rows)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


def existing_platform_rows():
    names = {
        1: "彩站云",
        2: "州运宝",
        3: "鸿瑞",
        4: "云彩",
    }
    return [
        {
            "platform_id": platform_id,
            "name": name,
            "enabled": 1,
            "spider_enabled": 1,
            "result_enabled": 1,
            "settlement_enabled": 1,
        }
        for platform_id, name in names.items()
    ]


class PlatformRegistrationTests(unittest.TestCase):
    def test_missing_platforms_continue_from_current_max_id(self):
        rows = existing_platform_rows()
        connection = PlatformConfigConnection(rows)
        resolved = ensure_platform_configs(
            connection_factory=lambda: connection
        )
        self.assertEqual(resolved["haodianzhu"]["platform_id"], 5)
        self.assertEqual(resolved["qishilu"]["platform_id"], 6)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(len(rows), 6)

    def test_registration_is_idempotent(self):
        rows = existing_platform_rows()
        connection = PlatformConfigConnection(rows)
        first = ensure_platform_configs(
            connection_factory=lambda: connection
        )
        second = ensure_platform_configs(
            connection_factory=lambda: connection
        )
        self.assertEqual(len(rows), 6)
        self.assertEqual(
            first["haodianzhu"]["platform_id"],
            second["haodianzhu"]["platform_id"],
        )
        self.assertEqual(
            first["qishilu"]["platform_id"],
            second["qishilu"]["platform_id"],
        )


class VerifiedHttpContractTests(unittest.TestCase):
    def test_zhouyunbao_login_resolves_dynamic_user_for_requests(self):
        session = RecordingSession(
            [
                {
                    "errorCode": "0",
                    "data": {
                        "userId": 96710,
                        "storeId": "offline-store",
                    },
                },
                {
                    "errorCode": "0",
                    "data": {"rankList": [], "recommendList": []},
                },
                {
                    "errorCode": "0",
                    "data": {
                        "starterInfo": {},
                        "prescientInfo": {},
                    },
                },
            ]
        )
        client = zhouyunbao.ZhouyunbaoClient(
            config={
                "token": "offline-auth-value",
                "store_id": "offline-store",
                "bootstrap_user_id": "93",
                "login_url": "https://offline.invalid/login",
                "list_url": "https://offline.invalid/list",
                "detail_url": "https://offline.invalid/detail",
            },
            session=session,
        )
        client.list_orders(page_num=1, page_size=10)
        client.order_detail("P-OFFLINE")
        self.assertEqual(client.user_id, 96710)
        list_call = session.calls[1][2]
        detail_call = session.calls[2][2]
        self.assertEqual(
            list_call["json"]["currentUserId"],
            "96710",
        )
        self.assertEqual(
            detail_call["json"]["prescientId"],
            "P-OFFLINE",
        )
        self.assertEqual(list_call["headers"]["userid"], "96710")

    def test_haodianzhu_uses_verified_router_methods(self):
        session = RecordingSession(
            [
                {
                    "code": "0000",
                    "result": [],
                },
                {
                    "code": "0000",
                    "result": {"contentList": []},
                },
            ]
        )
        client = haodianzhu.HaodianzhuClient(
            config={
                "sid": "offline-session",
                "uuid": "offline-device",
                "cookie": "offline-cookie",
                "shop_id": "7876",
                "url": "https://offline.invalid/router/rest",
            },
            session=session,
        )
        client.list_orders()
        client.order_content("14958010")
        self.assertIn(
            "method=fying.pg.billing.recommend.v2",
            session.calls[0][1],
        )
        self.assertIn(
            "method=fying.bp.content.get",
            session.calls[1][1],
        )
        self.assertEqual(
            session.calls[1][2]["data"]["planId"],
            "14958010",
        )

    def test_haodianzhu_reports_business_error_code_and_message(self):
        session = RecordingSession(
            [
                {
                    "code": "OFFLINE-401",
                    "message": "offline session expired",
                }
            ]
        )
        client = haodianzhu.HaodianzhuClient(
            config={
                "sid": "offline-session",
                "uuid": "offline-device",
                "cookie": "offline-cookie",
                "shop_id": "7876",
                "url": "https://offline.invalid/router/rest",
            },
            session=session,
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "code=OFFLINE-401 message=offline session expired",
        ):
            client.list_orders()

    def test_qishilu_uses_verified_list_detail_and_profile_paths(self):
        session = RecordingSession(
            [
                {"code": 200, "rows": []},
                {"code": 200, "data": {"id": 1}},
                {"code": 200, "data": {"userId": 2}},
            ]
        )
        client = qishilu.QishiluClient(
            config={
                "authorization": "offline-auth-value",
                "base_url": "https://offline.invalid",
            },
            session=session,
        )
        client.list_orders()
        client.order_detail(1)
        client.user_profile(2)
        paths = [call[1] for call in session.calls]
        self.assertTrue(paths[0].endswith("/portal/follow/list"))
        self.assertTrue(
            paths[1].endswith(
                "/portal/follow/selectFollowProInfo"
            )
        )
        self.assertTrue(
            paths[2].endswith("/portal/follow/selectUserHome")
        )
        self.assertTrue(
            session.calls[0][2]["headers"]["Authorization"].startswith(
                "Bearer "
            )
        )

    def test_yuncai_refuses_to_replay_one_time_ciphertext(self):
        status = yuncai.live_contract_status(
            {
                "YUNCAI_AUTHORIZATION": "offline-auth-value",
                "YUNCAI_COOKIE": "offline-cookie",
                "YUNCAI_X_CA_KEY": "offline-signature",
            }
        )
        self.assertFalse(status["ready"])
        self.assertEqual(
            status["reason"],
            "dynamic_signature_contract_missing",
        )
        with self.assertRaises(SourceContractUnavailable):
            yuncai.run_live()


class QishiluMarketTests(unittest.TestCase):
    def test_verified_g504_maps_to_half_full(self):
        detail = {
            "code": 200,
            "data": {
                "id": 4070470,
                "userId": 2000022478,
                "userName": "离线用户",
                "proCalState": 1,
                "proTicketAward": 2,
                "bets": 100,
                "manner": "单关",
                "stopSaleTime": 20260826220000,
                "matchContent": __import__("json").dumps(
                    [
                        {
                            "group": "测试联赛",
                            "home": "主队",
                            "guest": "客队",
                            "matchId": "M-1",
                            "openingDate": "2026-08-26",
                            "score": "1:0",
                            "halfScore": "0:0",
                            "p504": "平胜",
                            "proCon": {
                                "g504": [
                                    {
                                        "is": True,
                                        "na": "平胜",
                                        "s": "5.20",
                                    }
                                ]
                            },
                        }
                    ],
                    ensure_ascii=False,
                ),
            },
        }
        record = qishilu.build_record(
            {
                "proId": 4070470,
                "userId": 2000022478,
                "userName": "离线用户",
                "avatar": "https://offline.invalid/avatar.jpg",
            },
            detail,
            platform_id=6,
        )
        self.assertEqual(record["legs"][0]["play_type"], "半全场")
        self.assertEqual(record["legs"][0]["handicap"], 0)
        self.assertEqual(record["legs"][0]["result"], "赢")


class UnifiedPipelineTests(unittest.TestCase):
    def test_six_platforms_run_concurrently_and_record_independently(self):
        barrier = threading.Barrier(len(PLATFORM_DEFINITIONS))
        runners = {}

        for definition in PLATFORM_DEFINITIONS:
            def runner(_runtime, key=definition.key):
                barrier.wait(timeout=2)
                if key == "yuncai":
                    raise SourceContractUnavailable("offline contract")
                if key == "qishilu":
                    raise RuntimeError("offline platform failure")
                return {
                    "new_count": 1,
                    "duplicate_count": 0,
                    "failed_count": 0,
                }

            runners[definition.key] = runner

        runtimes = {
            definition.key: {
                "platform_id": definition.preferred_id,
                "name": definition.name,
                "enabled": 1,
                "spider_enabled": 1,
                "result_enabled": 1,
                "settlement_enabled": 1,
            }
            for definition in PLATFORM_DEFINITIONS
        }
        recorded = []
        statuses = pipeline.run(
            platform_resolver=lambda: runtimes,
            runners=runners,
            status_recorder=recorded.append,
        )
        self.assertEqual(len(statuses), 6)
        self.assertEqual(recorded, statuses)
        by_name = {
            item["platform_name"]: item["status"]
            for item in statuses
        }
        self.assertEqual(by_name["云彩"], "waiting_contract")
        self.assertEqual(by_name["启示录"], "failed")
        self.assertEqual(by_name["好店主"], "success")
        self.assertEqual(by_name["州运宝"], "success")


if __name__ == "__main__":
    unittest.main()
