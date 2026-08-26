import os
import sys
import json
import argparse
from collections import defaultdict

import requests
import pymysql


ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if ROOT not in sys.path:
    sys.path.insert(
        0,
        ROOT
    )


from common.match_identity import (
    build_match_identity,
    load_team_aliases,
    supports_identity_v2,
    table_columns,
)
from common.platform_field_mapping import (
    extract_hongrui_source_fields,
    resolve_hongrui_handicap,
)
from database.mysql import get_conn


PLATFORM_ID = 3

API_BASE = "https://playerhr.fxgzht.com.cn"

FOLLOW_ORDER_URL = (
    API_BASE
    +
    "/api/follow_order"
)

FOLLOW_DETAIL_URL = (
    API_BASE
    +
    "/api/follow_detail"
)


TOKEN = os.getenv(
    "HONGRUI_TOKEN",
    ""
).strip()


session = requests.Session()


session.headers.update({

    "Accept":
        "*/*",

    "Content-Type":
        "application/json",

    "Origin":
        "http://playerhf.fxgzht.com.cn",

    "Referer":
        "http://playerhf.fxgzht.com.cn/",

    "User-Agent":
        (
            "Mozilla/5.0 "
            "(iPhone; CPU iPhone OS 18_7 like Mac OS X) "
            "AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) "
            "Version/26.0.1 Mobile/15E148 Safari/604.1"
        ),

    "Accept-Language":
        "zh-CN,zh-Hans;q=0.9"
})


if TOKEN:

    session.headers[
        "Authorization"
    ] = TOKEN


# ============================================================
# 数字
# ============================================================

def to_float(
    value,
    default=0.0
):

    try:

        if value is None:
            return default


        text = str(
            value
        ).strip()


        text = text.replace(
            "%",
            ""
        )


        if text in (
            "",
            "-",
            "--"
        ):
            return default


        return float(
            text
        )


    except Exception:

        return default


def to_int(
    value,
    default=0
):

    try:

        return int(
            float(value)
        )

    except Exception:

        return default


# ============================================================
# HTTP
# ============================================================

def post_json(
    url,
    payload
):

    if not TOKEN:

        raise RuntimeError(
            "没有设置 HONGRUI_TOKEN"
        )


    response = session.post(
        url,
        json=payload,
        timeout=20
    )


    response.raise_for_status()


    try:

        data = response.json()

    except Exception:

        raise RuntimeError(
            "鸿瑞接口不是JSON响应: "
            +
            response.text[:300]
        )


    if to_int(
        data.get("code"),
        0
    ) != 1:

        raise RuntimeError(
            "鸿瑞接口返回失败: "
            +
            str(
                data.get("msg")
                or data
            )
        )


    return data


# ============================================================
# 跟单大厅
# ============================================================

def get_follow_orders(
    page=1,
    list_type=1
):

    result = post_json(
        FOLLOW_ORDER_URL,
        {
            "page": page,
            "type": 0,
            "list_type": list_type
        }
    )


    data = (
        result.get("data")
        or {}
    )


    return (
        data.get("data")
        or []
    )


def get_all_follow_orders(
    start_page=1,
    max_pages=100,
):

    orders = []
    seen = set()

    for page in range(
        max(int(start_page), 1),
        max(int(start_page), 1) + max(int(max_pages), 1),
    ):

        page_orders = get_follow_orders(page=page)
        added = 0

        for item in page_orders:

            order_id = str(
                item.get("order_id")
                or item.get("id")
                or ""
            ).strip()

            if not order_id or order_id in seen:
                continue

            seen.add(order_id)
            orders.append(item)
            added += 1

        if not page_orders or added == 0:
            break

    return orders


# ============================================================
# 订单详情
# ============================================================

def get_follow_detail(
    order_id
):

    return post_json(
        FOLLOW_DETAIL_URL,
        {
            "order_id":
                to_int(
                    order_id
                )
        }
    )


# ============================================================
# 选项标准化
# ============================================================

