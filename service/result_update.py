from database.mysql import get_conn
import pymysql



def update_result():

    conn=None
    cursor=None


    try:

        conn=get_conn()

        cursor=conn.cursor(
            pymysql.cursors.DictCursor
        )


        # 这里预留真实赛果接口
        #
        # 当前先处理已经人工录入的订单


        cursor.execute(
        """
        SELECT

        nickname,

        COUNT(*) total,

        SUM(
        CASE
        WHEN result='赢'
        THEN 1
        ELSE 0
        END
        ) win


        FROM orders


        GROUP BY nickname

        """
        )


        rows=cursor.fetchall()



        for item in rows:


            rate=0


            if item["total"]:

                rate=round(

                    item["win"]

                    /

                    item["total"]

                    *

                    100,

                    2

                )



            cursor.execute(
            """

            UPDATE expert_rank


            SET

            avg_hit_rate=%s


            WHERE nickname=%s


            """,
            (
                rate/100,
                item["nickname"]
            )

            )



        conn.commit()



        print(
            "赛果统计完成"
        )



    except Exception as e:


        print(
            e
        )


    finally:


        if cursor:

            cursor.close()


        if conn:

            conn.close()



if __name__=="__main__":

    update_result()

