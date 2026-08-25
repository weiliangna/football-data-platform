import argparse
import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from tools.source_contract import (
    build_source_contract,
    redact_text,
    sanitize_json,
)


CAIZHANYUN_LIST_URL = (
    "https://usergw.magicangle.cn"
    "/store/api/prescient-hall/order/recommend/list"
)
CAIZHANYUN_DETAIL_URL = (
    "https://userapi.magicangle.cn"
    "/lottery-store/api/prescient-hall/order/info"
)
HONGRUI_LIST_URL = (
    "https://playerhr.fxgzht.com.cn/api/follow_order"
)
HONGRUI_DETAIL_URL = (
    "https://playerhr.fxgzht.com.cn/api/follow_detail"
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class CaptureError(RuntimeError):
    pass


def safe_print(*values, file=None):
    output = " ".join(
        redact_text(value)
        for value in values
    )
    print(
        output,
        file=file or sys.stdout,
    )


def load_env_file(path):
    env_path = Path(path).expanduser().resolve()

    if not env_path.is_file():
        raise CaptureError("env 文件不存在")

    values = {}

    for line_number, raw_line in enumerate(
        env_path.read_text(
            encoding="utf-8-sig"
        ).splitlines(),
        1,
    ):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        if "=" not in line:
            raise CaptureError(
                f"env 文件第 {line_number} 行格式无效"
            )

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        if not key:
            raise CaptureError(
                f"env 文件第 {line_number} 行缺少变量名"
            )

        values[key] = value

    return values


def merged_config(file_values):
    result = dict(file_values)

    for key, value in os.environ.items():
        if key not in result:
            result[key] = value

    return result


def require_config(config, name):
    value = str(config.get(name) or "").strip()

    if not value:
        raise CaptureError(
            f"缺少必须的环境变量 {name}"
        )

    return value


def create_session(headers):
    import requests

    session = requests.Session()
    session.headers.update(headers)
    return session


def response_json(session, url, payload):
    try:
        response = session.post(
            url,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
    except Exception as exc:
        raise CaptureError(
            "只读接口请求失败: "
            + redact_text(type(exc).__name__)
        ) from None

    try:
        data = response.json()
    except Exception:
        raise CaptureError(
            "只读接口返回了非 JSON 响应"
        ) from None

    if not isinstance(data, (dict, list)):
        raise CaptureError(
            "只读接口 JSON 顶层必须是对象或列表"
        )

    return data


def validate_platform_response(platform, payload):
    if isinstance(payload, list):
        return payload

    if platform == "caizhanyun":
        if str(payload.get("errorCode") or "") != "0":
            raise CaptureError("彩站云只读接口返回失败状态")
        return payload

    if platform == "hongrui":
        try:
            success = int(payload.get("code") or 0) == 1
        except (TypeError, ValueError):
            success = False

        if not success:
            raise CaptureError("鸿瑞只读接口返回失败状态")
        return payload

    raise CaptureError("不支持的平台")


def nested_list(payload, path):
    current = payload

    for key in path:
        if not isinstance(current, dict):
            return []
        current = current.get(key)

    return current if isinstance(current, list) else []


def replace_nested_list(payload, path, selected):
    result = copy.deepcopy(payload)

    if not isinstance(result, dict):
        return list(selected)

    current = result

    for key in path[:-1]:
        next_value = current.get(key)
        if not isinstance(next_value, dict):
            return list(selected)
        current = next_value

    current[path[-1]] = list(selected)
    return result


def searchable_text(value):
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        ).lower()
    except Exception:
        return str(value or "").lower()


def caizhanyun_priority(item):
    text = searchable_text(item)
    score = 0

    if "让球胜平负" in text or "letpoint" in text:
        score += 8
    if "串" in text or "multiple" in text:
        score += 4
    if any(
        play in text
        for play in (
            "胜平负",
            "比分",
            "总进球",
            "半全场",
        )
    ):
        score += 2

    return score


def select_orders(items, limit, score=None):
    indexed = list(enumerate(items))

    if score:
        indexed.sort(
            key=lambda pair: (
                -score(pair[1]),
                pair[0],
            )
        )

    return [
        item
        for _, item in indexed[:limit]
    ]


def caizhanyun_headers(config):
    headers = {
        "userid": require_config(
            config,
            "CAIZHANYUN_USER_ID",
        ),
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    cookie = str(
        config.get("CAIZHANYUN_COOKIE")
        or ""
    ).strip()

    if cookie:
        headers["Cookie"] = cookie

    return headers


def caizhanyun_common_payload(config):
    return {
        "systemVersion": "unknown",
        "phoneType": "Web Browser",
        "channelNo": "web",
        "appVersion": "1.0.0-web",
        "resource": "web|web-browser",
        "clientType": "web",
        "token": require_config(
            config,
            "CAIZHANYUN_TOKEN",
        ),
        "storeId": require_config(
            config,
            "CAIZHANYUN_STORE_ID",
        ),
    }


def capture_caizhanyun(config, limit, session=None):
    client = session or create_session(
        caizhanyun_headers(config)
    )
    base_payload = caizhanyun_common_payload(config)
    list_payload = dict(base_payload)
    list_payload.update(
        {
            "pageNum": 1,
            "pageSize": min(9, max(limit * 3, limit)),
            "state": "1",
            "lotNo": "",
            "sort": 8,
            "currentUserId": require_config(
                config,
                "CAIZHANYUN_USER_ID",
            ),
        }
    )

    list_response = validate_platform_response(
        "caizhanyun",
        response_json(
            client,
            CAIZHANYUN_LIST_URL,
            list_payload,
        ),
    )
    candidates = nested_list(
        list_response,
        ("data", "rankList"),
    )
    selected = select_orders(
        candidates,
        limit,
        score=caizhanyun_priority,
    )
    details = []

    for item in selected:
        order_id = item.get("id") if isinstance(item, dict) else None

        if order_id in (None, ""):
            continue

        detail_payload = dict(base_payload)
        detail_payload["prescientId"] = order_id
        detail_response = validate_platform_response(
            "caizhanyun",
            response_json(
                client,
                CAIZHANYUN_DETAIL_URL,
                detail_payload,
            ),
        )
        details.append(
            {
                "order_reference": order_id,
                "response": detail_response,
            }
        )

    selected_ids = {
        item.get("order_reference")
        for item in details
    }
    selected = [
        item
        for item in selected
        if isinstance(item, dict)
        and item.get("id") in selected_ids
    ]

    return {
        "platform": "caizhanyun",
        "captured_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "read_only_endpoints": {
            "list": CAIZHANYUN_LIST_URL,
            "detail": CAIZHANYUN_DETAIL_URL,
        },
        "list_response": replace_nested_list(
            list_response,
            ("data", "rankList"),
            selected,
        ),
        "detail_responses": details,
        "orders_sampled": len(details),
    }


def hongrui_headers(config):
    return {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Origin": "http://playerhf.fxgzht.com.cn",
        "Referer": "http://playerhf.fxgzht.com.cn/",
        "User-Agent": (
            "Mozilla/5.0 "
            "(iPhone; CPU iPhone OS 18_7 like Mac OS X) "
            "AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) "
            "Version/26.0.1 Mobile/15E148 Safari/604.1"
        ),
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "Authorization": require_config(
            config,
            "HONGRUI_TOKEN",
        ),
    }


def capture_hongrui(config, limit, session=None):
    client = session or create_session(
        hongrui_headers(config)
    )
    list_response = validate_platform_response(
        "hongrui",
        response_json(
            client,
            HONGRUI_LIST_URL,
            {
                "page": 1,
                "type": 0,
                "list_type": 1,
            },
        ),
    )
    candidates = nested_list(
        list_response,
        ("data", "data"),
    )
    selected = select_orders(
        candidates,
        limit,
    )
    details = []

    for item in selected:
        order_id = (
            item.get("order_id")
            if isinstance(item, dict)
            else None
        )

        if order_id in (None, ""):
            continue

        detail_response = validate_platform_response(
            "hongrui",
            response_json(
                client,
                HONGRUI_DETAIL_URL,
                {
                    "order_id": order_id,
                },
            ),
        )
        details.append(
            {
                "order_reference": order_id,
                "response": detail_response,
            }
        )

    selected_ids = {
        item.get("order_reference")
        for item in details
    }
    selected = [
        item
        for item in selected
        if isinstance(item, dict)
        and item.get("order_id") in selected_ids
    ]

    return {
        "platform": "hongrui",
        "captured_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "read_only_endpoints": {
            "list": HONGRUI_LIST_URL,
            "detail": HONGRUI_DETAIL_URL,
        },
        "list_response": replace_nested_list(
            list_response,
            ("data", "data"),
            selected,
        ),
        "detail_responses": details,
        "orders_sampled": len(details),
    }