def normalize_option(
    market,
    option
):

    market = str(
        market
        or ""
    ).strip()


    option = str(
        option
        or ""
    ).strip()


    if market == "胜平负":

        return {
            "胜": "主胜",
            "平": "平",
            "负": "主负"
        }.get(
            option,
            option
        )


    if market == "让球胜平负":

        if option in (
            "让胜",
            "让平",
            "让负"
        ):
            return option


        return {
            "胜": "让胜",
            "平": "让平",
            "负": "让负"
        }.get(
            option,
            option
        )


    if market == "总进球":

        if option == "7":

            return "7+球"


        if option.isdigit():

            return (
                option
                +
                "球"
            )


    return option


# ============================================================
# 解析 follow_detail
# ============================================================

def parse_detail(
    raw,
    alias_map=None,
):

    data = (
        raw.get("data")
        or {}
    )


    head = (
        data.get("head")
        or {}
    )


    message = (
        data.get("order_message")
        or {}
    )


    lottery_list = (
        message.get("lottery_list")
        or []
    )


    matches = []


    for match in lottery_list:

        home = str(
            match.get("home")
            or ""
        ).strip()


        away = str(
            match.get("away")
            or ""
        ).strip()


        week_name = str(
            match.get("week_name")
            or ""
        ).strip()


        match_name = (
            home
            +
            ":"
            +
            away
        )


        grouped = defaultdict(
            lambda: {
                "options": [],
                "odds": [],
                "option_detail": []
            }
        )


        for play in (
            match.get("playing")
            or []
        ):

            market = str(
                play.get("name")
                or ""
            ).strip()


            handicap = resolve_hongrui_handicap(
                market,
                play.get("rq_number"),
            )


            option = normalize_option(
                market,
                play.get("odds_name")
            )


            odd = to_float(
                play.get("odds"),
                0
            )


            key = (
                market,
                handicap
            )


            if (
                option
                and
                option not in
                grouped[key][
                    "options"
                ]
            ):

                grouped[key][
                    "options"
                ].append(
                    option
                )


            if odd > 0:

                grouped[key][
                    "odds"
                ].append(
                    odd
                )


            if option:

                detail_item = {
                    "name":
                        option,

                    "odds":
                        (
                            odd
                            if odd > 0
                            else None
                        )
                }


                exists = False


                for old in grouped[key][
                    "option_detail"
                ]:

                    if (
                        old.get("name")
                        ==
                        detail_item["name"]
                    ):

                        exists = True

                        if (
                            old.get("odds")
                            is None
                            and
                            detail_item[
                                "odds"
                            ]
                            is not None
                        ):

                            old["odds"] = (
                                detail_item[
                                    "odds"
                                ]
                            )

                        break


                if not exists:

                    grouped[key][
                        "option_detail"
                    ].append(
                        detail_item
                    )


        for (
            market,
            handicap
        ), group in grouped.items():
            identity = build_match_identity(
                PLATFORM_ID,
                source_match_code=week_name,
                match_name=match_name,
                home_team=home,
                away_team=away,
                alias_map=alias_map,
            )

            matches.append({

                "week_name":
                    week_name,

                "home":
                    home,

                "away":
                    away,

                "match_name":
                    match_name,

                "market":
                    market,

                "handicap":
                    (
                        handicap
                        if
                        market
                        ==
                        "让球胜平负"
                        else 0
                    ),

                "options":
                    group[
                        "options"
                    ],

                "odds":
                    group[
                        "odds"
                    ],

                "option_detail":
                    group[
                        "option_detail"
                    ],

                "identity_candidate":
                    week_name,

                "match_identity":
                    identity["match_identity"],

                "identity_complete":
                    False,

                "match_date":
                    None,

                "match_key":
                    identity["match_key"],

                "normalized_home":
                    identity["normalized_home"],

                "normalized_away":
                    identity["normalized_away"],

                "identity_quality":
                    "incomplete"
            })


    return {

        "head":
            head,

        "message":
            message,

        "matches":
            matches,

        "follow_count":
            to_int(
                data.get(
                    "follow_count"
                ),
                0
            ),

        "source_fields":
            extract_hongrui_source_fields(raw)
    }


# ============================================================
# 推荐文字
# ============================================================

