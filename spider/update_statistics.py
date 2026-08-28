"""Refresh user statistics with bounded SQL work and a single-instance lock."""

from __future__ import annotations

import math
import os
import sys
import time
from collections import defaultdict
from contextlib import contextmanager

import pymysql

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.mysql import get_conn


STATISTICS_LOCK_PATH = "/tmp/football_statistics.lock"
UPSERT_BATCH_SIZE = 500

try:  # fcntl is available on the Linux production host, not on Windows CI.
    import fcntl
except ImportError:  # pragma: no cover - only used by local Windows tooling
    fcntl = None


@contextmanager
def statistics_lock(path: str = STATISTICS_LOCK_PATH):
    """Acquire the statistics lock, yielding False when another run is active."""

    handle = open(path, "a+", encoding="utf-8")
    acquired = False
    try:
        if fcntl is None:
            acquired = True
        else:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError:
                acquired = False
        yield acquired
    finally:
        if acquired and fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def calculate_streaks(results):
    """Return the current and maximum win streak using the legacy definitions."""

    settled = [value for value in results if value in ("赢", "输")]
    current = 0
    for value in settled:
        if value == "赢":
            current += 1
        else:
            break
    max_streak = 0
    running = 0
    for value in reversed(settled):
        if value == "赢":
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


def group_results(rows):
    """Group one ordered result query without changing the legacy result order."""

    grouped = defaultdict(list)
    for row in rows:
        key = (int(row.get("platform_id") or 0), int(row.get("user_id") or 0))
        grouped[key].append(str(row.get("result") or ""))
    return grouped


UPSERT_SQL = """
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
"""


def _upsert_values(user, result_rows):
    platform_id = int(user.get("platform_id") or 0)
    user_id = int(user.get("user_id") or 0)
    settled_orders = int(user.get("settled_orders") or 0)
    win_orders = int(user.get("win_orders") or 0)
    total_stake = float(user.get("total_stake") or 0)
    total_profit = float(user.get("total_profit") or 0)
    follow_num = int(user.get("follow_num") or 0)
    hit_rate = round(win_orders / settled_orders * 100, 2) if settled_orders else 0.0
    roi = round(total_profit / total_stake * 100, 2) if total_stake else 0.0
    results = result_rows.get((platform_id, user_id), [])
    current_streak, max_win_streak = calculate_streaks(results)
    recent_results = ",".join(results[:7])
    expert_score = calculate_score(settled_orders, hit_rate, roi, follow_num, max_win_streak)
    return (
        platform_id, user_id, user.get("nickname") or "", int(user.get("total_orders") or 0),
        settled_orders, win_orders, int(user.get("lose_orders") or 0),
        int(user.get("pending_orders") or 0), hit_rate, total_stake, total_profit, roi,
        follow_num, current_streak, max_win_streak, recent_results, expert_score,
        user.get("last_order_time"),
    )


def main():
    started = time.perf_counter()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with statistics_lock() as acquired:
        if not acquired:
            print("statistics already running, skip")
            return

        conn = None
        cursor = None
        aggregate_ms = results_ms = calculate_ms = upsert_ms = 0.0
        sql_query_count = 0
        commit_count = 0
        users = []
        try:
            conn = get_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            aggregate_started = time.perf_counter()
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
            sql_query_count += 1
            users = cursor.fetchall()
            aggregate_ms = (time.perf_counter() - aggregate_started) * 1000

            results_started = time.perf_counter()
            # One ordered read preserves the old per-user id DESC result sequence.
            cursor.execute(
                """
                SELECT platform_id,user_id,id,result
                FROM orders
                WHERE user_id IS NOT NULL AND user_id<>0
                  AND result IN ('赢','输')
                ORDER BY platform_id,user_id,id DESC
                """
            )
            sql_query_count += 1
            results_by_user = group_results(cursor.fetchall())
            results_ms = (time.perf_counter() - results_started) * 1000

            calculate_started = time.perf_counter()
            values = [_upsert_values(user, results_by_user) for user in users]
            calculate_ms = (time.perf_counter() - calculate_started) * 1000

            upsert_started = time.perf_counter()
            for offset in range(0, len(values), UPSERT_BATCH_SIZE):
                batch = values[offset : offset + UPSERT_BATCH_SIZE]
                if not batch:
                    continue
                try:
                    cursor.executemany(UPSERT_SQL, batch)
                    sql_query_count += 1
                    conn.commit()
                    commit_count += 1
                except Exception:
                    conn.rollback()
                    print("statistics batch failed:", [(row[0], row[1]) for row in batch])
                    raise
            upsert_ms = (time.perf_counter() - upsert_started) * 1000
            total_ms = (time.perf_counter() - started) * 1000
            orders_count = sum(int(user.get("total_orders") or 0) for user in users)
            upsert_count = (len(values) + UPSERT_BATCH_SIZE - 1) // UPSERT_BATCH_SIZE
            print(
                "[job] job_name=statistics started_at=%s rows_read=%d rows_updated=%d "
                "rows_skipped=0 sql_count=%d commit_count=%d duration_ms=%.2f "
                "users_processed=%d select_count=2 upsert_count=%d orders=%d "
                "aggregate=%.2fms results=%.2fms calculate=%.2fms upsert=%.2fms"
                % (started_at, orders_count, len(values),
                   sql_query_count, commit_count, total_ms, len(users), upsert_count,
                   orders_count, aggregate_ms, results_ms, calculate_ms, upsert_ms)
            )
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
