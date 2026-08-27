from collections import defaultdict
from datetime import datetime, timedelta
import json
import math
import re

import pymysql
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from database.mysql import get_conn
from api.settlement import check_play
from api.portal import (
    format_match_row,
    load_aliases,
    load_hongrui_match_references,
    load_order_matches,
)
from common.pass_utils import normalize_pass_summary
from common.platform_registry import default_platform_metadata


router = APIRouter(
    prefix="/api/hub",
    tags=["hub"]
)


PLATFORMS = default_platform_metadata()

MARKETS = ["胜平负", "让球胜平负", "半全场", "比分"]


def platform_name(pid):
    return PLATFORMS.get(int(pid or 0), {}).get("name", f"平台{pid}")


def money(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def intv(value):
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def split_options(selection):
    text = str(selection or "")
    for sep in ("，", ",", "|", "、"):
        text = text.replace(sep, "/")
    return [x.strip() for x in text.split("/") if x.strip()]


def event_day_sql(alias="o"):
    return f"DATE(DATE_SUB(COALESCE({alias}.publish_time,{alias}.created_time), INTERVAL 6 HOUR))"


def current_event_day(cursor):
    cursor.execute("SELECT DATE(DATE_SUB(NOW(), INTERVAL 6 HOUR)) AS d")
    row = cursor.fetchone()
    return str(row["d"])


def percentile_map(rows, key, group_key="platform_id"):
    result = {}
    groups = defaultdict(list)
    for row in rows:
        groups[row[group_key]].append(row)
    for group, items in groups.items():
        ordered = sorted(items, key=lambda x: money(x.get(key)))
        n = len(ordered)
        for idx, item in enumerate(ordered):
            if n <= 1:
                score = 50.0
            else:
                score = idx / (n - 1) * 100.0
            result[(group, item["user_id"])] = score
    return result


def user_grade_rows(cursor, only_active=True):
    # 近7个赛事日，按06:00切日
    cursor.execute(
        f"""
        SELECT
            o.platform_id,
            o.user_id,
            MAX(o.nickname) AS nickname,
            COUNT(*) AS orders7d,
            IFNULL(SUM(o.stake),0) AS self_buy7d,
            IFNULL(SUM(o.follow_num),0) AS followers7d,
            SUM(CASE WHEN o.result!='待开奖' THEN 1 ELSE 0 END) AS settled7d,
            SUM(CASE WHEN o.result='赢' THEN 1 ELSE 0 END) AS wins7d,
            IFNULL(SUM(CASE WHEN o.result!='待开奖' THEN o.stake ELSE 0 END),0) AS settled_stake7d,
            IFNULL(SUM(CASE WHEN o.result!='待开奖' THEN o.profit ELSE 0 END),0) AS profit7d,
            IFNULL(SUM(CASE WHEN o.platform_bonus>0 THEN o.platform_bonus ELSE 0 END),0) AS award7d
        FROM orders o
        WHERE
            o.user_id IS NOT NULL
            AND o.user_id<>0
            AND {event_day_sql('o')} >= DATE_SUB(DATE(DATE_SUB(NOW(), INTERVAL 6 HOUR)), INTERVAL 6 DAY)
            AND {event_day_sql('o')} <= DATE(DATE_SUB(NOW(), INTERVAL 6 HOUR))
        GROUP BY o.platform_id,o.user_id
        """
    )
    rows = cursor.fetchall()

    if not rows:
        return []

    # 累计奖金 + 现有综合分当作平台等级的弱代理
    cursor.execute(
        """
        SELECT
            o.platform_id,
            o.user_id,
            IFNULL(SUM(o.platform_bonus),0) AS total_prize,
            IFNULL(MAX(us.expert_score),0) AS platform_level
        FROM orders o
        LEFT JOIN user_statistics us
            ON us.platform_id=o.platform_id AND us.user_id=o.user_id
        WHERE o.user_id IS NOT NULL AND o.user_id<>0
        GROUP BY o.platform_id,o.user_id
        """
    )
    lifetime = {(r["platform_id"], r["user_id"]): r for r in cursor.fetchall()}

    # 最近5个已开奖结果
    for row in rows:
        key = (row["platform_id"], row["user_id"])
        life = lifetime.get(key, {})
        row["total_prize"] = money(life.get("total_prize"))
        row["platform_level"] = money(life.get("platform_level"))
        cursor.execute(
            """
            SELECT result
            FROM orders
            WHERE platform_id=%s AND user_id=%s AND result IN ('赢','输')
            ORDER BY id DESC
            LIMIT 5
            """,
            key
        )
        last5 = [r["result"] for r in cursor.fetchall()]
        row["last5"] = last5
        row["last5_wins"] = sum(1 for r in last5 if r == "赢")
        row["last5_rate"] = (row["last5_wins"] / len(last5)) if last5 else None

        settled = intv(row.get("settled7d"))
        wins = intv(row.get("wins7d"))
        settled_stake = money(row.get("settled_stake7d"))
        profit = money(row.get("profit7d"))
        row["roi7d"] = profit / settled_stake if settled_stake > 0 else None
        row["hit_rate7d"] = wins / settled if settled > 0 else None

    # 平台内分位：等级、自购、跟单、发单、累计奖金
    level_scores = percentile_map(rows, "platform_level")
    buy_scores = percentile_map(rows, "self_buy7d")
    follower_scores = percentile_map(rows, "followers7d")
    order_scores = percentile_map(rows, "orders7d")
    prize_scores = percentile_map(rows, "total_prize")

    cursor.execute("SELECT platform_id,user_id,grade FROM user_grade_overrides")
    manual = {(r["platform_id"],r["user_id"]): r["grade"] for r in cursor.fetchall()}

    result = []
    for row in rows:
        key = (row["platform_id"], row["user_id"])
        settled = intv(row.get("settled7d"))
        reliability = min(1.0, settled / 5.0)
        roi = row.get("roi7d")
        if roi is None:
            profit_score = 35.0
        else:
            raw = max(0.0, min(100.0, 50.0 + roi * 50.0))
            profit_score = 50.0 + (raw - 50.0) * reliability
        hit_score = ((intv(row.get("wins7d")) + 1) / (settled + 2)) * 100 if settled else 35.0
        last5_rate = row.get("last5_rate")
        if last5_rate is None:
            last5_score = 35.0
        else:
            raw_last5 = last5_rate * 100.0
            last5_score = 50.0 + (raw_last5 - 50.0) * min(1.0, len(row["last5"]) / 5.0)
        score = min(100, round(
            level_scores.get(key,50) * .04
            + buy_scores.get(key,50) * .30
            + follower_scores.get(key,50) * .25
            + order_scores.get(key,50) * .03
            + prize_scores.get(key,50) * .20
            + profit_score * .05
            + hit_score * .10
            + last5_score * .05
        ))
        auto_grade = (
            "S" if score >= 80 and intv(row.get("orders7d")) >= 5 and settled >= 5
            and money(row.get("profit7d")) > 0 and (row.get("hit_rate7d") or 0) >= .30
            and len(row["last5"]) >= 5 and (row.get("last5_rate") or 0) >= .30
            else "A" if score >= 60 and intv(row.get("orders7d")) >= 3 and settled >= 3
            and (row.get("roi7d") if row.get("roi7d") is not None else -1) >= 0
            else "B"
        )
        grade = manual.get(key) or auto_grade
        result.append({
            "platform_id": row["platform_id"],
            "platform_name": platform_name(row["platform_id"]),
            "user_id": row["user_id"],
            "nickname": row.get("nickname") or "未知发单人",
            "grade": grade,
            "auto_grade": auto_grade,
            "manual_grade": manual.get(key) or "",
            "score": score,
            "self_buy7d": money(row.get("self_buy7d")),
            "followers7d": intv(row.get("followers7d")),
            "orders7d": intv(row.get("orders7d")),
            "total_prize": money(row.get("total_prize")),
            "profit7d": money(row.get("profit7d")),
            "settled7d": settled,
            "wins7d": intv(row.get("wins7d")),
            "hit_rate7d": None if row.get("hit_rate7d") is None else round(row["hit_rate7d"]*100,2),
            "roi7d": None if row.get("roi7d") is None else round(row["roi7d"]*100,2),
            "last5": row["last5"],
            "last5_wins": row["last5_wins"],
            "last5_rate": None if row.get("last5_rate") is None else round(row["last5_rate"]*100,2),
        })
    result.sort(key=lambda x: ({"S":0,"A":1,"B":2}[x["grade"]], -x["score"], -x["profit7d"]))
    return result


class GradePayload(BaseModel):
    grade: str = ""


class PlatformImportPayload(BaseModel):
    records: list = []


def require_admin_token(x_admin_token: str = ""):
    import os
    expected = os.getenv("FOOTBALL_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="后台管理Token未配置")
    if x_admin_token != expected:
        raise HTTPException(status_code=401, detail="无权限")


def build_hot_plays(cursor, platform_id, day):
    cursor.execute(
        f"""
        SELECT om.match_name,om.match_code,om.play_type,om.selection,o.stake
        FROM order_matches om
        JOIN orders o ON o.id=om.order_id
        WHERE o.platform_id=%s AND {event_day_sql('o')}=%s AND o.result='待开奖'
        """,
        (platform_id,day)
    )
    agg=defaultdict(lambda:{"count":0,"amount":0.0})
    for r in cursor.fetchall():
        for opt in split_options(r.get("selection")):
            key=(r.get("play_type") or "其他", r.get("match_name") or "未知比赛", r.get("match_code") or "", opt)
            agg[key]["count"] += 1
            agg[key]["amount"] += money(r.get("stake"))
    rows=[]
    for (pt,match_name,match_code,opt),v in agg.items():
        rows.append({"play_type":pt,"match_name":match_name,"match_code":match_code,"option":opt,"count":v["count"],"amount":round(v["amount"],2)})
    rows.sort(key=lambda x:(-x["count"],-x["amount"]))
    return rows


@router.get("/platform-sites")
def platform_sites():
    return {"code": 200, "data": [{"id":k, **v} for k,v in PLATFORMS.items()]}


@router.get("/summary")
def summary():
    conn = get_conn()
    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )

    try:
        day = current_event_day(
            cursor
        )

        cursor.execute(
            f"""
            SELECT
                SUM(
                    CASE
                        WHEN {event_day_sql('o')}=DATE_SUB(%s,INTERVAL 1 DAY)
                        THEN 1 ELSE 0
                    END
                ) AS yesterday_plans,

                SUM(
                    CASE
                        WHEN {event_day_sql('o')}=DATE_SUB(%s,INTERVAL 1 DAY)
                        AND o.result='赢'
                        THEN 1 ELSE 0
                    END
                ) AS won_plans,

                SUM(
                    CASE
                        WHEN {event_day_sql('o')}=%s
                        THEN 1 ELSE 0
                    END
                ) AS today_plans,

                IFNULL(
                    SUM(
                        CASE
                            WHEN {event_day_sql('o')}=%s
                            THEN o.follow_num ELSE 0
                        END
                    ),
                    0
                ) AS today_followers,

                IFNULL(
                    SUM(
                        CASE
                            WHEN {event_day_sql('o')}=%s
                            THEN o.stake ELSE 0
                        END
                    ),
                    0
                ) AS today_amount,

                SUM(
                    CASE
                        WHEN {event_day_sql('o')}=DATE_SUB(%s,INTERVAL 1 DAY)
                        AND o.result!='待开奖'
                        THEN 1 ELSE 0
                    END
                ) AS yesterday_settled,

                SUM(
                    CASE
                        WHEN {event_day_sql('o')}=DATE_SUB(%s,INTERVAL 1 DAY)
                        AND o.result='输'
                        THEN 1 ELSE 0
                    END
                ) AS lost_plans

            FROM orders o
            """,
            (
                day,
                day,
                day,
                day,
                day,
                day,
                day
            )
        )

        metric = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT
                platform_id,
                COUNT(*) AS order_count,
                MAX(
                    COALESCE(
                        publish_time,
                        created_time
                    )
                ) AS last_order_time

            FROM orders

            GROUP BY platform_id
            """
        )

        pstats = {
            int(r["platform_id"]): r
            for r in cursor.fetchall()
        }

        platforms = []

        for pid, platform in PLATFORMS.items():
            stat = pstats.get(
                pid,
                {}
            )

            platforms.append({
                "id": pid,
                "name": platform["name"],
                "short": platform["short"],
                "site": platform["site"],
                "order_count": intv(
                    stat.get(
                        "order_count"
                    )
                ),
                "last_order_time": stat.get(
                    "last_order_time"
                ),
                "online": bool(
                    stat.get(
                        "last_order_time"
                    )
                )
            })

        trend = []

        for offset in range(
            6,
            -1,
            -1
        ):
            cursor.execute(
                f"""
                SELECT COUNT(*) AS c

                FROM orders o

                WHERE
                    {event_day_sql('o')}
                    = DATE_SUB(%s,INTERVAL %s DAY)
                """,
                (
                    day,
                    offset
                )
            )

            date_value = (
                datetime.strptime(
                    day,
                    "%Y-%m-%d"
                )
                -
                timedelta(
                    days=offset
                )
            )

            trend.append({
                "date": date_value.strftime(
                    "%Y-%m-%d"
                ),
                "count": intv(
                    cursor.fetchone()["c"]
                )
            })

        cursor.execute(
            f"""
            SELECT
                om.match_name,
                om.match_code,
                om.play_type,
                om.selection,
                o.stake

            FROM order_matches om

            JOIN orders o
                ON o.id=om.order_id

            WHERE
                {event_day_sql('o')}=%s
                AND o.result='待开奖'
                AND om.play_type IN
                ('胜平负','让球胜平负','半全场','比分')
            """,
            (
                day,
            )
        )

        hot = defaultdict(
            lambda: {
                "count": 0,
                "amount": 0.0
            }
        )

        for row in cursor.fetchall():
            for option in split_options(
                row.get(
                    "selection"
                )
            ):
                key = (
                    row.get(
                        "play_type"
                    )
                    or "其他",
                    row.get(
                        "match_name"
                    )
                    or "未知比赛",
                    row.get(
                        "match_code"
                    )
                    or "",
                    option
                )

                hot[key]["count"] += 1
                hot[key]["amount"] += money(
                    row.get(
                        "stake"
                    )
                )

        grouped_hot = defaultdict(
            list
        )

        for (
            play_type,
            match_name,
            match_code,
            option
        ), values in hot.items():
            grouped_hot[play_type].append({
                "play_type": play_type,
                "match_name": match_name,
                "match_code": match_code,
                "option": option,
                "count": values["count"],
                "amount": round(
                    values["amount"],
                    2
                )
            })

        hot_rows = []

        for market in MARKETS:
            rows = grouped_hot.get(
                market,
                []
            )

            rows.sort(
                key=lambda item: (
                    -item["count"],
                    -item["amount"]
                )
            )

            hot_rows.extend(
                rows[:3]
            )

        return {
            "code": 200,
            "data": {
                "day": day,
                "metrics": {
                    "yesterday_plans": intv(
                        metric.get(
                            "yesterday_plans"
                        )
                    ),
                    "won_plans": intv(
                        metric.get(
                            "won_plans"
                        )
                    ),
                    "today_plans": intv(
                        metric.get(
                            "today_plans"
                        )
                    ),
                    "today_followers": intv(
                        metric.get(
                            "today_followers"
                        )
                    ),
                    "today_amount": money(
                        metric.get(
                            "today_amount"
                        )
                    ),
                    "yesterday_settled": intv(
                        metric.get(
                            "yesterday_settled"
                        )
                    ),
                    "lost_plans": intv(
                        metric.get(
                            "lost_plans"
                        )
                    )
                },
                "platforms": platforms,
                "trend": trend,
                "hot_plays": hot_rows
            }
        }

    finally:
        cursor.close()
        conn.close()


@router.get("/platform/{platform_id}")
def platform_dashboard(
    platform_id: int
):
    conn = get_conn()
    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )

    try:
        day = current_event_day(
            cursor
        )

        cursor.execute(
            f"""
            SELECT
                SUM(
                    CASE
                        WHEN {event_day_sql('o')}=DATE_SUB(%s,INTERVAL 1 DAY)
                        THEN 1 ELSE 0
                    END
                ) AS yesterday_plans,

                SUM(
                    CASE
                        WHEN {event_day_sql('o')}=DATE_SUB(%s,INTERVAL 1 DAY)
                        AND o.result='赢'
                        THEN 1 ELSE 0
                    END
                ) AS yesterday_wins,

                SUM(
                    CASE
                        WHEN {event_day_sql('o')}=DATE_SUB(%s,INTERVAL 1 DAY)
                        AND o.result='输'
                        THEN 1 ELSE 0
                    END
                ) AS yesterday_lost,

                SUM(
                    CASE
                        WHEN {event_day_sql('o')}=DATE_SUB(%s,INTERVAL 1 DAY)
                        AND o.result!='待开奖'
                        THEN 1 ELSE 0
                    END
                ) AS yesterday_settled,

                SUM(
                    CASE
                        WHEN {event_day_sql('o')}=%s
                        THEN 1 ELSE 0
                    END
                ) AS today_plans,

                IFNULL(
                    SUM(
                        CASE
                            WHEN {event_day_sql('o')}=%s
                            THEN o.follow_num ELSE 0
                        END
                    ),
                    0
                ) AS today_followers,

                IFNULL(
                    SUM(o.stake),
                    0
                ) AS total_amount

            FROM orders o

            WHERE o.platform_id=%s
            """,
            (
                day,
                day,
                day,
                day,
                day,
                day,
                platform_id
            )
        )

        metrics = cursor.fetchone() or {}

        for key in (
            "yesterday_plans",
            "yesterday_wins",
            "yesterday_lost",
            "yesterday_settled",
            "today_plans",
            "today_followers"
        ):
            metrics[key] = intv(
                metrics.get(
                    key
                )
            )

        metrics["total_amount"] = money(
            metrics.get(
                "total_amount"
            )
        )

        trend = []

        for offset in range(
            6,
            -1,
            -1
        ):
            cursor.execute(
                f"""
                SELECT COUNT(*) AS c

                FROM orders o

                WHERE
                    o.platform_id=%s
                    AND {event_day_sql('o')}
                        =DATE_SUB(%s,INTERVAL %s DAY)
                """,
                (
                    platform_id,
                    day,
                    offset
                )
            )

            date_value = (
                datetime.strptime(
                    day,
                    "%Y-%m-%d"
                )
                -
                timedelta(
                    days=offset
                )
            )

            trend.append({
                "date": date_value.strftime(
                    "%m-%d"
                ),
                "count": intv(
                    cursor.fetchone()["c"]
                )
            })

        hot_rows = build_hot_plays(
            cursor,
            platform_id,
            day
        )

        fixed_hot = []

        for market in MARKETS:
            market_rows = [
                row
                for row in hot_rows
                if row.get(
                    "play_type"
                ) == market
            ]

            fixed_hot.extend(
                market_rows[:3]
            )

        cursor.execute(
            """
            SELECT
                id,
                nickname,
                match_name,
                pass_summary,
                selection,
                odds_text,
                stake,
                result,
                profit,
                follow_num,
                COALESCE(
                    publish_time,
                    created_time
                ) AS order_time

            FROM orders

            WHERE platform_id=%s

            ORDER BY id DESC

            LIMIT 30
            """,
            (
                platform_id,
            )
        )

        recent = cursor.fetchall()

        for row in recent:
            row["stake"] = money(
                row.get(
                    "stake"
                )
            )

            row["profit"] = money(
                row.get(
                    "profit"
                )
            )

            row["follow_num"] = intv(
                row.get(
                    "follow_num"
                )
            )

        cursor.execute(
            """
            SELECT
                enabled,
                spider_enabled,
                result_enabled,
                settlement_enabled,
                updated_time

            FROM platform_config

            WHERE platform_id=%s

            LIMIT 1
            """,
            (
                platform_id,
            )
        )

        collection = cursor.fetchone() or {
            "enabled": 1,
            "spider_enabled": 1,
            "result_enabled": 1,
            "settlement_enabled": 1
        }

        return {
            "code": 200,
            "data": {
                "day": day,
                "platform_id": platform_id,
                "platform_name": platform_name(
                    platform_id
                ),
                "metrics": metrics,
                "trend": trend,
                "hot_plays": fixed_hot,
                "recent": recent,
                "collection": collection
            }
        }

    finally:
        cursor.close()
        conn.close()


@router.get("/schemes")
def schemes(platform_id:int=0, mode:str="duplicates", keyword:str="", page:int=1, page_size:int=30):
    conn=get_conn(); cursor=conn.cursor(pymysql.cursors.DictCursor)
    try:
        page=max(1,page); page_size=max(10,min(100,page_size)); keyword=str(keyword or "").strip()
        where=["1=1"]; params=[]
        if platform_id>0: where.append("o.platform_id=%s"); params.append(platform_id)
        if keyword:
            like=f"%{keyword}%"; where.append("(o.nickname LIKE %s OR o.match_name LIKE %s OR o.selection LIKE %s OR o.platform_order_id LIKE %s)"); params += [like,like,like,like]
        ws=" AND ".join(where)
        if mode=="duplicates":
            cursor.execute(f"""
                SELECT
                  MAX(o.id) AS id,
                  o.platform_id,
                  MAX(o.nickname) AS nickname,
                  MAX(o.pass_summary) AS pass_summary,
                  o.selection,
                  COUNT(*) AS duplicate_count,
                  COUNT(DISTINCT o.user_id) AS user_count,
                  IFNULL(SUM(o.stake),0) AS total_stake,
                  IFNULL(SUM(o.follow_num),0) AS total_follow,
                  MAX(COALESCE(o.publish_time,o.created_time)) AS latest_time
                FROM orders o
                WHERE {ws}
                GROUP BY o.platform_id,o.selection
                HAVING COUNT(*)>=2
                ORDER BY duplicate_count DESC,total_stake DESC
                LIMIT %s OFFSET %s
            """, tuple(params+[page_size,(page-1)*page_size]))
            data=cursor.fetchall()
            for r in data:
                r["platform_name"]=platform_name(r["platform_id"]); r["total_stake"]=money(r["total_stake"]); r["total_follow"]=intv(r["total_follow"])
            cursor.execute(f"SELECT COUNT(*) AS c FROM (SELECT 1 FROM orders o WHERE {ws} GROUP BY o.platform_id,o.selection HAVING COUNT(*)>=2) t",tuple(params))
            total=intv(cursor.fetchone()["c"])
        else:
            cursor.execute(f"SELECT COUNT(*) AS c FROM orders o WHERE {ws}",tuple(params)); total=intv(cursor.fetchone()["c"])
            cursor.execute(f"""
                SELECT id,platform_id,platform_order_id,user_id,nickname,match_name,pass_summary,selection,odds_text,stake,follow_num,result,profit,COALESCE(publish_time,created_time) AS order_time
                FROM orders o WHERE {ws} ORDER BY o.id DESC LIMIT %s OFFSET %s
            """,tuple(params+[page_size,(page-1)*page_size]))
            data=cursor.fetchall()
            for r in data:
                r["platform_name"]=platform_name(r["platform_id"]); r["stake"]=money(r["stake"]); r["profit"]=money(r["profit"]); r["follow_num"]=intv(r["follow_num"])
        return {"code":200,"mode":mode,"page":page,"page_size":page_size,"total":total,"pages":math.ceil(total/page_size) if total else 1,"data":data}
    finally:
        cursor.close(); conn.close()


@router.get("/heatmap")
def heatmap(platform_id:int=0, date:str="", play_type:str="胜平负"):
    conn=get_conn(); cursor=conn.cursor(pymysql.cursors.DictCursor)
    try:
        if not date: date=current_event_day(cursor)
        where=[f"{event_day_sql('o')}=%s", "o.result='待开奖'"]
        params=[date]
        if platform_id>0: where.append("o.platform_id=%s"); params.append(platform_id)
        cursor.execute(f"""
            SELECT o.platform_id,o.user_id,o.stake,om.match_code,om.match_name,om.league,om.play_type,om.selection
            FROM order_matches om JOIN orders o ON o.id=om.order_id
            WHERE {' AND '.join(where)}
        """,tuple(params))
        rows=cursor.fetchall()

        market_agg=defaultdict(lambda:{"orders":0,"amount":0.0,"users":set()})
        matrix=defaultdict(lambda:defaultdict(lambda:{"orders":0,"amount":0.0,"users":set()}))
        match_meta={}
        for r in rows:
            pt=r.get("play_type") or "其他"
            for opt in split_options(r.get("selection")):
                key=(pt,opt)
                market_agg[key]["orders"]+=1
                market_agg[key]["amount"]+=money(r.get("stake"))
                market_agg[key]["users"].add(f"{r['platform_id']}:{r['user_id']}")
                mk=r.get("match_name") or "未知比赛"
                matrix[mk][(pt,opt)]["orders"]+=1
                matrix[mk][(pt,opt)]["amount"]+=money(r.get("stake"))
                matrix[mk][(pt,opt)]["users"].add(f"{r['platform_id']}:{r['user_id']}")
                match_meta[mk]={"match_code":r.get("match_code") or "","league":r.get("league") or "竞彩足球"}

        markets=defaultdict(list)
        for (pt,opt),v in market_agg.items():
            markets[pt].append({"option":opt,"orders":v["orders"],"amount":round(v["amount"],2),"users":len(v["users"])})
        market_rows=[]
        for pt,opts in markets.items():
            opts.sort(key=lambda x:(-x["orders"],-x["amount"]))
            market_rows.append({"play_type":pt,"options":opts})
        market_rows.sort(key=lambda x:-sum(o["orders"] for o in x["options"]))

        selected=play_type if play_type else "胜平负"
        option_names=sorted({opt for mk in matrix.values() for (pt,opt) in mk.keys() if pt==selected})
        match_rows=[]
        for match_name,cells in matrix.items():
            values=[]; total=0
            for opt in option_names:
                cell=cells.get((selected,opt),{"orders":0,"amount":0.0,"users":set()})
                total += intv(cell.get("orders"))
                values.append({"option":opt,"orders":intv(cell.get("orders")),"amount":round(money(cell.get("amount")),2),"users":len(cell.get("users") or [])})
            if total:
                meta=match_meta.get(match_name,{})
                match_rows.append({"match_name":match_name,"match_code":meta.get("match_code") or "","league":meta.get("league") or "竞彩足球","total_orders":total,"cells":values})
        match_rows.sort(key=lambda x:-x["total_orders"])

        return {"code":200,"data":{
            "date":date,
            "markets":market_rows,
            "selected_play":selected,
            "options":option_names,
            "matrix":match_rows[:30]
        }}
    finally:
        cursor.close(); conn.close()


@router.get("/users")
def users(grade:str="ALL", platform_id:int=0, keyword:str="", sort:str="self_buy7d", direction:str="desc", limit:int=500):
    conn=get_conn(); cursor=conn.cursor(pymysql.cursors.DictCursor)
    try:
        rows=user_grade_rows(cursor)
        keyword=str(keyword or "").strip().lower()
        if grade in ("S","A","B"): rows=[r for r in rows if r["grade"]==grade]
        if platform_id>0: rows=[r for r in rows if r["platform_id"]==platform_id]
        if keyword: rows=[r for r in rows if keyword in f"{r['nickname']} {r['user_id']} {r['platform_name']}".lower()]
        allowed={"score","self_buy7d","followers7d","orders7d","total_prize","profit7d","hit_rate7d","last5_rate"}
        key=sort if sort in allowed else "self_buy7d"
        reverse=direction!="asc"
        rows.sort(key=lambda r: (-1e18 if r.get(key) is None else r.get(key)), reverse=reverse)
        counts={g:sum(1 for r in user_grade_rows(cursor) if r["grade"]==g) for g in ("S","A","B")}
        return {"code":200,"data":{"counts":counts,"total":sum(counts.values()),"rows":rows[:max(1,min(limit,1000))]}}
    finally:
        cursor.close(); conn.close()


@router.put("/users/{platform_id}/{user_id}/grade")
def set_grade(platform_id:int,user_id:int,payload:GradePayload):
    grade=str(payload.grade or "").upper().strip()
    if grade not in ("","S","A","B"):
        return {"code":400,"msg":"grade必须为S/A/B或空"}
    conn=get_conn(); cursor=conn.cursor(pymysql.cursors.DictCursor)
    try:
        if grade:
            cursor.execute("""
                INSERT INTO user_grade_overrides(platform_id,user_id,grade,updated_time)
                VALUES(%s,%s,%s,NOW())
                ON DUPLICATE KEY UPDATE grade=VALUES(grade),updated_time=NOW()
            """,(platform_id,user_id,grade))
        else:
            cursor.execute("DELETE FROM user_grade_overrides WHERE platform_id=%s AND user_id=%s",(platform_id,user_id))
        conn.commit(); return {"code":200,"message":"保存成功"}
    finally:
        cursor.close(); conn.close()


def parse_option_detail(value):
    if not value: return {}
    try:
        arr=json.loads(value)
        if isinstance(arr,list): return {str(x.get("name")):x.get("odds") for x in arr if isinstance(x,dict)}
    except Exception: pass
    return {}


@router.get("/analysis")
def analysis(date:str="", grade:str="ALL", mode:str="consensus", platform_id:int=0):
    conn=get_conn(); cursor=conn.cursor(pymysql.cursors.DictCursor)
    try:
        if not date: date=current_event_day(cursor)
        grade_rows=user_grade_rows(cursor)
        grade_map={(r["platform_id"],r["user_id"]):r for r in grade_rows}
        where=[f"{event_day_sql('o')}=%s", "om.play_type IN ('胜平负','让球胜平负','半全场','比分')"]
        params=[date]
        if platform_id>0: where.append("o.platform_id=%s"); params.append(platform_id)
        if mode=="people": where.append("o.result='待开奖'")
        cursor.execute(f"""
            SELECT
              om.id,om.match_code,om.match_name,om.league,om.play_type,om.selection,om.option_detail,om.handicap,
              o.id AS order_id,o.platform_id,o.user_id,o.nickname,o.stake,o.result AS order_result,
              mr.home_score,mr.away_score,mr.half_home_score,mr.half_away_score,mr.status AS match_status
            FROM order_matches om
            JOIN orders o ON o.id=om.order_id
            LEFT JOIN match_results mr ON mr.match_name=om.match_name
            WHERE {' AND '.join(where)}
            ORDER BY om.match_name,om.play_type,om.id
        """,tuple(params))
        raw=cursor.fetchall()
        events={}
        for r in raw:
            user=grade_map.get((r["platform_id"],r["user_id"]),{"grade":"B","score":0,"nickname":r.get("nickname")})
            g=user["grade"]
            if grade in ("S","A","B") and g!=grade: continue
            if mode=="consensus" and g=="B": continue
            ev=events.setdefault(r["match_name"],{
                "match_name":r["match_name"],"match_code":r.get("match_code") or "","league":r.get("league") or "竞彩足球","handicap":r.get("handicap") if r.get("play_type")=="让球胜平负" else None,
                "score":None,"half_score":None,"platforms":set(),"markets":{m:{} for m in MARKETS}
            })
            ev["platforms"].add(platform_name(r["platform_id"]))
            if r.get("match_status")=="已结束" and r.get("home_score") is not None and r.get("away_score") is not None:
                ev["score"]=f"{r['home_score']}:{r['away_score']}"
                if r.get("half_home_score") is not None and r.get("half_away_score") is not None: ev["half_score"]=f"{r['half_home_score']}:{r['half_away_score']}"
            odds_map=parse_option_detail(r.get("option_detail"))
            for opt in split_options(r.get("selection")):
                market=ev["markets"].setdefault(r["play_type"],{})
                item=market.setdefault(opt,{"label":opt,"users":{},"odds":odds_map.get(opt),"hit":None})
                ukey=f"{r['platform_id']}:{r['user_id']}"
                if ukey not in item["users"]:
                    amount=money(r.get("stake")); reliability=max(.6,money(user.get("score"))/100)
                    value = 1.0 if mode=="people" else amount if mode=="amount" else reliability*amount
                    item["users"][ukey]={"grade":g,"amount":amount,"value":value,"name":r.get("nickname") or str(r.get("user_id"))}
                if r.get("match_status")=="已结束" and r.get("home_score") is not None and r.get("away_score") is not None:
                    item["hit"]=bool(check_play(r["play_type"],opt,intv(r["home_score"]),intv(r["away_score"]),intv(r.get("handicap")),r.get("half_home_score"),r.get("half_away_score")))
        out=[]
        for ev in events.values():
            market_rows=[]; top_shares=[]
            for mt in MARKETS:
                opts=[]; market=ev["markets"].get(mt,{})
                total_value=sum(sum(u["value"] for u in x["users"].values()) for x in market.values()) or 1
                for item in market.values():
                    users=list(item["users"].values()); value=sum(u["value"] for u in users); amount=sum(u["amount"] for u in users)
                    grade_values={g:sum(u["value"] for u in users if u["grade"]==g) for g in ("S","A","B")}
                    opts.append({"label":item["label"],"share":round(value/total_value,4),"value":round(value,2),"people":len(users),"amount":round(amount,2),"odds":item["odds"],"hit":item["hit"],"grade_values":grade_values})
                opts.sort(key=lambda x:-x["value"]); market_rows.append({"type":mt,"options":opts[:9]})
                if opts: top_shares.append(opts[0]["share"])
            ev["markets"]=market_rows; ev["platforms"]=sorted(ev["platforms"])
            # top2接近则标记分歧场
            split=False
            for mr in market_rows:
                if len(mr["options"])>=2 and mr["options"][0]["share"]-mr["options"][1]["share"]<.15: split=True; break
            ev["split"]=split; out.append(ev)
        out.sort(key=lambda x:(x["split"],x["match_code"] or x["match_name"]))
        counts={g:sum(1 for r in grade_rows if r["grade"]==g) for g in ("S","A","B")}
        
        sports=defaultdict(int)
        for ev in out:
            sports[ev.get("league") or "竞彩足球"] += 1
        summary={
            "market_count":len(out),
            "consensus_hits":0,
            "covered":sum(1 for ev in out if ev.get("score")),
            "settled":sum(1 for ev in out if ev.get("score"))
        }
        return {"code":200,"data":{"date":date,"mode":mode,"grade":grade,"grade_counts":counts,"events":out,"sports":[{"name":k,"count":v} for k,v in sorted(sports.items())],"summary":summary}}
    finally:
        cursor.close(); conn.close()


@router.get("/ranking")
def ranking(period:str="day", platform_id:int=0):
    conn=get_conn(); cursor=conn.cursor(pymysql.cursors.DictCursor)
    try:
        days={"day":1,"week":7,"month":30}.get(period,1)
        where=[f"{event_day_sql('o')} >= DATE_SUB(DATE(DATE_SUB(NOW(),INTERVAL 6 HOUR)), INTERVAL %s DAY)"]
        params=[days-1]
        if platform_id>0: where.append("o.platform_id=%s"); params.append(platform_id)
        cursor.execute(f"""
            SELECT o.platform_id,o.user_id,MAX(o.nickname) AS nickname,COUNT(*) AS orders,
              SUM(CASE WHEN o.result!='待开奖' THEN 1 ELSE 0 END) AS settled,
              SUM(CASE WHEN o.result='赢' THEN 1 ELSE 0 END) AS wins,
              IFNULL(SUM(o.platform_bonus),0) AS bonus,
              IFNULL(SUM(o.follow_num),0) AS followers,
              IFNULL(SUM(o.profit),0) AS profit
            FROM orders o WHERE {' AND '.join(where)} GROUP BY o.platform_id,o.user_id
        """,tuple(params))
        rows=cursor.fetchall()
        for r in rows:
            r["platform_name"]=platform_name(r["platform_id"]); r["settled"]=intv(r["settled"]); r["wins"]=intv(r["wins"]); r["hit_rate"]=round(r["wins"]/r["settled"]*100,2) if r["settled"] else 0; r["bonus"]=money(r["bonus"]); r["followers"]=intv(r["followers"]); r["profit"]=money(r["profit"])
        return {"code":200,"data":{"period":period,"rows":rows}}
    finally:
        cursor.close(); conn.close()


@router.get("/results")
def hub_results(platform_id:int=0, month:str="", day:str="", keyword:str="", status:str="", page:int=1, page_size:int=100):
    conn=get_conn(); cursor=conn.cursor(pymysql.cursors.DictCursor)
    try:
        page=max(1,page); page_size=max(20,min(200,page_size))
        if not month:
            cursor.execute("SELECT DATE_FORMAT(CURDATE(),'%Y-%m') AS m")
            month=cursor.fetchone()["m"]
        where=[
            f"DATE_FORMAT({event_day_sql('o')},'%Y-%m')=%s",
            "o.platform_id IN (1,2,3,4)",
        ]
        params=[month]
        if platform_id>0:
            where.append("o.platform_id=%s"); params.append(platform_id)
        if day:
            where.append(f"{event_day_sql('o')}=%s"); params.append(day)
        keyword=str(keyword or "").strip()
        if keyword:
            like=f"%{keyword}%"; where.append("(o.nickname LIKE %s OR o.platform_order_id LIKE %s OR o.match_name LIKE %s OR o.selection LIKE %s)"); params.extend([like,like,like,like])
        if status=="won": where.append("o.result='赢'")
        elif status=="pending": where.append("o.result='待开奖'")
        elif status=="lost": where.append("o.result='输'")
        ws=" AND ".join(where)
        cursor.execute(f"SELECT COUNT(*) AS c FROM orders o WHERE {ws}",tuple(params)); total=intv(cursor.fetchone()["c"])
        cursor.execute(f"""
            SELECT o.id,o.platform_id,o.platform_order_id,o.user_id,o.nickname,o.match_name,o.pass_summary,o.pass_composition,o.bet_count,o.selection,o.odds_text,o.stake,o.follow_num,o.result,o.profit,o.platform_bonus,COALESCE(o.publish_time,o.created_time) AS order_time,
                   us.win_orders,us.lose_orders,us.hit_rate,up.avatar_url
            FROM orders o
            LEFT JOIN user_statistics us
              ON us.platform_id=o.platform_id AND us.user_id=o.user_id
            LEFT JOIN user_profiles_ext up
              ON up.platform_id=o.platform_id AND up.user_id=o.user_id
            WHERE {ws} ORDER BY order_time DESC,o.id DESC LIMIT %s OFFSET %s
        """,tuple(params+[page_size,(page-1)*page_size]))
        rows=cursor.fetchall()
        alias_map=load_aliases(cursor)
        hongrui_references=load_hongrui_match_references(cursor,alias_map)
        grouped=load_order_matches(cursor,[intv(row.get("id")) for row in rows])
        for r in rows:
            r["platform_name"]=platform_name(r["platform_id"]); r["stake"]=money(r["stake"]); r["profit"]=money(r["profit"]); r["platform_bonus"]=money(r["platform_bonus"]); r["follow_num"]=intv(r["follow_num"])
            r["pass_summary"]=normalize_pass_summary(r.get("pass_summary")) or r.get("pass_composition") or ""
            r["matches"]=[format_match_row(item,alias_map,r["platform_id"],hongrui_references) for item in grouped.get(intv(r.get("id")),[])]
            if not r.get("odds_text"):
                r["odds_text"]=" / ".join(item["odds"] for item in r["matches"] if item.get("odds"))
            wins=intv(r.get("win_orders")); losses=intv(r.get("lose_orders"))
            r["history_record"]=f"{wins}胜{losses}负" if wins+losses else "--"
        cursor.execute("SELECT DISTINCT DATE_FORMAT("+event_day_sql('o')+",'%Y-%m') AS m FROM orders o WHERE o.platform_id IN (1,2,3,4) AND (%s=0 OR o.platform_id=%s) ORDER BY m DESC LIMIT 24",(platform_id,platform_id))
        months=[x["m"] for x in cursor.fetchall() if x.get("m")]
        summary_where=[f"DATE_FORMAT({event_day_sql('o')},'%Y-%m')=%s","o.platform_id IN (1,2,3,4)"]
        summary_params=[month]
        if platform_id>0:
            summary_where.append("o.platform_id=%s"); summary_params.append(platform_id)
        summary_sql=" AND ".join(summary_where)
        cursor.execute(f"""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN result='赢' THEN 1 ELSE 0 END) AS won,
                   SUM(CASE WHEN result='输' THEN 1 ELSE 0 END) AS lost,
                   SUM(CASE WHEN result='待开奖' THEN 1 ELSE 0 END) AS pending,
                   IFNULL(SUM(stake),0) AS total_stake,
                   IFNULL(SUM(follow_num),0) AS followers,
                   IFNULL(SUM(platform_bonus),0) AS total_bonus
            FROM orders o WHERE {summary_sql}
        """,tuple(summary_params))
        summary=cursor.fetchone() or {}
        summary={"total":intv(summary.get("total")),"won":intv(summary.get("won")),"lost":intv(summary.get("lost")),"pending":intv(summary.get("pending")),"total_stake":money(summary.get("total_stake")),"followers":intv(summary.get("followers")),"total_bonus":money(summary.get("total_bonus"))}
        cursor.execute(f"""
            SELECT {event_day_sql('o')} AS day,COUNT(*) AS count
            FROM orders o WHERE {summary_sql}
            GROUP BY {event_day_sql('o')} ORDER BY day
        """,tuple(summary_params))
        date_counts=[{"day":str(item.get("day")),"count":intv(item.get("count"))} for item in cursor.fetchall() if item.get("day")]
        return {"code":200,"data":{"month":month,"months":months,"rows":rows,"total":total,"page":page,"pages":math.ceil(total/page_size) if total else 1,"summary":summary,"date_counts":date_counts}}
    finally:
        cursor.close(); conn.close()


@router.delete("/results")
def clear_result_archive(
    month: str,
    confirm: str,
    x_admin_token: str = Header(default=""),
):
    require_admin_token(x_admin_token)
    month = str(month or "").strip()
    expected = f"DELETE_RESULTS_{month}"
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(status_code=400, detail="月份格式必须为 YYYY-MM")
    if confirm != expected:
        raise HTTPException(status_code=400, detail="删除确认文本不正确")

    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute(
            f"""
            SELECT id FROM orders o
            WHERE o.platform_id IN (1,2,3,4)
              AND DATE_FORMAT({event_day_sql('o')},'%Y-%m')=%s
            """,
            (month,),
        )
        order_ids = [intv(row.get("id")) for row in cursor.fetchall()]
        deleted_matches = 0
        if order_ids:
            marks = ",".join(["%s"] * len(order_ids))
            cursor.execute(
                f"DELETE FROM settlement_logs WHERE order_id IN ({marks})",
                tuple(order_ids),
            )
            cursor.execute(
                f"DELETE FROM order_matches WHERE order_id IN ({marks})",
                tuple(order_ids),
            )
            deleted_matches = cursor.rowcount
            cursor.execute(
                f"DELETE FROM orders WHERE id IN ({marks})",
                tuple(order_ids),
            )
            deleted_orders = cursor.rowcount
        else:
            deleted_orders = 0
        conn.commit()
        return {
            "code": 200,
            "month": month,
            "deleted_orders": deleted_orders,
            "deleted_matches": deleted_matches,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@router.get("/platform/{platform_id}/export")
def export_platform_records(platform_id:int):
    conn=get_conn(); cursor=conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("SELECT * FROM orders WHERE platform_id=%s ORDER BY id",(platform_id,))
        orders=cursor.fetchall()
        for o in orders:
            cursor.execute("SELECT * FROM order_matches WHERE order_id=%s ORDER BY id",(o["id"],))
            o["matches"]=cursor.fetchall()
        return {"code":200,"platform_id":platform_id,"platform_name":platform_name(platform_id),"exported_at":datetime.now().strftime('%Y-%m-%d %H:%M:%S'),"records":orders}
    finally:
        cursor.close(); conn.close()


@router.put("/platform/{platform_id}/collection")
def set_platform_collection(platform_id:int, enabled:bool=True, x_admin_token:str=Header(default="")):
    require_admin_token(x_admin_token)
    conn=get_conn(); cursor=conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("UPDATE platform_config SET spider_enabled=%s,result_enabled=%s WHERE platform_id=%s",(1 if enabled else 0,1 if enabled else 0,platform_id))
        conn.commit(); return {"code":200,"enabled":bool(enabled)}
    finally:
        cursor.close(); conn.close()


@router.post("/platform/{platform_id}/import")
def import_platform_records(
    platform_id: int,
    payload: PlatformImportPayload,
    x_admin_token: str = Header(
        default=""
    )
):
    require_admin_token(
        x_admin_token
    )

    conn = get_conn()
    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )

    imported = 0
    imported_matches = 0

    try:
        for item in payload.records or []:
            if not isinstance(
                item,
                dict
            ):
                continue

            platform_order_id = str(
                item.get(
                    "platform_order_id"
                )
                or ""
            ).strip()

            if not platform_order_id:
                continue

            cursor.execute(
                """
                SELECT id

                FROM orders

                WHERE
                    platform_id=%s
                    AND platform_order_id=%s

                LIMIT 1
                """,
                (
                    platform_id,
                    platform_order_id
                )
            )

            old = cursor.fetchone()

            values = (
                item.get(
                    "user_id"
                )
                or 0,
                item.get(
                    "nickname"
                )
                or "",
                item.get(
                    "match_name"
                )
                or "",
                item.get(
                    "league"
                )
                or "竞彩足球",
                item.get(
                    "play_type"
                )
                or item.get(
                    "pass_summary"
                )
                or "",
                item.get(
                    "pass_summary"
                )
                or "",
                item.get(
                    "selection"
                )
                or "",
                item.get(
                    "odds_text"
                )
                or "",
                money(
                    item.get(
                        "stake"
                    )
                ),
                item.get(
                    "result"
                )
                or "待开奖",
                money(
                    item.get(
                        "profit"
                    )
                ),
                intv(
                    item.get(
                        "follow_num"
                    )
                )
            )

            if old:
                cursor.execute(
                    """
                    UPDATE orders

                    SET
                        user_id=%s,
                        nickname=%s,
                        match_name=%s,
                        league=%s,
                        play_type=%s,
                        pass_summary=%s,
                        selection=%s,
                        odds_text=%s,
                        stake=%s,
                        result=%s,
                        profit=%s,
                        follow_num=%s

                    WHERE id=%s
                    """,
                    values
                    +
                    (
                        old["id"],
                    )
                )

                order_id = old["id"]

            else:
                cursor.execute(
                    """
                    INSERT INTO orders
                    (
                        platform_id,
                        platform_order_id,
                        user_id,
                        nickname,
                        match_name,
                        league,
                        play_type,
                        pass_summary,
                        selection,
                        odds_text,
                        stake,
                        result,
                        profit,
                        follow_num
                    )
                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        platform_id,
                        platform_order_id
                    )
                    +
                    values
                )

                order_id = cursor.lastrowid

            matches = item.get(
                "matches"
            )

            if isinstance(
                matches,
                list
            ):
                for match in matches:
                    if not isinstance(
                        match,
                        dict
                    ):
                        continue

                    match_name = str(
                        match.get(
                            "match_name"
                        )
                        or ""
                    ).strip()

                    play_type = str(
                        match.get(
                            "play_type"
                        )
                        or ""
                    ).strip()

                    handicap = intv(
                        match.get(
                            "handicap"
                        )
                    )

                    if (
                        not match_name
                        or
                        not play_type
                    ):
                        continue

                    cursor.execute(
                        """
                        SELECT id

                        FROM order_matches

                        WHERE
                            order_id=%s
                            AND match_name=%s
                            AND play_type=%s
                            AND handicap=%s

                        LIMIT 1
                        """,
                        (
                            order_id,
                            match_name,
                            play_type,
                            handicap
                        )
                    )

                    old_match = cursor.fetchone()

                    match_values = (
                        match.get(
                            "match_code"
                        )
                        or "",
                        match_name,
                        match.get(
                            "match_key"
                        )
                        or "",
                        match.get(
                            "league"
                        )
                        or item.get(
                            "league"
                        )
                        or "竞彩足球",
                        play_type,
                        match.get(
                            "selection"
                        )
                        or "",
                        (
                            json.dumps(
                                match.get(
                                    "option_detail"
                                ),
                                ensure_ascii=False
                            )
                            if isinstance(
                                match.get(
                                    "option_detail"
                                ),
                                (
                                    list,
                                    dict
                                )
                            )
                            else match.get(
                                "option_detail"
                            )
                        ),
                        handicap,
                        match.get(
                            "result"
                        )
                        or "待开奖"
                    )

                    if old_match:
                        cursor.execute(
                            """
                            UPDATE order_matches

                            SET
                                match_code=%s,
                                match_name=%s,
                                match_key=%s,
                                league=%s,
                                play_type=%s,
                                selection=%s,
                                option_detail=%s,
                                handicap=%s,
                                result=%s

                            WHERE id=%s
                            """,
                            match_values
                            +
                            (
                                old_match["id"],
                            )
                        )

                    else:
                        cursor.execute(
                            """
                            INSERT INTO order_matches
                            (
                                order_id,
                                match_code,
                                match_name,
                                match_key,
                                league,
                                play_type,
                                selection,
                                option_detail,
                                handicap,
                                result,
                                profit
                            )
                            VALUES
                            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)
                            """,
                            (
                                order_id,
                            )
                            +
                            match_values
                        )

                    imported_matches += 1

            imported += 1

        conn.commit()

        return {
            "code": 200,
            "imported": imported,
            "imported_matches": imported_matches
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


@router.delete("/platform/{platform_id}/records")
def clear_platform_records(platform_id:int,x_admin_token:str=Header(default="")):
    require_admin_token(x_admin_token)
    conn=get_conn(); cursor=conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("SELECT id FROM orders WHERE platform_id=%s",(platform_id,)); ids=[r["id"] for r in cursor.fetchall()]
        if ids:
            marks=','.join(['%s']*len(ids)); cursor.execute(f"DELETE FROM order_matches WHERE order_id IN ({marks})",tuple(ids))
        cursor.execute("DELETE FROM orders WHERE platform_id=%s",(platform_id,)); deleted=cursor.rowcount
        conn.commit(); return {"code":200,"deleted":deleted}
    except Exception:
        conn.rollback(); raise
    finally:
        cursor.close(); conn.close()
