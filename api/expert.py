from fastapi import APIRouter
from database.mysql import get_conn
import pymysql

# ===============================
# 玩法代码映射
# ===============================

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




router = APIRouter(
    prefix="/api/expert",
    tags=["expert"]
)



# =====================================================
# 专家排行榜
# 按 user_id 聚合
# =====================================================

@router.get("/list")
def expert_list():


    conn = None
    cursor = None


    try:


        conn = get_conn()


        cursor = conn.cursor(
            pymysql.cursors.DictCursor
        )


        cursor.execute(
            """

            SELECT


                user_id,


                MAX(nickname) nickname,


                COUNT(*) order_count,


                SUM(stake) total_amount,


                SUM(profit) total_profit,


                SUM(
                    CASE
                    WHEN result='赢'
                    THEN 1
                    ELSE 0
                    END
                ) win_count,


                SUM(
                    CASE
                    WHEN result='输'
                    THEN 1
                    ELSE 0
                    END
                ) lose_count


            FROM orders


            WHERE user_id IS NOT NULL


            GROUP BY user_id


            """
        )


        rows = cursor.fetchall()


        data=[]


        for row in rows:


            order_count = row["order_count"] or 0


            win_count = row["win_count"] or 0


            lose_count = row["lose_count"] or 0


            amount=float(
                row["total_amount"] or 0
            )


            profit=float(
                row["total_profit"] or 0
            )


            settled = (
                win_count +
                lose_count
            )


            hit_rate=0


            if settled:

                hit_rate=round(
                    win_count /
                    settled *
                    100,
                    2
                )


            roi=0


            if amount:

                roi=round(
                    profit /
                    amount *
                    100,
                    2
                )


            money_score=min(
                amount / 10000,
                100
            )


            stability=min(
                order_count * 5,
                100
            )


            score=round(

                roi * 0.35

                +

                hit_rate * 0.30

                +

                money_score * 0.20

                +

                stability * 0.15,

                2
            )


            data.append({

                "user_id":
                    row["user_id"],

                "nickname":
                    row["nickname"],

                "order_count":
                    order_count,

                "total_amount":
                    amount,

                "win_count":
                    win_count,

                "lose_count":
                    lose_count,

                "profit":
                    profit,

                "hit_rate":
                    hit_rate,

                "roi":
                    roi,

                "expert_score":
                    score

            })


        data.sort(
            key=lambda x:
            x["expert_score"],
            reverse=True
        )


        return {

            "code":200,

            "count":
                len(data),

            "data":
                data[:50]

        }



    except Exception as e:


        return {

            "code":500,

            "msg":str(e),

            "data":[]

        }



    finally:


        if cursor:

            cursor.close()


        if conn:

            conn.close()




# =====================================================
# 专家盈利榜
# =====================================================

@router.get("/profit")
def expert_profit():

    return expert_list()




# =====================================================
# 专家详情
# user_id模式
# =====================================================

@router.get("/detail/{user_id}")
def expert_detail(
    user_id:int
):


    conn=None
    cursor=None


    try:


        conn=get_conn()


        cursor=conn.cursor(
            pymysql.cursors.DictCursor
        )



        cursor.execute(
            """

            SELECT


                user_id,


                MAX(nickname) nickname,


                COUNT(*) order_count,


                SUM(stake) total_amount,


                SUM(profit) total_profit,


                SUM(
                    CASE
                    WHEN result='赢'
                    THEN 1
                    ELSE 0
                    END
                ) win_count,


                SUM(
                    CASE
                    WHEN result='输'
                    THEN 1
                    ELSE 0
                    END
                ) lose_count


            FROM orders


            WHERE user_id=%s


            GROUP BY user_id


            """,
            (
                user_id,
            )
        )


        summary=cursor.fetchone()


        if not summary:


            return {

                "code":404,

                "msg":"专家不存在"

            }



        order_count = (
            summary["order_count"]
            or 0
        )


        win_count = (
            summary["win_count"]
            or 0
        )


        lose_count = (
            summary["lose_count"]
            or 0
        )


        amount=float(
            summary["total_amount"]
            or 0
        )


        profit=float(
            summary["total_profit"]
            or 0
        )


        settled = (
            win_count +
            lose_count
        )


        hit_rate=0


        if settled:

            hit_rate=round(
                win_count /
                settled *
                100,
                2
            )


        roi=0


        if amount:

            roi=round(
                profit /
                amount *
                100,
                2
            )



        cursor.execute(
            """

            SELECT


                id,


                match_name,


                play_type,


                pass_summary,


                selection,


                result,


                stake,


                profit,


                publish_time


            FROM orders


            WHERE user_id=%s


            ORDER BY id DESC


            LIMIT 20


            """,
            (
                user_id,
            )
        )


        orders=cursor.fetchall()


        # ============================
        # 玩法代码转换
        # ============================

        for item in orders:


            code = str(
                item.get("play_type")
                or ""
            )


            item["play_name"] = PASS_MAP.get(
                code,
                code
            )



        return {

            "code":200,


            "data":{


                "user_id":
                    user_id,


                "nickname":
                    summary["nickname"],


                "summary":{


                    "order_count":
                        order_count,


                    "settled_count":
                        settled,


                    "win_count":
                        win_count,


                    "lose_count":
                        lose_count,


                    "total_amount":
                        amount,


                    "profit":
                        profit,


                    "hit_rate":
                        hit_rate,


                    "roi":
                        roi

                },


                "recent_orders":
                    orders


            }

        }



    except Exception as e:


        return {

            "code":500,

            "msg":str(e)

        }



    finally:


        if cursor:

            cursor.close()


        if conn:

            conn.close()
# =====================================================
# 专家收益曲线
# =====================================================

@router.get("/chart/{user_id}")
def expert_chart(
    user_id:int
):


    conn=None
    cursor=None


    try:


        conn=get_conn()


        cursor=conn.cursor(
            pymysql.cursors.DictCursor
        )


        cursor.execute(
            """

            SELECT


                DATE(created_time) AS date,


                SUM(profit) AS daily_profit


            FROM orders


            WHERE user_id=%s


            GROUP BY DATE(created_time)


            ORDER BY date ASC


            """,
            (
                user_id,
            )
        )


        rows=cursor.fetchall()



        total_profit=0


        data=[]


        for row in rows:


            daily=float(
                row["daily_profit"]
                or 0
            )


            total_profit += daily



            data.append({

                "date":
                    str(row["date"]),


                "profit":
                    daily,


                "total_profit":
                    total_profit

            })



        return {


            "code":200,


            "data":data


        }



    except Exception as e:


        return {


            "code":500,

            "msg":str(e),

            "data":[]

        }



    finally:


        if cursor:

            cursor.close()


        if conn:

            conn.close()