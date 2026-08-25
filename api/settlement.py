from typing import Optional
import re

import pymysql
from fastapi import APIRouter

from common.match_identity import (
    build_match_identity,
    load_team_aliases,
    supports_identity_v2,
    table_columns,
)
from database.mysql import get_conn


router = APIRouter(
    prefix="/api/settlement",
    tags=["settlement"],
)


def win_type(home, away):
    if home > away:
        return "主胜"
    if home == away:
        return "平"
    return "客胜"


def split_options(selection):
    text = str(selection or "")
    for separator in ("，", ",", "|", "、"):
        text = text.replace(separator, "/")
    return [
        item.strip()
        for item in text.split("/")
        if item.strip()
    ]


def check_score(selection, home, away):
    target = f"{home}:{away}"
    for option in split_options(selection):
        normalized = option.replace("：", ":").replace("-", ":")
        if normalized == target:
            return True
    return False


def check_total_goals(selection, home, away):
    total = int(home) + int(away)
    for option in split_options(selection):
        text = option.replace("球", "")
        if "7+" in text or "7及以上" in text:
            if total >= 7:
                return True
            continue
        for number in re.findall(r"\d+", text):
            if int(number) == total:
                return True
    return False


def check_spf(selection, home, away):
    actual = win_type(int(home), int(away))
    normalized = set()
    for option in split_options(selection):
        if option in ("胜", "主胜"):
            normalized.add("主胜")
        elif option == "平":
            normalized.add("平")
        elif option in ("负", "主负", "客胜"):
            normalized.add("客胜")
    return actual in normalized


def check_handicap(selection, home, away, handicap):
    final_home = int(home) + int(handicap or 0)
    if final_home > int(away):
        actual = "让胜"
    elif final_home == int(away):
        actual = "让平"
    else:
        actual = "让负"

    normalized = set()
    for option in split_options(selection):
        if option in ("胜", "让胜"):
            normalized.add("让胜")
        elif option in ("平", "让平"):
            normalized.add("让平")
        elif option in ("负", "让负"):
            normalized.add("让负")
    return actual in normalized


def check_half_full(
    selection,
    home,
    away,
    half_home,
    half_away,
):
    if half_home is None or half_away is None:
        return None

    short = {
        "主胜": "胜",
        "平": "平",
        "客胜": "负",
    }
    actual = (
        short[win_type(int(half_home), int(half_away))]
        + short[win_type(int(home), int(away))]
    )
    return actual in split_options(selection)


def check_play(
    play_type,
    selection,
    home,
    away,
    handicap=0,
    half_home=None,
    half_away=None,
):
    play_type = str(play_type or "").strip()
    if play_type == "比分":
        return check_score(selection, home, away)
    if play_type == "总进球":
        return check_total_goals(selection, home, away)
    if play_type == "胜平负":
        return check_spf(selection, home, away)
    if play_type == "让球胜平负":
        return check_handicap(
            selection,
            home,
            away,
            handicap,
        )
    if play_type == "半全场":
        return check_half_full(
            selection,
            home,
            away,
            half_home,
            half_away,
        )
    return None


def refresh_order_result(cursor, order_id):
    cursor.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN result='赢' THEN 1 ELSE 0 END) AS win_num,
            SUM(CASE WHEN result='输' THEN 1 ELSE 0 END) AS lose_num,
            SUM(CASE WHEN result='待开奖' THEN 1 ELSE 0 END) AS pending_num
        FROM order_matches
        WHERE order_id=%s
        """,
        (order_id,),
    )
    stat = cursor.fetchone()
    total = int(stat.get("total") or 0)
    win_num = int(stat.get("win_num") or 0)
    lose_num = int(stat.get("lose_num") or 0)
    pending_num = int(stat.get("pending_num") or 0)

    if total <= 0 or pending_num > 0:
        result = "待开奖"
    elif lose_num > 0:
        result = "输"
    elif win_num == total:
        result = "赢"
    else:
        result = "待开奖"

    cursor.execute(
        "UPDATE orders SET result=%s WHERE id=%s",
        (result, order_id),
    )
    return result


def log_settlement(
    cursor,
    row,
    old_result,
    new_result,
    home_score,
    away_score,
    half_home,
    half_away,
    reason,
):
    cursor.execute(
        """
        INSERT INTO settlement_logs
        (
            order_id,order_match_id,match_name,play_type,selection,
            handicap,home_score,away_score,half_home_score,
            half_away_score,old_result,new_result,reason
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            row.get("order_id"),
            row.get("id"),
            row.get("match_name"),
            row.get("play_type"),
            row.get("selection"),
            int(row.get("handicap") or 0),
            home_score,
            away_score,
            half_home,
            half_away,
            old_result,
            new_result,
            reason,
        ),
    )


