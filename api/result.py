from fastapi import APIRouter
from database.mysql import get_conn
import pymysql


router = APIRouter(
    prefix="/api/result",
    tags=["result"]
)


PASS_MAP = {
    "500": "单关",
    "502": "2串1",
    "503": "3串1",
    "504": "4串1",
    "505": "5串1",
    "506": "6串1",
    "507": "7串1",
    "MIX": "混合过关"
}


def platform_name(platform_id):

    mapping = {
        1: "彩站云",
        2: "州运宝",
        3: "鸿瑞",
        4: "云彩"
    }

    return mapping.get(
        int(platform_id or 0),
        "未知平台"
    )


def play_name(
    play_type,
    pass_summary
):

    value = str(
        pass_summary
        or
        play_type
        or ""
    ).strip()


    return PASS_MAP.get(
        value,
        value
    )


@router.get("/summary")
def result_summary(
    platform_id: int = 0
):

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(
            pymysql.cursors.DictCursor
        )


        # ====================================================
        # 总体统计
        # ====================================================

        summary_sql = """
            SELECT

                COUNT(*) AS total,


                SUM(
                    CASE
                        WHEN result != '待开奖'
                        THEN 1
                        ELSE 0
                    END
                ) AS finished,


                SUM(
                    CASE
                        WHEN result = '赢'
                        THEN 1
                        ELSE 0
                    END
                ) AS win,


                SUM(
                    CASE
                        WHEN result = '输'
                        THEN 1
                        ELSE 0
                    END
                ) AS lose,


                SUM(
                    CASE
                        WHEN result = '待开奖'
                        THEN 1
                        ELSE 0
                    END
                ) AS pending,


                IFNULL(
                    SUM(profit),
                    0
                ) AS profit,


                IFNULL(
                    SUM(stake),
                    0
                ) AS total_amount


            FROM orders
        """


        summary_params = []


        if platform_id > 0:

            summary_sql += """
                WHERE platform_id = %s
            """

            summary_params.append(
                platform_id
            )


        cursor.execute(
            summary_sql,
            tuple(summary_params)
        )


        summary = cursor.fetchone() or {}


        total = int(
            summary.get("total")
            or 0
        )

        finished = int(
            summary.get("finished")
            or 0
        )

        win = int(
            summary.get("win")
            or 0
        )

        lose = int(
            summary.get("lose")
            or 0
        )

        pending = int(
            summary.get("pending")
            or 0
        )


        win_rate = 0.0


        if finished > 0:

            win_rate = round(
                win
                /
                finished
                *
                100,
                2
            )


        summary = {
            "total": total,
            "finished": finished,
            "win": win,
            "lose": lose,
            "pending": pending,
            "win_rate": win_rate,
            "profit": float(
                summary.get("profit")
                or 0
            ),
            "total_amount": float(
                summary.get("total_amount")
                or 0
            )
        }


        # ====================================================
        # 用户战绩
        # ====================================================

        expert_sql = """
            SELECT

                platform_id,

                user_id,

                MAX(nickname) AS nickname,

                COUNT(*) AS orders,


                SUM(
                    CASE
                        WHEN result != '待开奖'
                        THEN 1
                        ELSE 0
                    END
                ) AS finished,


                SUM(
                    CASE
                        WHEN result = '赢'
                        THEN 1
                        ELSE 0
                    END
                ) AS win,


                SUM(
                    CASE
                        WHEN result = '输'
                        THEN 1
                        ELSE 0
                    END
                ) AS lose,


                IFNULL(
                    SUM(profit),
                    0
                ) AS profit,


                IFNULL(
                    SUM(stake),
                    0
                ) AS total_amount


            FROM orders
        """


        expert_params = []


        if platform_id > 0:

            expert_sql += """
                WHERE platform_id = %s
            """

            expert_params.append(
                platform_id
            )


        expert_sql += """
            GROUP BY

                platform_id,

                user_id


            ORDER BY

                profit DESC,

                orders DESC


            LIMIT 100
        """


        cursor.execute(
            expert_sql,
            tuple(expert_params)
        )


        experts = cursor.fetchall()


        for item in experts:

            item_finished = int(
                item.get("finished")
                or 0
            )

            item_win = int(
                item.get("win")
                or 0
            )


            item["platform_name"] = platform_name(
                item.get("platform_id")
            )


            item["orders"] = int(
                item.get("orders")
                or 0
            )

            item["finished"] = item_finished

            item["win"] = item_win

            item["lose"] = int(
                item.get("lose")
                or 0
            )


            if item_finished > 0:

                item["win_rate"] = round(
                    item_win
                    /
                    item_finished
                    *
                    100,
                    2
                )

            else:

                item["win_rate"] = 0.0


            item["profit"] = float(
                item.get("profit")
                or 0
            )

            item["total_amount"] = float(
                item.get("total_amount")
                or 0
            )


        # ====================================================
        # 最近订单结果
        # ====================================================

        order_sql = """
            SELECT

                id,

                platform_id,

                platform_order_id,

                user_id,

                nickname,

                match_name,

                league,

                play_type,

                pass_summary,

                selection,

                odds_text,

                stake,

                follow_num,

                handicap,

                result,

                profit,

                publish_time,

                created_time


            FROM orders
        """


        order_params = []


        if platform_id > 0:

            order_sql += """
                WHERE platform_id = %s
            """

            order_params.append(
                platform_id
            )


        order_sql += """
            ORDER BY id DESC

            LIMIT 50
        """


        cursor.execute(
            order_sql,
            tuple(order_params)
        )


        recent_orders = cursor.fetchall()


        for item in recent_orders:

            item["platform_name"] = platform_name(
                item.get("platform_id")
            )


            item["play_name"] = play_name(
                item.get("play_type"),
                item.get("pass_summary")
            )


            item["stake"] = float(
                item.get("stake")
                or 0
            )

            item["profit"] = float(
                item.get("profit")
                or 0
            )

            item["follow_num"] = int(
                item.get("follow_num")
                or 0
            )

            item["handicap"] = int(
                item.get("handicap")
                or 0
            )


        # ====================================================
        # 真实比赛赛果
        #
        # 全部平台：
        # 返回 match_results
        #
        # 指定平台：
        # 只返回该平台订单涉及的比赛
        # ====================================================

        match_sql = """
            SELECT

                mr.id,

                mr.match_name,

                mr.league,

                mr.home_team,

                mr.away_team,

                mr.home_score,

                mr.away_score,

                mr.half_home_score,

                mr.half_away_score,

                mr.status,

                mr.finished_time,

                mr.created_time


            FROM match_results mr
        """


        match_params = []


        if platform_id > 0:

            match_sql += """
                WHERE EXISTS
                (
                    SELECT 1

                    FROM order_matches om

                    INNER JOIN orders o

                        ON o.id = om.order_id

                    WHERE

                        om.match_name = mr.match_name

                        AND o.platform_id = %s
                )
            """

            match_params.append(
                platform_id
            )


        match_sql += """
            ORDER BY

                mr.finished_time DESC,

                mr.id DESC

            LIMIT 100
        """


        cursor.execute(
            match_sql,
            tuple(match_params)
        )


        matches = cursor.fetchall()


        for item in matches:

            item["home_score"] = int(
                item.get("home_score")
                or 0
            )

            item["away_score"] = int(
                item.get("away_score")
                or 0
            )


            if (
                item.get("half_home_score")
                is not None
            ):

                item["half_home_score"] = int(
                    item["half_home_score"]
                )


            if (
                item.get("half_away_score")
                is not None
            ):

                item["half_away_score"] = int(
                    item["half_away_score"]
                )


        return {
            "code": 200,

            "platform_id": platform_id,

            "data": {

                "summary":
                    summary,

                "experts":
                    experts,

                "recent_orders":
                    recent_orders,

                "matches":
                    matches
            }
        }


    except Exception as e:

        return {
            "code": 500,
            "msg": str(e),
            "data": {}
        }


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
