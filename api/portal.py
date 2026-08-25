import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta

import pymysql
from fastapi import APIRouter

from database.mysql import get_conn


router = APIRouter(
    prefix="/api/portal",
    tags=["portal-v6"]
)


PLATFORMS = {
    1: "彩站云",
    2: "州运宝",
    3: "鸿瑞",
    4: "云彩",
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
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    return re.sub(r"\s+", "", text)


def split_match_name(value):
    text = str(value or "").strip()
    for sep in (":", "：", " VS ", " vs ", " V ", " v "):
        if sep in text:
            home, away = text.split(sep, 1)
            return home.strip(), away.strip()
    return text, ""


def split_options(value):
    text = str(value or "")
    for sep in ("，", ",", "|", "、"):
        text = text.replace(sep, "/")
    return [
        item.strip()
        for item in text.split("/")
        if item.strip()
    ]


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


def table_columns(cursor, table_name):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        """,
        (table_name,)
    )
    return {row["COLUMN_NAME"] for row in cursor.fetchall()}


def load_aliases(cursor):
    alias_map = {}
    try:
        cursor.execute(
            """
            SELECT platform_id,canonical_name,alias_name
            FROM team_aliases
            """
        )
        for row in cursor.fetchall():
            pid = intv(row.get("platform_id"))
            alias = normalize_text(row.get("alias_name")).lower()
            canonical = str(row.get("canonical_name") or "").strip()
            if alias and canonical:
                alias_map[(pid, alias)] = canonical
                if pid == 0:
                    alias_map[(-1, alias)] = canonical
    except Exception:
        pass
    return alias_map


def canonical_team(alias_map, platform_id, team):
    team = str(team or "").strip()
    if not team:
        return ""
    key = normalize_text(team).lower()
    return (
        alias_map.get((intv(platform_id), key))
        or alias_map.get((0, key))
        or alias_map.get((-1, key))
        or team
    )


def canonical_match(alias_map, platform_id, match_name):
    home, away = split_match_name(match_name)
    home = canonical_team(alias_map, platform_id, home)
    away = canonical_team(alias_map, platform_id, away)

    if home and away:
        return {
            "home": home,
            "away": away,
            "display": f"{home} VS {away}",
            "key": (
                normalize_text(home).lower()
                + "|"
                + normalize_text(away).lower()
            ),
        }

    return {
        "home": home,
        "away": away,
        "display": home or str(match_name or ""),
        "key": normalize_text(match_name).lower(),
    }


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


def load_match_schedule(cursor):
    by_code = {}
    by_name = {}

    try:
        columns = table_columns(cursor, "matches")
        if not columns:
            return by_code, by_name

        time_col = next(
            (
                value
                for value in (
                    "deadline_time",
                    "stop_time",
                    "end_sale_time",
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

        if not time_col:
            return by_code, by_name

        code_col = next(
            (
                value
                for value in ("match_code", "week_name", "code")
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

        select_fields = [f"`{time_col}` AS deadline_value"]
        select_fields.append(
            f"`{code_col}` AS match_code"
            if code_col
            else "'' AS match_code"
        )
        select_fields.append(
            f"`{name_col}` AS match_name"
            if name_col
            else "'' AS match_name"
        )

        cursor.execute(
            f"""
            SELECT {",".join(select_fields)}
            FROM matches
            ORDER BY `{time_col}` DESC
            LIMIT 1000
            """
        )

        for row in cursor.fetchall():
            deadline = parse_datetime(row.get("deadline_value"))
            if not deadline:
                continue

            code = normalize_text(row.get("match_code"))
            name = normalize_text(row.get("match_name")).lower()

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

    cursor.execute(
        f"""
        SELECT
            om.id,
            om.order_id,
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
        LEFT JOIN match_results mr
            ON mr.match_name=om.match_name
        WHERE om.order_id IN ({placeholders})
        ORDER BY om.order_id DESC,om.id ASC
        """,
        tuple(order_ids),
    )

    for row in cursor.fetchall():
        grouped[intv(row.get("order_id"))].append(row)

    return grouped


def match_deadline(match_row, schedule_by_code, schedule_by_name):
    direct = parse_datetime(match_row.get("deadline_time"))
    if direct:
        return direct

    code = normalize_text(match_row.get("match_code"))
    if code and code in schedule_by_code:
        return schedule_by_code[code]

    name = normalize_text(match_row.get("match_name")).lower()
    if name and name in schedule_by_name:
        return schedule_by_name[name]

    return None


def is_order_unexpired(
    order,
    matches,
    now,
    schedule_by_code,
    schedule_by_name
):
    deadlines = []

    for match in matches:
        deadline = match_deadline(
            match,
            schedule_by_code,
            schedule_by_name
        )
        if deadline:
            deadlines.append(deadline)

    if deadlines:
        return min(deadlines) > now

    return str(order.get("result") or "") == "待开奖"


def format_match_row(row, alias_map, platform_id):
    match = canonical_match(
        alias_map,
        platform_id,
        row.get("match_name")
    )

    return {
        "id": intv(row.get("id")),
        "match_code": row.get("match_code") or "",
        "home": match["home"],
        "away": match["away"],
        "match_name": match["display"],
        "league": row.get("league") or "",
        "play_type": row.get("play_type") or "",
        "selection": row.get("selection") or "",
        "options": split_options(row.get("selection")),
        "handicap": intv(row.get("handicap")),
        "result": row.get("bet_result") or "待开奖",
        "home_score": row.get("home_score"),
        "away_score": row.get("away_score"),
        "half_home_score": row.get("half_home_score"),
        "half_away_score": row.get("half_away_score"),
    }


def enrich_order(order, matches, alias_map, profiles):
    platform_id = intv(order.get("platform_id"))
    user_id = intv(order.get("user_id"))
    profile = profiles.get((platform_id, user_id), {})

    formatted_matches = [
        format_match_row(
            row,
            alias_map,
            platform_id
        )
        for row in matches
    ]

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
        "publish_time": (
            order.get("publish_time")
            or order.get("created_time")
        ),
        "pass_summary": (
            order.get("pass_summary")
            or order.get("play_type")
            or ""
        ),
        "pass_composition": order.get("pass_composition") or "",
        "bet_count": intv(order.get("bet_count")),
        "odds_text": order.get("odds_text") or "",
        "stake": money(order.get("stake")),
        "follow_num": intv(order.get("follow_num")),
        "result": order.get("result") or "待开奖",
        "profit": money(order.get("profit")),
        "bonus": money(order.get("platform_bonus")),
        "matches": formatted_matches,
    }


def build_current_context(cursor):
    cursor.execute("SELECT NOW() AS now_time")
    now = cursor.fetchone()["now_time"]
    target_day = current_event_day(now)

    alias_map = load_aliases(cursor)
    profiles = load_profiles(cursor)
    schedule_by_code, schedule_by_name = load_match_schedule(cursor)

    orders = load_orders_for_day(
        cursor,
        target_day,
        pending_only=True
    )

    grouped = load_order_matches(
        cursor,
        [intv(order.get("id")) for order in orders]
    )

    unexpired = []

    for order in orders:
        order_id = intv(order.get("id"))
        order_matches = grouped.get(order_id, [])

        if is_order_unexpired(
            order,
            order_matches,
            now,
            schedule_by_code,
            schedule_by_name,
        ):
            unexpired.append((order, order_matches))

    return {
        "now": now,
        "day": target_day,
        "alias_map": alias_map,
        "profiles": profiles,
        "unexpired": unexpired,
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

        metrics = {
            "yesterday_plans": len(yesterday_orders),
            "yesterday_wins": sum(
                1
                for order in yesterday_orders
                if str(order.get("result") or "") == "赢"
            ),
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
                    profiles
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

        where = ["1=1"]
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
        profiles = load_profiles(cursor)

        data = [
            enrich_order(
                order,
                grouped.get(intv(order.get("id")), []),
                alias_map,
                profiles,
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
                platform_id
            )

            key = (
                formatted["match_code"]
                or formatted["match_name"]
            )

            if key not in match_groups:
                match_groups[key] = {
                    "match_code": formatted["match_code"],
                    "home": formatted["home"],
                    "away": formatted["away"],
                    "match_name": formatted["match_name"],
                    "league": formatted["league"],
                    "option_counts": defaultdict(int),
                    "platform_counts": defaultdict(
                        lambda: defaultdict(int)
                    ),
                }

            group = match_groups[key]

            for option in split_options(
                formatted["selection"]
            ):
                group["option_counts"][option] += 1
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
                "match_code": group["match_code"],
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
                    row["match_code"]
                    or row["match_name"]
                )

                if key not in match_map:
                    match_map[key] = {
                        "match_code": row["match_code"],
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

        where = ["1=1"]
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

        cursor.execute(
            """
            SELECT COUNT(*) AS c
            FROM match_results
            WHERE status='已结束'
            """
        )
        total = intv(cursor.fetchone()["c"])

        offset = (page - 1) * page_size

        cursor.execute(
            """
            SELECT
                id,
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
            WHERE status='已结束'
            ORDER BY
                COALESCE(finished_time,created_time) DESC,
                id DESC
            LIMIT %s OFFSET %s
            """,
            (page_size, offset)
        )

        rows = []

        for row in cursor.fetchall():
            split_home, split_away = split_match_name(
                row.get("match_name")
            )

            home = canonical_team(
                alias_map,
                0,
                row.get("home_team") or split_home
            )
            away = canonical_team(
                alias_map,
                0,
                row.get("away_team") or split_away
            )

            rows.append(
                {
                    "id": intv(row.get("id")),
                    "match_code": row.get("match_code") or "",
                    "home": home,
                    "away": away,
                    "match_name": (
                        f"{home} VS {away}"
                        if home and away
                        else row.get("match_name")
                    ),
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
        profiles = load_profiles(cursor)

        data = enrich_order(
            order,
            grouped.get(order_id, []),
            alias_map,
            profiles
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
