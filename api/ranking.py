from fastapi import APIRouter
from database.mysql import get_conn
from common.platform_registry import default_platform_metadata
import pymysql


router = APIRouter(
    prefix="/api/ranking",
    tags=["ranking"]
)


SORT_MAP = {

    "score":
        "expert_score DESC",

    "hit":
        "hit_rate DESC, settled_orders DESC",

    "profit":
        "total_profit DESC",

    "roi":
        "roi DESC, settled_orders DESC",

    "streak":
        "max_win_streak DESC, current_streak DESC",

    "follow":
        "follow_num DESC"
}


@router.get("/list")
def ranking_list(
    platform_id: int = 0,
    sort: str = "score",
    limit: int = 100
):

    conn = None
    cursor = None


    try:

        if limit < 1:
            limit = 100


        if limit > 500:
            limit = 500


        order_by = SORT_MAP.get(
            sort,
            SORT_MAP["score"]
        )


        conn = get_conn()


        cursor = conn.cursor(
            pymysql.cursors.DictCursor
        )


        sql = """
            SELECT

                platform_id,

                user_id,

                nickname,

                total_orders,

                settled_orders,

                win_orders,

                lose_orders,

                pending_orders,

                hit_rate,

                total_stake,

                total_profit,

                roi,

                follow_num,

                current_streak,

                max_win_streak,

                recent_results,

                expert_score,

                last_order_time,

                updated_time


            FROM user_statistics
        """


        params = []


        if platform_id > 0:

            sql += """
                WHERE platform_id=%s
            """

            params.append(
                platform_id
            )


        sql += (
            "\n ORDER BY "
            +
            order_by
            +
            "\n LIMIT %s"
        )


        params.append(
            limit
        )


        cursor.execute(
            sql,
            tuple(params)
        )


        data = cursor.fetchall()


        platform_map = {
            platform_id: item["name"]
            for platform_id, item in default_platform_metadata().items()
        }


        for index, item in enumerate(
            data,
            start=1
        ):

            item["rank"] = index


            item["platform_name"] = (
                platform_map.get(
                    int(
                        item.get(
                            "platform_id"
                        )
                        or 0
                    ),
                    "未知平台"
                )
            )


            item["total_stake"] = float(
                item.get(
                    "total_stake"
                )
                or 0
            )


            item["total_profit"] = float(
                item.get(
                    "total_profit"
                )
                or 0
            )


            item["hit_rate"] = float(
                item.get(
                    "hit_rate"
                )
                or 0
            )


            item["roi"] = float(
                item.get(
                    "roi"
                )
                or 0
            )


            item["expert_score"] = float(
                item.get(
                    "expert_score"
                )
                or 0
            )


            recent = str(
                item.get(
                    "recent_results"
                )
                or ""
            )


            item["recent7"] = [

                value

                for value
                in recent.split(",")

                if value
            ]


        return {
            "code": 200,
            "count": len(data),
            "platform_id": platform_id,
            "sort": sort,
            "data": data
        }


    except Exception as e:

        return {
            "code": 500,
            "msg": str(e),
            "data": []
        }


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
