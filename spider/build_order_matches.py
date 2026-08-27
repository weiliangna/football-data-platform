import argparse
import json
import re

import pymysql

from common.match_identity import (
    build_match_identity,
    load_team_aliases,
    supports_identity_v2,
    table_columns,
)
from common.match_utils import parse_match_name
from common.platform_field_mapping import (
    resolve_caizhanyun_handicap,
)
from database.mysql import get_conn
from spider.magicangle_contract import build_option_detail


PLATFORM_ID = 1

SUPPORTED_PLAY_TYPES = {
    "胜平负",
    "让球胜平负",
    "比分",
    "总进球",
    "半全场",
}


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


def parse_selection_legs(
    selection,
    order_handicap=0,
    league="",
    alias_map=None,
):
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

        handicap_result = resolve_caizhanyun_handicap(
            play_type,
            letpoint=None,
            legacy_order_handicap=order_handicap,
            allow_legacy_fallback=True,
        )
        identity = build_match_identity(
            PLATFORM_ID,
            match_name=match_name,
            alias_map=alias_map,
        )

        legs.append(
            {
                "platform_id": PLATFORM_ID,
                "match_code": "",
                "match_name": match_name,
                "match_key": identity["match_key"],
                "match_date": None,
                "normalized_home": identity[
                    "normalized_home"
                ],
                "normalized_away": identity[
                    "normalized_away"
                ],
                "match_identity": "",
                "identity_quality": "legacy",
                "league": str(league or ""),
                "play_type": play_type,
                "selection": leg_selection,
                "handicap": handicap_result["handicap"],
                "handicap_source": handicap_result["source"],
                "used_legacy_fallback": handicap_result[
                    "used_legacy_fallback"
                ],
                "deadline_time": None,
                "day": "",
                "team_id": "",
                "week": "",
                "enddate": "",
                "kickoff_time": None,
                "kickoff_source": None,
                "kickoff_exact": False,
                "identity_candidate": "",
            }
        )

    return legs


def build_structured_legs(decoded_items, alias_map=None):
    legs = []

    for item in decoded_items or []:
        if not isinstance(item, dict):
            continue

        play_type = str(
            item.get("market_name")
            or ""
        ).strip()
        match_name = str(
            item.get("team")
            or item.get("match_name")
            or ""
        ).strip()
        labels = item.get("labels") or []
        selection = "/".join(
            str(value).strip()
            for value in labels
            if str(value).strip()
        )

        if (
            play_type not in SUPPORTED_PLAY_TYPES
            or not match_name
            or not selection
        ):
            continue

        handicap_result = resolve_caizhanyun_handicap(
            play_type,
            letpoint=item.get("letpoint"),
            allow_legacy_fallback=False,
        )
        day = str(item.get("day") or "").strip()
        team_id = str(
            item.get("team_id")
            or item.get("teamId")
            or ""
        ).strip()
        match_id = str(
            item.get("match_id")
            or item.get("matchId")
            or ""
        ).strip()
        identity = build_match_identity(
            PLATFORM_ID,
            match_date=day,
            source_match_code=match_id,
            match_name=match_name,
            alias_map=alias_map,
        )

        legs.append(
            {
                "platform_id": PLATFORM_ID,
                "match_code": team_id or match_id,
                "match_name": match_name,
                "match_key": identity["match_key"],
                "match_date": identity["match_date"],
                "normalized_home": identity[
                    "normalized_home"
                ],
                "normalized_away": identity[
                    "normalized_away"
                ],
                "match_identity": identity[
                    "match_identity"
                ],
                "identity_quality": identity[
                    "identity_quality"
                ],
                "league": str(
                    item.get("league")
                    or ""
                ).strip(),
                "play_type": play_type,
                "selection": selection,
                "option_detail": build_option_detail(item),
                "handicap": handicap_result["handicap"],
                "handicap_source": handicap_result["source"],
                "used_legacy_fallback": False,
                "deadline_time": None,
                "day": day,
                "team_id": team_id,
                "week": str(
                    item.get("week")
                    or ""
                ).strip(),
                "enddate": str(
                    item.get("enddate")
                    or ""
                ).strip(),
                "kickoff_time": item.get("kickoff_time"),
                "kickoff_source": (
                    item.get("kickoff_source")
                    or (
                        "kickoff_proxy"
                        if item.get("kickoff_time")
                        else None
                    )
                ),
                "kickoff_exact": False,
                "identity_candidate": str(
                    item.get("identity_candidate")
                    or ""
                ).strip(),
            }
        )

    return legs