def identity_schema_available(cursor):
    order_columns = table_columns(
        cursor,
        "order_matches",
    )
    result_columns = table_columns(
        cursor,
        "match_results",
    )
    return (
        supports_identity_v2(order_columns)
        and supports_identity_v2(result_columns)
    )


def upsert_match_result(
    cursor,
    identity,
    match_name,
    home_score,
    away_score,
    half_home,
    half_away,
    identity_v2,
):
    if not identity_v2:
        cursor.execute(
            """
            INSERT INTO match_results
            (
                match_name,match_key,home_team,away_team,
                home_score,away_score,half_home_score,
                half_away_score,status,finished_time
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,'已结束',NOW())
            ON DUPLICATE KEY UPDATE
                match_key=VALUES(match_key),
                home_team=VALUES(home_team),
                away_team=VALUES(away_team),
                home_score=VALUES(home_score),
                away_score=VALUES(away_score),
                half_home_score=VALUES(half_home_score),
                half_away_score=VALUES(half_away_score),
                status='已结束',
                finished_time=COALESCE(finished_time,NOW())
            """,
            (
                match_name,
                identity["match_key"],
                identity["home_team"],
                identity["away_team"],
                home_score,
                away_score,
                half_home,
                half_away,
            ),
        )
        return {
            **identity,
            "match_name": match_name,
        }

    existing = None

    if (
        identity["platform_id"] is not None
        and identity["match_date"] is not None
        and identity["source_match_code"]
    ):
        cursor.execute(
            """
            SELECT id
            FROM match_results
            WHERE platform_id=%s
              AND match_date=%s
              AND match_code=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                identity["platform_id"],
                identity["match_date"],
                identity["source_match_code"],
            ),
        )
        existing = cursor.fetchone()

    if (
        not existing
        and identity["platform_id"] is not None
        and identity["match_date"] is not None
        and identity["match_key"]
    ):
        cursor.execute(
            """
            SELECT id
            FROM match_results
            WHERE platform_id=%s
              AND match_date=%s
              AND match_key=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                identity["platform_id"],
                identity["match_date"],
                identity["match_key"],
            ),
        )
        existing = cursor.fetchone()

    if (
        not existing
        and identity["platform_id"] is not None
        and identity["match_date"] is None
        and identity["source_match_code"]
        and identity["match_key"]
    ):
        cursor.execute(
            """
            SELECT id
            FROM match_results
            WHERE platform_id=%s
              AND match_date IS NULL
              AND match_code=%s
              AND match_key=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                identity["platform_id"],
                identity["source_match_code"],
                identity["match_key"],
            ),
        )
        existing = cursor.fetchone()

    if (
        not existing
        and (
            identity["platform_id"] is None
            or identity["match_date"] is None
        )
    ):
        cursor.execute(
            """
            SELECT id
            FROM match_results
            WHERE match_name=%s
              AND (
                    platform_id IS NULL
                    OR %s IS NULL
                    OR platform_id=%s
              )
              AND (
                    match_date IS NULL
                    OR %s IS NULL
              )
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                match_name,
                identity["platform_id"],
                identity["platform_id"],
                identity["match_date"],
            ),
        )
        existing = cursor.fetchone()

    values = (
        identity["platform_id"],
        identity["match_date"],
        identity["source_match_code"],
        identity["match_key"],
        identity["normalized_home"],
        identity["normalized_away"],
        identity["match_identity"],
        identity["identity_quality"],
        match_name,
        identity["home_team"],
        identity["away_team"],
        home_score,
        away_score,
        half_home,
        half_away,
    )

    if existing:
        cursor.execute(
            """
            UPDATE match_results
            SET
                platform_id=%s,
                match_date=%s,
                match_code=%s,
                match_key=%s,
                normalized_home=%s,
                normalized_away=%s,
                match_identity=%s,
                identity_quality=%s,
                match_name=%s,
                home_team=%s,
                away_team=%s,
                home_score=%s,
                away_score=%s,
                half_home_score=%s,
                half_away_score=%s,
                status='已结束',
                finished_time=COALESCE(finished_time,NOW())
            WHERE id=%s
            """,
            values + (existing["id"],),
        )
    else:
        cursor.execute(
            """
            INSERT INTO match_results
            (
                platform_id,match_date,match_code,match_key,
                normalized_home,normalized_away,match_identity,
                identity_quality,match_name,home_team,away_team,
                home_score,away_score,half_home_score,
                half_away_score,status,finished_time
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
             '已结束',NOW())
            """,
            values,
        )

    return {
        **identity,
        "match_name": match_name,
    }


