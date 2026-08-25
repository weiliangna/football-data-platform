import os
import sys

import pymysql


ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from api.settlement import (
    identity_schema_available,
    settle_match_with_connection,
)
from database.mysql import get_conn


def load_pending_match_results(cursor, identity_v2):
    if not identity_v2:
        cursor.execute(
            """
            SELECT DISTINCT
                mr.id,
                mr.match_name,
                mr.home_score,
                mr.away_score,
                mr.half_home_score,
                mr.half_away_score,
                mr.finished_time
            FROM match_results mr
            INNER JOIN order_matches om
                ON om.match_name=mr.match_name
            WHERE mr.status='已结束'
              AND om.result='待开奖'
            ORDER BY mr.id ASC
            LIMIT 200
            """
        )
        return cursor.fetchall()

    cursor.execute(
        """
        SELECT
            mr.id,
            mr.platform_id,
            mr.match_date,
            mr.match_code,
            mr.match_key,
            mr.match_identity,
            mr.identity_quality,
            mr.match_name,
            mr.home_team,
            mr.away_team,
            mr.home_score,
            mr.away_score,
            mr.half_home_score,
            mr.half_away_score,
            mr.finished_time
        FROM match_results mr
        WHERE mr.status='已结束'
          AND EXISTS
          (
              SELECT 1
              FROM order_matches om
              WHERE om.result='待开奖'
                AND
                (
                    (
                        mr.platform_id IS NOT NULL
                        AND mr.match_date IS NOT NULL
                        AND mr.match_code IS NOT NULL
                        AND mr.match_code<>''
                        AND om.platform_id=mr.platform_id
                        AND om.match_date=mr.match_date
                        AND om.match_code=mr.match_code
                    )
                    OR
                    (
                        mr.platform_id IS NOT NULL
                        AND mr.match_date IS NOT NULL
                        AND mr.match_key IS NOT NULL
                        AND mr.match_key<>''
                        AND om.platform_id=mr.platform_id
                        AND om.match_date=mr.match_date
                        AND om.match_key=mr.match_key
                    )
                    OR
                    (
                        om.match_name=mr.match_name
                        AND (
                            om.platform_id IS NULL
                            OR mr.platform_id IS NULL
                            OR om.platform_id=mr.platform_id
                        )
                        AND (
                            om.match_date IS NULL
                            OR mr.match_date IS NULL
                            OR om.platform_id IS NULL
                            OR mr.platform_id IS NULL
                        )
                    )
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
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        identity_v2 = identity_schema_available(cursor)
        matches = load_pending_match_results(
            cursor,
            identity_v2,
        )

        print("待自动结算比赛:", len(matches))
        success = 0
        failed = 0

        for match in matches:
            match_name = match.get("match_name")

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
                conn.commit()
                success += 1

                print()
                print("✓", match_name)
                print(
                    "比分:",
                    match.get("home_score"),
                    "-",
                    match.get("away_score"),
                )
                print("拆单:", result.get("match_rows"))
                print("赢:", result.get("win_rows"))
                print("输:", result.get("lose_rows"))
                print("待开奖:", result.get("pending_rows"))
                print("涉及订单:", result.get("orders"))
                print(
                    "匹配策略:",
                    result.get("match_strategies"),
                )
            except Exception as exc:
                conn.rollback()
                failed += 1
                print()
                print("✗ 自动结算失败:", match_name)
                print("原因:", str(exc))

        print()
        print("=" * 70)
        print("自动结算完成")
        print("成功:", success)
        print("失败:", failed)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
