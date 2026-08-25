from fastapi import APIRouter
from database.mysql import get_conn


router = APIRouter()


@router.get("/mysql")
def mysql_test():

    try:

        conn = get_conn()

        cursor = conn.cursor()

        cursor.execute(
            "show tables"
        )

        tables = cursor.fetchall()


        cursor.close()

        conn.close()


        return {
            "code":200,
            "msg":"数据库连接成功",
            "tables":tables
        }


    except Exception as e:

        return {
            "code":500,
            "msg":str(e)
        }
