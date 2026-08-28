import asyncio
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Lock
from time import monotonic, perf_counter

import pymysql
from fastapi import APIRouter

from common.match_identity import (
    canonical_match,
    canonical_team,
    load_team_aliases,
    normalize_identity_text,
    supports_identity_v2,
    table_columns,
)
from common.match_utils import parse_match_name
from common.match_utils import match_pair_similarity
from common.bet_aggregation import (
    STANDARD_PLAYS,
    normalize_play_type,
    normalize_selection_combination,
)
from common.pass_utils import normalize_pass_summary
from common.platform_registry import (
    ACTIVE_PLATFORM_IDS,
    default_platform_metadata,
)
from common.user_grading import load_user_grades
from common.user_labels import build_first_order_profile
from database.mysql import get_conn
from common.snapshot_store import attach_meta, load_snapshot, save_snapshot


router = APIRouter(
    prefix="/api/portal",
    tags=["portal-v6"]
)


PLATFORMS = {
    platform_id: item["name"]
    for platform_id, item in default_platform_metadata().items()
}

FOUR_PLAYS = STANDARD_PLAYS

DASHBOARD_CACHE_SECONDS = 60.0
DASHBOARD_STALE_SECONDS = 300.0
# Never make a browser request wait for a full dashboard rebuild.  A persisted
# or in-process snapshot is returned immediately; only a cold start may wait a
# short grace period while the single-flight refresh warms in the background.
DASHBOARD_FIRST_RESPONSE_TIMEOUT = 2.5
_dashboard_executor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="portal-dashboard",
)
_snapshot_executor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="portal-snapshot",
)
_dashboard_cache = {
    "data": None,
    "created_at": 0.0,
}
_dashboard_refresh_task = None
CURRENT_CONTEXT_CACHE_SECONDS = 30.0
_current_context_cache = {
    "data": None,
    "created_at": 0.0,
    "has_profiles": False,
}
_current_context_lock = Lock()


def _empty_dashboard_response(*, freshness="refreshing", refreshing=True,
                              updated_at=None, age_seconds=None):
    """Return a renderable dashboard envelope while a snapshot warms."""

    data = {
        "day": str(datetime.now().date()),
        "server_time": datetime.now(),
        "metrics": {
            "yesterday_plans": 0,
            "yesterday_wins": 0,
            "yesterday_lost": 0,
            "yesterday_settled": 0,
            "today_plans": 0,
            "today_followers": 0,
            "today_amount": 0.0,
            "unexpired_plans": 0,
        },
        "platform_bets": [],
        "sender_ranking": [],
        "hot_plays": [
            {"play_type": play_type, "items": []}
            for play_type in FOUR_PLAYS
        ],
    }
    response_meta = {
        "freshness": freshness,
        "updated_at": updated_at,
        "age_seconds": age_seconds,
        "refreshing": bool(refreshing),
    }
    return {
        "code": 200,
        "data": data,
        "meta": response_meta,
    }


def _build_dashboard_minimal_response():
    """Build a small orders-only dashboard while the full context warms.

    This deliberately avoids order_matches, profile, and settlement joins so
    a cold start can still render useful counters on a busy two-core host.
    The normal single-flight build replaces this payload once complete.
    """

    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT NOW() AS now_time")
        now = cursor.fetchone().get("now_time") or datetime.now()
        target_day = current_event_day(now)
        day_start = datetime.combine(target_day, datetime.min.time()) + timedelta(hours=6)
        day_end = day_start + timedelta(days=1)
        cursor.execute(
            """
            SELECT platform_id,user_id,MAX(nickname) AS nickname,
                   COUNT(*) AS order_count,
                   IFNULL(SUM(stake),0) AS amount,
                   IFNULL(SUM(follow_num),0) AS followers
            FROM orders
            WHERE COALESCE(publish_time,created_time)>=%s
              AND COALESCE(publish_time,created_time)<%s
              AND platform_id IN (1,2,3,4)
            GROUP BY platform_id,user_id
            ORDER BY amount DESC,followers DESC,order_count DESC
            LIMIT 30
            """,
            (day_start, day_end),
        )
        ranking = []
        for row in cursor.fetchall() or []:
            ranking.append({
                "platform_id": intv(row.get("platform_id")),
                "platform_name": PLATFORMS.get(intv(row.get("platform_id")), ""),
                "user_id": intv(row.get("user_id")),
                "nickname": row.get("nickname") or "未知用户",
                "avatar_url": "",
                "amount": round(money(row.get("amount")), 2),
                "followers": intv(row.get("followers")),
                "order_count": intv(row.get("order_count")),
                "orders": [],
                "history_record": "--",
                "history_hit_rate": None,
            })
        return {
            "code": 200,
            "data": {
                "day": str(target_day),
                "server_time": now,
                "metrics": {
                    "yesterday_plans": 0,
                    "yesterday_wins": 0,
                    "yesterday_lost": 0,
                    "yesterday_settled": 0,
                    "today_plans": sum(item["order_count"] for item in ranking),
                    "today_followers": sum(item["followers"] for item in ranking),
                    "today_amount": round(sum(item["amount"] for item in ranking), 2),
                    "unexpired_plans": 0,
                },
                "platform_bets": [],
                "sender_ranking": ranking,
                "hot_plays": [
                    {"play_type": play_type, "items": []}
                    for play_type in FOUR_PLAYS
                ],
            },
            "meta": {
                "freshness": "degraded",
                "updated_at": datetime.now().isoformat(),
                "age_seconds": 0.0,
                "refreshing": True,
            },
        }
    except Exception:
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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


def normalize_text(value):
    return normalize_identity_text(value)

def split_match_name(value):
    parsed = parse_match_name(value)
    return (
        parsed["home_team"] or "",
        parsed["away_team"] or "",
    )


def split_options(value):
    text = str(value or "")
    for sep in ("，", ",", "|", "、"):
        text = text.replace(sep, "/")
    return [
        item.strip()
        for item in text.split("/")
        if item.strip()
    ]


def parse_option_detail(value):
    if isinstance(value, list):
        rows = value
    else:
        try:
            rows = json.loads(str(value or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            rows = []
    if isinstance(rows, dict):
        rows = rows.get("options") or [rows]
    return [item for item in rows if isinstance(item, dict)]


def selection_odds(row):
    details = parse_option_detail(row.get("option_detail"))
    selected = {
        normalize_text(item)
        for item in split_options(row.get("selection"))
    }
    values = []
    for item in details:
        name = normalize_text(
            item.get("name")
            or item.get("selection")
            or item.get("label")
        )
        odds = item.get("odds")
        if odds in (None, ""):
            odds = item.get("sp")
        if odds in (None, ""):
            odds = item.get("value")
        if odds in (None, ""):
            continue
        if selected and name and name not in selected:
            continue
        text = str(odds).strip()
        if text and text not in values:
            values.append(text)
    if not values and len(details) == 1:
        odds = details[0].get("odds")
        if odds not in (None, ""):
            values.append(str(odds).strip())
    return " / ".join(values)


def option_odds(row, option):
    target = normalize_text(option)
    for item in parse_option_detail(row.get("option_detail")):
        name = normalize_text(
            item.get("name")
            or item.get("selection")
            or item.get("label")
        )
        if name != target:
            continue
        value = item.get("odds")
        if value in (None, ""):
            value = item.get("sp")
        if value not in (None, ""):
            return str(value).strip()
    return ""


def current_event_day(now):
    return (now - timedelta(hours=6)).date()


def parse_datetime(value):
    if isinstance(value, datetime):
        return (
            value.astimezone().replace(tzinfo=None)
            if value.tzinfo
            else value
        )

    text = str(value or "").strip()
    if not text:
        return None

    if re.fullmatch(r"\d{10,13}", text):
        try:
            timestamp = int(text)
            if len(text) >= 13:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp)
        except (OSError, OverflowError, ValueError):
            return None

    text = text.replace("T", " ").replace("Z", "")
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ):
        try:
            return datetime.strptime(text[:19], fmt)
        except Exception:
            continue
    return None


def order_deadline(order):
    source = order or {}
    for key in (
        "betEndTime",
        "bet_end_time",
        "expireTimestamp",
        "expire_timestamp",
        "deadline",
        "endTime",
        "end_time",
    ):
        parsed = parse_datetime(source.get(key))
        if parsed:
            return {
                "deadline_time": parsed,
                "deadline_source": key,
                "deadline_exact": True,
            }
    return None


def load_aliases(cursor):
    try:
        return load_team_aliases(cursor)
    except Exception:
        return {}


def load_caizhanyun_match_references(cursor, alias_map):
    references = {
        "by_date": defaultdict(list),
        "all": [],
    }
    try:
        columns = table_columns(cursor, "order_matches")
        match_date_sql = (
            "om.match_date"
            if "match_date" in columns
            else "NULL"
        )
        cursor.execute(
            f"""
            SELECT
                om.match_code,
                om.match_name,
                om.league,
                COALESCE(
                    {match_date_sql},
                    DATE(om.deadline_time),
                    DATE(COALESCE(o.publish_time,o.created_time))
                ) AS event_day
            FROM order_matches om
            INNER JOIN orders o ON o.id=om.order_id
            WHERE o.platform_id=1
              AND om.match_name IS NOT NULL
              AND om.match_name<>''
            ORDER BY om.id DESC
            LIMIT 5000
            """
        )
        for row in cursor.fetchall() or []:
            match = canonical_match(
                alias_map,
                1,
                row.get("match_name"),
            )
            if not match["normalized_home"] or not match["normalized_away"]:
                continue
            event_day = str(row.get("event_day") or "")
            reference = {
                "match_code": row.get("match_code") or "",
                "home": match["home"],
                "away": match["away"],
                "match_name": match["display"],
                "league": row.get("league") or "",
                "event_day": event_day,
                "canonical_display_key": (
                    f"{event_day}|{match['normalized_home']}|"
                    f"{match['normalized_away']}"
                ),
            }
            if event_day:
                references["by_date"][event_day].append(reference)
            references["all"].append(reference)
    except Exception:
        return {"by_date": {}, "all": []}
    return references