def build_selection(
    matches
):

    result = []


    for item in matches:

        options = "/".join(
            item.get(
                "options"
            )
            or []
        )


        result.append(
            (
                item.get(
                    "match_name",
                    ""
                )
                +
                " → "
                +
                item.get(
                    "market",
                    ""
                )
                +
                "："
                +
                options
            )
        )


    return "；".join(
        result
    )


# ============================================================
# 赔率范围
# ============================================================

def build_odds_text(
    matches
):

    values = []


    for item in matches:

        values.extend(
            item.get(
                "odds"
            )
            or []
        )


    if not values:

        return None


    minimum = min(
        values
    )


    maximum = max(
        values
    )


    if minimum == maximum:

        return (
            f"{minimum:.2f}"
        )


    return (
        f"{minimum:.2f}"
        "~"
        f"{maximum:.2f}"
    )


# ============================================================
# 预览
# ============================================================

def preview_order(
    list_item,
    raw_detail,
    alias_map=None,
):

    parsed = parse_detail(
        raw_detail,
        alias_map=alias_map,
    )


    head = parsed[
        "head"
    ]


    message = parsed[
        "message"
    ]


    matches = parsed[
        "matches"
    ]


    list_user = (
        list_item.get("user")
        or {}
    )


    list_detail = (
        list_item.get(
            "order_detail"
        )
        or {}
    )


    order_id = list_item.get(
        "order_id"
    )


    user_id = (
        head.get("user_id")
        or
        list_item.get("user_id")
    )


    nickname = (
        head.get("user_name")
        or
        list_user.get("user_name")
        or ""
    )


    stake = to_float(
        head.get(
            "purchase_amount"
        )
        or
        list_item.get(
            "purchase_amount"
        ),
        0
    )


    pass_summary = (
        message.get("customs")
        or
        list_detail.get("customs")
        or ""
    )


    expected_bonus = to_float(
        list_detail.get(
            "predictive_bonus"
        ),
        0
    )


    print()
    print(
        "=" * 90
    )


    print(
        "鸿瑞订单:",
        order_id
    )


    print(
        "用户:",
        user_id,
        nickname
    )


    print(
        "金额:",
        stake
    )


    print(
        "过关:",
        pass_summary
    )


    print(
        "预计回报:",
        expected_bonus
    )


    print(
        "推荐:",
        build_selection(
            matches
        )
    )


    print(
        "赔率范围:",
        build_odds_text(
            matches
        )
    )


    print(
        "跟单人数:",
        parsed[
            "follow_count"
        ]
    )


    for index, item in enumerate(
        matches,
        1
    ):

        print()

        print(
            f"第{index}项"
        )


        print(
            "场次:",
            item[
                "week_name"
            ]
        )
        print(
            "比赛:",
            item[
                "match_name"
            ]
        )


        print(
            "玩法:",
            item[
                "market"
            ]
        )


        print(
            "让球:",
            item[
                "handicap"
            ]
        )


        for option in item[
            "option_detail"
        ]:

            print(
                "选项:",
                option.get("name"),
                "赔率:",
                option.get("odds")
            )


def save_user_avatar(
    cursor,
    user_id,
    nickname,
    avatar_url,
):
    avatar = str(avatar_url or "").strip()

    if user_id in (None, "", 0) or not avatar:
        return False

    cursor.execute(
        """
        INSERT INTO user_profiles_ext
        (
            platform_id,
            user_id,
            nickname,
            avatar_url,
            source
        )
        VALUES
        (3,%s,%s,%s,'hongrui_detail')
        ON DUPLICATE KEY UPDATE
            nickname=CASE
                WHEN VALUES(nickname)<>''
                THEN VALUES(nickname)
                ELSE nickname
            END,
            avatar_url=CASE
                WHEN VALUES(avatar_url)<>''
                THEN VALUES(avatar_url)
                ELSE avatar_url
            END,
            source='hongrui_detail',
            updated_time=NOW()
        """,
        (
            user_id,
            str(nickname or ""),
            avatar,
        ),
    )
    return True


# ============================================================
# 保存订单
# ============================================================

