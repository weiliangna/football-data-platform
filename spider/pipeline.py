import sys
import os
import time
from datetime import datetime


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(
    0,
    BASE_DIR
)


from database.mysql import get_conn
import pymysql



def save_sync_log(
        platform_name,
        new_count,
        duplicate_count,
        cost_time,
        status="success"
):

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor()


        cursor.execute(
            """
            INSERT INTO sync_log
            (
                platform_name,
                new_count,
                duplicate_count,
                status,
                cost_time,
                created_time
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW()
            )

            """,
            (
                platform_name,
                new_count,
                duplicate_count,
                status,
                cost_time
            )
        )


        conn.commit()


    except Exception as e:

        print(
            "写入同步日志失败:",
            e
        )


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()



def run_caizhanyun():

    start = time.time()


    new_count = 0

    duplicate_count = 0


    try:

        print(
            "采集：彩站云"
        )


        from spider.caizhanyun_pipeline import main


        result = main()


        # 兼容旧版本
        if isinstance(result, dict):

            new_count = result.get(
                "new_count",
                0
            )

            duplicate_count = result.get(
                "duplicate_count",
                0
            )


        cost = round(
            time.time()-start,
            2
        )


        save_sync_log(
            "彩站云",
            new_count,
            duplicate_count,
            cost
        )


        print(
            f"彩站云完成 新增:{new_count} 重复:{duplicate_count} 耗时:{cost}s"
        )



    except Exception as e:


        cost = round(
            time.time()-start,
            2
        )


        save_sync_log(
            "彩站云",
            0,
            0,
            cost,
            "failed"
        )


        print(
            "彩站云异常:",
            e
        )





def run_empty_platform(name):

    start=time.time()


    print(
        f"采集：{name}"
    )


    cost=round(
        time.time()-start,
        2
    )


    save_sync_log(
        name,
        0,
        0,
        cost,
        "waiting"
    )


    print(
        f"{name}接口待接入"
    )




def run():


    print("="*60)

    print(
        "开始四平台订单采集"
    )

    print("="*60)



    # 彩站云

    run_caizhanyun()



    # 其他平台

    run_empty_platform(
        "州运宝"
    )


    run_empty_platform(
        "鸿瑞"
    )


    run_empty_platform(
        "云彩"
    )



    print("="*60)

    print(
        "四平台采集完成"
    )

    print("="*60)




if __name__=="__main__":

    run()

