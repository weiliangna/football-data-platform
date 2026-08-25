from fastapi import APIRouter
from database.mysql import get_conn
import pymysql


router = APIRouter(
    prefix="/api/rank",
    tags=["rank"]
)



@router.get("/list")
def rank_list():


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


            nickname,


            COUNT(*) order_count,


            ROUND(

            SUM(

            CASE

            WHEN result='赢'

            THEN 1

            ELSE 0

            END

            )

            /

            COUNT(*)

            *

            100,

            2

            )

            win_rate,


            IFNULL(
            SUM(profit),
            0
            )
            profit,


            IFNULL(
            SUM(follow_num),
            0
            )
            fans,


            ROUND(

            (
            IFNULL(SUM(profit),0)

            +

            COUNT(*)*10

            +

            IFNULL(SUM(follow_num),0)/100

            ),

            2

            )

            score


            FROM orders


            WHERE platform_id=1


            GROUP BY nickname


            ORDER BY score DESC


            LIMIT 50


            """
        )


        data=cursor.fetchall()



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

