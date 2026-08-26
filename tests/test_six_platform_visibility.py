import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_platform_module(get_conn=None):
    fake_mysql = types.ModuleType("database.mysql")
    fake_mysql.get_conn = get_conn or (lambda: None)
    module_name = "platform_visibility_test_module"
    spec = importlib.util.spec_from_file_location(
        module_name,
        ROOT / "api" / "platform.py",
    )
    module = importlib.util.module_from_spec(spec)

    with patch.dict(
        sys.modules,
        {
            "database.mysql": fake_mysql,
            module_name: module,
        },
    ):
        spec.loader.exec_module(module)

    return module


class PlatformApiVisibilityTests(unittest.TestCase):
    def test_four_database_rows_are_completed_to_six(self):
        module = load_platform_module()
        rows = [
            {
                "platform_id": 1,
                "name": "彩站云",
                "enabled": 1,
                "spider_enabled": 1,
                "result_enabled": 1,
                "settlement_enabled": 1,
            },
            {
                "platform_id": 2,
                "name": "州运宝",
                "enabled": 1,
                "spider_enabled": 1,
                "result_enabled": 1,
                "settlement_enabled": 1,
            },
            {
                "platform_id": 3,
                "name": "鸿瑞",
                "enabled": 1,
                "spider_enabled": 1,
                "result_enabled": 1,
                "settlement_enabled": 1,
            },
            {
                "platform_id": 4,
                "name": "云彩",
                "enabled": 1,
                "spider_enabled": 1,
                "result_enabled": 1,
                "settlement_enabled": 1,
            },
        ]

        merged = module.merge_platform_configs(rows)

        self.assertEqual(len(merged), 6)
        self.assertEqual(
            [(item["platform_id"], item["name"]) for item in merged],
            [
                (1, "彩站云"),
                (2, "州运宝"),
                (3, "鸿瑞"),
                (4, "云彩"),
                (5, "好店主"),
                (6, "启示录"),
            ],
        )
        self.assertFalse(merged[4]["configured"])
        self.assertFalse(merged[5]["configured"])

    def test_occupied_preferred_ids_continue_from_current_max(self):
        module = load_platform_module()
        rows = [
            {
                "platform_id": platform_id,
                "name": name,
            }
            for platform_id, name in (
                (1, "彩站云"),
                (2, "州运宝"),
                (3, "鸿瑞"),
                (4, "云彩"),
                (5, "既有平台"),
            )
        ]

        merged = module.merge_platform_configs(rows)
        by_name = {item["name"]: item for item in merged}

        self.assertEqual(by_name["好店主"]["platform_id"], 6)
        self.assertEqual(by_name["启示录"]["platform_id"], 7)
        self.assertEqual(by_name["既有平台"]["platform_id"], 5)

    def test_database_failure_returns_safe_six_platform_fallback(self):
        def unavailable():
            raise RuntimeError("database detail must not leak")

        module = load_platform_module(unavailable)
        response = module.platform_list()

        self.assertEqual(response["code"], 200)
        self.assertEqual(response["status"], "degraded")
        self.assertEqual(len(response["data"]), 6)
        self.assertNotIn("database detail", response["msg"])

    def test_runtime_status_uses_latest_sync_result(self):
        module = load_platform_module()
        platforms = module.merge_platform_configs(
            [
                {
                    "platform_id": 2,
                    "name": "州运宝",
                    "enabled": 1,
                },
                {
                    "platform_id": 3,
                    "name": "鸿瑞",
                    "enabled": 1,
                },
            ]
        )
        rows = module.attach_runtime_status(
            platforms,
            [
                {
                    "platform_id": 2,
                    "status": "waiting_config",
                    "new_count": 0,
                },
                {
                    "platform_id": 3,
                    "status": "success",
                    "new_count": 65,
                },
            ],
        )
        by_id = {item["platform_id"]: item for item in rows}

        self.assertEqual(by_id[2]["runtime_status"], "waiting_config")
        self.assertFalse(by_id[2]["runtime_ready"])
        self.assertEqual(by_id[3]["runtime_status"], "success")
        self.assertTrue(by_id[3]["runtime_ready"])
        self.assertEqual(by_id[3]["last_new_count"], 65)


class FrontendPlatformVisibilityTests(unittest.TestCase):
    def test_experts_page_loads_platform_api_and_has_six_fallbacks(self):
        source = (
            ROOT / "frontend" / "src" / "views" / "Experts.vue"
        ).read_text(encoding="utf-8-sig")

        self.assertIn('/api/platform/list', source)
        for name in (
            "彩站云",
            "州运宝",
            "鸿瑞",
            "云彩",
            "好店主",
            "启示录",
        ):
            self.assertIn(name, source)

    def test_sidebar_shows_runtime_status_instead_of_database_flag(self):
        source = (
            ROOT
            / "frontend"
            / "src"
            / "components"
            / "layout"
            / "AppSidebar.vue"
        ).read_text(encoding="utf-8-sig")

        for label in ("部分成功", "采集失败", "缺少配置", "契约待补"):
            self.assertIn(label, source)
        self.assertIn("item.runtime_status", source)


if __name__ == "__main__":
    unittest.main()
