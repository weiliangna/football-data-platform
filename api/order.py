from fastapi import APIRouter
from database.mysql import get_conn
import pymysql
import json

router = APIRouter(prefix="/api/order", tags=["order"])

PASS_MAP = {"500":"单关","502":"2串1","503":"3串1","504":"4串1","505":"5串1","506":"6串1","507":"7串1","MIX":"混合过关"}
PLATFORM_MAP = {1:"彩站云",2:"州运宝",3:"鸿瑞",4:"云彩"}


def get_play_name(play_type, pass_summary=None):
    value = str(pass_summary or play_type or "").strip()
    return PASS_MAP.get(value, value)


def parse_option_detail(value, selection=""):
    if value:
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return [{"name":x.strip(),"odds":None} for x in str(selection or "").split("/") if x.strip()]


@router.get("/list")
def order_list(platform_id:int=0, keyword:str="", result:str="", play_type:str="", page:int=1, page_size:int=20):
    conn = cursor = None
    try:
        page = max(1,page)
        page_size = max(10,min(page_size,100))
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        where = ["1=1"]
        params = []
        if platform_id > 0:
            where.append("o.platform_id=%s")
            params.append(platform_id)
        keyword = str(keyword or "").strip()
        if keyword:
            like = f"%{keyword}%"
            where.append("(o.nickname LIKE %s OR o.match_name LIKE %s OR o.platform_order_id LIKE %s OR CAST(o.user_id AS CHAR) LIKE %s)")
            params.extend([like,like,like,like])
        result = str(result or "").strip()
        if result:
            where.append("o.result=%s")
            params.append(result)
        play_type = str(play_type or "").strip()
        if play_type:
            where.append("(o.play_type=%s OR o.pass_summary=%s)")
            params.extend([play_type,play_type])
        where_sql = " AND ".join(where)

        cursor.execute(f"SELECT COUNT(*) AS c FROM orders o WHERE {where_sql}", tuple(params))
        total = int(cursor.fetchone()["c"] or 0)
        offset = (page-1) * page_size
        query_params = list(params) + [page_size,offset]

        cursor.execute(
            f"""
            SELECT o.id,o.platform_id,p.name AS platform_name,o.platform_order_id,o.user_id,o.nickname,
                   o.match_name,o.league,o.play_type,o.pass_summary,o.selection,o.odds_text,o.stake,o.result,
                   o.profit,o.follow_num,o.handicap,o.lot_multi,o.expected_bonus,o.platform_bonus,
                   o.commission_total,o.settlement_status,o.publish_time,o.created_time
            FROM orders o
            LEFT JOIN platforms p ON p.id=o.platform_id
            WHERE {where_sql}
            ORDER BY o.id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(query_params),
        )
        data = cursor.fetchall()
        for item in data:
            item["platform_name"] = item.get("platform_name") or PLATFORM_MAP.get(int(item.get("platform_id") or 0),"未知平台")
            item["play_name"] = get_play_name(item.get("play_type"), item.get("pass_summary"))
            for key in ("stake","profit","lot_multi","expected_bonus","platform_bonus","commission_total"):
                item[key] = float(item.get(key) or 0)

        pages = (total + page_size - 1) // page_size
        return {"code":200,"page":page,"page_size":page_size,"total":total,"pages":pages,"data":data}
    except Exception as e:
        return {"code":500,"msg":str(e),"data":[]}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/detail/{order_id}")
def order_detail(order_id:int):
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            SELECT o.*,p.name AS platform_name
            FROM orders o
            LEFT JOIN platforms p ON p.id=o.platform_id
            WHERE o.id=%s
            LIMIT 1
            """,
            (order_id,),
        )
        order = cursor.fetchone()
        if not order:
            return {"code":404,"msg":"订单不存在"}
        order["platform_name"] = order.get("platform_name") or PLATFORM_MAP.get(int(order.get("platform_id") or 0),"未知平台")
        order["play_name"] = get_play_name(order.get("play_type"),order.get("pass_summary"))
        for key in ("stake","profit","expected_bonus","platform_bonus","commission_total","lot_multi"):
            order[key] = float(order.get(key) or 0)

        cursor.execute(
            """
            SELECT om.id,om.order_id,om.match_code,om.match_name,om.match_key,om.league,om.play_type,
                   om.selection,om.option_detail,om.handicap,om.result AS bet_result,
                   mr.home_team,mr.away_team,mr.home_score,mr.away_score,mr.half_home_score,mr.half_away_score,
                   mr.status AS match_status,mr.finished_time
            FROM order_matches om
            LEFT JOIN match_results mr
              ON (mr.match_name=om.match_name OR (om.match_key<>'' AND mr.match_key=om.match_key))
            WHERE om.order_id=%s
            ORDER BY om.id ASC
            """,
            (order_id,),
        )
        matches = cursor.fetchall()
        for item in matches:
            item["handicap"] = int(item.get("handicap") or 0)
            item["options"] = parse_option_detail(item.get("option_detail"),item.get("selection"))
            if not item.get("home_team") or not item.get("away_team"):
                parts = str(item.get("match_name") or "").split(":",1)
                if len(parts)==2:
                    item["home_team"] = item.get("home_team") or parts[0]
                    item["away_team"] = item.get("away_team") or parts[1]

        cursor.execute(
            """
            SELECT id,old_result,new_result,reason,home_score,away_score,half_home_score,half_away_score,created_time
            FROM settlement_logs
            WHERE order_id=%s
            ORDER BY id DESC
            LIMIT 100
            """,
            (order_id,),
        )
        logs = cursor.fetchall()
        return {"code":200,"data":{"order":order,"matches":matches,"settlement_logs":logs}}
    except Exception as e:
        return {"code":500,"msg":str(e),"data":{}}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
