import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import pymysql
import requests

from config.caizhanyun_config import CAIZHANYUN_CONFIG
from database.save_order import save_order
from database.save_user import save_user


CONFIG = {
    "url": f"{CAIZHANYUN_CONFIG['base_url']}/store/api/prescient-hall/order/recommend/list",
    "token": CAIZHANYUN_CONFIG["token"],
    "userid": CAIZHANYUN_CONFIG["request_user_id"],
    "storeId": CAIZHANYUN_CONFIG["store_id"],
}


def get_orders():
    headers = {
        "userid": CONFIG["userid"],
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    data = {
        "systemVersion": "unknown",
        "phoneType": "Web Browser",
        "channelNo": "web",
        "appVersion": "1.0.0-web",
        "resource": "web|web-browser",
        "clientType": "web",
        "token": CONFIG["token"],
        "storeId": CONFIG["storeId"],
        "pageNum": 1,
        "pageSize": 10,
        "state": "1",
        "lotNo": "",
        "sort": 8,
        "currentUserId": CONFIG["userid"],
    }

    response = requests.post(
        CONFIG["url"],
        headers=headers,
        json=data,
        timeout=20,
    )

    print("HTTP状态:", response.status_code)

    result = response.json()

    if result.get("errorCode") != "0":
        print(result)
        return []

    return result["data"]["rankList"]


def run():
    orders = get_orders()

    print("获取订单数量:", len(orders))

    for item in orders:
        try:
            order = {
                "platform_id": 1,
                "user_id": item.get("starterId"),
                "nickname": item.get("staterName"),
                "platform_order_id": item.get("id"),
                "stake": item.get("selfBuyAmt", 0) / 100,
                "hit_rate": float(item.get("rate", 0)) / 10000,
                "profitability": item.get("profitRate", 0),
                "follow_num": item.get("fansNumber", 0),
                "avatar_url": item.get("staterPhoto"),
                "avatar_source": "caizhanyun_list",
            }

            print("保存订单:", order["nickname"], order["stake"])

            save_user(order)
            save_order(order)

            print("保存成功:", order["nickname"])

        except Exception as error:
            print("保存失败:", error)


if __name__ == "__main__":
    run()
