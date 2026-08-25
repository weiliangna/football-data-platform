from database.mysql import get_conn
import pymysql



def generate_rank():


    conn=get_conn()

    cursor=conn.cursor()



    cursor.execute(
    """

    UPDATE expert_rank r

    SET

    expert_score=

    (

    r.avg_hit_rate*50

    +

    r.avg_profitability*30

    +

    r.avg_follow/100

    )


    """
    )


    conn.commit()


    cursor.close()

    conn.close()



    print(
    "排行榜更新完成"
    )



if __name__=="__main__":

    generate_rank()

