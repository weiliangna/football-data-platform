from fastapi import APIRouter
from database.mysql import get_conn
from common.platform_registry import default_platform_metadata
import pymysql

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
PLATFORM_MAP = {
    platform_id: item["name"]
    for platform_id, item in default_platform_metadata().items()
}


@router.get("/summary")
def dashboard_summary(platform_id:int=0):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        where = ["DATE(COALESCE(publish_time,created_time))=CURDATE()"]
        params = []
        if platform_id > 0:
            where.append("platform_id=%s")
            params.append(platform_id)
        where_sql = " AND ".join(where)
        cursor.execute(
            f"""
            SELECT COUNT(*) AS total_orders,
                   SUM(CASE WHEN result!='待开奖' THEN 1 ELSE 0 END) AS settled_orders,
                   SUM(CASE WHEN result='赢' THEN 1 ELSE 0 END) AS win_orders,
                   SUM(CASE WHEN result='输' THEN 1 ELSE 0 END) AS lose_orders,
                   IFNULL(SUM(stake),0) AS total_stake,
                   IFNULL(SUM(profit),0) AS total_profit
            FROM orders
            WHERE {where_sql}
            """,
            tuple(params),
        )
        summary = cursor.fetchone()
        settled = int(summary.get("settled_orders") or 0)
        wins = int(summary.get("win_orders") or 0)
        summary["win_rate"] = round(wins/settled*100,2) if settled else 0.0
        summary["total_stake"] = float(summary.get("total_stake") or 0)
        summary["total_profit"] = float(summary.get("total_profit") or 0)

        cursor.execute(
            """
            SELECT platform_id,COUNT(*) AS orders,IFNULL(SUM(stake),0) AS stake,IFNULL(SUM(profit),0) AS profit
            FROM orders
            WHERE DATE(COALESCE(publish_time,created_time))=CURDATE()
            GROUP BY platform_id
            ORDER BY orders DESC
            """
        )
        platforms = cursor.fetchall()
        for item in platforms:
            item["platform_name"] = PLATFORM_MAP.get(int(item.get("platform_id") or 0),"未知平台")
            item["stake"] = float(item.get("stake") or 0)
            item["profit"] = float(item.get("profit") or 0)

        top_where = "WHERE platform_id=%s" if platform_id > 0 else ""
        top_params = (platform_id,) if platform_id > 0 else ()
        cursor.execute(
            f"""
            SELECT platform_id,user_id,nickname,total_orders,hit_rate,total_profit,roi,expert_score
            FROM user_statistics
            {top_where}
            ORDER BY expert_score DESC
            LIMIT 10
            """,
            top_params,
        )
        top_users = cursor.fetchall()
        for item in top_users:
            item["platform_name"] = PLATFORM_MAP.get(int(item.get("platform_id") or 0),"未知平台")
            for key in ("hit_rate","total_profit","roi","expert_score"):
                item[key] = float(item.get(key) or 0)

        recent_where = "WHERE platform_id=%s" if platform_id > 0 else ""
        recent_params = (platform_id,) if platform_id > 0 else ()
        cursor.execute(
            f"""
            SELECT id,platform_id,nickname,match_name,pass_summary,selection,stake,result,profit,
                   COALESCE(publish_time,created_time) AS order_time
            FROM orders
            {recent_where}
            ORDER BY id DESC
            LIMIT 10
            """,
            recent_params,
        )
        recent_orders = cursor.fetchall()
        for item in recent_orders:
            item["platform_name"] = PLATFORM_MAP.get(int(item.get("platform_id") or 0),"未知平台")
            item["stake"] = float(item.get("stake") or 0)
            item["profit"] = float(item.get("profit") or 0)

        return {"code":200,"data":{"summary":summary,"platforms":platforms,"top_users":top_users,"recent_orders":recent_orders}}
    except Exception as e:
        return {"code":500,"msg":str(e),"data":{}}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
