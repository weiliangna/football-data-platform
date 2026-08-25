import math
import os
import sys
import pymysql

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.mysql import get_conn
from common.match_utils import build_match_key


def calculate_streaks(results):
    settled = [x for x in results if x in ("赢", "输")]
    current = 0
    for r in settled:
        if r == "赢":
            current += 1
        else:
            break
    max_streak = 0
    running = 0
    for r in reversed(settled):
        if r == "赢":
            running += 1
            max_streak = max(max_streak, running)
        else:
            running = 0
    return current, max_streak


def calculate_score(settled_orders, hit_rate, roi, follow_num, max_win_streak):
    sample = min(1.0, settled_orders / 20.0)
    hit_component = hit_rate * sample * 0.45
    roi_component = max(0.0, min(100.0, roi)) * 0.25
    sample_component = sample * 15
    streak_component = min(float(max_win_streak) * 3, 15)
    follow_component = min(math.log10(follow_num + 1) * 4, 15) if follow_num > 0 else 0
    return round(max(0, hit_component + roi_component + sample_component + streak_component + follow_component), 2)


def backfill_match_keys(cursor):
    cursor.execute("SELECT id,match_name FROM order_matches WHERE match_key IS NULL OR match_key=''")
    for row in cursor.fetchall():
        cursor.execute(
            "UPDATE order_matches SET match_key=%s WHERE id=%s",
            (build_match_key(match_name=row.get("match_name")), row["id"]),
        )

    cursor.execute(
        "SELECT id,match_name,home_team,away_team FROM match_results WHERE match_key IS NULL OR match_key=''"
    )
    for row in cursor.fetchall():
        cursor.execute(
            "UPDATE match_results SET match_key=%s WHERE id=%s",
            (
                build_match_key(
                    home_team=row.get("home_team"),
                    away_team=row.get("away_team"),
                    match_name=row.get("match_name"),
                ),
                row["id"],
            ),
        )


def main():
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        backfill_match_keys(cursor)

        cursor.execute(
            """
            SELECT
                platform_id,user_id,MAX(nickname) AS nickname,
                COUNT(*) AS total_orders,
                SUM(CASE WHEN result!='待开奖' THEN 1 ELSE 0 END) AS settled_orders,
                SUM(CASE WHEN result='赢' THEN 1 ELSE 0 END) AS win_orders,
                SUM(CASE WHEN result='输' THEN 1 ELSE 0 END) AS lose_orders,
                SUM(CASE WHEN result='待开奖' THEN 1 ELSE 0 END) AS pending_orders,
                IFNULL(SUM(stake),0) AS total_stake,
                IFNULL(SUM(profit),0) AS total_profit,
                IFNULL(SUM(follow_num),0) AS follow_num,
                MAX(COALESCE(publish_time,created_time)) AS last_order_time
            FROM orders
            WHERE user_id IS NOT NULL AND user_id<>0
            GROUP BY platform_id,user_id
            """
        )
        users = cursor.fetchall()
        print("待刷新用户:", len(users))

        for user in users:
            platform_id = int(user.get("platform_id") or 0)
            user_id = int(user.get("user_id") or 0)
            settled_orders = int(user.get("settled_orders") or 0)
            win_orders = int(user.get("win_orders") or 0)
            total_stake = float(user.get("total_stake") or 0)
            total_profit = float(user.get("total_profit") or 0)
            follow_num = int(user.get("follow_num") or 0)
            hit_rate = round(win_orders / settled_orders * 100, 2) if settled_orders else 0.0
            roi = round(total_profit / total_stake * 100, 2) if total_stake else 0.0

            cursor.execute(
                "SELECT result FROM orders WHERE platform_id=%s AND user_id=%s ORDER BY id DESC LIMIT 1000",
                (platform_id,user_id),
            )
            results = [str(row.get("result") or "") for row in cursor.fetchall()]
            current_streak, max_win_streak = calculate_streaks(results)
            recent_results = ",".join(results[:7])
            expert_score = calculate_score(settled_orders, hit_rate, roi, follow_num, max_win_streak)

            cursor.execute(
                """
                INSERT INTO user_statistics
                (platform_id,user_id,nickname,total_orders,settled_orders,win_orders,lose_orders,pending_orders,
                 hit_rate,total_stake,total_profit,roi,follow_num,current_streak,max_win_streak,recent_results,
                 expert_score,last_order_time,updated_time)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                ON DUPLICATE KEY UPDATE
                    nickname=VALUES(nickname),total_orders=VALUES(total_orders),settled_orders=VALUES(settled_orders),
                    win_orders=VALUES(win_orders),lose_orders=VALUES(lose_orders),pending_orders=VALUES(pending_orders),
                    hit_rate=VALUES(hit_rate),total_stake=VALUES(total_stake),total_profit=VALUES(total_profit),
                    roi=VALUES(roi),follow_num=VALUES(follow_num),current_streak=VALUES(current_streak),
                    max_win_streak=VALUES(max_win_streak),recent_results=VALUES(recent_results),
                    expert_score=VALUES(expert_score),last_order_time=VALUES(last_order_time),updated_time=NOW()
                """,
                (
                    platform_id,user_id,user.get("nickname") or "",int(user.get("total_orders") or 0),
                    settled_orders,win_orders,int(user.get("lose_orders") or 0),int(user.get("pending_orders") or 0),
                    hit_rate,total_stake,total_profit,roi,follow_num,current_streak,max_win_streak,recent_results,
                    expert_score,user.get("last_order_time"),
                ),
            )

        conn.commit()
        print("统计刷新完成:", len(users))
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
