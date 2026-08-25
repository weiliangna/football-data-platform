from fastapi import APIRouter
import pymysql
from database.mysql import get_conn


router = APIRouter()


ACTIVE_PLATFORM_ID = 1



PASS_MAP = {

    "500":"单关",

    "502":"2串1",

    "503":"3串1",

    "504":"4串1",

    "505":"5串1",

    "506":"6串1",

    "507":"7串1",

    "MIX":"混合过关"

}



def classify_result(value):

    text=str(value or "").strip()


    if not text:
        return "pending"


    if "输" in text or "黑" in text:
        return "loss"


    if "赢" in text or "红" in text or "命中" in text:
        return "win"


    return "pending"




def calculate_streaks(orders):

    settled=[]


    for item in orders:

        r=classify_result(
            item.get("result")
        )

        if r in ("win","loss"):

            settled.append(r)



    current=0


    for r in settled:

        if r=="win":

            current+=1

        else:

            break



    max_streak=0
    run=0


    for r in reversed(settled):

        if r=="win":

            run+=1

            max_streak=max(
                max_streak,
                run
            )

        else:

            run=0


    return current,max_streak




def add_play_name(items):

    for item in items:

        code=str(
            item.get("play_type")
            or ""
        )

        item["play_name"]=PASS_MAP.get(
            code,
            code
        )

    return items




@router.get("/{user_id}")
def expert_detail(user_id:int):


    conn=None
    cursor=None


    try:


        conn=get_conn()


        cursor=conn.cursor(
            pymysql.cursors.DictCursor
        )



        cursor.execute(
            """
            SELECT *
            FROM expert_rank
            WHERE platform_id=%s
            AND user_id=%s
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                ACTIVE_PLATFORM_ID,
                user_id
            )
        )


        expert=cursor.fetchone()



        cursor.execute(
            """
            SELECT nickname
            FROM orders
            WHERE platform_id=%s
            AND user_id=%s
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                ACTIVE_PLATFORM_ID,
                user_id
            )
        )


        row=cursor.fetchone()


        nickname = (
            row["nickname"]
            if row
            else None
        )



        cursor.execute(
            """
            SELECT *
            FROM orders
            WHERE platform_id=%s
            AND user_id=%s
            ORDER BY
            COALESCE(
                publish_time,
                created_time
            ) DESC
            LIMIT 100
            """,
            (
                ACTIVE_PLATFORM_ID,
                user_id
            )
        )


        orders=cursor.fetchall()


        orders=add_play_name(
            orders
        )



        total_order=len(
            orders
        )


        win=0
        lose=0
        pending=0

        amount=0
        profit=0
        follow=0



        for item in orders:


            amount += float(
                item.get("stake")
                or 0
            )


            profit += float(
                item.get("profit")
                or 0
            )


            follow += int(
                item.get("follow_num")
                or 0
            )


            r=classify_result(
                item.get("result")
            )


            if r=="win":

                win+=1

            elif r=="loss":

                lose+=1

            else:

                pending+=1



        settled=win+lose


        hit_rate=round(
            win/settled*100,
            2
        ) if settled else 0



        roi=round(
            profit/amount*100,
            2
        ) if amount else 0



        current_streak,max_streak = calculate_streaks(
            orders
        )



        return {


            "code":200,


            "data":{


                "expert":expert or {

                    "user_id":user_id,

                    "nickname":nickname or "未知专家"

                },


                "real_stats":{


                    "total_order":total_order,

                    "win_order":win,

                    "lose_order":lose,

                    "pending_order":pending,

                    "win_rate":hit_rate,

                    "roi":roi,

                    "total_amount":round(amount,2),

                    "total_profit":round(profit,2),

                    "total_follow":follow,

                    "current_streak":current_streak,

                    "max_streak":max_streak

                },


                "orders":orders


            }

        }



    except Exception as e:


        return {

            "code":500,

            "msg":str(e),

            "data":None

        }



    finally:


        if cursor:

            cursor.close()


        if conn:

            conn.close()