def decode_detail_items(detail_response):
    response = (
        detail_response
        if isinstance(detail_response, dict)
        else {}
    )

    if str(response.get("errorCode") or "") != "0":
        return []

    data = response.get("data") or {}
    info = data.get("prescientInfo") or {}
    matches = info.get("jingcaiResultList") or []

    from spider.caizhanyun_enrich import build_selection_text

    _, _, decoded_items = build_selection_text(
        info,
        matches,
    )
    return decoded_items


def fetch_caizhanyun_detail(platform_order_id):
    from spider.caizhanyun_detail import get_detail

    return get_detail(platform_order_id)


def choose_legs(
    order,
    detail_response=None,
    logger=print,
    allow_legacy_fallback=True,
    alias_map=None,
):
    decoded_items = decode_detail_items(
        detail_response
    )
    structured = build_structured_legs(
        decoded_items,
        alias_map=alias_map,
    )

    if structured:
        return structured

    if not allow_legacy_fallback:
        raise RuntimeError(
            "订单 "
            f"{order.get('id')} 缺少可验证的彩站云逐腿字段；"
            "未启用 orders.handicap legacy fallback"
        )

    legacy = parse_selection_legs(
        order.get("selection"),
        order_handicap=order.get("handicap"),
        league=order.get("league"),
        alias_map=alias_map,
    )

    for leg in legacy:
        if leg["used_legacy_fallback"]:
            logger(
                "警告: 订单 "
                f"{order.get('id')} 比赛 "
                f"{leg['match_name']} 缺少逐腿 letpoint，"
                "使用 orders.handicap legacy fallback"
            )

    return legacy

def find_existing_leg(
    cursor,
    order_id,
    leg,
    identity_v2=False,
):
    match_code = str(
        leg.get("match_code")
        or ""
    ).strip()

    if (
        identity_v2
        and leg.get("platform_id") is not None
        and leg.get("match_date") is not None
        and match_code
    ):
        cursor.execute(
            """
            SELECT id,result
            FROM order_matches
            WHERE order_id=%s
              AND platform_id=%s
              AND match_date=%s
              AND match_code=%s
              AND play_type=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                order_id,
                leg["platform_id"],
                leg["match_date"],
                match_code,
                leg["play_type"],
            ),
        )
        existing = cursor.fetchone()

        if existing:
            return existing

    if (
        identity_v2
        and leg.get("platform_id") is not None
        and leg.get("match_date") is not None
        and leg.get("match_key")
    ):
        cursor.execute(
            """
            SELECT id,result
            FROM order_matches
            WHERE order_id=%s
              AND platform_id=%s
              AND match_date=%s
              AND match_key=%s
              AND play_type=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                order_id,
                leg["platform_id"],
                leg["match_date"],
                leg["match_key"],
                leg["play_type"],
            ),
        )
        existing = cursor.fetchone()

        if existing:
            return existing

    if match_code:
        cursor.execute(
            """
            SELECT id,result
            FROM order_matches
            WHERE order_id=%s
              AND play_type=%s
              AND match_code=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                order_id,
                leg["play_type"],
                match_code,
            ),
        )
        existing = cursor.fetchone()

        if existing:
            return existing

        cursor.execute(
            """
            SELECT id,result
            FROM order_matches
            WHERE order_id=%s
              AND match_name=%s
              AND play_type=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                order_id,
                leg["match_name"],
                leg["play_type"],
            ),
        )
        return cursor.fetchone()

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
    return cursor.fetchone()