def load_hongrui_match_references(cursor, alias_map):
    return load_caizhanyun_match_references(cursor, alias_map)


def find_caizhanyun_reference(
    references,
    reference_day,
    home,
    away,
):
    if not home or not away:
        return {}
    date_text = str(reference_day or "")[:10]
    candidates = list(
        (references or {}).get("by_date", {}).get(date_text, [])
    )
    if not candidates:
        return {}
    best = None
    best_score = 0.0
    for candidate in candidates:
        score, reversed_order = match_pair_similarity(
            home,
            away,
            candidate.get("home"),
            candidate.get("away"),
        )
        if score > best_score:
            best_score = score
            best = dict(candidate)
            best["reversed_order"] = reversed_order
    return best if best_score >= 0.62 else {}

def _user_pair_filter(user_keys, alias=""):
    prefix = f"{alias}." if alias else ""
    if user_keys is None:
        return "", []
    keys = [
        (intv(platform_id), intv(user_id))
        for platform_id, user_id in user_keys
        if intv(platform_id) and intv(user_id)
    ]
    if not keys:
        return " WHERE 1=0", []
    sql = " OR ".join(
        [f"({prefix}platform_id=%s AND {prefix}user_id=%s)" for _ in keys]
    )
    return f" WHERE ({sql})", [value for key in keys for value in key]


def load_profiles(cursor, user_keys=None):
    result = {}
    try:
        where_sql, params = _user_pair_filter(user_keys)
        cursor.execute(
            f"""
            SELECT platform_id,user_id,nickname,avatar_url
            FROM user_profiles_ext
            {where_sql}
            """,
            tuple(params),
        )
        for row in cursor.fetchall():
            result[
                (
                    intv(row.get("platform_id")),
                    intv(row.get("user_id")),
                )
            ] = {
                "nickname": row.get("nickname") or "",
                "avatar_url": row.get("avatar_url") or "",
            }
    except Exception:
        pass
    return result


def load_user_statistics(cursor, user_keys=None):
    result = {}
    try:
        where_sql, params = _user_pair_filter(user_keys)
        cursor.execute(
            f"""
            SELECT
                platform_id,
                user_id,
                total_orders,
                win_orders,
                lose_orders,
                hit_rate,
                roi,
                follow_num
            FROM user_statistics
            {where_sql}
            """,
            tuple(params),
        )
        for row in cursor.fetchall():
            result[
                (
                    intv(row.get("platform_id")),
                    intv(row.get("user_id")),
                )
            ] = dict(row)
    except Exception:
        pass
    return result



def load_match_schedule(cursor):
    by_code = {}
    by_name = {}

    try:
        columns = table_columns(cursor, "matches")
        if not columns:
            return by_code, by_name

        exact_col = next(
            (
                value
                for value in (
                    "deadline_time",
                    "stop_time",
                    "end_sale_time",
                )
                if value in columns
            ),
            None,
        )
        proxy_col = next(
            (
                value
                for value in (
                    "match_time",
                    "start_time",
                    "kickoff_time",
                    "match_datetime",
                    "game_time",
                )
                if value in columns
            ),
            None,
        )

        if not exact_col and not proxy_col:
            return by_code, by_name

        code_col = next(
            (
                value
                for value in (
                    "match_code",
                    "week_name",
                    "code",
                    "match_id",
                )
                if value in columns
            ),
            None,
        )
        name_col = next(
            (
                value
                for value in ("match_name", "name", "match")
                if value in columns
            ),
            None,
        )
        home_col = next(
            (
                value
                for value in ("home_team", "home")
                if value in columns
            ),
            None,
        )
        away_col = next(
            (
                value
                for value in ("away_team", "away")
                if value in columns
            ),
            None,
        )
        identity_v2 = supports_identity_v2(columns)

        select_fields = [
            (
                f"`{exact_col}` AS exact_value"
                if exact_col
                else "NULL AS exact_value"
            ),
            (
                f"`{proxy_col}` AS proxy_value"
                if proxy_col
                else "NULL AS proxy_value"
            ),
            (
                f"`{code_col}` AS match_code"
                if code_col
                else "'' AS match_code"
            ),
            (
                f"`{name_col}` AS match_name"
                if name_col
                else "'' AS match_name"
            ),
            (
                f"`{home_col}` AS home_team"
                if home_col
                else "'' AS home_team"
            ),
            (
                f"`{away_col}` AS away_team"
                if away_col
                else "'' AS away_team"
            ),
            (
                "platform_id"
                if identity_v2
                else "NULL AS platform_id"
            ),
            (
                "match_date"
                if identity_v2
                else "NULL AS match_date"
            ),
            (
                "match_identity"
                if identity_v2
                else "NULL AS match_identity"
            ),
            (
                "normalized_home"
                if identity_v2
                else "NULL AS normalized_home"
            ),
            (
                "normalized_away"
                if identity_v2
                else "NULL AS normalized_away"
            ),
        ]
        order_col = exact_col or proxy_col

        cursor.execute(
            f"""
            SELECT {",".join(select_fields)}
            FROM matches
            ORDER BY `{order_col}` DESC
            LIMIT 1000
            """
        )

        for row in cursor.fetchall():
            exact_time = parse_datetime(row.get("exact_value"))
            proxy_time = parse_datetime(row.get("proxy_value"))

            if exact_time:
                deadline = {
                    "deadline_time": exact_time,
                    "deadline_source": "deadline",
                    "deadline_exact": True,
                }
            elif proxy_time:
                deadline = {
                    "deadline_time": proxy_time,
                    "deadline_source": "kickoff_proxy",
                    "deadline_exact": False,
                }
            else:
                continue

            platform_id = intv(row.get("platform_id"))
            match_date = row.get("match_date")
            date_text = (
                str(match_date)
                if match_date not in (None, "")
                else ""
            )
            code = normalize_text(row.get("match_code"))
            identity = str(
                row.get("match_identity")
                or ""
            ).strip()
            normalized_home = normalize_text(
                row.get("normalized_home")
                or row.get("home_team")
            )
            normalized_away = normalize_text(
                row.get("normalized_away")
                or row.get("away_team")
            )
            raw_name = row.get("match_name") or ""

            if not raw_name:
                home_team = str(
                    row.get("home_team")
                    or ""
                ).strip()
                away_team = str(
                    row.get("away_team")
                    or ""
                ).strip()
                if home_team and away_team:
                    raw_name = f"{home_team}:{away_team}"

            name = normalize_text(raw_name)

            if identity:
                by_code[("identity", identity)] = deadline
            if platform_id and date_text and code:
                by_code[
                    (
                        "code",
                        platform_id,
                        date_text,
                        code,
                    )
                ] = deadline
            if (
                platform_id
                and date_text
                and normalized_home
                and normalized_away
            ):
                by_name[
                    (
                        "teams",
                        platform_id,
                        date_text,
                        normalized_home,
                        normalized_away,
                    )
                ] = deadline

            if code:
                by_code[code] = deadline
            if name:
                by_name[name] = deadline

    except Exception:
        pass

    return by_code, by_name

def load_orders_for_day(cursor, target_day, pending_only=False):
    day_start = datetime.combine(
        target_day,
        datetime.min.time()
    ) + timedelta(hours=6)

    day_end = day_start + timedelta(days=1)

    where = [
        "COALESCE(o.publish_time,o.created_time)>=%s",
        "COALESCE(o.publish_time,o.created_time)<%s",
        "o.platform_id IN (1,2,3,4)",
    ]
    params = [day_start, day_end]

    if pending_only:
        where.append("o.result='待开奖'")

    cursor.execute(
        f"""
        SELECT o.*
        FROM orders o
        WHERE {" AND ".join(where)}
        ORDER BY o.id DESC
        """,
        tuple(params),
    )
    return cursor.fetchall()


