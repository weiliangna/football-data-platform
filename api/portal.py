import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

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
from common.pass_utils import normalize_pass_summary
from common.platform_registry import (
    ACTIVE_PLATFORM_IDS,
    default_platform_metadata,
)
from database.mysql import get_conn


router = APIRouter(
    prefix="/api/portal",
    tags=["portal-v6"]
)


PLATFORMS = {
    platform_id: item["name"]
    for platform_id, item in default_platform_metadata().items()
}

FOUR_PLAYS = (
    "胜平负",
    "让球胜平负",
    "半全场",
    "比分",
)


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
        return value

    text = str(value or "").strip()
    if not text:
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


def load_aliases(cursor):
    try:
        return load_team_aliases(cursor)
    except Exception:
        return {}


def load_hongrui_match_references(cursor, alias_map):
    references = {}
    team_candidates = defaultdict(dict)
    try:
        cursor.execute(
            """
            SELECT
                om.match_code,
                om.match_name,
                om.league,
                DATE(
                    DATE_SUB(
                        COALESCE(o.publish_time,o.created_time),
                        INTERVAL 6 HOUR
                    )
                ) AS event_day
            FROM order_matches om
            INNER JOIN orders o ON o.id=om.order_id
            WHERE o.platform_id=3
              AND om.match_name IS NOT NULL
              AND om.match_name<>''
            ORDER BY om.id DESC
            LIMIT 5000
            """
        )
        for row in cursor.fetchall() or []:
            match = canonical_match(
                alias_map,
                3,
                row.get("match_name"),
            )
            key = (
                match["normalized_home"],
                match["normalized_away"],
            )
            if not all(key):
                continue
            reference = {
                "match_code": row.get("match_code") or "",
                "home": match["home"],
                "away": match["away"],
                "match_name": match["display"],
                "league": row.get("league") or "",
                "canonical_display_key": "|".join(key),
            }
            event_day = str(row.get("event_day") or "")
            if event_day:
                references.setdefault(
                    ("date", event_day, *key),
                    reference,
                )
            code = str(row.get("match_code") or "").strip()
            if code:
                team_candidates[key].setdefault(code, reference)
        for key, candidates in team_candidates.items():
            if len(candidates) == 1:
                references[("teams", *key)] = next(
                    iter(candidates.values())
                )
    except Exception:
        return {}
    return references