def ensure_safe_output_directory(path):
    output = Path(path).expanduser().resolve()

    try:
        output.relative_to(REPOSITORY_ROOT)
    except ValueError:
        pass
    else:
        raise CaptureError(
            "样本输出目录不能位于 Git 仓库内部"
        )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        output.chmod(0o700)
    except OSError:
        pass

    return output


def write_json_secure(path, payload):
    target = Path(path)
    serialized = json.dumps(
        sanitize_json(payload),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    target.write_text(
        serialized + "\n",
        encoding="utf-8",
    )

    try:
        target.chmod(0o600)
    except OSError:
        pass


def capture(platform, limit, env_file, out):
    if limit < 1 or limit > 3:
        raise CaptureError("--limit 必须在 1 到 3 之间")

    config = merged_config(
        load_env_file(env_file)
    )

    if platform == "caizhanyun":
        raw_sample = capture_caizhanyun(
            config,
            limit,
        )
    elif platform == "hongrui":
        raw_sample = capture_hongrui(
            config,
            limit,
        )
    else:
        raise CaptureError("不支持的平台")

    sanitized_sample = sanitize_json(raw_sample)
    report = build_source_contract(
        platform,
        sanitized_sample,
        orders_sampled=raw_sample["orders_sampled"],
        captured_at=raw_sample["captured_at"],
    )
    output = ensure_safe_output_directory(out)
    sample_path = output / f"{platform}_samples.json"
    report_path = output / "source_contract_report.json"

    write_json_secure(
        sample_path,
        sanitized_sample,
    )
    write_json_secure(
        report_path,
        report,
    )

    return {
        "platform": platform,
        "orders_sampled": raw_sample["orders_sampled"],
        "sample_path": str(sample_path),
        "report_path": str(report_path),
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="安全采集真实平台只读响应样本"
    )
    parser.add_argument(
        "--platform",
        required=True,
        choices=("caizhanyun", "hongrui"),
    )
    parser.add_argument(
        "--limit",
        required=True,
        type=int,
    )
    parser.add_argument(
        "--env-file",
        required=True,
    )
    parser.add_argument(
        "--out",
        required=True,
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        result = capture(
            platform=args.platform,
            limit=args.limit,
            env_file=args.env_file,
            out=args.out,
        )
    except Exception as exc:
        safe_print(
            "采样失败:",
            redact_text(str(exc)),
            file=sys.stderr,
        )
        return 1

    safe_print(
        "采样完成:",
        result["platform"],
        "订单数:",
        result["orders_sampled"],
    )
    safe_print(
        "脱敏样本:",
        result["sample_path"],
    )
    safe_print(
        "字段报告:",
        result["report_path"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