def upsert_order_matches(
    cursor,
    order,
    detail_response=None,
    logger=print,
    allow_legacy_fallback=True,
    alias_map=None,
    identity_v2=False,
):
    order_id = int(order["id"])
    legs = choose_legs(
        order,
        detail_response=detail_response,
        logger=logger,
        allow_legacy_fallback=allow_legacy_fallback,
        alias_map=alias_map,
    )
    stats = {
        "order_id": order_id,
        "parsed": len(legs),
        "inserted": 0,
        "updated": 0,
        "legacy_fallbacks": sum(
            1
            for leg in legs
            if leg["used_legacy_fallback"]
        ),
    }

    for leg in legs:
        existing = find_existing_leg(
            cursor,
            order_id,
            leg,
            identity_v2=identity_v2,
        )

        if existing:
            if identity_v2:
                cursor.execute(
                    """
                    UPDATE order_matches
                    SET
                        platform_id=%s,
                        match_code=%s,
                        match_key=%s,
                        match_date=%s,
                        normalized_home=%s,
                        normalized_away=%s,
                        match_identity=%s,
                        identity_quality=%s,
                        league=%s,
                        selection=%s,
                        option_detail=%s,
                        handicap=%s
                    WHERE id=%s
                    """,
                    (
                        leg["platform_id"],
                        leg["match_code"],
                        leg["match_key"],
                        leg["match_date"],
                        leg["normalized_home"],
                        leg["normalized_away"],
                        leg["match_identity"],
                        leg["identity_quality"],
                        leg["league"],
                        leg["selection"],
                        json.dumps(leg.get("option_detail") or [], ensure_ascii=False),
                        leg["handicap"],
                        existing["id"],
                    ),
                )
            else:
                cursor.execute(
                    """
                    UPDATE order_matches
                    SET
                        match_code=%s,
                        match_key=%s,
                        league=%s,
                        selection=%s,
                        option_detail=%s,
                        handicap=%s
                    WHERE id=%s
                    """,
                    (
                        leg["match_code"],
                        leg["match_key"],
                        leg["league"],
                        leg["selection"],
                        json.dumps(leg.get("option_detail") or [], ensure_ascii=False),
                        leg["handicap"],
                        existing["id"],
                    ),
                )

            stats["updated"] += 1
            continue

        if identity_v2:
            cursor.execute(
                """
                INSERT INTO order_matches
                (
                    order_id,
                    platform_id,
                    match_code,
                    match_name,
                    match_key,
                    match_date,
                    normalized_home,
                    normalized_away,
                    match_identity,
                    identity_quality,
                    league,
                    play_type,
                    selection,
                    option_detail,
                    handicap,
                    deadline_time,
                    result,
                    profit
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,
                    '待开奖',
                    0
                )
                """,
                (
                    order_id,
                    leg["platform_id"],
                    leg["match_code"],
                    leg["match_name"],
                    leg["match_key"],
                    leg["match_date"],
                    leg["normalized_home"],
                    leg["normalized_away"],
                    leg["match_identity"],
                    leg["identity_quality"],
                    leg["league"],
                    leg["play_type"],
                    leg["selection"],
                    json.dumps(leg.get("option_detail") or [], ensure_ascii=False),
                    leg["handicap"],
                    leg["deadline_time"],
                ),
            )
        else:
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
                    option_detail,
                    handicap,
                    deadline_time,
                    result,
                    profit
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
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
                    json.dumps(leg.get("option_detail") or [], ensure_ascii=False),
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
        SELECT
            id,
            platform_order_id,
            league,
            selection,
            handicap
        FROM orders
        WHERE {" AND ".join(where)}
        ORDER BY id ASC
        """,
        tuple(params),
    )
    return cursor.fetchall()


def build_order_matches(
    order_id=None,
    connection_factory=get_conn,
    detail_fetcher=None,
    logger=print,
    allow_legacy_fallback=False,
):
    conn = connection_factory()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    fetcher = (
        detail_fetcher
        or fetch_caizhanyun_detail
    )
    summary = {
        "orders": 0,
        "inserted": 0,
        "updated": 0,
        "legacy_fallbacks": 0,
        "failed": [],
    }

    try:
        orders = load_orders(cursor, order_id=order_id)

        for order in orders:
            summary["orders"] += 1

            try:
                detail_response = None
                platform_order_id = order.get(
                    "platform_order_id"
                )

                if platform_order_id not in (None, ""):
                    try:
                        detail_response = fetcher(
                            platform_order_id
                        )
                    except Exception as exc:
                        logger(
                            "警告: 订单 "
                            f"{order['id']} 无法取得逐腿详情；"
                            f"异常类型={type(exc).__name__}"
                        )

                        if not allow_legacy_fallback:
                            raise RuntimeError(
                                "无法取得可验证的彩站云逐腿详情"
                            ) from exc

                stats = upsert_order_matches(
                    cursor,
                    order,
                    detail_response=detail_response,
                    logger=logger,
                    allow_legacy_fallback=(
                        allow_legacy_fallback
                    ),
                )
                conn.commit()
                summary["inserted"] += stats["inserted"]
                summary["updated"] += stats["updated"]
                summary["legacy_fallbacks"] += stats[
                    "legacy_fallbacks"
                ]
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
    parser.add_argument(
        "--allow-legacy-fallback",
        action="store_true",
        help=(
            "仅用于旧订单修复：详情缺失时允许使用 "
            "orders.handicap"
        ),
    )
    args = parser.parse_args()

    summary = build_order_matches(
        order_id=args.id,
        allow_legacy_fallback=(
            args.allow_legacy_fallback
        ),
    )

    print(
        "彩站云拆腿完成:",
        "订单",
        summary["orders"],
        "新增",
        summary["inserted"],
        "更新",
        summary["updated"],
        "legacy fallback",
        summary["legacy_fallbacks"],
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