def save_order(
    cursor,
    list_item,
    raw_detail,
    alias_map=None,
    identity_v2=False,
):

    parsed = parse_detail(
        raw_detail
    )


    head = parsed[
        "head"
    ]


    message = parsed[
        "message"
    ]


    matches = parsed[
        "matches"
    ]


    list_user = (
        list_item.get("user")
        or {}
    )


    list_detail = (
        list_item.get(
            "order_detail"
        )
        or {}
    )


    source_fields = extract_hongrui_source_fields(
        raw_detail,
        list_item,
    )


    platform_order_id = str(
        list_item.get(
            "order_id"
        )
        or ""
    )


    if not platform_order_id:

        return False


    user_id = to_int(
        head.get("user_id")
        or
        list_item.get("user_id"),
        0
    )


    nickname = str(
        head.get("user_name")
        or
        list_user.get("user_name")
        or ""
    ).strip()


    stake = to_float(
        head.get(
            "purchase_amount"
        )
        or
        list_item.get(
            "purchase_amount"
        ),
        0
    )


    pass_summary = str(
        message.get("customs")
        or
        list_detail.get("customs")
        or ""
    ).strip()


    selection = build_selection(
        matches
    )


    odds_text = build_odds_text(
        matches
    )


    declaration = (
        head.get("declaration")
        or
        list_detail.get(
            "declaration"
        )
        or ""
    )


    # head.fans_count is a user-level follower candidate.
    # orders.follow_num is the order-level follow count, so the two
    # fields must not be conflated without a schema designed for it.
    follow_num = (
        parsed.get(
            "follow_count"
        )
        or
        to_int(
            list_item.get(
                "current_count"
            ),
            0
        )
    )


    hit_rate = to_float(
        list_item.get(
            "seven_bonus_odds"
        ),
        0
    )


    if (
        hit_rate > 0
        and
        hit_rate <= 1
    ):

        hit_rate = (
            hit_rate
            *
            100
        )


    profitability = to_float(
        list_item.get(
            "profit_rate"
        ),
        0
    )


    lot_multi = to_float(
        message.get(
            "multiple"
        ),
        0
    )


    expected_bonus = to_float(
        list_detail.get(
            "predictive_bonus"
        ),
        0
    )


    first_match = (
        matches[0]
        if matches
        else {}
    )


    match_name = first_match.get(
        "match_name"
    )


    league = (
        message.get("cate_name")
        or
        list_detail.get(
            "cate_name"
        )
        or
        "竞彩足球"
    )


    order_handicap = 0


    for item in matches:

        if (
            item.get(
                "market"
            )
            ==
            "让球胜平负"
        ):

            order_handicap = to_int(
                item.get(
                    "handicap"
                ),
                0
            )

            break


    raw_after_lottery = (
        list_detail.get(
            "after_lottery"
        )
    )


    if isinstance(
        raw_after_lottery,
        (
            dict,
            list
        )
    ):

        raw_after_lottery = json.dumps(
            raw_after_lottery,
            ensure_ascii=False
        )


    # ========================================================
    # 查本地订单
    # ========================================================

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
            PLATFORM_ID,
            platform_order_id
        )
    )


    existing = cursor.fetchone()


    if existing:

        local_order_id = (
            existing[
                "id"
            ]
        )


        #
        # 注意：
        #
        # 这里不更新 result / profit
        # 防止采集器覆盖已经结算的数据
        #

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

                bet_code=%s,

                odds_text=%s,

                stake=%s,

                declaration=%s,

                hit_rate=%s,

                profitability=%s,

                follow_num=%s,

                lot_multi=%s,

                expected_bonus=%s,

                handicap=%s

            WHERE id=%s
            """,
            (
                user_id,

                nickname,

                match_name,

                league,

                pass_summary,

                pass_summary,

                selection,

                raw_after_lottery,

                odds_text,

                stake,

                declaration,

                hit_rate,

                profitability,

                follow_num,

                lot_multi,

                expected_bonus,

                order_handicap,

                local_order_id
            )
        )


    else:

        cursor.execute(
            """
            INSERT INTO orders
            (
                platform_id,

                user_id,

                nickname,

                platform_order_id,

                match_name,

                league,

                play_type,

                pass_summary,

                selection,

                bet_code,

                odds_text,

                stake,

                declaration,

                hit_rate,

                profitability,

                follow_num,

                lot_multi,

                expected_bonus,

                handicap,

                result,

                profit
            )

            VALUES
            (
                %s,%s,%s,%s,
                %s,%s,
                %s,%s,
                %s,%s,%s,
                %s,%s,
                %s,%s,%s,
                %s,%s,%s,
                '待开奖',
                0
            )
            """,
            (
                PLATFORM_ID,

                user_id,

                nickname,

                platform_order_id,

                match_name,

                league,

                pass_summary,

                pass_summary,

                selection,

                raw_after_lottery,

                odds_text,

                stake,

                declaration,

                hit_rate,

                profitability,

                follow_num,

                lot_multi,

                expected_bonus,

                order_handicap
            )
        )


        local_order_id = (
            cursor.lastrowid
        )


    # ========================================================
    # 拆单
    #
    # 不再 DELETE 重建；已有 result/profit 保持不变。
    # 鸿瑞没有已验证比赛日期，因此 identity_quality 保持
    # incomplete，match_date 保持 NULL，不能建立唯一约束。
    # ========================================================

    for item in matches:
        option_text = "/".join(
            item.get("options")
            or []
        )
        option_json = json.dumps(
            item.get("option_detail")
            or [],
            ensure_ascii=False
        )

        if identity_v2:
            cursor.execute(
                """
                SELECT id,result
                FROM order_matches
                WHERE order_id=%s
                  AND platform_id=%s
                  AND match_date IS NULL
                  AND match_code=%s
                  AND match_key=%s
                  AND play_type=%s
                  AND handicap=%s
                ORDER BY id ASC
                LIMIT 1
                """,
                (
                    local_order_id,
                    PLATFORM_ID,
                    item.get("week_name") or "",
                    item.get("match_key") or "",
                    item.get("market"),
                    item.get("handicap") or 0,
                ),
            )
            old_match = cursor.fetchone()
        else:
            cursor.execute(
                """
                SELECT id,result
                FROM order_matches
                WHERE order_id=%s
                  AND match_name=%s
                  AND play_type=%s
                  AND handicap=%s
                ORDER BY id ASC
                LIMIT 1
                """,
                (
                    local_order_id,
                    item.get("match_name"),
                    item.get("market"),
                    item.get("handicap") or 0,
                ),
            )
            old_match = cursor.fetchone()

        if old_match:
            if identity_v2:
                cursor.execute(
                    """
                    UPDATE order_matches
                    SET
                        platform_id=%s,
                        match_code=%s,
                        match_key=%s,
                        match_date=NULL,
                        normalized_home=%s,
                        normalized_away=%s,
                        match_identity=%s,
                        identity_quality='incomplete',
                        league=%s,
                        selection=%s,
                        option_detail=%s,
                        handicap=%s
                    WHERE id=%s
                    """,
                    (
                        PLATFORM_ID,
                        item.get("week_name") or "",
                        item.get("match_key") or "",
                        item.get("normalized_home") or "",
                        item.get("normalized_away") or "",
                        item.get("match_identity") or "",
                        league,
                        option_text,
                        option_json,
                        item.get("handicap") or 0,
                        old_match["id"],
                    ),
                )
            else:
                cursor.execute(
                    """
                    UPDATE order_matches
                    SET
                        match_code=%s,
                        league=%s,
                        selection=%s,
                        option_detail=%s,
                        handicap=%s
                    WHERE id=%s
                    """,
                    (
                        item.get("week_name") or "",
                        league,
                        option_text,
                        option_json,
                        item.get("handicap") or 0,
                        old_match["id"],
                    ),
                )
            continue

        if identity_v2:
            cursor.execute(
                """
                INSERT INTO order_matches
                (
                    order_id,
                    platform_id,
                    match_code,
                    match_name,
                    match_key,
                    match_date,
                    normalized_home,
                    normalized_away,
                    match_identity,
                    identity_quality,
                    league,
                    play_type,
                    selection,
                    option_detail,
                    handicap,
                    result,
                    profit
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,NULL,%s,%s,%s,'incomplete',
                    %s,%s,%s,%s,%s,
                    '待开奖',
                    0
                )
                """,
                (
                    local_order_id,
                    PLATFORM_ID,
                    item.get("week_name") or "",
                    item.get("match_name"),
                    item.get("match_key") or "",
                    item.get("normalized_home") or "",
                    item.get("normalized_away") or "",
                    item.get("match_identity") or "",
                    league,
                    item.get("market"),
                    option_text,
                    option_json,
                    item.get("handicap") or 0,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO order_matches
                (
                    order_id,
                    match_code,
                    match_name,
                    league,
                    play_type,
                    selection,
                    option_detail,
                    handicap,
                    result,
                    profit
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,
                    '待开奖',
                    0
                )
                """,
                (
                    local_order_id,
                    item.get("week_name") or "",
                    item.get("match_name"),
                    league,
                    item.get("market"),
                    option_text,
                    option_json,
                    item.get("handicap") or 0,
                ),
            )


    cursor.execute(
        """
        INSERT INTO users
        (platform_id,platform_user_id,username,nickname,total_orders)
        VALUES(%s,%s,%s,%s,0)
        ON DUPLICATE KEY UPDATE
            username=VALUES(username),
            nickname=CASE
                WHEN VALUES(nickname)<>'' THEN VALUES(nickname)
                ELSE nickname
            END
        """,
        (
            PLATFORM_ID,
            user_id,
            str(user_id),
            nickname,
        ),
    )


    save_user_avatar(
        cursor,
        user_id,
        nickname,
        source_fields.get("avatar_url"),
    )


    return True


