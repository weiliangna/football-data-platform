"""Settle pending matches in bounded transactions and skip unchanged rows."""

import os
import sys
import time

import pymysql

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api.settlement import identity_schema_available, settle_match_with_connection
from database.mysql import get_conn


SETTLEMENT_BATCH_SIZE = 50


def load_pending_match_results(cursor, identity_v2):
    if not identity_v2:
        cursor.execute(
            """
            SELECT DISTINCT
                mr.id,mr.match_name,mr.home_score,mr.away_score,
                mr.half_home_score,mr.half_away_score,mr.finished_time
            FROM match_results mr
            INNER JOIN order_matches om ON om.match_name=mr.match_name
            WHERE mr.status='已结束' AND om.result='待开奖'
            ORDER BY mr.id ASC
            LIMIT 200
            """
        )
        return cursor.fetchall()

    cursor.execute(
        """
        SELECT
            mr.id,mr.platform_id,mr.match_date,mr.match_code,mr.match_key,
            mr.match_identity,mr.identity_quality,mr.match_name,mr.home_team,
            mr.away_team,mr.home_score,mr.away_score,mr.half_home_score,
            mr.half_away_score,mr.finished_time
        FROM match_results mr
        WHERE mr.status='已结束'
          AND EXISTS (
              SELECT 1
              FROM order_matches om
              WHERE om.result='待开奖'
                AND (
                    (mr.platform_id IS NOT NULL AND mr.match_date IS NOT NULL
                     AND mr.match_code IS NOT NULL AND mr.match_code<>''
                     AND om.platform_id=mr.platform_id
                     AND om.match_date=mr.match_date
                     AND om.match_code=mr.match_code)
                    OR
                    (mr.platform_id IS NOT NULL AND mr.match_date IS NOT NULL
                     AND mr.match_key IS NOT NULL AND mr.match_key<>''
                     AND om.platform_id=mr.platform_id
                     AND om.match_date=mr.match_date
                     AND om.match_key=mr.match_key)
                    OR
                    (om.match_name=mr.match_name
                     AND (om.platform_id IS NULL OR mr.platform_id IS NULL
                          OR om.platform_id=mr.platform_id)
                     AND (om.match_date IS NULL OR mr.match_date IS NULL
                          OR om.platform_id IS NULL OR mr.platform_id IS NULL))
                )
          )
        ORDER BY mr.id ASC
        LIMIT 200
        """
    )
    return cursor.fetchall()


def optional_score(row, key):
    value = row.get(key)
    return int(value) if value is not None else None


def main():
    started = time.perf_counter()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    conn = None
    cursor = None
    sql_count = 0
    commit_count = 0
    rows_updated = 0
    rows_skipped = 0
    pending_found = 0
    result_changed = 0
    unchanged_skipped = 0
    success = failed = 0

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        identity_v2 = identity_schema_available(cursor)
        sql_count += 3  # two schema reads plus the pending-match query
        matches = load_pending_match_results(cursor, identity_v2)
        pending_found = len(matches)
        print("待自动结算比赛:", pending_found)

        for index, match in enumerate(matches, 1):
            match_name = match.get("match_name")
            cursor.execute("SAVEPOINT settlement_match")
            sql_count += 1
            try:
                result = settle_match_with_connection(
                    conn,
                    match_name,
                    int(match.get("home_score") or 0),
                    int(match.get("away_score") or 0),
                    optional_score(match, "half_home_score"),
                    optional_score(match, "half_away_score"),
                    platform_id=match.get("platform_id"),
                    source_match_code=match.get("match_code"),
                    match_date=match.get("match_date"),
                    home_team=match.get("home_team"),
                    away_team=match.get("away_team"),
                )
                success += 1
                rows_updated += int(result.get("rows_updated") or 0)
                rows_skipped += int(result.get("rows_skipped") or 0)
                result_changed += int(result.get("result_changed") or 0)
                unchanged_skipped += int(result.get("unchanged_skipped") or 0)
                print(
                    "✓", match_name,
                    "更新=", result.get("rows_updated", 0),
                    "跳过=", result.get("rows_skipped", 0),
                )
                if index % SETTLEMENT_BATCH_SIZE == 0:
                    conn.commit()
                    commit_count += 1
            except Exception as exc:
                cursor.execute("ROLLBACK TO SAVEPOINT settlement_match")
                sql_count += 1
                failed += 1
                print("✗ 自动结算失败:", match_name)
                print("原因:", str(exc))

        if success or failed:
            conn.commit()
            commit_count += 1
        duration_ms = (time.perf_counter() - started) * 1000
        print(
            "[job] job_name=settlement started_at=%s rows_read=%d rows_updated=%d "
            "rows_skipped=%d sql_count=%d commit_count=%d duration_ms=%.2f "
            "pending_found=%d result_changed=%d unchanged_skipped=%d success=%d failed=%d"
            % (
                started_at,
                pending_found,
                rows_updated,
                rows_skipped,
                sql_count,
                commit_count,
                duration_ms,
                pending_found,
                result_changed,
                unchanged_skipped,
                success,
                failed,
            )
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