def load_pending_orders(cursor, target_day=None):
    if target_day is None:
        cursor.execute(
            """
            SELECT o.*
            FROM orders o
            WHERE o.platform_id IN (1,2,3,4)
              AND o.result='待开奖'
            ORDER BY o.id DESC
            """
        )
        return cursor.fetchall()

    day_start = datetime.combine(target_day, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    match_columns = table_columns(cursor, "order_matches")
    deadline_clause = ""
    params = [day_start - timedelta(days=14)]
    if "deadline_time" in match_columns:
        deadline_clause = """
            OR EXISTS (
                SELECT 1
                FROM order_matches deadline_match
                WHERE deadline_match.order_id=o.id
                  AND deadline_match.deadline_time>=%s
                  AND deadline_match.deadline_time<%s
            )
        """
        params.extend([day_start, day_end])
    if "match_date" in match_columns:
        deadline_clause += """
            OR EXISTS (
                SELECT 1
                FROM order_matches dated_match
                WHERE dated_match.order_id=o.id
                  AND dated_match.match_date=%s
            )
        """
        params.append(target_day)
    cursor.execute(
        f"""
        SELECT o.*
        FROM orders o
        WHERE o.platform_id IN (1,2,3,4)
          AND o.result='待开奖'
          AND (
              COALESCE(o.publish_time,o.created_time)>=%s
              {deadline_clause}
          )
        ORDER BY o.id DESC
        """,
        tuple(params),
    )
    return cursor.fetchall()


def load_order_matches(cursor, order_ids):
    grouped = defaultdict(list)
    if not order_ids:
        return grouped

    placeholders = ",".join(["%s" for _ in order_ids])
    order_columns = table_columns(
        cursor,
        "order_matches",
    )
    result_columns = table_columns(
        cursor,
        "match_results",
    )
    identity_v2 = (
        supports_identity_v2(order_columns)
        and supports_identity_v2(result_columns)
    )

    if identity_v2:
        join_sql = """
        LEFT JOIN match_results mr
            ON mr.id=
            (
                SELECT mr2.id
                FROM match_results mr2
                WHERE
                    (
                        om.platform_id IS NOT NULL
                        AND om.match_date IS NOT NULL
                        AND om.match_code IS NOT NULL
                        AND om.match_code<>''
                        AND mr2.platform_id=om.platform_id
                        AND mr2.match_date=om.match_date
                        AND mr2.match_code=om.match_code
                    )
                    OR
                    (
                        om.platform_id IS NOT NULL
                        AND om.match_date IS NOT NULL
                        AND om.match_key IS NOT NULL
                        AND om.match_key<>''
                        AND mr2.platform_id=om.platform_id
                        AND mr2.match_date=om.match_date
                        AND mr2.match_key=om.match_key
                    )
                    OR
                    (
                        mr2.match_name=om.match_name
                        AND (
                            mr2.platform_id IS NULL
                            OR om.platform_id IS NULL
                            OR mr2.platform_id=om.platform_id
                        )
                        AND (
                            mr2.match_date IS NULL
                            OR om.match_date IS NULL
                            OR mr2.platform_id IS NULL
                            OR om.platform_id IS NULL
                        )
                    )
                ORDER BY
                    CASE
                        WHEN om.platform_id IS NOT NULL
                         AND om.match_date IS NOT NULL
                         AND om.match_code IS NOT NULL
                         AND om.match_code<>''
                         AND mr2.platform_id=om.platform_id
                         AND mr2.match_date=om.match_date
                         AND mr2.match_code=om.match_code
                        THEN 1
                        WHEN om.platform_id IS NOT NULL
                         AND om.match_date IS NOT NULL
                         AND om.match_key IS NOT NULL
                         AND om.match_key<>''
                         AND mr2.platform_id=om.platform_id
                         AND mr2.match_date=om.match_date
                         AND mr2.match_key=om.match_key
                        THEN 2
                        ELSE 3
                    END,
                    mr2.id DESC
                LIMIT 1
            )
        """
        identity_fields = """
            om.platform_id,
            om.match_date,
            om.match_key,
            om.normalized_home,
            om.normalized_away,
            om.match_identity,
            om.identity_quality,
        """
    else:
        join_sql = """
        LEFT JOIN match_results mr
            ON mr.match_name=om.match_name
        """
        identity_fields = """
            o.platform_id,
            NULL AS match_date,
            om.match_key,
            NULL AS normalized_home,
            NULL AS normalized_away,
            NULL AS match_identity,
            'legacy' AS identity_quality,
        """

    cursor.execute(
        f"""
        SELECT
            om.id,
            om.order_id,
            DATE(
                DATE_SUB(
                    COALESCE(o.publish_time,o.created_time),
                    INTERVAL 6 HOUR
                )
            ) AS order_event_day,
            {identity_fields}
            om.match_code,
            om.match_name,
            om.league,
            om.play_type,
            om.selection,
            om.option_detail,
            om.handicap,
            om.deadline_time,
            om.result AS bet_result,
            mr.home_score,
            mr.away_score,
            mr.half_home_score,
            mr.half_away_score,
            mr.status AS match_status
        FROM order_matches om
        INNER JOIN orders o ON o.id=om.order_id
        {join_sql}
        WHERE om.order_id IN ({placeholders})
        ORDER BY om.order_id DESC,om.id ASC
        """,
        tuple(order_ids),
    )

    for row in cursor.fetchall():
        grouped[intv(row.get("order_id"))].append(row)

    return grouped


def load_hot_play_matches(cursor, order_ids):
    """Load betting legs without the expensive match-results correlation.

    The live hot-play calculation only reads match identity, play, selection,
    odds and deadline fields. Joining match_results here added no business
    value and made every dashboard refresh scan the settlement table once per
    leg. Keep the full loader for pages that actually display settled scores.
    """
    grouped = defaultdict(list)
    if not order_ids:
        return grouped

    columns = table_columns(cursor, "order_matches")
    identity_v2 = supports_identity_v2(columns)
    if identity_v2:
        identity_fields = """
            om.platform_id,
            om.match_date,
            om.match_key,
            om.normalized_home,
            om.normalized_away,
            om.match_identity,
            om.identity_quality,
        """
    else:
        identity_fields = """
            o.platform_id,
            NULL AS match_date,
            om.match_key,
            NULL AS normalized_home,
            NULL AS normalized_away,
            NULL AS match_identity,
            'legacy' AS identity_quality,
        """

    chunk_size = 1000
    for offset in range(0, len(order_ids), chunk_size):
        chunk = order_ids[offset:offset + chunk_size]
        placeholders = ",".join(["%s" for _ in chunk])
        cursor.execute(
            f"""
            SELECT
                om.id,
                om.order_id,
                DATE(
                    DATE_SUB(
                        COALESCE(o.publish_time,o.created_time),
                        INTERVAL 6 HOUR
                    )
                ) AS order_event_day,
                {identity_fields}
                om.match_code,
                om.match_name,
                om.league,
                om.play_type,
                om.selection,
                om.option_detail,
                om.handicap,
                om.deadline_time,
                om.result AS bet_result,
                NULL AS home_score,
                NULL AS away_score,
                NULL AS half_home_score,
                NULL AS half_away_score,
                NULL AS match_status
            FROM order_matches om
            INNER JOIN orders o ON o.id=om.order_id
            WHERE om.order_id IN ({placeholders})
            ORDER BY om.order_id DESC,om.id ASC
            """,
            tuple(chunk),
        )
        for row in cursor.fetchall():
            grouped[intv(row.get("order_id"))].append(row)

    return grouped

def match_deadline(
    match_row,
    schedule_by_code,
    schedule_by_name,
):
    direct = parse_datetime(match_row.get("deadline_time"))
    if direct:
        return {
            "deadline_time": direct,
            "deadline_source": "deadline",
            "deadline_exact": True,
        }

    identity = str(
        match_row.get("match_identity")
        or ""
    ).strip()
    if (
        identity
        and ("identity", identity) in schedule_by_code
    ):
        return schedule_by_code[("identity", identity)]

    platform_id = intv(match_row.get("platform_id"))
    match_date = match_row.get("match_date")
    date_text = (
        str(match_date)
        if match_date not in (None, "")
        else ""
    )
    code = normalize_text(match_row.get("match_code"))

    if platform_id and date_text and code:
        key = (
            "code",
            platform_id,
            date_text,
            code,
        )
        if key in schedule_by_code:
            return schedule_by_code[key]

    normalized_home = normalize_text(
        match_row.get("normalized_home")
    )
    normalized_away = normalize_text(
        match_row.get("normalized_away")
    )

    if (
        platform_id
        and date_text
        and normalized_home
        and normalized_away
    ):
        key = (
            "teams",
            platform_id,
            date_text,
            normalized_home,
            normalized_away,
        )
        if key in schedule_by_name:
            return schedule_by_name[key]

    if code and code in schedule_by_code:
        return schedule_by_code[code]

    name = normalize_text(match_row.get("match_name"))
    if name and name in schedule_by_name:
        return schedule_by_name[name]

    return None

def resolve_order_deadline(
    order,
    matches,
    now,
    schedule_by_code,
    schedule_by_name,
):
    deadlines = []

    for match in matches:
        deadline = match_deadline(
            match,
            schedule_by_code,
            schedule_by_name,
        )
        if deadline and deadline.get("deadline_time"):
            deadlines.append(deadline)

    if deadlines:
        earliest = min(
            deadlines,
            key=lambda item: item["deadline_time"],
        )
        return {
            "unexpired": earliest["deadline_time"] > now,
            "deadline_time": earliest["deadline_time"],
            "deadline_source": earliest["deadline_source"],
            "deadline_exact": bool(earliest["deadline_exact"]),
        }

    pending = str(order.get("result") or "") == "待开奖"
    return {
        "unexpired": pending,
        "deadline_time": None,
        "deadline_source": "pending_fallback" if pending else None,
        "deadline_exact": False,
    }


def is_order_unexpired(
    order,
    matches,
    now,
    schedule_by_code,
    schedule_by_name,
):
    return resolve_order_deadline(
        order,
        matches,
        now,
        schedule_by_code,
        schedule_by_name,
    )["unexpired"]


def portal_match_group_key(row, platform_id=None):
    canonical_display_key = str(
        row.get("canonical_display_key")
        or ""
    ).strip()
    if canonical_display_key:
        return f"display:{canonical_display_key}"

    display_date = str(
        row.get("match_date")
        or row.get("order_event_day")
        or ""
    )[:10]
    normalized_home = str(row.get("normalized_home") or "").strip()
    normalized_away = str(row.get("normalized_away") or "").strip()
    if display_date and normalized_home and normalized_away:
        pair = sorted((normalized_home, normalized_away))
        return f"date_teams:{display_date}|{pair[0]}|{pair[1]}"

    identity = str(
        row.get("match_identity")
        or ""
    ).strip()
    if identity:
        return f"identity:{identity}"

    platform = intv(
        row.get("platform_id")
        or platform_id
    )
    match_date = row.get("match_date")
    match_key = str(row.get("match_key") or "").strip()
    match_code = str(
        row.get("match_code")
        or ""
    ).strip()

    if platform and match_date and match_key:
        return (
            f"date_teams:{platform}|{match_date}|"
            f"{match_key}"
        )

    if platform and match_code and match_key:
        return (
            f"incomplete:{platform}|{match_code}|"
            f"{match_key}"
        )

    return (
        f"legacy:{platform}|"
        f"{row.get('match_name') or ''}"
    )


def format_match_row(
    row,
    alias_map,
    platform_id,
    match_references=None,
):
    match = canonical_match(
        alias_map,
        platform_id,
        row.get("match_name"),
        row.get("home_team"),
        row.get("away_team"),
    )

    normalized_pair = (
        match["normalized_home"],
        match["normalized_away"],
    )
    reference_day = (
        row.get("match_date")
        or (
            parse_datetime(row.get("deadline_time")).date()
            if parse_datetime(row.get("deadline_time"))
            else None
        )
        or row.get("order_event_day")
    )
    if not reference_day and row.get("finished_time"):
        parsed_finished = parse_datetime(row.get("finished_time"))
        reference_day = parsed_finished.date() if parsed_finished else None
    reference = find_caizhanyun_reference(
        match_references or {},
        reference_day,
        match["home"],
        match["away"],
    )
    home = reference.get("home") or match["home"]
    away = reference.get("away") or match["away"]
    match_name = (
        reference.get("match_name")
        or match["display"]
    )

    return {
        "id": intv(row.get("id")),
        "platform_id": intv(
            row.get("platform_id")
            or platform_id
        ),
        "match_code": (
            reference.get("match_code")
            or row.get("match_code")
            or ""
        ),
        "match_date": (
            reference.get("event_day")
            or row.get("match_date")
            or reference_day
        ),
        "match_key": (
            row.get("match_key")
            or match["match_key"]
        ),
        "match_identity": row.get("match_identity") or "",
        "identity_quality": (
            row.get("identity_quality")
            or "legacy"
        ),
        "normalized_home": (
            row.get("normalized_home")
            or match["normalized_home"]
        ),
        "normalized_away": (
            row.get("normalized_away")
            or match["normalized_away"]
        ),
        "home": home,
        "away": away,
        "match_name": match_name,
        "canonical_display_key": (
            reference.get("canonical_display_key")
            or match["match_key"]
        ),
        "league": (
            reference.get("league")
            or row.get("league")
            or ""
        ),
        "play_type": row.get("play_type") or "",
        "selection": row.get("selection") or "",
        "options": split_options(row.get("selection")),
        "odds": selection_odds(row),
        "handicap": intv(row.get("handicap")),
        "result": row.get("bet_result") or "待开奖",
        "home_score": row.get("home_score"),
        "away_score": row.get("away_score"),
        "half_home_score": row.get("half_home_score"),
        "half_away_score": row.get("half_away_score"),
        "deadline_time": parse_datetime(
            row.get("deadline_time")
        ),
        "deadline_source": (
            "deadline"
            if parse_datetime(row.get("deadline_time"))
            else None
        ),
        "deadline_exact": bool(
            parse_datetime(row.get("deadline_time"))
        ),
    }

def enrich_order(
    order,
    matches,
    alias_map,
    profiles,
    statistics=None,
    match_references=None,
):
    platform_id = intv(order.get("platform_id"))
    user_id = intv(order.get("user_id"))
    profile = profiles.get((platform_id, user_id), {})
    stat = (statistics or {}).get((platform_id, user_id), {})
    wins = intv(stat.get("win_orders"))
    losses = intv(stat.get("lose_orders"))
    total_orders = intv(stat.get("total_orders"))
    if wins + losses > 0:
        history_record = f"{wins}胜{losses}负"
    elif total_orders > 0:
        history_record = f"{total_orders}单"
    else:
        history_record = "--"

    formatted_matches = [
        format_match_row(
            row,
            alias_map,
            platform_id,
            match_references,
        )
        for row in matches
    ]

    deadline_state = order.get("_deadline_state")
    if not deadline_state:
        deadline_state = resolve_order_deadline(
            order,
            matches,
            datetime.now(),
            {},
            {},
        )

    return {
        "id": intv(order.get("id")),
        "platform_id": platform_id,
        "platform_name": PLATFORMS.get(
            platform_id,
            f"平台{platform_id}"
        ),
        "platform_order_id": order.get("platform_order_id") or "",
        "user_id": user_id,
        "nickname": (
            order.get("nickname")
            or profile.get("nickname")
            or "未知用户"
        ),
        "avatar_url": profile.get("avatar_url") or "",
        "history_record": history_record,
        "history_hit_rate": (
            money(stat.get("hit_rate")) if stat else None
        ),
        "history_roi": money(stat.get("roi")) if stat else None,
        "publish_time": (
            order.get("publish_time")
            or order.get("created_time")
        ),
        "pass_summary": (
            normalize_pass_summary(order.get("pass_summary"))
            or order.get("play_type")
            or ""
        ),
        "pass_composition": order.get("pass_composition") or "",
        "bet_count": intv(order.get("bet_count")),
        "odds_text": (
            order.get("odds_text")
            or " / ".join(
                match["odds"]
                for match in formatted_matches
                if match.get("odds")
            )
        ),
        "stake": money(order.get("stake")),
        "follow_num": intv(order.get("follow_num")),
        "result": order.get("result") or "待开奖",
        "profit": money(order.get("profit")),
        "bonus": money(order.get("platform_bonus")),
        "expected_bonus": money(order.get("expected_bonus")),
        "lot_multi": money(order.get("lot_multi")),
        "deadline_time": deadline_state["deadline_time"],
        "deadline_source": deadline_state["deadline_source"],
        "deadline_exact": bool(deadline_state["deadline_exact"]),
        "matches": formatted_matches,
    }



def build_current_context(cursor, include_profiles=False):
    cursor.execute("SELECT NOW() AS now_time")
    now = cursor.fetchone()["now_time"]
    target_day = current_event_day(now)

    alias_map = load_aliases(cursor)
    match_references = load_caizhanyun_match_references(
        cursor,
        alias_map,
    )
    profiles = {}
    schedule_by_code, schedule_by_name = load_match_schedule(cursor)

    orders = load_orders_for_day(
        cursor,
        target_day,
        pending_only=True,
    )
    grouped = load_hot_play_matches(
        cursor,
        [intv(order.get("id")) for order in orders],
    )

    unexpired = []
    deadline_summary = {
        "deadline": 0,
        "kickoff_proxy": 0,
        "pending_fallback": 0,
    }

    for order in orders:
        order_id = intv(order.get("id"))
        order_matches = grouped.get(order_id, [])
        deadline_state = resolve_order_deadline(
            order,
            order_matches,
            now,
            schedule_by_code,
            schedule_by_name,
        )

        if deadline_state["unexpired"]:
            enriched_order = dict(order)
            enriched_order["_deadline_state"] = deadline_state
            unexpired.append((enriched_order, order_matches))
            source = deadline_state["deadline_source"]
            if source in deadline_summary:
                deadline_summary[source] += 1

    # ``load_orders_for_day`` already fetched and grouped all pending orders
    # published during the current event day.  ``load_pending_orders`` also
    # includes older orders whose match deadline falls today; only fetch match
    # legs for that disjoint remainder so the common case does not issue a
    # second large IN query for the same order ids.
    pending_orders = load_pending_orders(cursor, target_day)
    initial_order_ids = {
        intv(order.get("id"))
        for order in orders
    }
    extra_pending_orders = [
        order
        for order in pending_orders
        if intv(order.get("id")) not in initial_order_ids
    ]
    pending_grouped = {
        order_id: rows
        for order_id, rows in grouped.items()
    }
    if extra_pending_orders:
        pending_grouped.update(
            load_hot_play_matches(
                cursor,
                [intv(order.get("id")) for order in extra_pending_orders],
            )
        )
    hot_orders = [*orders, *extra_pending_orders]
    today_hot_legs = []
    for order in hot_orders:
        order_level_deadline = order_deadline(order)
        for row in pending_grouped.get(intv(order.get("id")), []):
            deadline = order_level_deadline or match_deadline(
                    row,
                    schedule_by_code,
                    schedule_by_name,
                )
            deadline_time = (
                deadline.get("deadline_time")
                if deadline
                else None
            )
            if not deadline_time:
                continue
            if deadline_time.date() != target_day:
                continue
            if deadline_time <= now:
                continue
            today_hot_legs.append((order, row, deadline))

    if include_profiles:
        profiles = load_profiles(
            cursor,
            [
                (order.get("platform_id"), order.get("user_id"))
                for order, _matches in unexpired
            ],
        )

    return {
        "now": now,
        "day": target_day,
        "alias_map": alias_map,
        "match_references": match_references,
        "schedule_by_code": schedule_by_code,
        "schedule_by_name": schedule_by_name,
        "profiles": profiles,
        "unexpired": unexpired,
        "today_hot_legs": today_hot_legs,
        "deadline_summary": deadline_summary,
    }


def get_current_context(cursor, include_profiles=False):
    now = monotonic()
    cached = _current_context_cache.get("data")
    age = now - float(_current_context_cache.get("created_at") or 0.0)
    profiles_ready = bool(_current_context_cache.get("has_profiles"))
    if (
        cached is not None
        and age <= CURRENT_CONTEXT_CACHE_SECONDS
        and (not include_profiles or profiles_ready)
    ):
        return cached

    with _current_context_lock:
        now = monotonic()
        cached = _current_context_cache.get("data")
        age = now - float(_current_context_cache.get("created_at") or 0.0)
        profiles_ready = bool(_current_context_cache.get("has_profiles"))
        if (
            cached is not None
            and age <= CURRENT_CONTEXT_CACHE_SECONDS
            and (not include_profiles or profiles_ready)
        ):
            return cached
        context = build_current_context(cursor, include_profiles=include_profiles)
        _current_context_cache["data"] = context
        _current_context_cache["created_at"] = now
        _current_context_cache["has_profiles"] = bool(include_profiles)
        return context


def aggregate_today_hot_plays(ctx):
    alias_map = ctx["alias_map"]
    match_references = ctx["match_references"]
    groups = {}
    seen = set()

    for order, row, deadline in ctx.get("today_hot_legs", []):
        platform_id = intv(order.get("platform_id"))
        formatted = format_match_row(
            row,
            alias_map,
            platform_id,
            match_references,
        )
        play_type = normalize_play_type(formatted.get("play_type"))
        selection = normalize_selection_combination(
            play_type,
            formatted.get("selection"),
        )
        if play_type not in FOUR_PLAYS or not selection:
            continue
        match_key = portal_match_group_key(formatted, platform_id)
        dedupe_key = (
            intv(order.get("id")),
            match_key,
            play_type,
            selection,
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        group_key = (match_key, play_type, selection)
        if group_key not in groups:
            groups[group_key] = {
                "play_type": play_type,
                "selection": selection,
                "match_code": formatted.get("match_code") or "",
                "home": formatted.get("home") or "",
                "away": formatted.get("away") or "",
                "match_name": formatted.get("match_name") or "",
                "league": formatted.get("league") or "",
                "deadline_time": deadline.get("deadline_time"),
                "count": 0,
            }
        group = groups[group_key]
        group["count"] += 1
        candidate_time = deadline.get("deadline_time")
        if candidate_time and (
            not group.get("deadline_time")
            or candidate_time < group["deadline_time"]
        ):
            group["deadline_time"] = candidate_time

    result = []
    for play_type in FOUR_PLAYS:
        rows = [
            item
            for item in groups.values()
            if item["play_type"] == play_type
        ]
        rows.sort(
            key=lambda item: (
                -item["count"],
                item["match_name"],
                item["selection"],
            )
        )
        result.append({
            "play_type": play_type,
            "items": rows[:3],
        })
    return result


def load_recent_user_metrics(cursor, user_keys):
    """Load page-level seven-day metrics without per-user SQL queries."""
    keys = [
        (intv(platform_id), intv(user_id))
        for platform_id, user_id in user_keys
        if intv(platform_id) and intv(user_id)
    ]
    if not keys:
        return {}

    pair_sql = " OR ".join(
        ["(o.platform_id=%s AND o.user_id=%s)" for _ in keys]
    )
    pair_params = [value for key in keys for value in key]
    cursor.execute(
        f"""
        SELECT
            o.platform_id,
            o.user_id,
            SUM(CASE WHEN COALESCE(o.publish_time,o.created_time)>=DATE_SUB(NOW(),INTERVAL 7 DAY) THEN 1 ELSE 0 END) AS orders7d,
            IFNULL(SUM(CASE WHEN COALESCE(o.publish_time,o.created_time)>=DATE_SUB(NOW(),INTERVAL 7 DAY) THEN o.stake ELSE 0 END),0) AS self_buy7d,
            IFNULL(SUM(CASE WHEN COALESCE(o.publish_time,o.created_time)>=DATE_SUB(NOW(),INTERVAL 7 DAY) THEN o.follow_num ELSE 0 END),0) AS followers7d,
            IFNULL(SUM(CASE WHEN COALESCE(o.publish_time,o.created_time)>=DATE_SUB(NOW(),INTERVAL 7 DAY) AND o.result<>'待开奖' THEN o.profit ELSE 0 END),0) AS profit7d,
            SUM(CASE WHEN COALESCE(o.publish_time,o.created_time)>=CURDATE() THEN 1 ELSE 0 END) AS today_orders,
            IFNULL(SUM(CASE WHEN COALESCE(o.publish_time,o.created_time)>=CURDATE() THEN o.follow_num ELSE 0 END),0) AS today_followers,
            IFNULL(SUM(CASE WHEN COALESCE(o.publish_time,o.created_time)>=DATE_FORMAT(CURDATE(),'%%Y-%%m-01') AND o.result<>'待开奖' THEN o.stake ELSE 0 END),0) AS month_stake,
            IFNULL(SUM(CASE WHEN COALESCE(o.publish_time,o.created_time)>=DATE_FORMAT(CURDATE(),'%%Y-%%m-01') AND o.result<>'待开奖' THEN o.profit ELSE 0 END),0) AS month_profit
        FROM orders o
        WHERE ({pair_sql})
          AND COALESCE(o.publish_time,o.created_time)<=NOW()
        GROUP BY o.platform_id,o.user_id
        """,
        tuple(pair_params),
    )
    metrics = {
        (intv(row.get("platform_id")), intv(row.get("user_id"))): dict(row)
        for row in cursor.fetchall() or []
    }
    cursor.execute(
        f"""
        SELECT
            o.platform_id,
            o.user_id,
            SUBSTRING_INDEX(
                GROUP_CONCAT(
                    CASE WHEN o.result IN ('赢','输') THEN o.result END
                    ORDER BY o.id DESC SEPARATOR ','
                ),
                ',',
                10
            ) AS recent_results
        FROM orders o
        WHERE ({pair_sql})
        GROUP BY o.platform_id,o.user_id
        """,
        tuple(pair_params),
    )
    for row in cursor.fetchall() or []:
        key = (intv(row.get("platform_id")), intv(row.get("user_id")))
        metric = metrics.setdefault(key, {})
        metric["recent10"] = [
            value
            for value in str(row.get("recent_results") or "").split(",")
            if value in {"赢", "输"}
        ][:10]
        metric["recent5"] = metric["recent10"][:5]

    cursor.execute(
        f"""
        SELECT o.platform_id,o.user_id,om.play_type,COUNT(DISTINCT o.id) AS play_orders
        FROM orders o
        INNER JOIN order_matches om ON om.order_id=o.id
        WHERE ({pair_sql})
          AND om.play_type IS NOT NULL
          AND om.play_type<>''
        GROUP BY o.platform_id,o.user_id,om.play_type
        ORDER BY o.platform_id,o.user_id,play_orders DESC,om.play_type
        """,
        tuple(pair_params),
    )
    for row in cursor.fetchall() or []:
        key = (intv(row.get("platform_id")), intv(row.get("user_id")))
        metric = metrics.setdefault(key, {})
        if not metric.get("favorite_play"):
            metric["favorite_play"] = row.get("play_type") or ""

    cursor.execute(
        f"""
        SELECT
            o.platform_id,
            o.user_id,
            COUNT(*) AS lifetime_orders,
            MIN(COALESCE(o.publish_time,o.created_time)) AS first_order_time,
            SUBSTRING_INDEX(
                GROUP_CONCAT(
                    CAST(o.stake AS CHAR)
                    ORDER BY COALESCE(o.publish_time,o.created_time),o.id
                    SEPARATOR ','
                ),
                ',',
                1
            ) AS first_order_amount
        FROM orders o
        WHERE ({pair_sql})
          AND o.stake IS NOT NULL
          AND o.stake>0
        GROUP BY o.platform_id,o.user_id
        """,
        tuple(pair_params),
    )
    for row in cursor.fetchall() or []:
        key = (intv(row.get("platform_id")), intv(row.get("user_id")))
        metric = metrics.setdefault(key, {})
        metric.update(
            build_first_order_profile(
                row.get("first_order_amount"),
                row.get("first_order_time"),
                intv(row.get("lifetime_orders")),
                history_complete=False,
            )
        )

    for metric in metrics.values():
        month_stake = money(metric.get("month_stake"))
        metric["month_roi"] = (
            round(money(metric.get("month_profit")) / month_stake * 100, 2)
            if month_stake > 0
            else None
        )
    return metrics


def load_day_metrics(cursor, target_day):
    """Aggregate dashboard day counters in MySQL using the existing event-day window."""

    day_start = datetime.combine(target_day, datetime.min.time()) + timedelta(hours=6)
    day_end = day_start + timedelta(days=1)
    cursor.execute(
        """
        SELECT
            COUNT(*) AS plans,
            SUM(CASE WHEN result='赢' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN result='输' THEN 1 ELSE 0 END) AS lost,
            SUM(CASE WHEN result<>'待开奖' THEN 1 ELSE 0 END) AS settled,
            IFNULL(SUM(follow_num),0) AS followers,
            IFNULL(SUM(stake),0) AS amount
        FROM orders
        WHERE COALESCE(publish_time,created_time)>=%s
          AND COALESCE(publish_time,created_time)<%s
          AND platform_id IN (1,2,3,4)
        """,
        (day_start, day_end),
    )
    row = cursor.fetchone() or {}
    return {
        "plans": intv(row.get("plans")),
        "wins": intv(row.get("wins")),
        "lost": intv(row.get("lost")),
        "settled": intv(row.get("settled")),
        "followers": intv(row.get("followers")),
        "amount": round(money(row.get("amount")), 2),
    }


def load_platform_day_metrics(cursor, target_day):
    day_start = datetime.combine(target_day, datetime.min.time()) + timedelta(hours=6)
    day_end = day_start + timedelta(days=1)
    cursor.execute(
        """
        SELECT platform_id,COUNT(*) AS order_count,
               IFNULL(SUM(stake),0) AS amount,
               IFNULL(SUM(follow_num),0) AS followers
        FROM orders
        WHERE COALESCE(publish_time,created_time)>=%s
          AND COALESCE(publish_time,created_time)<%s
          AND platform_id IN (1,2,3,4)
        GROUP BY platform_id
        """,
        (day_start, day_end),
    )
    return {
        intv(row.get("platform_id")): {
            "order_count": intv(row.get("order_count")),
            "amount": round(money(row.get("amount")), 2),
            "followers": intv(row.get("followers")),
        }
        for row in cursor.fetchall() or []
    }


def build_dashboard_response():
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        build_started = perf_counter()
        ctx = get_current_context(cursor, include_profiles=False)
        current_context_ms = (perf_counter() - build_started) * 1000
        target_day = ctx["day"]
        now = ctx["now"]
        alias_map = ctx["alias_map"]
        match_references = ctx["match_references"]
        unexpired = ctx["unexpired"]
        users_count = len({(intv(order.get("platform_id")), intv(order.get("user_id"))) for order, _ in unexpired})
        ranking_candidates = 0
        hot_plays = aggregate_today_hot_plays(ctx)
        hot_plays_ms = (perf_counter() - build_started) * 1000 - current_context_ms

        yesterday = target_day - timedelta(days=1)
        today_metrics_started = perf_counter()
        today_day_metrics = load_day_metrics(cursor, target_day)
        today_metrics_ms = (perf_counter() - today_metrics_started) * 1000
        yesterday_metrics_started = perf_counter()
        yesterday_day_metrics = load_day_metrics(cursor, yesterday)
        yesterday_metrics_ms = (perf_counter() - yesterday_metrics_started) * 1000
        platform_metrics_started = perf_counter()
        platform_metrics = load_platform_day_metrics(cursor, target_day)
        platform_metrics_ms = (perf_counter() - platform_metrics_started) * 1000

        metrics = {
            "yesterday_plans": yesterday_day_metrics["plans"],
            "yesterday_wins": yesterday_day_metrics["wins"],
            "yesterday_lost": yesterday_day_metrics["lost"],
            "yesterday_settled": yesterday_day_metrics["settled"],
            "today_plans": today_day_metrics["plans"],
            "today_followers": today_day_metrics["followers"],
            "today_amount": today_day_metrics["amount"],
            "unexpired_plans": len(unexpired),
        }

        platform_rows = []
        for platform_id in (1, 3, 2, 4):
            row = platform_metrics.get(platform_id, {})
            platform_rows.append(
                {
                    "platform_id": platform_id,
                    "platform_name": PLATFORMS[platform_id],
                    "order_count": row.get("order_count", 0),
                    "amount": row.get("amount", 0.0),
                    "followers": row.get("followers", 0),
                }
            )

        lightweight_groups = {}
        for order, _matches in unexpired:
            platform_id = intv(order.get("platform_id"))
            user_id = intv(order.get("user_id"))
            key = (platform_id, user_id)
            group = lightweight_groups.setdefault(
                key,
                {"platform_id": platform_id, "user_id": user_id,
                 "amount": 0.0, "followers": 0, "order_count": 0},
            )
            group["amount"] += money(order.get("stake"))
            group["followers"] += intv(order.get("follow_num"))
            group["order_count"] += 1

        ranking_candidates = len(lightweight_groups)
        candidate_ranking = sorted(
            lightweight_groups.values(),
            key=lambda item: (item["amount"], item["followers"], item["order_count"]),
            reverse=True,
        )
        top_keys = {
            (item["platform_id"], item["user_id"])
            for item in candidate_ranking[:30]
        }

        profiles_started = perf_counter()
        profiles = load_profiles(cursor, top_keys)
        profiles_ms = (perf_counter() - profiles_started) * 1000
        statistics_started = perf_counter()
        statistics = load_user_statistics(cursor, top_keys)
        user_statistics_ms = (perf_counter() - statistics_started) * 1000

        user_groups = {}
        enrich_started = perf_counter()
        for order, matches in unexpired:
            platform_id = intv(order.get("platform_id"))
            user_id = intv(order.get("user_id"))
            key = (platform_id, user_id)
            if key not in top_keys:
                continue
            if key not in user_groups:
                profile = profiles.get(key, {})
                user_groups[key] = {
                    "platform_id": platform_id,
                    "platform_name": PLATFORMS.get(platform_id, f"平台{platform_id}"),
                    "user_id": user_id,
                    "nickname": order.get("nickname") or profile.get("nickname") or "未知用户",
                    "avatar_url": profile.get("avatar_url") or "",
                    "amount": 0.0,
                    "followers": 0,
                    "bonus": 0.0,
                    "orders": [],
                }
            group = user_groups[key]
            group["amount"] += money(order.get("stake"))
            group["followers"] += intv(order.get("follow_num"))
            group["bonus"] += money(order.get("platform_bonus"))
            group["orders"].append(
                enrich_order(order, matches, alias_map, profiles,
                             statistics=statistics, match_references=match_references)
            )
        enrich_ms = (perf_counter() - enrich_started) * 1000

        for key, group in user_groups.items():
            stat = statistics.get(key, {})
            wins = intv(stat.get("win_orders"))
            losses = intv(stat.get("lose_orders"))
            total = intv(stat.get("total_orders"))

            if wins + losses > 0:
                record = f"{wins}胜{losses}负"
            elif total > 0:
                record = f"{total}单"
            else:
                record = "--"

            group["history_record"] = record
            group["history_hit_rate"] = money(
                stat.get("hit_rate")
            )

        ranking = sorted(
            user_groups.values(),
            key=lambda item: (
                item["amount"],
                item["followers"],
                len(item["orders"]),
            ),
            reverse=True,
        )[:30]

        dashboard_total_ms = (perf_counter() - build_started) * 1000
        print(
            "[dashboard] context=%.2fms hot_plays=%.2fms today_metrics=%.2fms "
            "yesterday_metrics=%.2fms platform_metrics=%.2fms profiles=%.2fms "
            "user_statistics=%.2fms enrich=%.2fms total=%.2fms orders_count=%d "
            "unexpired_count=%d users_count=%d ranking_candidates=%d enriched_orders_count=%d"
            % (current_context_ms, hot_plays_ms, today_metrics_ms, yesterday_metrics_ms,
               platform_metrics_ms, profiles_ms, user_statistics_ms, enrich_ms,
               dashboard_total_ms, metrics["today_plans"], len(unexpired), users_count,
               ranking_candidates, sum(len(item["orders"]) for item in ranking))
        )

        for index, group in enumerate(ranking, start=1):
            group["rank"] = index
            group["amount"] = round(group["amount"], 2)
            group["bonus"] = round(group["bonus"], 2)
            group["order_count"] = len(group["orders"])

        return {
            "code": 200,
            "data": {
                "day": str(target_day),
                "server_time": now,
                "metrics": metrics,
                "platform_bets": platform_rows,
                "sender_ranking": ranking,
                "hot_plays": hot_plays,
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


async def refresh_dashboard_cache():
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            _dashboard_executor,
            build_dashboard_response,
        )
    except Exception as exc:
        result = {
            "code": 500,
            "msg": str(exc),
            "data": {},
        }

    if result.get("code") == 200:
        refreshed_at = datetime.now()
        data = result.get("data") or {}
        data_with_meta = attach_meta(
            data,
            freshness="fresh",
            updated_at=refreshed_at.isoformat(),
            age_seconds=0.0,
            refreshing=False,
        )
        result["data"] = data_with_meta
        result["meta"] = data_with_meta.get("meta")
        _dashboard_cache["data"] = result
        _dashboard_cache["created_at"] = monotonic()
        # Persistence is best-effort.  If api_snapshots has not been migrated
        # yet, the in-process cache remains fully functional.
        # Snapshot persistence must never extend the API response latency.
        loop.run_in_executor(
            _snapshot_executor,
            save_snapshot,
            "portal:dashboard",
            data,
            "fresh",
        )
    return result


@router.get("/dashboard")
async def dashboard():
    global _dashboard_refresh_task

    now = monotonic()
    cached = _dashboard_cache.get("data")
    if cached is None:
        snapshot, snapshot_meta = load_snapshot("portal:dashboard")
        if snapshot is not None:
            cached = {
                "code": 200,
                "data": snapshot,
                "meta": {
                    **(snapshot_meta or {}),
                    "freshness": "stale",
                    "refreshing": True,
                },
            }
            cached["data"] = attach_meta(
                    snapshot,
                    freshness="stale",
                    updated_at=(snapshot_meta or {}).get("updated_at"),
                    age_seconds=(snapshot_meta or {}).get("age_seconds"),
                    refreshing=True,
                )
            _dashboard_cache["data"] = cached
            _dashboard_cache["created_at"] = monotonic()
            # A persisted snapshot is immediately usable; refresh it in the
            # background instead of blocking the first page request.
            _dashboard_refresh_task = asyncio.create_task(
                refresh_dashboard_cache()
            )
    cache_age = now - float(_dashboard_cache.get("created_at") or 0.0)
    if cached is not None and cache_age <= DASHBOARD_CACHE_SECONDS:
        return cached

    if _dashboard_refresh_task is None or _dashboard_refresh_task.done():
        _dashboard_refresh_task = asyncio.create_task(
            refresh_dashboard_cache()
        )

    if cached is not None and cache_age <= DASHBOARD_STALE_SECONDS:
        return cached

    try:
        return await asyncio.wait_for(
            asyncio.shield(_dashboard_refresh_task),
            timeout=DASHBOARD_FIRST_RESPONSE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        # Keep the response renderable.  A bounded orders-only query may add
        # useful counters; the full single-flight task continues in the
        # background and replaces this payload once complete.
        try:
            minimal = await asyncio.wait_for(
                asyncio.to_thread(_build_dashboard_minimal_response),
                timeout=1.0,
            )
        except asyncio.TimeoutError:
            minimal = None
        return minimal or _empty_dashboard_response()


@router.get("/schemes")
def schemes(
    platform_id: int = 0,
    keyword: str = "",
    result: str = "",
    page: int = 1,
    page_size: int = 30,
):
    conn = None
    cursor = None

    try:
        page = max(1, page)
        page_size = max(10, min(page_size, 100))

        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        where = ["o.platform_id IN (1,2,3,4)"]
        params = []

        if platform_id > 0:
            where.append("o.platform_id=%s")
            params.append(platform_id)

        keyword = str(keyword or "").strip()
        if keyword:
            like = "%" + keyword + "%"
            where.append(
                """
                (
                    o.nickname LIKE %s
                    OR o.platform_order_id LIKE %s
                    OR o.match_name LIKE %s
                    OR CAST(o.user_id AS CHAR) LIKE %s
                )
                """
            )
            params.extend([like, like, like, like])

        result = str(result or "").strip()
        if result:
            where.append("o.result=%s")
            params.append(result)

        where_sql = " AND ".join(where)

        cursor.execute(
            f"SELECT COUNT(*) AS c FROM orders o WHERE {where_sql}",
            tuple(params)
        )
        total = intv(cursor.fetchone()["c"])

        offset = (page - 1) * page_size
        query_params = list(params) + [page_size, offset]

        cursor.execute(
            f"""
            SELECT o.*
            FROM orders o
            WHERE {where_sql}
            ORDER BY o.id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(query_params)
        )
        orders = cursor.fetchall()

        grouped = load_order_matches(
            cursor,
            [intv(order.get("id")) for order in orders]
        )
        alias_map = load_aliases(cursor)
        match_references = load_caizhanyun_match_references(
            cursor,
            alias_map,
        )
        user_keys = [
            (order.get("platform_id"), order.get("user_id"))
            for order in orders
        ]
        profiles = load_profiles(cursor, user_keys)
        statistics = load_user_statistics(cursor, user_keys)

        data = [
            enrich_order(
                order,
                grouped.get(intv(order.get("id")), []),
                alias_map,
                profiles,
                statistics,
                match_references,
            )
            for order in orders
        ]

        pages = max(
            1,
            (total + page_size - 1) // page_size
        )

        return {
            "code": 200,
            "page": page,
            "pages": pages,
            "page_size": page_size,
            "total": total,
            "data": data,
        }

    except Exception as exc:
        return {
            "code": 500,
            "msg": str(exc),
            "data": [],
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/user/{platform_id}/{user_id}")
def user_detail(platform_id: int, user_id: int):
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        alias_map = load_aliases(cursor)
        match_references = load_caizhanyun_match_references(
            cursor,
            alias_map,
        )
        cursor.execute(
            """
            SELECT nickname,avatar_url
            FROM user_profiles_ext
            WHERE platform_id=%s AND user_id=%s
            LIMIT 1
            """,
            (platform_id, user_id),
        )
        profile = cursor.fetchone() or {}
        profiles = {(platform_id, user_id): profile}

        cursor.execute(
            """
            SELECT *
            FROM user_statistics
            WHERE platform_id=%s AND user_id=%s
            LIMIT 1
            """,
            (platform_id, user_id)
        )
        stat = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT o.*
            FROM orders o
            WHERE o.platform_id=%s AND o.user_id=%s
            ORDER BY o.id DESC
            LIMIT 20
            """,
            (platform_id, user_id)
        )
        orders = cursor.fetchall()

        grouped = load_order_matches(
            cursor,
            [intv(order.get("id")) for order in orders]
        )
        recent = load_recent_user_metrics(
            cursor,
            [(platform_id, user_id)],
        ).get((platform_id, user_id), {})
        grade = next(
            (
                item
                for item in load_user_grades(cursor)
                if intv(item.get("platform_id")) == platform_id
                and intv(item.get("user_id")) == user_id
            ),
            {},
        )

        data_orders = [
            enrich_order(
                order,
                grouped.get(intv(order.get("id")), []),
                alias_map,
                profiles,
                match_references=match_references,
            )
            for order in orders
        ]

        nickname = (
            stat.get("nickname")
            or profile.get("nickname")
            or (
                data_orders[0]["nickname"]
                if data_orders
                else "未知用户"
            )
        )

        return {
            "code": 200,
            "data": {
                "user": {
                    "platform_id": platform_id,
                    "platform_name": PLATFORMS.get(
                        platform_id,
                        f"平台{platform_id}"
                    ),
                    "user_id": user_id,
                    "nickname": nickname,
                    "avatar_url": profile.get("avatar_url") or "",
                    "total_orders": intv(stat.get("total_orders")),
                    "settled_orders": intv(stat.get("settled_orders")),
                    "win_orders": intv(stat.get("win_orders")),
                    "lose_orders": intv(stat.get("lose_orders")),
                    "hit_rate": money(stat.get("hit_rate")),
                    "total_stake": money(stat.get("total_stake")),
                    "total_profit": money(stat.get("total_profit")),
                    "roi": money(stat.get("roi")),
                    "follow_num": intv(stat.get("follow_num")),
                    "expert_score": money(stat.get("expert_score")),
                    "grade": grade.get("grade") or "B",
                    "auto_grade": grade.get("auto_grade") or "B",
                    "manual_grade": grade.get("manual_grade") or "",
                    "grade_score": intv(grade.get("score")),
                    "score_detail": grade.get("score_detail") or {},
                    "grade_reasons": grade.get("grade_reasons") or {},
                    "self_buy7d": money(recent.get("self_buy7d")),
                    "orders7d": intv(recent.get("orders7d")),
                    "followers7d": intv(recent.get("followers7d")),
                    "profit7d": money(recent.get("profit7d")),
                    "recent5": recent.get("recent5") or [],
                    "recent10": recent.get("recent10") or [],
                    "month_roi": recent.get("month_roi"),
                    "today_orders": intv(recent.get("today_orders")),
                    "today_followers": intv(recent.get("today_followers")),
                    "current_streak": intv(stat.get("current_streak")),
                    "max_win_streak": intv(stat.get("max_win_streak")),
                    "favorite_play": recent.get("favorite_play") or "",
                    "first_order_amount": recent.get("first_order_amount"),
                    "first_order_time": recent.get("first_order_time"),
                    "first_order_confidence": recent.get("first_order_confidence") or "suspected",
                    "auto_tags": recent.get("auto_tags") or [],
                },
                "orders": data_orders,
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


def aggregate_heatmap(ctx, play_type):
    alias_map = ctx["alias_map"]
    match_references = ctx["match_references"]
    match_groups = {}
    seen = set()
    for order, row, _deadline in ctx.get("today_hot_legs", []):
        platform_id = intv(order.get("platform_id"))
        normalized_play = normalize_play_type(row.get("play_type"))
        if normalized_play != play_type:
            continue
        formatted = format_match_row(
            row,
            alias_map,
            platform_id,
            match_references,
        )
        option = normalize_selection_combination(
            normalized_play,
            formatted["selection"],
        )
        if not option:
            continue
        key = portal_match_group_key(formatted, platform_id)
        dedupe_key = (
            intv(order.get("id")),
            key,
            normalized_play,
            option,
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        if key not in match_groups:
            match_groups[key] = {
                "platform_id": formatted["platform_id"],
                "match_code": formatted["match_code"],
                "match_date": formatted["match_date"],
                "match_key": formatted["match_key"],
                "match_identity": formatted["match_identity"],
                "identity_quality": formatted["identity_quality"],
                "home": formatted["home"],
                "away": formatted["away"],
                "match_name": formatted["match_name"],
                "league": formatted["league"],
                "option_counts": defaultdict(int),
                "option_odds": {},
            }
        group = match_groups[key]
        group["option_counts"][option] += 1
        odds = option_odds(row, option)
        if odds and option not in group["option_odds"]:
            group["option_odds"][option] = odds

    matches = []

    for group in match_groups.values():
        total_items = sum(
            group["option_counts"].values()
        )

        options = []

        for option, count in sorted(
            group["option_counts"].items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        ):
            options.append(
                {
                    "option": option,
                    "count": count,
                    "odds": group["option_odds"].get(option) or "",
                    "share": round(
                        count / total_items * 100,
                        2
                    )
                    if total_items
                    else 0.0,
                }
            )

        matches.append(
            {
                "platform_id": group["platform_id"],
                "match_code": group["match_code"],
                "match_date": group["match_date"],
                "match_key": group["match_key"],
                "match_identity": group["match_identity"],
                "identity_quality": group["identity_quality"],
                "home": group["home"],
                "away": group["away"],
                "match_name": group["match_name"],
                "league": group["league"],
                "total_items": total_items,
                "options": options,
            }
        )

    matches.sort(
        key=lambda item: item["total_items"],
        reverse=True
    )

    focus = []

    for row in matches[:4]:
        hottest = (
            row["options"][0]
            if row["options"]
            else {
                "option": "-",
                "count": 0,
                "share": 0,
            }
        )

        focus.append(
            {
                "match_code": row["match_code"],
                "match_name": row["match_name"],
                "league": row["league"],
                "option": hottest["option"],
                "count": hottest["count"],
                "share": hottest["share"],
                "total_items": row["total_items"],
            }
        )

    return {
        "play_type": play_type,
        "focus": focus,
        "matches": matches,
    }


@router.get("/heatmap")
def heatmap(play_type: str = "胜平负"):
    conn = None
    cursor = None

    try:
        if play_type not in FOUR_PLAYS:
            play_type = "胜平负"

        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        ctx = get_current_context(cursor)
        data = aggregate_heatmap(ctx, play_type)

        data["day"] = str(ctx["day"])
        data["unexpired_orders"] = len(
            ctx["unexpired"]
        )

        return {
            "code": 200,
            "data": data,
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


@router.get("/analysis")
def analysis():
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        ctx = get_current_context(cursor)

        play_data = {
            play: aggregate_heatmap(ctx, play)
            for play in FOUR_PLAYS
        }

        match_map = {}

        for play, data in play_data.items():
            for row in data["matches"]:
                key = (
                    row.get("match_identity")
                    or (
                        f"{row.get('platform_id')}|"
                        f"{row.get('match_date')}|"
                        f"{row.get('match_key')}"
                    )
                    or row["match_name"]
                )

                if key not in match_map:
                    match_map[key] = {
                        "platform_id": row.get("platform_id"),
                        "match_code": row["match_code"],
                        "match_date": row.get("match_date"),
                        "match_key": row.get("match_key"),
                        "match_identity": row.get("match_identity"),
                        "identity_quality": row.get("identity_quality"),
                        "match_name": row["match_name"],
                        "league": row["league"],
                        "plays": {},
                    }

                match_map[key]["plays"][play] = row["options"]

        matches = list(match_map.values())
        matches.sort(
            key=lambda item: (
                item["match_code"]
                or item["match_name"]
            )
        )

        return {
            "code": 200,
            "data": {
                "day": str(ctx["day"]),
                "unexpired_orders": len(
                    ctx["unexpired"]
                ),
                "matches": matches,
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


@router.get("/users")
def users(
    platform_id: int = 0,
    keyword: str = "",
    sort: str = "score",
    real_profit: str = "all",
    favorite_play: str = "",
    min_streak: int = 0,
    recent_form: str = "all",
    min_hit_rate: float = 0,
    min_roi: float = -999999,
    first_order_tag: str = "",
    page: int = 1,
    page_size: int = 30,
):
    conn = None
    cursor = None

    try:
        page = max(1, page)
        page_size = max(10, min(page_size, 100))

        sort_map = {
            "score": "us.expert_score DESC",
            "orders": "us.total_orders DESC",
            "hit": "us.hit_rate DESC, us.settled_orders DESC",
            "profit": "us.total_profit DESC",
            "roi": "us.roi DESC, us.settled_orders DESC",
            "follow": "us.follow_num DESC",
        }

        order_by = sort_map.get(
            sort,
            sort_map["score"]
        )

        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        where = ["us.platform_id IN (1,2,3,4)"]
        params = []

        if platform_id > 0:
            where.append("us.platform_id=%s")
            params.append(platform_id)

        if real_profit == "profit":
            where.append("us.total_profit>0")
        elif real_profit == "profit_5000":
            where.append("us.total_profit>=5000")
        elif real_profit == "profit_10000":
            where.append("us.total_profit>=10000")
        elif real_profit == "loss":
            where.append("us.total_profit<0")

        if min_streak > 0:
            where.append("us.current_streak>=%s")
            params.append(min_streak)

        if recent_form == "latest_win":
            where.append("us.recent_results LIKE '赢%'")
        elif recent_form == "last3_win":
            where.append("us.recent_results LIKE '赢,赢,赢%'")
        elif recent_form == "latest_loss":
            where.append("us.recent_results LIKE '输%'")

        if min_hit_rate > 0:
            where.append("us.hit_rate>=%s")
            params.append(min_hit_rate)

        if min_roi > -999999:
            where.append("us.roi>=%s")
            params.append(min_roi)

        favorite_play = str(favorite_play or "").strip()
        if favorite_play:
            where.append(
                """
                EXISTS (
                    SELECT 1
                    FROM orders play_order
                    INNER JOIN order_matches play_match
                        ON play_match.order_id=play_order.id
                    WHERE play_order.platform_id=us.platform_id
                      AND play_order.user_id=us.user_id
                      AND play_match.play_type=%s
                )
                """
            )
            params.append(favorite_play)

        first_order_tag = str(first_order_tag or "").strip()
        first_amount_rules = {
            "NEW_FIRST_ORDER_100": "=100",
            "NEW_FIRST_ORDER_200": "=200",
            "NEW_FIRST_ORDER_LOW_AMOUNT": "<=200",
            "SUSPECTED_FIRST_ORDER_100": "=100",
            "SUSPECTED_FIRST_ORDER_200": "=200",
        }
        if first_order_tag in first_amount_rules:
            where.append(
                f"""
                (
                    SELECT first_order.stake
                    FROM orders first_order
                    WHERE first_order.platform_id=us.platform_id
                      AND first_order.user_id=us.user_id
                      AND first_order.stake>0
                    ORDER BY COALESCE(first_order.publish_time,first_order.created_time),first_order.id
                    LIMIT 1
                ) {first_amount_rules[first_order_tag]}
                """
            )
        elif first_order_tag == "NEW_ACCOUNT_OBSERVE":
            where.append(
                """
                (SELECT COUNT(*) FROM orders observed_order
                 WHERE observed_order.platform_id=us.platform_id
                   AND observed_order.user_id=us.user_id
                   AND observed_order.stake>0) BETWEEN 1 AND 3
                """
            )
            where.append(
                """
                (SELECT MIN(COALESCE(observed_order.publish_time,observed_order.created_time))
                 FROM orders observed_order
                 WHERE observed_order.platform_id=us.platform_id
                   AND observed_order.user_id=us.user_id
                   AND observed_order.stake>0)
                BETWEEN DATE_SUB(NOW(),INTERVAL 7 DAY) AND NOW()
                """
            )

        keyword = str(keyword or "").strip()
        if keyword:
            if keyword.isdigit():
                where.append("us.user_id=%s")
                params.append(int(keyword))
            else:
                where.append("us.nickname LIKE %s")
                params.append("%" + keyword + "%")

        where_sql = " AND ".join(where)

        cursor.execute(
            f"""
            SELECT COUNT(*) AS c
            FROM user_statistics us
            WHERE {where_sql}
            """,
            tuple(params)
        )
        total = intv(cursor.fetchone()["c"])

        offset = (page - 1) * page_size
        query_params = list(params) + [page_size, offset]

        cursor.execute(
            f"""
            SELECT us.*,up.avatar_url
            FROM user_statistics us
            LEFT JOIN user_profiles_ext up
                ON up.platform_id=us.platform_id
               AND up.user_id=us.user_id
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
            """,
            tuple(query_params)
        )

        fetched_rows = cursor.fetchall()
        recent_metrics = load_recent_user_metrics(
            cursor,
            [
                (row.get("platform_id"), row.get("user_id"))
                for row in fetched_rows
            ],
        )
        grades = {
            (intv(item.get("platform_id")), intv(item.get("user_id"))): item
            for item in load_user_grades(cursor)
        }
        rows = []

        for index, row in enumerate(
            fetched_rows,
            start=offset + 1
        ):
            pid = intv(row.get("platform_id"))
            uid = intv(row.get("user_id"))
            recent = recent_metrics.get((pid, uid), {})
            grade = grades.get((pid, uid), {})
            rows.append(
                {
                    "rank": index,
                    "platform_id": pid,
                    "platform_name": PLATFORMS.get(
                        pid,
                        "未知平台"
                    ),
                    "user_id": uid,
                    "nickname": row.get("nickname") or "未知用户",
                    "avatar_url": row.get("avatar_url") or "",
                    "total_orders": intv(row.get("total_orders")),
                    "settled_orders": intv(row.get("settled_orders")),
                    "hit_rate": money(row.get("hit_rate")),
                    "total_stake": money(row.get("total_stake")),
                    "total_profit": money(row.get("total_profit")),
                    "roi": money(row.get("roi")),
                    "follow_num": intv(row.get("follow_num")),
                    "expert_score": money(row.get("expert_score")),
                    "grade": grade.get("grade") or "B",
                    "auto_grade": grade.get("auto_grade") or "B",
                    "grade_score": intv(grade.get("score")),
                    "self_buy7d": money(recent.get("self_buy7d")),
                    "orders7d": intv(recent.get("orders7d")),
                    "followers7d": intv(recent.get("followers7d")),
                    "profit7d": money(recent.get("profit7d")),
                    "recent5": recent.get("recent5") or [],
                    "recent10": recent.get("recent10") or [],
                    "history_record": (
                        f"{intv(row.get('win_orders'))}胜{intv(row.get('lose_orders'))}负"
                    ),
                    "current_streak": intv(row.get("current_streak")),
                    "month_roi": recent.get("month_roi"),
                    "today_orders": intv(recent.get("today_orders")),
                    "today_followers": intv(recent.get("today_followers")),
                    "follow_amount": None,
                    "favorite_play": recent.get("favorite_play") or "",
                    "first_order_amount": recent.get("first_order_amount"),
                    "first_order_time": recent.get("first_order_time"),
                    "first_order_confidence": recent.get("first_order_confidence") or "suspected",
                    "auto_tags": recent.get("auto_tags") or [],
                }
            )

        pages = max(
            1,
            (total + page_size - 1) // page_size
        )

        return {
            "code": 200,
            "page": page,
            "pages": pages,
            "total": total,
            "data": rows,
        }

    except Exception as exc:
        return {
            "code": 500,
            "msg": str(exc),
            "data": [],
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/results")
def results(
    page: int = 1,
    page_size: int = 50,
):
    conn = None
    cursor = None

    try:
        page = max(1, page)
        page_size = max(20, min(page_size, 100))

        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        alias_map = load_aliases(cursor)
        match_references = load_caizhanyun_match_references(
            cursor,
            alias_map,
        )
        result_columns = table_columns(
            cursor,
            "match_results",
        )
        result_identity_v2 = supports_identity_v2(
            result_columns
        )
        identity_fields = (
            """
                platform_id,
                match_date,
                match_key,
                normalized_home,
                normalized_away,
                match_identity,
                identity_quality,
            """
            if result_identity_v2
            else
            """
                NULL AS platform_id,
                NULL AS match_date,
                match_key,
                NULL AS normalized_home,
                NULL AS normalized_away,
                NULL AS match_identity,
                'legacy' AS identity_quality,
            """
        )

        active_results_where = (
            "status='已结束' AND "
            "(platform_id IS NULL OR platform_id IN (1,2,3,4))"
            if result_identity_v2
            else "status='已结束'"
        )

        cursor.execute(
            f"""
            SELECT COUNT(*) AS c
            FROM match_results
            WHERE {active_results_where}
            """
        )
        total = intv(cursor.fetchone()["c"])

        offset = (page - 1) * page_size

        cursor.execute(
            f"""
            SELECT
                id,
                {identity_fields}
                match_code,
                match_name,
                home_team,
                away_team,
                home_score,
                away_score,
                half_home_score,
                half_away_score,
                status,
                finished_time
            FROM match_results
            WHERE {active_results_where}
            ORDER BY
                COALESCE(finished_time,created_time) DESC,
                id DESC
            LIMIT %s OFFSET %s
            """,
            (page_size, offset)
        )

        rows = []

        for row in cursor.fetchall():
            platform_id = intv(row.get("platform_id"))
            formatted = format_match_row(
                row,
                alias_map,
                platform_id,
                match_references,
            )

            rows.append(
                {
                    "id": intv(row.get("id")),
                    "platform_id": platform_id,
                    "match_code": formatted["match_code"],
                    "match_date": row.get("match_date"),
                    "match_key": row.get("match_key") or "",
                    "match_identity": (
                        row.get("match_identity")
                        or ""
                    ),
                    "identity_quality": (
                        row.get("identity_quality")
                        or "legacy"
                    ),
                    "home": formatted["home"],
                    "away": formatted["away"],
                    "match_name": formatted["match_name"],
                    "home_score": row.get("home_score"),
                    "away_score": row.get("away_score"),
                    "half_home_score": row.get("half_home_score"),
                    "half_away_score": row.get("half_away_score"),
                    "finished_time": row.get("finished_time"),
                }
            )

        pages = max(
            1,
            (total + page_size - 1) // page_size
        )

        return {
            "code": 200,
            "page": page,
            "pages": pages,
            "total": total,
            "data": rows,
        }

    except Exception as exc:
        return {
            "code": 500,
            "msg": str(exc),
            "data": [],
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/order/{order_id}")
def order_detail(order_id: int):
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute(
            """
            SELECT o.*
            FROM orders o
            WHERE o.id=%s
            LIMIT 1
            """,
            (order_id,)
        )

        order = cursor.fetchone()

        if not order:
            return {
                "code": 404,
                "msg": "订单不存在",
                "data": {}
            }

        grouped = load_order_matches(
            cursor,
            [order_id]
        )

        alias_map = load_aliases(cursor)
        match_references = load_caizhanyun_match_references(
            cursor,
            alias_map,
        )
        profiles = load_profiles(
            cursor,
            [(order.get("platform_id"), order.get("user_id"))],
        )

        data = enrich_order(
            order,
            grouped.get(order_id, []),
            alias_map,
            profiles,
            match_references=match_references,
        )

        return {
            "code": 200,
            "data": data
        }

    except Exception as exc:
        return {
            "code": 500,
            "msg": str(exc),
            "data": {}
        }

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()
