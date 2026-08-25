import os
import sys

import pymysql


ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if ROOT not in sys.path:
    sys.path.insert(
        0,
        ROOT
    )


from database.mysql import get_conn
from api.settlement import settle_match_with_connection


def main():

    conn = None
    cursor = None


    try:

        conn = get_conn()

        cursor = conn.cursor(
            pymysql.cursors.DictCursor
        )


        # ====================================================
        # 找已经结束、并且仍有待开奖订单的比赛
        # ====================================================

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

                ON om.match_name = mr.match_name


            WHERE

                mr.status = '已结束'

                AND om.result = '待开奖'


            ORDER BY mr.id ASC


            LIMIT 200
            """
        )


        matches = cursor.fetchall()


        print(
            "待自动结算比赛:",
            len(matches)
        )


        success = 0
        failed = 0


        for match in matches:

            match_name = match.get(
                "match_name"
            )


            try:

                result = settle_match_with_connection(
                    conn,
                    match_name,
                    int(
                        match.get(
                            "home_score"
                        )
                        or 0
                    ),
                    int(
                        match.get(
                            "away_score"
                        )
                        or 0
                    ),
                    (
                        int(
                            match[
                                "half_home_score"
                            ]
                        )
                        if
                        match.get(
                            "half_home_score"
                        )
                        is not None
                        else None
                    ),
                    (
                        int(
                            match[
                                "half_away_score"
                            ]
                        )
                        if
                        match.get(
                            "half_away_score"
                        )
                        is not None
                        else None
                    )
                )


                conn.commit()


                success += 1


                print()
                print(
                    "✓",
                    match_name
                )

                print(
                    "比分:",
                    match.get("home_score"),
                    "-",
                    match.get("away_score")
                )

                print(
                    "拆单:",
                    result.get("match_rows")
                )

                print(
                    "赢:",
                    result.get("win_rows")
                )

                print(
                    "输:",
                    result.get("lose_rows")
                )

                print(
                    "待开奖:",
                    result.get("pending_rows")
                )

                print(
                    "涉及订单:",
                    result.get("orders")
                )


            except Exception as e:

                conn.rollback()

                failed += 1


                print()
                print(
                    "✗ 自动结算失败:",
                    match_name
                )

                print(
                    "原因:",
                    str(e)
                )


        print()
        print("=" * 70)

        print(
            "自动结算完成"
        )

        print(
            "成功:",
            success
        )

        print(
            "失败:",
            failed
        )


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


if __name__ == "__main__":

    main()
