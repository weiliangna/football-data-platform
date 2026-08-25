from fastapi import APIRouter
from database.mysql import get_conn
import pymysql


router = APIRouter()


@router.get("/today")
def today_matches():

    try:

        conn = get_conn()


        cursor = conn.cursor(
            pymysql.cursors.DictCursor
        )


        sql = """

        SELECT

            id,
            league,
            home_team,
            away_team,
            match_time,
            home_score,
            away_score,
            status


        FROM matches


        ORDER BY match_time ASC


        LIMIT 50


        """


        cursor.execute(sql)


        data = cursor.fetchall()


        cursor.close()

        conn.close()


        return {

            "code":200,

            "data":data

        }


    except Exception as e:


        return {

            "code":500,

            "msg":str(e)

        }
