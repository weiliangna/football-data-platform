import argparse
import re

import pymysql

from common.match_utils import build_match_key, parse_match_name
from database.mysql import get_conn


PLATFORM_ID = 1

SUPPORTED_PLAY_TYPES = {
    "胜平负",
    "让球胜平负",
    "比分",
    "总进球",
    "半全场",
}


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def split_selection_parts(selection):
    return [
        part.strip()
        for part in re.split(r"[；;]", str(selection or ""))
        if part.strip()
    ]


def split_play(play_text):
    text = str(play_text or "").strip()

    for separator in ("：", ":"):
        if separator in text:
            play_type, selection = text.split(separator, 1)
            return play_type.strip(), selection.strip()

    return "", text


def parse_selection_legs(selection, order_handicap=0, league=""):
    legs = []

    for part in split_selection_parts(selection):
        if "→" not in part:
            continue

        raw_match_name, raw_play = part.split("→", 1)
        parsed_match = parse_match_name(raw_match_name)
        match_name = parsed_match["raw_name"]
        play_type, leg_selection = split_play(raw_play)

        if (
            not match_name
            or not play_type
            or not leg_selection
            or play_type not in SUPPORTED_PLAY_TYPES
        ):
            continue

        handicap = (
            to_int(order_handicap, 0)
            if play_type == "让球胜平负"
            else 0
        )

        legs.append(
            {
                "match_code": "",
                "match_name": match_name,
                "match_key": build_match_key(
                    home_team=parsed_match["home_team"],
                    away_team=parsed_match["away_team"],
                    match_name=match_name,
                ),
                "league": str(league or ""),
                "play_type": play_type,
                "selection": leg_selection,
                "handicap": handicap,
                "deadline_time": None,
            }
        )

    return legs


def upsert_order_matches(cursor, order):
    order_id = int(order["id"])
    legs = parse_selection_legs(
        order.get("selection"),
        order_handicap=order.get("handicap"),
        league=order.get("league"),
    )

    stats = {
        "order_id": order_id,
        "parsed": len(legs),
        "inserted": 0,
        "updated": 0,
    }

    for leg in legs:
        cursor.execute(
            """
            SELECT id,result
            FROM order_matches
            WHERE order_id=%s
              AND match_name=%s
              AND play_type=%s
              AND IFNULL(handicap,0)=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                order_id,
                leg["match_name"],
                leg["play_type"],
                leg["handicap"],
            ),
        )

        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE order_matches
                SET
                    match_code=%s,
                    match_key=%s,
                    league=%s,
                    selection=%s,
                    handicap=%s
                WHERE id=%s
                """,
                (
                    leg["match_code"],
                    leg["match_key"],
                    leg["league"],
                    leg["selection"],
                    leg["handicap"],
                    existing["id"],
                ),
            )
            stats["updated"] += 1
            continue

        cursor.execute(
            """
            INSERT INTO order_matches
            (
                order_id,
                match_code,
                match_name,
                match_key,
                league,
                play_type,
                selection,
                handicap,
                deadline_time,
                result,
                profit
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,
                '待开奖',
                0
            )
            """,
            (
                order_id,
                leg["match_code"],
                leg["match_name"],
                leg["match_key"],
                leg["league"],
                leg["play_type"],
                leg["selection"],
                leg["handicap"],
                leg["deadline_time"],
            ),
        )
        stats["inserted"] += 1

    return stats


def load_orders(cursor, order_id=None):
    where = [
        "platform_id=%s",
        "selection IS NOT NULL",
        "selection<>''",
    ]
    params = [PLATFORM_ID]

    if order_id is not None:
        where.append("id=%s")
        params.append(int(order_id))

    cursor.execute(
        f"""
        SELECT id,league,selection,handicap
        FROM orders
        WHERE {" AND ".join(where)}
        ORDER BY id ASC
        """,
        tuple(params),
    )

    return cursor.fetchall()


def build_order_matches(order_id=None, connection_factory=get_conn):
    conn = connection_factory()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    summary = {
        "orders": 0,
        "inserted": 0,
        "updated": 0,
        "failed": [],
    }

    try:
        orders = load_orders(cursor, order_id=order_id)

        for order in orders:
            summary["orders"] += 1

            try:
                stats = upsert_order_matches(cursor, order)
                conn.commit()
                summary["inserted"] += stats["inserted"]
                summary["updated"] += stats["updated"]
            except Exception as exc:
                conn.rollback()
                summary["failed"].append(
                    {
                        "order_id": int(order["id"]),
                        "error": str(exc),
                    }
                )

        return summary
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="彩站云订单拆腿"
    )
    parser.add_argument(
        "--id",
        type=int,
        default=None,
        help="只处理指定数据库订单 ID",
    )
    args = parser.parse_args()

    summary = build_order_matches(order_id=args.id)

    print(
        "彩站云拆腿完成:",
        "订单",
        summary["orders"],
        "新增",
        summary["inserted"],
        "更新",
        summary["updated"],
        "失败",
        len(summary["failed"]),
    )

    for failure in summary["failed"]:
        print(
            "拆腿失败:",
            failure["order_id"],
            failure["error"],
        )

    if summary["failed"]:
        raise SystemExit(1)

    return summary


if __name__ == "__main__":
    main()
