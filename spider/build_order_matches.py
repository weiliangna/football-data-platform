from database.mysql import get_conn
import pymysql



def split_orders():


    conn = get_conn()


    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )



    cursor.execute(
        """
        SELECT

            id,

            league,

            selection,

            handicap

        FROM orders

        WHERE selection IS NOT NULL

        """
    )


    orders = cursor.fetchall()


    count = 0



    for order in orders:


        order_id = order["id"]

        league = order["league"]

        selection = order["selection"]

        order_handicap = (
            order["handicap"]
            or 0
        )



        if not selection:

            continue



        parts = selection.split("；")



        for part in parts:



            if "→" not in part:

                continue



            match_name, play = part.split(
                "→",
                1
            )



            match_name = match_name.strip()

            play = play.strip()



            real_play_type = ""

            real_selection = play



            # 提取玩法

            if "：" in play:


                real_play_type, real_selection = play.split(
                    "：",
                    1
                )


                real_play_type = (
                    real_play_type.strip()
                )


                real_selection = (
                    real_selection.strip()
                )



            # ===========================
            # 盘口处理
            # ===========================

            match_handicap = 0


            if real_play_type == "让球胜平负":

                match_handicap = order_handicap



            # ===========================
            # 防重复
            # ===========================

            cursor.execute(
                """

                SELECT id

                FROM order_matches

                WHERE

                order_id=%s

                AND match_name=%s

                AND play_type=%s

                AND selection=%s


                """,
                (

                    order_id,

                    match_name,

                    real_play_type,

                    real_selection

                )
            )


            exists = cursor.fetchone()



            if exists:

                continue



            cursor.execute(
                """

                INSERT INTO order_matches

                (

                    order_id,

                    match_name,

                    league,

                    play_type,

                    selection,

                    handicap

                )


                VALUES

                (

                    %s,

                    %s,

                    %s,

                    %s,

                    %s,

                    %s

                )


                """,
                (

                    order_id,

                    match_name,

                    league,

                    real_play_type,

                    real_selection,

                    match_handicap

                )
            )



            count += 1



    conn.commit()


    cursor.close()


    conn.close()



    print(
        "拆解完成:",
        count
    )




if __name__ == "__main__":


    split_orders()
