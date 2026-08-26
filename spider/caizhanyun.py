import os
import sys


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from config.caizhanyun_config import CAIZHANYUN_CONFIG
from spider.magicangle_contract import parse_list_response
from spider.pagination import collect_numbered_pages


CONFIG = {
    "url": (
        f"{CAIZHANYUN_CONFIG['base_url']}"
        "/store/api/prescient-hall/order/recommend/list"
    ),
    "token": CAIZHANYUN_CONFIG["token"],
    "cookie": CAIZHANYUN_CONFIG["cookie"],
    "userid": CAIZHANYUN_CONFIG["request_user_id"],
    "storeId": CAIZHANYUN_CONFIG["store_id"],
}


def build_headers(config=None):
    values = config or CONFIG
    headers = {
        "userid": values["userid"],
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    cookie = str(values.get("cookie") or "").strip()
    if cookie:
        headers["Cookie"] = cookie
    return headers


def build_list_payload(config=None, page_num=1, page_size=10):
    values = config or CONFIG
    return {
        "systemVersion": "unknown",
        "phoneType": "Web Browser",
        "channelNo": "web",
        "appVersion": "1.0.0-web",
        "resource": "web|web-browser",
        "clientType": "web",
        "token": values["token"],
        "storeId": values["storeId"],
        "pageNum": max(int(page_num), 1),
        "pageSize": max(int(page_size), 1),
        "state": "1",
        "lotNo": "",
        "sort": 8,
        "currentUserId": values["userid"],
    }


def _fetch_list_page(session, page_num, page_size):
    response = session.post(
        CONFIG["url"],
        headers=build_headers(),
        json=build_list_payload(
            page_num=page_num,
            page_size=page_size,
        ),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_orders(session=None, page_size=10, max_pages=100):
    if not CONFIG["token"]:
        raise RuntimeError("没有设置 CAIZHANYUN_TOKEN")
    if not CONFIG["cookie"]:
        raise RuntimeError("没有设置 CAIZHANYUN_COOKIE")

    if session is None:
        import requests

        session = requests.Session()

    return collect_numbered_pages(
        lambda page, size: _fetch_list_page(
            session,
            page,
            size,
        ),
        parse_list_response,
        lambda item: item.get("id"),
        page_size=page_size,
        max_pages=max_pages,
    )


def normalize_list_item(item):
    return {
        "platform_id": 1,
        "user_id": item.get("starterId"),
        "nickname": item.get("staterName"),
        "platform_order_id": item.get("id"),
        "stake": float(item.get("selfBuyAmt") or 0) / 100,
        "hit_rate": float(item.get("rate") or 0) / 10000,
        "profitability": item.get("profitRate", 0),
        "follow_num": item.get("fansNumber", 0),
        "avatar_url": item.get("staterPhoto"),
        "avatar_source": "caizhanyun_list",
    }


def run(order_fetcher=None, user_saver=None, order_saver=None):
    fetcher = order_fetcher or get_orders

    if user_saver is None or order_saver is None:
        from database.save_order import save_order
        from database.save_user import save_user

        user_saver = user_saver or save_user
        order_saver = order_saver or save_order

    orders = fetcher()
    print("获取订单数量:", len(orders))

    saved = 0
    failed = 0
    for item in orders:
        try:
            order = normalize_list_item(item)
            user_saver(order)
            order_saver(order)
            saved += 1
        except Exception as error:
            failed += 1
            print("订单保存失败:", type(error).__name__)

    return {
        "total_count": len(orders),
        "success_count": saved,
        "failed_count": failed,
    }


if __name__ == "__main__":
    run()
