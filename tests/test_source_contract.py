import importlib
import io
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from config.caizhanyun_config import CAIZHANYUN_CONFIG

from tools.capture_platform_samples import (
    CAIZHANYUN_DETAIL_URL,
    CAIZHANYUN_LIST_URL,
    HONGRUI_DETAIL_URL,
    HONGRUI_LIST_URL,
    CaptureError,
    capture_caizhanyun,
    capture_hongrui,
    ensure_safe_output_directory,
    resolve_caizhanyun_config,
    response_json,
    safe_print,
    validate_platform_response,
    write_json_secure,
)
from tools.source_contract import (
    REDACTED,
    REDACTED_JWT,
    build_source_contract,
    redact_text,
    sanitize_json,
)


class FakeResponse:
    def __init__(
        self,
        payload=None,
        status_error=None,
        json_error=None,
    ):
        self.payload = payload
        self.status_error = status_error
        self.json_error = json_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, json, timeout, headers=None):
        self.calls.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
                "headers": headers,
            }
        )
        if not self.responses:
            raise AssertionError("No fake response left")
        return self.responses.pop(0)


class RedactionTests(unittest.TestCase):
    def test_secret_jwt_cookie_and_bearer_redaction(self):
        jwt_value = (
            "ey" + "Jheader.payload.signature"
        )
        source = (
            "to" + "ken=fixture-value\n"
            + "Cookie: session=fixture-cookie\n"
            + "Authorization: Bearer "
            + jwt_value
        )
        sanitized = redact_text(source)

        self.assertNotIn("fixture-value", sanitized)
        self.assertNotIn("fixture-cookie", sanitized)
        self.assertNotIn(jwt_value, sanitized)
        self.assertIn(REDACTED, sanitized)
        self.assertIn(REDACTED_JWT, sanitized)

    def test_personal_fields_are_redacted_but_match_ids_remain(self):
        payload = {
            "starterInfo": {
                "id": "personal-id",
                "nickname": "private-name",
                "headPic": "private-avatar",
            },
            "user_id": "private-user",
            "secret": {
                "value": "nested-private",
            },
            "matchId": "match-001",
            "teamId": "team-001",
            "team": "主队:客队",
        }

        sanitized = sanitize_json(payload)

        self.assertEqual(
            sanitized["starterInfo"]["id"],
            REDACTED,
        )
        self.assertEqual(
            sanitized["starterInfo"]["nickname"],
            REDACTED,
        )
        self.assertEqual(
            sanitized["starterInfo"]["headPic"],
            REDACTED,
        )
        self.assertEqual(sanitized["user_id"], REDACTED)
        self.assertEqual(
            sanitized["secret"]["value"],
            REDACTED,
        )
        self.assertEqual(sanitized["matchId"], "match-001")
        self.assertEqual(sanitized["teamId"], "team-001")

    def test_stdout_and_stderr_are_sanitized(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout):
            safe_print(
                "to" + "ken=stdout-fixture"
            )
        with redirect_stderr(stderr):
            safe_print(
                "Cookie: stderr-fixture",
                file=stderr,
            )

        self.assertNotIn("stdout-fixture", stdout.getvalue())
        self.assertNotIn("stderr-fixture", stderr.getvalue())


