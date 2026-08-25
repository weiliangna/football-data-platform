import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pymysql
import requests

from config.caizhanyun_config import CAIZHANYUN_CONFIG
from database.mysql import get_conn


CONFIG = {
    "url": f"{CAIZHANYUN_CONFIG['detail_url']}/lottery-store/api/prescient-hall/order/info",
    "token": CAIZHANYUN_CONFIG["token"],
    "userid": "260610",
    "storeId": "ds711",
}


def get_detail(pid):
    headers = {
        "userid": CONFIG["userid"],
        "token": CONFIG["token"],
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
        "prescientId": pid,
    }

    response = requests.post(
        CONFIG["url"],
        headers=headers,
        json=data,
        timeout=15,
    )

    return response.json()


def save_match(cursor, item):
    match_id = item["matchId"]

    teams = item["team"].split(":")

    home = teams[0]
    away = teams[1]

    cursor.execute(
        """
        INSERT INTO matches
        (
            match_id,
            league,
            home_team,
            away_team,
            status
        )
        VALUES
        (%s,%s,%s,%s,'未结束')

        ON DUPLICATE KEY UPDATE
            league=VALUES(league),
            home_team=VALUES(home_team),
            away_team=VALUES(away_team)
        """,
        (
            match_id,
            item["league"],
            home,
            away,
        ),
    )


def update_orders():
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.Cursor)

    cursor.execute(
        """
        SELECT
            id,
            platform_order_id
        FROM orders
        WHERE
            platform_id=1
        """
    )

    orders = cursor.fetchall()

    print("解析订单:", len(orders))

    for order in orders:
        order_id = order[0]
        platform_order_id = order[1]

        result = get_detail(platform_order_id)

        if result.get("errorCode") != "0":
            continue

        info = result["data"]["prescientInfo"]

        matches = info.get("jingcaiResultList", [])

        if not matches:
            continue

        first = matches[0]

        cursor.execute(
            """
            UPDATE orders
            SET
                match_id=%s,
                match_name=%s,
                league=%s
            WHERE id=%s
            """,
            (
                first["matchId"],
                first["team"],
                first["league"],
                order_id,
            ),
        )

        for match in matches:
            save_match(cursor, match)

        print("更新:", first["team"])

    conn.commit()
    cursor.close()
    conn.close()

    print("比赛绑定完成")


if __name__ == "__main__":
    update_orders()