def select_order_matches(
    cursor,
    result_identity,
    match_name,
    identity_v2,
):
    if not identity_v2:
        cursor.execute(
            """
            SELECT
                id,order_id,match_name,match_key,play_type,
                selection,handicap,result,
                'legacy_match_name' AS identity_strategy
            FROM order_matches
            WHERE match_name=%s
               OR (%s<>'' AND match_key=%s)
            """,
            (
                match_name,
                result_identity["match_key"],
                result_identity["match_key"],
            ),
        )
        return cursor.fetchall()

    platform_id = result_identity["platform_id"]
    match_date = result_identity["match_date"]
    match_code = result_identity["source_match_code"]
    match_key = result_identity["match_key"]

    cursor.execute(
        """
        SELECT
            id,order_id,match_name,match_key,play_type,
            selection,handicap,result,
            CASE
                WHEN %s IS NOT NULL
                 AND %s IS NOT NULL
                 AND %s<>''
                 AND platform_id=%s
                 AND match_date=%s
                 AND match_code=%s
                THEN 'identity_v2'
                WHEN %s IS NOT NULL
                 AND %s IS NOT NULL
                 AND %s<>''
                 AND platform_id=%s
                 AND match_date=%s
                 AND match_key=%s
                THEN 'identity_fallback'
                ELSE 'legacy_match_name'
            END AS identity_strategy
        FROM order_matches
        WHERE
            (
                %s IS NOT NULL
                AND %s IS NOT NULL
                AND %s<>''
                AND platform_id=%s
                AND match_date=%s
                AND match_code=%s
            )
            OR
            (
                %s IS NOT NULL
                AND %s IS NOT NULL
                AND %s<>''
                AND platform_id=%s
                AND match_date=%s
                AND match_key=%s
            )
            OR
            (
                match_name=%s
                AND (
                    platform_id IS NULL
                    OR %s IS NULL
                    OR platform_id=%s
                )
                AND (
                    match_date IS NULL
                    OR %s IS NULL
                    OR platform_id IS NULL
                    OR %s IS NULL
                )
            )
        """,
        (
            platform_id,
            match_date,
            match_code,
            platform_id,
            match_date,
            match_code,
            platform_id,
            match_date,
            match_key,
            platform_id,
            match_date,
            match_key,
            platform_id,
            match_date,
            match_code,
            platform_id,
            match_date,
            match_code,
            platform_id,
            match_date,
            match_key,
            platform_id,
            match_date,
            match_key,
            match_name,
            platform_id,
            platform_id,
            match_date,
            platform_id,
        ),
    )
    return cursor.fetchall()