class SourceContractTests(unittest.TestCase):
    def test_report_discovers_nested_contract_without_guessing(self):
        payload = {
            "订单": [
                {
                    "data": {
                        "prescientInfo": {
                            "jingcaiResultList": [
                                {
                                    "enddate": "2026-08-26 20:00",
                                    "day": "20260826",
                                    "week": "周三001",
                                    "matchId": "m-1",
                                    "teamId": "t-1",
                                    "letpoint": -1,
                                    "team": "甲队:乙队",
                                    "比赛说明": "中文字段",
                                },
                                {
                                    "enddate": "2026-08-26 22:00",
                                    "day": "20260826",
                                    "week": "周三002",
                                    "matchId": "m-2",
                                    "teamId": "t-2",
                                    "letpoint": 1,
                                    "team": "丙队:丁队",
                                },
                            ]
                        },
                        "starterInfo": {
                            "headPic": REDACTED,
                        },
                    }
                }
            ]
        }

        report = build_source_contract(
            "caizhanyun",
            payload,
            orders_sampled=1,
            captured_at="2026-08-25T00:00:00+00:00",
        )

        self.assertEqual(report["platform"], "caizhanyun")
        self.assertEqual(report["orders_sampled"], 1)
        self.assertIn("比赛说明", report["fields"])

        enddate = [
            item
            for item in report["time_candidates"]
            if item["field_name"] == "enddate"
        ]
        self.assertTrue(enddate)
        self.assertTrue(
            all(
                item["semantic_status"] == "unknown"
                for item in enddate
            )
        )
        self.assertTrue(
            any(
                item["field_name"] == "matchId"
                for item in report[
                    "match_identity_candidates"
                ]
            )
        )
        self.assertTrue(
            any(
                item["field_name"] == "letpoint"
                for item in report[
                    "handicap_candidates"
                ]
            )
        )
        self.assertTrue(
            any(
                item["field_name"] == "headPic"
                for item in report["avatar_candidates"]
            )
        )

    def test_empty_dictionary_and_list_reports(self):
        for payload in ({}, []):
            with self.subTest(payload=payload):
                report = build_source_contract(
                    "empty",
                    payload,
                )
                self.assertEqual(report["fields"], {})
                self.assertEqual(report["time_candidates"], [])
                self.assertEqual(report["unknown_fields"], [])

    def test_json_dictionary_and_list_are_supported(self):
        dictionary_report = build_source_contract(
            "dict",
            {"create_time": "2026-08-25"},
        )
        list_report = build_source_contract(
            "list",
            [{"kickoff": "20:00"}],
        )

        self.assertEqual(
            dictionary_report["time_candidates"][0][
                "semantic_status"
            ],
            "unknown",
        )
        self.assertEqual(
            list_report["time_candidates"][0][
                "semantic_status"
            ],
            "unknown",
        )

    def test_report_can_be_saved_as_sanitized_json(self):
        payload = {
            "Authorization": "Bearer private-fixture",
            "matchId": "m-1",
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            write_json_secure(
                path,
                build_source_contract(
                    "test",
                    payload,
                ),
            )
            saved = path.read_text(encoding="utf-8")

        self.assertNotIn("private-fixture", saved)
        self.assertIn("matchId", saved)


class ResponseTests(unittest.TestCase):
    def test_response_json_accepts_dictionary_and_list(self):
        session = FakeSession(
            [
                FakeResponse({"code": 1}),
                FakeResponse([{"id": 1}]),
            ]
        )

        self.assertIsInstance(
            response_json(session, "https://example.invalid/a", {}),
            dict,
        )
        self.assertIsInstance(
            response_json(session, "https://example.invalid/b", {}),
            list,
        )

    def test_non_json_and_scalar_responses_are_rejected(self):
        non_json = FakeSession(
            [
                FakeResponse(
                    json_error=ValueError("invalid fixture")
                )
            ]
        )
        scalar = FakeSession(
            [
                FakeResponse("unexpected scalar")
            ]
        )

        with self.assertRaises(CaptureError):
            response_json(
                non_json,
                "https://example.invalid/a",
                {},
            )
        with self.assertRaises(CaptureError):
            response_json(
                scalar,
                "https://example.invalid/b",
                {},
            )

    def test_platform_error_responses_are_rejected(self):
        with self.assertRaises(CaptureError):
            validate_platform_response(
                "caizhanyun",
                {"errorCode": "1"},
            )
        with self.assertRaises(CaptureError):
            validate_platform_response(
                "hongrui",
                {"code": 0},
            )


class CaizhanyunConfigurationTests(unittest.TestCase):
    def valid_config(self):
        return {
            "CAIZHANYUN_TOKEN": (
                "fixture-" + "credential"
            ),
            "CAIZHANYUN_COOKIE": (
                "session=" + "fixture-cookie"
            ),
        }

    def test_only_token_and_cookie_are_required(self):
        resolved = resolve_caizhanyun_config(
            self.valid_config()
        )
        self.assertTrue(resolved["token"])
        self.assertTrue(resolved["cookie"])

    def test_user_id_environment_variable_is_not_required(self):
        config = self.valid_config()
        self.assertNotIn("CAIZHANYUN_USER_ID", config)
        resolved = resolve_caizhanyun_config(config)
        self.assertTrue(resolved["request_user_id"])

    def test_store_id_falls_back_to_verified_config(self):
        resolved = resolve_caizhanyun_config(
            self.valid_config()
        )
        self.assertEqual(
            resolved["store_id"],
            CAIZHANYUN_CONFIG["store_id"],
        )

    def test_store_id_environment_override_is_allowed(self):
        config = self.valid_config()
        config["CAIZHANYUN_STORE_ID"] = "override-store"
        resolved = resolve_caizhanyun_config(config)
        self.assertEqual(
            resolved["store_id"],
            "override-store",
        )

    def test_missing_token_fails(self):
        config = self.valid_config()
        config.pop("CAIZHANYUN_TOKEN")

        with self.assertRaises(CaptureError) as caught:
            resolve_caizhanyun_config(config)

        self.assertIn(
            "CAIZHANYUN_TOKEN",
            str(caught.exception),
        )

    def test_missing_cookie_fails(self):
        config = self.valid_config()
        config.pop("CAIZHANYUN_COOKIE")

        with self.assertRaises(CaptureError) as caught:
            resolve_caizhanyun_config(config)

        self.assertIn(
            "CAIZHANYUN_COOKIE",
            str(caught.exception),
        )

    def test_configuration_error_does_not_leak_secret(self):
        config = {
            "CAIZHANYUN_COOKIE": (
                "session=" + "do-not-print-this"
            ),
        }

        with self.assertRaises(CaptureError) as caught:
            resolve_caizhanyun_config(config)

        self.assertNotIn(
            "do-not-print-this",
            str(caught.exception),
        )


class ImportSafetyTests(unittest.TestCase):
    def import_spider_with_spies(self):
        calls = {
            "http": 0,
            "database": 0,
        }
        fake_requests = types.ModuleType("requests")
        fake_pymysql = types.ModuleType("pymysql")
        fake_save_order = types.ModuleType(
            "database.save_order"
        )
        fake_save_user = types.ModuleType(
            "database.save_user"
        )

        def http_post(*args, **kwargs):
            calls["http"] += 1
            raise AssertionError("HTTP called during import")

        def database_write(*args, **kwargs):
            calls["database"] += 1
            raise AssertionError("DB called during import")

        fake_requests.post = http_post
        fake_save_order.save_order = database_write
        fake_save_user.save_user = database_write

        module_name = "spider.caizhanyun"
        sys.modules.pop(module_name, None)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch.dict(
            sys.modules,
            {
                "requests": fake_requests,
                "pymysql": fake_pymysql,
                "database.save_order": fake_save_order,
                "database.save_user": fake_save_user,
            },
        ):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                imported = importlib.import_module(module_name)

        sys.modules.pop(module_name, None)

        return calls, stdout.getvalue(), stderr.getvalue(), imported

    def test_import_does_not_make_http_request(self):
        calls, stdout, stderr, imported = (
            self.import_spider_with_spies()
        )
        self.assertEqual(calls["http"], 0)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        self.assertTrue(imported.CONFIG["storeId"])

    def test_import_does_not_connect_or_write_database(self):
        calls, stdout, stderr, imported = (
            self.import_spider_with_spies()
        )
        self.assertEqual(calls["database"], 0)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        self.assertTrue(imported.CONFIG["userid"])


class OfflineCaptureTests(unittest.TestCase):
    def caizhanyun_config(self, store_id=None):
        config = {
            "CAIZHANYUN_TOKEN": (
                "fixture-" + "credential"
            ),
            "CAIZHANYUN_COOKIE": (
                "session=" + "fixture-cookie"
            ),
        }
        if store_id is not None:
            config["CAIZHANYUN_STORE_ID"] = store_id
        return config

    def test_caizhanyun_uses_dynamic_starter_id(self):
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "errorCode": "0",
                        "data": {
                            "rankList": [
                                {
                                    "id": "o-1",
                                    "starterId": "starter-101",
                                    "play": "让球胜平负",
                                },
                                {
                                    "id": "o-2",
                                    "starterId": "starter-102",
                                    "play": "胜平负",
                                },
                            ]
                        },
                    }
                ),
                FakeResponse(
                    {
                        "errorCode": "0",
                        "data": {
                            "prescientInfo": {
                                "jingcaiResultList": []
                            }
                        },
                    }
                ),
            ]
        )

        result = capture_caizhanyun(
            self.caizhanyun_config(),
            limit=1,
            session=session,
        )

        self.assertEqual(result["orders_sampled"], 1)
        self.assertEqual(
            result["detail_responses"][0]["starter_id"],
            "starter-101",
        )
        self.assertEqual(
            session.calls[1]["headers"],
            {"userid": "starter-101"},
        )
        self.assertEqual(
            [item["url"] for item in session.calls],
            [
                CAIZHANYUN_LIST_URL,
                CAIZHANYUN_DETAIL_URL,
            ],
        )
        self.assertNotIn(
            "CAIZHANYUN_USER_ID",
            self.caizhanyun_config(),
        )
        self.assertNotIn(
            "CAIZHANYUN_STORE_ID",
            self.caizhanyun_config(),
        )

    def test_hongrui_uses_only_follow_order_and_follow_detail(self):
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "code": 1,
                        "data": {
                            "data": [
                                {"order_id": 101},
                                {"order_id": 102},
                            ]
                        },
                    }
                ),
                FakeResponse(
                    {
                        "code": 1,
                        "data": {
                            "head": {
                                "user_pic": "private-avatar"
                            },
                            "order_message": {
                                "lottery_list": []
                            },
                        },
                    }
                ),
            ]
        )

        result = capture_hongrui(
            {},
            limit=1,
            session=session,
        )

        self.assertEqual(result["orders_sampled"], 1)
        self.assertEqual(
            [item["url"] for item in session.calls],
            [
                HONGRUI_LIST_URL,
                HONGRUI_DETAIL_URL,
            ],
        )

    def test_repository_output_is_rejected(self):
        with self.assertRaises(CaptureError):
            ensure_safe_output_directory(
                Path(__file__).resolve().parents[1]
                / "unsafe-samples"
            )


if __name__ == "__main__":
    unittest.main()
