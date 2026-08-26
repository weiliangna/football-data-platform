import os
import sys


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from config.caizhanyun_config import CAIZHANYUN_CONFIG
from spider.magicangle_contract import parse_list_response


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


def build_list_payload(config=None):
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
        "pageNum": 1,
        "pageSize": 10,
        "state": "1",
        "lotNo": "",
        "sort": 8,
        "currentUserId": values["userid"],
    }


def get_orders(session=None):
    if not CONFIG["token"]:
        raise RuntimeError("没有设置 CAIZHANYUN_TOKEN")

    if session is None:
        import requests

        session = requests

    response = session.post(
        CONFIG["url"],
        headers=build_headers(),
        json=build_list_payload(),
        timeout=20,
    )
    print("HTTP状态:", response.status_code)
    response.raise_for_status()
    return parse_list_response(response.json())


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

    for item in orders:
        try:
            order = normalize_list_item(item)
            print("保存订单:", order["nickname"], order["stake"])
            user_saver(order)
            order_saver(order)
            print("保存成功:", order["nickname"])
        except Exception as error:
            print("保存失败:", type(error).__name__)


if __name__ == "__main__":
    run()
