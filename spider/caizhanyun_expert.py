import os
import sys

import pymysql
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.caizhanyun_config import CAIZHANYUN_CONFIG
from database.mysql import get_conn


URL = f"{CAIZHANYUN_CONFIG['detail_url']}/lottery-store/api/prescient-hall/order/info"
TOKEN = CAIZHANYUN_CONFIG["token"]

HEADERS = {
    "Content-Type": "application/json",
    "token": TOKEN,
    "userid": "260610",
    "Origin": "https://hfive.cfgsdok.com",
}


def update_profile(item):
    starter = item["starterInfo"]
    military = starter["militaryInfo"]
    focus = starter["focusInfo"]

    conn = get_conn()
    cursor = conn.cursor()

    sql = """
    UPDATE expert_profile
    SET
        avatar=%s,
        fans=%s,
        source_hit_rate=%s,
        source_profit_rate=%s,
        month_profit=%s,
        last_ten=%s
    WHERE
        platform_id=1
        AND user_id=%s
    """

    cursor.execute(
        sql,
        (
            starter["headPic"],
            focus.get("subscribeCount", 0),
            float(military["hitRate"].replace("%", "")),
            float(military["earningsRate"].replace("%", "")),
            float(military["monthHitMoney"]),
            military["lastTen"],
            starter["id"],
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()


def run():
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.Cursor)

    cursor.execute(
        """
        SELECT DISTINCT user_id
        FROM orders
        WHERE platform_id=1
        """
    )

    users = cursor.fetchall()

    cursor.close()
    conn.close()

    for user in users:
        payload = {
            "prescientId": user[0],
        }

        try:
            response = requests.post(URL, json=payload, headers=HEADERS)

            data = response.json()

            if data.get("errorCode") == "0":
                update_profile(data["data"])
                print("更新彩站云:", user[0])

        except Exception as error:
            print(error)


if __name__ == "__main__":
    run()
