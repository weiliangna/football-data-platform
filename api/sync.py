from fastapi import APIRouter
from database.mysql import get_conn
import pymysql


router = APIRouter(
    prefix="/api/sync",
    tags=["sync"]
)



@router.get("/latest")
def latest_sync():

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

        FROM sync_log

        ORDER BY id DESC

        LIMIT 20

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

