from fastapi import APIRouter
from database.mysql import get_conn
import pymysql

router = APIRouter(prefix="/api/user", tags=["user"])
SORT_MAP = {
    "latest":"last_order_time DESC",
    "orders":"total_orders DESC",
    "hit":"hit_rate DESC, settled_orders DESC",
    "profit":"total_profit DESC",
    "roi":"roi DESC, settled_orders DESC",
    "follow":"follow_num DESC",
    "score":"expert_score DESC",
}


@router.get("/list")
def user_list(platform_id:int=1, keyword:str="", sort:str="latest", page:int=1, page_size:int=20):
    conn = cursor = None
    try:
        page = max(1,page)
        page_size = max(10,min(page_size,100))
        order_by = SORT_MAP.get(sort,SORT_MAP["latest"])
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        where = ["platform_id=%s"]
        params = [platform_id]
        keyword = str(keyword or "").strip()
        if keyword:
            like = f"%{keyword}%"
            where.append("(nickname LIKE %s OR CAST(user_id AS CHAR) LIKE %s)")
            params.extend([like,like])
        where_sql = " AND ".join(where)
        cursor.execute(f"SELECT COUNT(*) AS c FROM user_statistics WHERE {where_sql}",tuple(params))
        total = int(cursor.fetchone()["c"] or 0)
        offset = (page-1)*page_size
        qparams = list(params)+[page_size,offset]
        cursor.execute(
            f"""
            SELECT platform_id,user_id,nickname,total_orders AS order_count,settled_orders,win_orders,lose_orders,
                   pending_orders,hit_rate AS avg_hit_rate,roi AS avg_profitability,follow_num AS avg_follow,
                   expert_score,total_stake AS total_amount,total_profit,follow_num,current_streak,max_win_streak,
                   recent_results,last_order_time
            FROM user_statistics
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
            """,
            tuple(qparams),
        )
        data = cursor.fetchall()
        for item in data:
            item["level"] = "重点" if float(item.get("expert_score") or 0) >= 60 else "普通"
            for key in ("avg_hit_rate","avg_profitability","expert_score","total_amount","total_profit"):
                item[key] = float(item.get(key) or 0)
            item["recent7"] = [x for x in str(item.get("recent_results") or "").split(",") if x]
        pages = (total+page_size-1)//page_size
        return {"code":200,"platform_id":platform_id,"page":page,"page_size":page_size,"total":total,"pages":pages,"data":data}
    except Exception as e:
        return {"code":500,"msg":str(e),"data":[]}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/detail/{platform_id}/{user_id}")
def user_detail(platform_id:int,user_id:int):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM user_statistics WHERE platform_id=%s AND user_id=%s LIMIT 1",(platform_id,user_id))
        user = cursor.fetchone()
        if not user:
            return {"code":404,"msg":"用户不存在","data":None}
        recent7 = [x for x in str(user.get("recent_results") or "").split(",") if x]
        for key in ("hit_rate","total_stake","total_profit","roi","expert_score"):
            user[key] = float(user.get(key) or 0)
        cursor.execute(
            """
            SELECT id,platform_order_id,match_name,league,play_type,pass_summary,selection,odds_text,
                   stake,result,profit,follow_num,publish_time,created_time
            FROM orders
            WHERE platform_id=%s AND user_id=%s
            ORDER BY id DESC
            LIMIT 50
            """,
            (platform_id,user_id),
        )
        orders = cursor.fetchall()
        for item in orders:
            item["stake"] = float(item.get("stake") or 0)
            item["profit"] = float(item.get("profit") or 0)
        stats = {
            "total_orders":int(user.get("total_orders") or 0),
            "settled_orders":int(user.get("settled_orders") or 0),
            "win_orders":int(user.get("win_orders") or 0),
            "lose_orders":int(user.get("lose_orders") or 0),
            "win_rate":float(user.get("hit_rate") or 0),
            "profit":float(user.get("total_profit") or 0),
            "roi":float(user.get("roi") or 0),
        }
        return {"code":200,"data":{"user":user,"statistics":stats,"recent7":recent7,"orders":orders}}
    except Exception as e:
        return {"code":500,"msg":str(e),"data":None}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
