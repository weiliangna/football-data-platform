from typing import Optional
import re
import pymysql
from fastapi import APIRouter
from database.mysql import get_conn
from common.match_utils import build_match_key

router = APIRouter(prefix="/api/settlement", tags=["settlement"])


def win_type(home, away):
    if home > away:
        return "主胜"
    if home == away:
        return "平"
    return "客胜"


def split_options(selection):
    text = str(selection or "")
    for sep in ("，", ",", "|", "、"):
        text = text.replace(sep, "/")
    return [x.strip() for x in text.split("/") if x.strip()]


def check_score(selection, home, away):
    target = f"{home}:{away}"
    for option in split_options(selection):
        option = option.replace("：", ":").replace("-", ":")
        if option == target:
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
        for num in re.findall(r"\d+", text):
            if int(num) == total:
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
    actual = "让胜" if final_home > int(away) else "让平" if final_home == int(away) else "让负"
    normalized = set()
    for option in split_options(selection):
        if option in ("胜", "让胜"):
            normalized.add("让胜")
        elif option in ("平", "让平"):
            normalized.add("让平")
        elif option in ("负", "让负"):
            normalized.add("让负")
    return actual in normalized


def check_half_full(selection, home, away, half_home, half_away):
    if half_home is None or half_away is None:
        return None
    short = {"主胜": "胜", "平": "平", "客胜": "负"}
    actual = short[win_type(int(half_home), int(half_away))] + short[win_type(int(home), int(away))]
    return actual in split_options(selection)


def check_play(play_type, selection, home, away, handicap=0, half_home=None, half_away=None):
    play_type = str(play_type or "").strip()
    if play_type == "比分":
        return check_score(selection, home, away)
    if play_type == "总进球":
        return check_total_goals(selection, home, away)
    if play_type == "胜平负":
        return check_spf(selection, home, away)
    if play_type == "让球胜平负":
        return check_handicap(selection, home, away, handicap)
    if play_type == "半全场":
        return check_half_full(selection, home, away, half_home, half_away)
    return None


def refresh_order_result(cursor, order_id):
    cursor.execute(
        """
        SELECT COUNT(*) AS total,
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
    cursor.execute("UPDATE orders SET result=%s WHERE id=%s", (result, order_id))
    return result


def log_settlement(cursor, row, old_result, new_result, home_score, away_score, half_home, half_away, reason):
    cursor.execute(
        """
        INSERT INTO settlement_logs
        (order_id,order_match_id,match_name,play_type,selection,handicap,home_score,away_score,
         half_home_score,half_away_score,old_result,new_result,reason)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            row.get("order_id"),row.get("id"),row.get("match_name"),row.get("play_type"),row.get("selection"),
            int(row.get("handicap") or 0),home_score,away_score,half_home,half_away,old_result,new_result,reason,
        ),
    )


def settle_match_with_connection(conn, match_name, home_score, away_score, half_home=None, half_away=None):
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        match_key = build_match_key(match_name=match_name)
        cursor.execute(
            """
            INSERT INTO match_results
            (match_name,match_key,home_score,away_score,half_home_score,half_away_score,status,finished_time)
            VALUES (%s,%s,%s,%s,%s,%s,'已结束',NOW())
            ON DUPLICATE KEY UPDATE
                match_key=VALUES(match_key),home_score=VALUES(home_score),away_score=VALUES(away_score),
                half_home_score=VALUES(half_home_score),half_away_score=VALUES(half_away_score),
                status='已结束',finished_time=COALESCE(finished_time,NOW())
            """,
            (match_name,match_key,home_score,away_score,half_home,half_away),
        )
        cursor.execute(
            """
            SELECT id,order_id,match_name,match_key,play_type,selection,handicap,result
            FROM order_matches
            WHERE match_name=%s OR (%s<>'' AND match_key=%s)
            """,
            (match_name,match_key,match_key),
        )
        rows = cursor.fetchall()
        affected_orders = set()
        win_count = lose_count = pending_count = 0
        for row in rows:
            checked = check_play(
                row.get("play_type"),row.get("selection"),home_score,away_score,row.get("handicap") or 0,half_home,half_away
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
                log_settlement(cursor,row,old_result,new_result,home_score,away_score,half_home,half_away,reason)
            cursor.execute("UPDATE order_matches SET result=%s WHERE id=%s", (new_result,row["id"]))
            affected_orders.add(row["order_id"])

        order_results = {"赢":0,"输":0,"待开奖":0}
        for order_id in affected_orders:
            order_result = refresh_order_result(cursor, order_id)
            order_results[order_result] = order_results.get(order_result,0) + 1

        return {
            "match_name": match_name,
            "match_rows": len(rows),
            "win_rows": win_count,
            "lose_rows": lose_count,
            "pending_rows": pending_count,
            "orders": len(affected_orders),
            "order_results": order_results,
        }
    finally:
        cursor.close()


@router.post("/run")
def settlement_run(match_name: str, home_score: int, away_score: int, half_home: Optional[int] = None, half_away: Optional[int] = None):
    conn = None
    try:
        conn = get_conn()
        result = settle_match_with_connection(conn,match_name,home_score,away_score,half_home,half_away)
        conn.commit()
        return {"code":200,"message":"结算完成","data":result}
    except Exception as e:
        if conn:
            conn.rollback()
        return {"code":500,"msg":str(e)}
    finally:
        if conn:
            conn.close()