def load_profiles(cursor):
    result = {}
    try:
        cursor.execute(
            """
            SELECT platform_id,user_id,nickname,avatar_url
            FROM user_profiles_ext
            """
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


def load_user_statistics(cursor):
    result = {}
    try:
        cursor.execute(
            """
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
            """
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
    hongrui_references=None,
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
        or row.get("order_event_day")
    )
    if not reference_day and row.get("finished_time"):
        parsed_finished = parse_datetime(row.get("finished_time"))
        reference_day = parsed_finished.date() if parsed_finished else None
    references = hongrui_references or {}
    reference = references.get(
        ("date", str(reference_day), *normalized_pair),
        {},
    )
    if not reference:
        reference = references.get(
            ("teams", *normalized_pair),
            references.get(normalized_pair, {}),
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
        "match_date": row.get("match_date"),
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
    hongrui_references=None,
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
            hongrui_references,
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
        "deadline_time": deadline_state["deadline_time"],
        "deadline_source": deadline_state["deadline_source"],
        "deadline_exact": bool(deadline_state["deadline_exact"]),
        "matches": formatted_matches,
    }



def build_current_context(cursor):
    cursor.execute("SELECT NOW() AS now_time")
    now = cursor.fetchone()["now_time"]
    target_day = current_event_day(now)

    alias_map = load_aliases(cursor)
    hongrui_references = load_hongrui_match_references(
        cursor,
        alias_map,
    )
    profiles = load_profiles(cursor)
    schedule_by_code, schedule_by_name = load_match_schedule(cursor)

    orders = load_orders_for_day(
        cursor,
        target_day,
        pending_only=True,
    )
    grouped = load_order_matches(
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

    return {
        "now": now,
        "day": target_day,
        "alias_map": alias_map,
        "hongrui_references": hongrui_references,
        "profiles": profiles,
        "unexpired": unexpired,
        "deadline_summary": deadline_summary,
    }


@router.get("/dashboard")
def dashboard():
    conn = None
    cursor = None

    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        ctx = build_current_context(cursor)
        target_day = ctx["day"]
        now = ctx["now"]
        alias_map = ctx["alias_map"]
        hongrui_references = ctx["hongrui_references"]
        profiles = ctx["profiles"]
        unexpired = ctx["unexpired"]

        yesterday = target_day - timedelta(days=1)

        yesterday_orders = load_orders_for_day(
            cursor,
            yesterday,
            pending_only=False
        )
        today_all = load_orders_for_day(
            cursor,
            target_day,
            pending_only=False
        )
        yesterday_settled = [
            order
            for order in yesterday_orders
            if str(order.get("result") or "") != "待开奖"
        ]

        metrics = {
            "yesterday_plans": len(yesterday_orders),
            "yesterday_wins": sum(
                1
                for order in yesterday_orders
                if str(order.get("result") or "") == "赢"
            ),
            "yesterday_lost": sum(
                1
                for order in yesterday_settled
                if str(order.get("result") or "") == "输"
            ),
            "yesterday_settled": len(yesterday_settled),
            "today_plans": len(today_all),
            "today_followers": sum(
                intv(order.get("follow_num"))
                for order in today_all
            ),
            "today_amount": round(
                sum(
                    money(order.get("stake"))
                    for order in today_all
                ),
                2
            ),
            "unexpired_plans": len(unexpired),
        }

        platform_rows = []
        for platform_id in (1, 3, 2, 4):
            rows = [
                order
                for order in today_all
                if intv(order.get("platform_id")) == platform_id
            ]
            platform_rows.append(
                {
                    "platform_id": platform_id,
                    "platform_name": PLATFORMS[platform_id],
                    "order_count": len(rows),
                    "amount": round(
                        sum(
                            money(order.get("stake"))
                            for order in rows
                        ),
                        2
                    ),
                    "followers": sum(
                        intv(order.get("follow_num"))
                        for order in rows
                    ),
                }
            )

        user_groups = {}

        for order, matches in unexpired:
            platform_id = intv(order.get("platform_id"))
            user_id = intv(order.get("user_id"))
            key = (platform_id, user_id)

            if key not in user_groups:
                profile = profiles.get(key, {})
                user_groups[key] = {
                    "platform_id": platform_id,
                    "platform_name": PLATFORMS.get(
                        platform_id,
                        f"平台{platform_id}"
                    ),
                    "user_id": user_id,
                    "nickname": (
                        order.get("nickname")
                        or profile.get("nickname")
                        or "未知用户"
                    ),
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
                enrich_order(
                    order,
                    matches,
                    alias_map,
                    profiles,
                    hongrui_references=hongrui_references,
                )
            )

        for key, group in user_groups.items():
            cursor.execute(
                """
                SELECT total_orders,win_orders,lose_orders,hit_rate
                FROM user_statistics
                WHERE platform_id=%s AND user_id=%s
                LIMIT 1
                """,
                key
            )

            stat = cursor.fetchone() or {}
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
        hongrui_references = load_hongrui_match_references(
            cursor,
            alias_map,
        )
        profiles = load_profiles(cursor)
        statistics = load_user_statistics(cursor)

        data = [
            enrich_order(
                order,
                grouped.get(intv(order.get("id")), []),
                alias_map,
                profiles,
                statistics,
                hongrui_references,
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
        hongrui_references = load_hongrui_match_references(
            cursor,
            alias_map,
        )
        profiles = load_profiles(cursor)
        profile = profiles.get((platform_id, user_id), {})

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
            LIMIT 100
            """,
            (platform_id, user_id)
        )
        orders = cursor.fetchall()

        grouped = load_order_matches(
            cursor,
            [intv(order.get("id")) for order in orders]
        )

        data_orders = [
            enrich_order(
                order,
                grouped.get(intv(order.get("id")), []),
                alias_map,
                profiles,
                hongrui_references=hongrui_references,
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
    hongrui_references = ctx["hongrui_references"]
    match_groups = {}
    platform_total = defaultdict(int)

    for order, matches in ctx["unexpired"]:
        platform_id = intv(order.get("platform_id"))

        for row in matches:
            if str(row.get("play_type") or "") != play_type:
                continue

            formatted = format_match_row(
                row,
                alias_map,
                platform_id,
                hongrui_references,
            )

            key = portal_match_group_key(
                formatted,
                platform_id,
            )

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
                    "platform_counts": defaultdict(
                        lambda: defaultdict(int)
                    ),
                }

            group = match_groups[key]

            for option in split_options(
                formatted["selection"]
            ):
                group["option_counts"][option] += 1
                odds = option_odds(row, option)
                if odds and option not in group["option_odds"]:
                    group["option_odds"][option] = odds
                group["platform_counts"][platform_id][option] += 1
                platform_total[(platform_id, option)] += 1

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
                    "platforms": {
                        str(pid): group["platform_counts"][pid].get(
                            option,
                            0
                        )
                        for pid in (1, 3, 2, 4)
                    },
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

    platform_summary = []

    for platform_id in (1, 3, 2, 4):
        option_rows = [
            {
                "option": option,
                "count": count,
            }
            for (pid, option), count
            in platform_total.items()
            if pid == platform_id
        ]

        option_rows.sort(
            key=lambda item: item["count"],
            reverse=True
        )

        platform_summary.append(
            {
                "platform_id": platform_id,
                "platform_name": PLATFORMS[platform_id],
                "total_items": sum(
                    item["count"]
                    for item in option_rows
                ),
                "options": option_rows,
            }
        )

    return {
        "play_type": play_type,
        "focus": focus,
        "matches": matches,
        "platform_summary": platform_summary,
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

        ctx = build_current_context(cursor)
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

        ctx = build_current_context(cursor)

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

        keyword = str(keyword or "").strip()
        if keyword:
            like = "%" + keyword + "%"
            where.append(
                """
                (
                    us.nickname LIKE %s
                    OR CAST(us.user_id AS CHAR) LIKE %s
                )
                """
            )
            params.extend([like, like])

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

        rows = []

        for index, row in enumerate(
            cursor.fetchall(),
            start=offset + 1
        ):
            pid = intv(row.get("platform_id"))
            rows.append(
                {
                    "rank": index,
                    "platform_id": pid,
                    "platform_name": PLATFORMS.get(
                        pid,
                        "未知平台"
                    ),
                    "user_id": intv(row.get("user_id")),
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
        hongrui_references = load_hongrui_match_references(
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
                hongrui_references,
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
        hongrui_references = load_hongrui_match_references(
            cursor,
            alias_map,
        )
        profiles = load_profiles(cursor)

        data = enrich_order(
            order,
            grouped.get(order_id, []),
            alias_map,
            profiles,
            hongrui_references=hongrui_references,
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
