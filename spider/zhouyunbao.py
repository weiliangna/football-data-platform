import argparse

from common.platform_registry import default_platform_id
from config.platform_ingestion_config import (
    get_zhouyunbao_config,
    require_values,
)
from spider.magicangle_contract import (
    build_record as build_magicangle_record,
    parse_list_response as parse_magicangle_list_response,
)
from spider.platform_pending import load_pending_order_refs
from spider.pagination import collect_numbered_pages
from spider.unified_ingestion import (
    DatabaseRepository,
    ingest_records,
    load_detail_map,
    load_json_file,
    preview_repository,
)


PLATFORM_ID = default_platform_id("zhouyunbao")
PLATFORM_NAME = "州运宝"


def _response_json(response):
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("州运宝响应不是 JSON 对象")
    return data


def _common_payload(token, store_id):
    return {
        "systemVersion": "unknown",
        "phoneType": "Web Browser",
        "channelNo": "web",
        "appVersion": "1.0.0-web",
        "resource": "web|web-browser",
        "clientType": "web",
        "token": token,
        "storeId": store_id,
    }


class ZhouyunbaoClient:
    def __init__(self, config=None, session=None):
        self.config = require_values(
            config or get_zhouyunbao_config(),
            PLATFORM_NAME,
            ("token", "store_id"),
        )
        if session is None:
            import requests

            session = requests.Session()
        self.session = session
        self.user_id = None
        self.store_id = self.config["store_id"]

    def _headers(self, user_id=None):
        return {
            "content-type": "application/json",
            "accept": "*/*",
            "userid": str(
                user_id
                or self.user_id
                or self.config.get("bootstrap_user_id")
                or ""
            ),
            "token": self.config["token"],
            "origin": "https://hfive.cfkjmagic.cn",
            "referer": "https://hfive.cfkjmagic.cn/",
            "user-agent": "Mozilla/5.0",
        }

    def login(self):
        response = self.session.post(
            self.config["login_url"],
            headers=self._headers(),
            json=_common_payload(
                self.config["token"],
                self.store_id,
            ),
            timeout=20,
        )
        raw = _response_json(response)
        if str(raw.get("errorCode") or "") != "0":
            raise RuntimeError("州运宝登录令牌校验失败")
        data = raw.get("data") or {}
        self.user_id = data.get("userId")
        self.store_id = str(
            data.get("storeId") or self.store_id or ""
        ).strip()
        if not self.user_id or not self.store_id:
            raise RuntimeError("州运宝登录响应缺少 userId/storeId")
        return data

    def list_orders(self, page_num=1, page_size=30):
        if not self.user_id:
            self.login()
        payload = _common_payload(
            self.config["token"],
            self.store_id,
        )
        payload.update(
            {
                "pageNum": max(int(page_num), 1),
                "pageSize": max(int(page_size), 1),
                "state": "1",
                "lotNo": "",
                "sort": 7,
                "currentUserId": str(self.user_id),
            }
        )
        return _response_json(
            self.session.post(
                self.config["list_url"],
                headers=self._headers(),
                json=payload,
                timeout=20,
            )
        )

    def order_detail(self, platform_order_id):
        if not self.user_id:
            self.login()
        payload = _common_payload(
            self.config["token"],
            self.store_id,
        )
        payload["prescientId"] = str(platform_order_id)
        return _response_json(
            self.session.post(
                self.config["detail_url"],
                headers=self._headers(),
                json=payload,
                timeout=20,
            )
        )


def parse_list_response(response):
    return parse_magicangle_list_response(response)


def build_record(list_item, detail_response, platform_id=PLATFORM_ID):
    return build_magicangle_record(
        list_item,
        detail_response,
        platform_id=int(platform_id),
        platform_name=PLATFORM_NAME,
        avatar_source="zhouyunbao_response",
    )


def _merge_pending_items(rows, pending_refs):
    merged = []
    seen = set()

    for item in list(rows or []):
        source_id = str(item.get("id") or "").strip()
        if source_id and source_id not in seen:
            seen.add(source_id)
            merged.append(item)

    for ref in pending_refs or []:
        source_id = str(
            ref.get("platform_order_id") or ""
        ).strip()
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        merged.append(
            {
                "id": source_id,
                "starterId": ref.get("user_id"),
                "staterName": ref.get("nickname"),
            }
        )

    return merged


def ingest_responses(
    list_response,
    detail_fetcher,
    repository=None,
    status_recorder=None,
    limit=None,
    platform_id=PLATFORM_ID,
    pending_refs=None,
):
    rows = _merge_pending_items(
        parse_list_response(list_response),
        pending_refs,
    )
    if limit is not None:
        rows = rows[:max(int(limit), 0)]
    target_repository = repository or preview_repository()

    def fetch(item):
        source_id = str(item.get("id") or "").strip()
        if not source_id:
            raise ValueError("州运宝列表项缺少 id")
        return source_id, detail_fetcher(source_id, item)

    return ingest_records(
        rows,
        fetch,
        lambda item, detail: build_record(
            item,
            detail,
            platform_id=platform_id,
        ),
        int(platform_id),
        PLATFORM_NAME,
        target_repository,
        status_recorder=status_recorder,
    )


def run_live(
    platform_id=PLATFORM_ID,
    limit=None,
    repository=None,
    client=None,
    pending_refs=None,
):
    target_client = client or ZhouyunbaoClient()
    target_repository = repository or DatabaseRepository()
    refs = pending_refs
    if refs is None:
        refs = load_pending_order_refs(platform_id)
    page_size = max(int(limit or 10), 1)
    rows = collect_numbered_pages(
        lambda page, size: target_client.list_orders(
            page_num=page,
            page_size=size,
        ),
        parse_list_response,
        lambda item: item.get("id"),
        page_size=page_size,
    )
    return ingest_responses(
        {
            "errorCode": "0",
            "data": {"rankList": rows},
        },
        lambda source_id, _item: target_client.order_detail(
            source_id
        ),
        repository=target_repository,
        limit=None,
        platform_id=platform_id,
        pending_refs=refs,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="州运宝采集与已取证响应接管工具"
    )
    parser.add_argument("--platform-id", type=int, default=PLATFORM_ID)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--list-json")
    parser.add_argument("--details-json")
    args = parser.parse_args(argv)

    repository = (
        DatabaseRepository() if args.write else preview_repository()
    )

    if args.live:
        if not args.write:
            raise ValueError("州运宝线上采集必须显式使用 --write")
        summary = run_live(
            platform_id=args.platform_id,
            limit=args.limit or None,
            repository=repository,
        )
    else:
        if not args.list_json or not args.details_json:
            parser.error("离线模式需要 --list-json 和 --details-json")
        details = load_detail_map(args.details_json)
        summary = ingest_responses(
            load_json_file(args.list_json),
            lambda source_id, _item: details[source_id],
            repository=repository,
            limit=args.limit or None,
            platform_id=args.platform_id,
        )

    print(
        "州运宝处理完成:",
        "总数",
        summary["total_count"],
        "新增",
        summary["new_count"],
        "重复",
        summary["duplicate_count"],
        "失败",
        summary["failed_count"],
    )
    if summary["failed_count"]:
        raise SystemExit(1)
    return summary


def run():
    return main()


if __name__ == "__main__":
    main()