def settle_match_with_connection(
    conn,
    match_name,
    home_score,
    away_score,
    half_home=None,
    half_away=None,
    platform_id=None,
    source_match_code=None,
    match_date=None,
    home_team=None,
    away_team=None,
):
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        try:
            alias_map = load_team_aliases(cursor)
        except Exception:
            alias_map = {}

        identity_v2 = identity_schema_available(cursor)
        identity = build_match_identity(
            platform_id,
            match_date=match_date,
            source_match_code=source_match_code,
            match_name=match_name,
            home_team=home_team,
            away_team=away_team,
            alias_map=alias_map,
        )
        result_identity = upsert_match_result(
            cursor,
            identity,
            match_name,
            home_score,
            away_score,
            half_home,
            half_away,
            identity_v2,
        )
        rows = select_order_matches(
            cursor,
            result_identity,
            match_name,
            identity_v2,
        )
        affected_orders = set()
        win_count = 0
        lose_count = 0
        pending_count = 0
        strategy_counts = {
            "identity_v2": 0,
            "identity_fallback": 0,
            "legacy_match_name": 0,
        }

        for row in rows:
            strategy = str(
                row.get("identity_strategy")
                or "legacy_match_name"
            )
            strategy_counts[strategy] = (
                strategy_counts.get(strategy, 0) + 1
            )
            print(
                "settlement_match_strategy=",
                strategy,
                " order_match_id=",
                row.get("id"),
                sep="",
            )
            checked = check_play(
                row.get("play_type"),
                row.get("selection"),
                home_score,
                away_score,
                row.get("handicap") or 0,
                half_home,
                half_away,
            )

            if checked is None:
                new_result = "待开奖"
                pending_count += 1
                reason = "玩法条件不足或暂不支持"
            elif checked:
                new_result = "赢"
                win_count += 1
                reason = "玩法规则命中"
            else:
                new_result = "输"
                lose_count += 1
                reason = "玩法规则未命中"

            old_result = str(row.get("result") or "待开奖")
            if old_result != new_result:
                log_settlement(
                    cursor,
                    row,
                    old_result,
                    new_result,
                    home_score,
                    away_score,
                    half_home,
                    half_away,
                    f"{strategy}: {reason}",
                )

            cursor.execute(
                "UPDATE order_matches SET result=%s WHERE id=%s",
                (new_result, row["id"]),
            )
            affected_orders.add(row["order_id"])

        order_results = {
            "赢": 0,
            "输": 0,
            "待开奖": 0,
        }
        for order_id in affected_orders:
            order_result = refresh_order_result(
                cursor,
                order_id,
            )
            order_results[order_result] = (
                order_results.get(order_result, 0) + 1
            )

        return {
            "match_name": match_name,
            "match_identity": result_identity[
                "match_identity"
            ],
            "identity_quality": result_identity[
                "identity_quality"
            ],
            "match_rows": len(rows),
            "win_rows": win_count,
            "lose_rows": lose_count,
            "pending_rows": pending_count,
            "orders": len(affected_orders),
            "order_results": order_results,
            "match_strategies": strategy_counts,
        }
    finally:
        cursor.close()


@router.post("/run")
def settlement_run(
    match_name: str,
    home_score: int,
    away_score: int,
    half_home: Optional[int] = None,
    half_away: Optional[int] = None,
    platform_id: Optional[int] = None,
    source_match_code: Optional[str] = None,
    match_date: Optional[str] = None,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
):
    conn = None

    try:
        conn = get_conn()
        result = settle_match_with_connection(
            conn,
            match_name,
            home_score,
            away_score,
            half_home,
            half_away,
            platform_id=platform_id,
            source_match_code=source_match_code,
            match_date=match_date,
            home_team=home_team,
            away_team=away_team,
        )
        conn.commit()
        return {
            "code": 200,
            "message": "结算完成",
            "data": result,
        }
    except Exception as exc:
        if conn:
            conn.rollback()
        return {
            "code": 500,
            "msg": str(exc),
        }
    finally:
        if conn:
            conn.close()
