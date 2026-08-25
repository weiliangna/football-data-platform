from fastapi import APIRouter
from database.mysql import get_conn
import pymysql

router = APIRouter(prefix="/api/platform", tags=["platform"])


@router.get("/list")
def platform_list():
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            SELECT platform_id,name,enabled,spider_enabled,result_enabled,settlement_enabled,updated_time
            FROM platform_config
            ORDER BY platform_id ASC
            """
        )
        return {"code":200,"data":cursor.fetchall()}
    except Exception as e:
        return {"code":500,"msg":str(e),"data":[]}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