# ============================================================
# main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=
            "鸿瑞竞彩足球采集器"
    )


    parser.add_argument(
        "--page",
        type=int,
        default=1
    )


    parser.add_argument(
        "--limit",
        type=int,
        default=20
    )


    parser.add_argument(
        "--order-id",
        type=int,
        default=None
    )


    parser.add_argument(
        "--write",
        action="store_true"
    )


    args = parser.parse_args()


    if args.limit <= 0:

        orders = get_all_follow_orders(
            start_page=args.page,
        )

    else:

        orders = get_follow_orders(
            page=args.page
        )


    if args.order_id:

        orders = [

            item

            for item in orders

            if to_int(
                item.get(
                    "order_id"
                ),
                0
            )
            ==
            args.order_id

        ]


    if args.limit > 0:

        orders = orders[
            :args.limit
        ]


    print(
        "鸿瑞订单数量:",
        len(orders)
    )


    conn = None
    cursor = None
    alias_map = {}
    identity_v2 = False

    try:

        if args.write:

            conn = get_conn()


            cursor = conn.cursor(
                pymysql.cursors.DictCursor
            )
            alias_map = load_team_aliases(cursor)
            identity_v2 = supports_identity_v2(
                table_columns(cursor, "order_matches")
            )


        success = 0

        failed = 0


        for list_item in orders:

            order_id = list_item.get(
                "order_id"
            )


            try:

                detail = get_follow_detail(
                    order_id
                )


                preview_order(
                    list_item,
                    detail,
                    alias_map=alias_map,
                )


                if args.write:

                    save_order(
                        cursor,
                        list_item,
                        detail,
                        alias_map=alias_map,
                        identity_v2=identity_v2,
                    )


                    conn.commit()


                success += 1


            except Exception as e:

                if conn:

                    conn.rollback()


                failed += 1


                print()
                print(
                    "订单失败:",
                    order_id
                )


                print(
                    "原因:",
                    str(e)
                )


        print()
        print(
            "=" * 90
        )


        print(
            "处理完成"
        )


        print(
            "成功:",
            success
        )


        print(
            "失败:",
            failed
        )


        print(
            "总数:",
            len(orders)
        )


        if args.write:

            print(
                "数据库写入完成"
            )

        else:

            print(
                "当前为预览模式，没有写数据库"
            )


    finally:

        if cursor:

            cursor.close()


        if conn:

            conn.close()


if __name__ == "__main__":

    main()
