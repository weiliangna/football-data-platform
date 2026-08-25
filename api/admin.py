import os

import pymysql
from fastapi import APIRouter, Header, HTTPException

from api.settlement import settle_match_with_connection
from database.mysql import get_conn


router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin_token(
    x_admin_token: str = Header(default=""),
):
    expected = os.getenv(
        "FOOTBALL_ADMIN_TOKEN",
        "",
    ).strip()

    if not expected:
        raise HTTPException(
            status_code=503,
            detail="后台管理Token未配置",
        )

    if x_admin_token != expected:
        raise HTTPException(
            status_code=401,
            detail="无权限",
        )


@router.get("/status")
def system_status():
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            SELECT
                spider_name,platform_id,status,exit_code,
                finished_time,message
            FROM spider_logs
            ORDER BY id DESC
            LIMIT 100
            """
        )
        latest = {}
        for row in cursor.fetchall():
            name = row.get("spider_name")
            if name not in latest:
                latest[name] = row

        counts = {}
        for table in (
            "orders",
            "match_results",
            "user_statistics",
        ):
            cursor.execute(
                f"SELECT COUNT(*) AS c FROM `{table}`"
            )
            counts[table] = int(
                cursor.fetchone()["c"] or 0
            )

        return {
            "code": 200,
            "data": {
                "database": "ok",
                "order_count": counts["orders"],
                "match_count": counts["match_results"],
                "user_count": counts["user_statistics"],
                "jobs": list(latest.values()),
            },
        }
    except Exception as exc:
        return {
            "code": 500,
            "msg": str(exc),
            "data": {},
        }
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.post("/resettle/{match_id}")
def resettle_match(
    match_id: int,
    x_admin_token: str = Header(default=""),
):
    require_admin_token(x_admin_token)
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT * FROM match_results WHERE id=%s LIMIT 1",
            (match_id,),
        )
        match = cursor.fetchone()

        if not match:
            raise HTTPException(
                status_code=404,
                detail="比赛不存在",
            )

        result = settle_match_with_connection(
            conn,
            match.get("match_name"),
            int(match.get("home_score") or 0),
            int(match.get("away_score") or 0),
            (
                int(match.get("half_home_score"))
                if match.get("half_home_score") is not None
                else None
            ),
            (
                int(match.get("half_away_score"))
                if match.get("half_away_score") is not None
                else None
            ),
            platform_id=match.get("platform_id"),
            source_match_code=match.get("match_code"),
            match_date=match.get("match_date"),
            home_team=match.get("home_team"),
            away_team=match.get("away_team"),
        )
        conn.commit()
        return {
            "code": 200,
            "data": result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        return {
            "code": 500,
            "msg": str(exc),
        }
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
