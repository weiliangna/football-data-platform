import os
import sys


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


import pymysql
import requests

from common.match_identity import (
    build_match_identity,
    load_team_aliases,
    supports_identity_v2,
    table_columns,
)
from common.match_utils import parse_match_name
from config.caizhanyun_config import CAIZHANYUN_CONFIG
from database.mysql import get_conn


PLATFORM_ID = 1

CONFIG = {
    "url": (
        f"{CAIZHANYUN_CONFIG['detail_url']}"
        "/lottery-store/api/prescient-hall/order/info"
    ),
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


def save_match(
    cursor,
    item,
    alias_map=None,
    identity_v2=False,
):
    match_id = str(item.get("matchId") or "").strip()

    if not match_id:
        return

    parsed_match = parse_match_name(item.get("team"))
    home = parsed_match["home_team"] or ""
    away = parsed_match["away_team"] or ""
    identity = build_match_identity(
        PLATFORM_ID,
        match_date=item.get("day"),
        source_match_code=match_id,
        match_name=item.get("team"),
        home_team=home,
        away_team=away,
        alias_map=alias_map,
    )

    if identity_v2:
        cursor.execute(
            """
            SELECT id
            FROM matches
            WHERE platform_id=%s
              AND match_date=%s
              AND match_id=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                PLATFORM_ID,
                identity["match_date"],
                match_id,
            ),
        )
        existing = cursor.fetchone()

        if existing:
            existing_id = (
                existing.get("id")
                if isinstance(existing, dict)
                else existing[0]
            )
            cursor.execute(
                """
                UPDATE matches
                SET
                    platform_id=%s,
                    match_date=%s,
                    normalized_home=%s,
                    normalized_away=%s,
                    match_identity=%s,
                    identity_quality=%s,
                    league=%s,
                    home_team=%s,
                    away_team=%s
                WHERE id=%s
                """,
                (
                    PLATFORM_ID,
                    identity["match_date"],
                    identity["normalized_home"],
                    identity["normalized_away"],
                    identity["match_identity"],
                    identity["identity_quality"],
                    item.get("league"),
                    home,
                    away,
                    existing_id,
                ),
            )
            return

        cursor.execute(
            """
            INSERT INTO matches
            (
                platform_id,
                match_id,
                match_date,
                normalized_home,
                normalized_away,
                match_identity,
                identity_quality,
                league,
                home_team,
                away_team,
                status
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'未结束')
            """,
            (
                PLATFORM_ID,
                match_id,
                identity["match_date"],
                identity["normalized_home"],
                identity["normalized_away"],
                identity["match_identity"],
                identity["identity_quality"],
                item.get("league"),
                home,
                away,
            ),
        )
        return

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
            item.get("league"),
            home,
            away,
        ),
    )


def update_orders():
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.Cursor)
    metadata_cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        alias_map = load_team_aliases(metadata_cursor)
        identity_v2 = supports_identity_v2(
            table_columns(metadata_cursor, "matches")
        )

        cursor.execute(
            """
            SELECT id,platform_order_id
            FROM orders
            WHERE platform_id=1
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
                SET match_id=%s,match_name=%s,league=%s
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
                save_match(
                    cursor,
                    match,
                    alias_map=alias_map,
                    identity_v2=identity_v2,
                )

            print("更新:", first["team"])

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        metadata_cursor.close()
        cursor.close()
        conn.close()

    print("比赛绑定完成")


if __name__ == "__main__":
    update_orders()
