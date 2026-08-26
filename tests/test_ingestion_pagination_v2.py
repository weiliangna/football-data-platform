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
    pymysql_stub.connect = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("offline test attempted database connection")
    )
    sys.modules["pymysql"] = pymysql_stub


from spider import caizhanyun, haodianzhu, qishilu
from spider.pagination import collect_numbered_pages
from api.portal import enrich_order


ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class CaizhanyunSession:
    def __init__(self):
        self.pages = []

    def post(self, _url, **kwargs):
        page = kwargs["json"]["pageNum"]
        self.pages.append(page)
        rows = (
            [{"id": "C-1"}, {"id": "C-2"}]
            if page == 1
            else [{"id": "C-3"}]
        )
        return FakeResponse(
            {
                "errorCode": "0",
                "data": {"rankList": rows},
            }
        )


class HaodianzhuClient:
    def __init__(self):
        self.pages = []
        self.profile_calls = []

    def list_orders(self, page, page_size):
        self.pages.append((page, page_size))
        if page == 1:
            return {
                "code": "0000",
                "result": [
                    {"planId": "H-1", "memberId": 10},
                    {"planId": "H-2", "memberId": 20},
                ],
                "hasNext": True,
                "nextPage": 2,
            }
        return {
            "code": "0000",
            "result": [{"planId": "H-3", "memberId": 10}],
            "hasNext": False,
            "nextPage": None,
        }

    def profile(self, member_id):
        self.profile_calls.append(member_id)
        return {
            "code": "0000",
            "memberId": member_id,
            "nickName": f"用户{member_id}",
            "headImage": f"https://offline.invalid/{member_id}.jpg",
        }

    def history(self, _member_id, page=1, page_size=99):
        return {"code": "0000", "result": []}

    def order_content(self, _plan_id):
        return {"code": "0000", "result": {"contentList": []}}


class PaginationTests(unittest.TestCase):
    def test_numbered_pages_deduplicate_and_stop(self):
        responses = {
            1: {"rows": [{"id": 1}, {"id": 2}]},
            2: {"rows": [{"id": 2}, {"id": 3}]},
            3: {"rows": []},
        }
        rows = collect_numbered_pages(
            lambda page, _size: responses[page],
            lambda response: response["rows"],
            lambda item: item["id"],
            page_size=2,
        )
        self.assertEqual([item["id"] for item in rows], [1, 2, 3])

    def test_known_total_continues_when_server_caps_page_size(self):
        pages = []

        def fetch(page, _size):
            pages.append(page)
            start = (page - 1) * 2
            return {
                "total": 5,
                "rows": [
                    {"id": value}
                    for value in range(start + 1, min(start + 3, 6))
                ],
            }

        rows = collect_numbered_pages(
            fetch,
            lambda response: response["rows"],
            lambda item: item["id"],
            page_size=50,
            metadata=lambda response: {"total": response["total"]},
        )
        self.assertEqual(pages, [1, 2, 3])
        self.assertEqual(len(rows), 5)

    def test_caizhanyun_collects_every_page(self):
        session = CaizhanyunSession()
        with patch.dict(
            caizhanyun.CONFIG,
            {"token": "offline-token", "cookie": "offline-cookie"},
        ):
            rows = caizhanyun.get_orders(
                session=session,
                page_size=2,
                max_pages=5,
            )
        self.assertEqual(session.pages, [1, 2])
        self.assertEqual([item["id"] for item in rows], ["C-1", "C-2", "C-3"])

    def test_haodianzhu_uses_has_next_and_enriches_all_avatars(self):
        client = HaodianzhuClient()
        rows, _details = haodianzhu.collect_live_items(
            client,
            pending_refs=[],
            page_size=2,
        )
        self.assertEqual([item["planId"] for item in rows], ["H-1", "H-2", "H-3"])
        self.assertEqual(client.pages, [(1, 2), (2, 2)])
        self.assertEqual(client.profile_calls, [10, 20])
        self.assertTrue(all(item.get("headImage") for item in rows))

    def test_qishilu_profile_overrides_list_avatar(self):
        class Client:
            def user_profile(self, user_id):
                return {
                    "code": 200,
                    "data": {
                        "userId": user_id,
                        "nickName": "主页昵称",
                        "avatar": "https://offline.invalid/profile.jpg",
                    },
                }

        rows = qishilu._merge_live_items(
            Client(),
            [{"proId": 1, "userId": 2, "userName": "列表昵称"}],
            [],
        )
        self.assertEqual(rows[0]["userName"], "主页昵称")
        self.assertEqual(rows[0]["avatar"], "https://offline.invalid/profile.jpg")

    def test_yuncai_dynamic_signer_is_still_required(self):
        module = importlib.import_module("spider.yuncai")
        status = module.live_contract_status(
            {
                "YUNCAI_AUTHORIZATION": "offline-auth",
                "YUNCAI_COOKIE": "offline-cookie",
                "YUNCAI_X_CA_KEY": "offline-key",
            }
        )
        self.assertFalse(status["ready"])
        self.assertEqual(status["reason"], "dynamic_signature_contract_missing")


class FrontendContractTests(unittest.TestCase):
    def test_portal_enriches_scheme_with_user_history(self):
        order = enrich_order(
            {"id": 1, "platform_id": 3, "user_id": 9},
            [],
            {},
            {},
            {
                (3, 9): {
                    "total_orders": 8,
                    "win_orders": 5,
                    "lose_orders": 3,
                    "hit_rate": 62.5,
                    "roi": 12.3,
                }
            },
        )
        self.assertEqual(order["history_record"], "5胜3负")
        self.assertEqual(order["history_hit_rate"], 62.5)

    def test_orders_use_avatar_modal_platform_palette_and_history(self):
        source = (ROOT / "frontend" / "src" / "views" / "Orders.vue").read_text(encoding="utf-8")
        self.assertIn('v-if="order.avatar_url"', source)
        self.assertIn("user-modal", source)
        self.assertIn("rgba(${color.join", source)
        self.assertIn("历史战绩", source)
        self.assertIn("order.history_record", source)

    def test_home_ranking_is_five_rows_high_and_scrollable(self):
        source = (ROOT / "frontend" / "src" / "views" / "Home.vue").read_text(encoding="utf-8")
        self.assertIn("默认展示 5 位", source)
        self.assertIn("height:350px", source)
        self.assertIn("overflow-y:auto", source)

    def test_heatmap_keeps_api_and_uses_matrix_table(self):
        source = (ROOT / "frontend" / "src" / "views" / "Heatmap.vue").read_text(encoding="utf-8")
        self.assertIn('/api/portal/heatmap', source)
        self.assertIn("matrix-table", source)
        self.assertIn("各玩法重心分析", source)


if __name__ == "__main__":
    unittest.main()
