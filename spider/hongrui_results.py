import os
import sys
import re

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
from database.mysql import get_conn
from spider.hongrui import get_follow_detail


PLATFORM_ID = 3


# ============================================================
# 数字转换
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
# 比分解析
#
# 例：
#
# 1:0 / 半：1:0
# 2:0 / 半：2:0
# 0:0
#
# ============================================================

def parse_score_text(
    text
):

    text = str(
        text
        or ""
    ).strip()


    if text in (
        "",
        "-",
        "--"
    ):
        return None


    matches = re.findall(
        r"(\d+)\s*[:：]\s*(\d+)",
        text
    )


    if not matches:
        return None


    home_score = int(
        matches[0][0]
    )

    away_score = int(
        matches[0][1]
    )


    half_home_score = None

    half_away_score = None


    if len(matches) >= 2:

        half_home_score = int(
            matches[1][0]
        )

        half_away_score = int(
            matches[1][1]
        )


    return {

        "home_score":
            home_score,

        "away_score":
            away_score,

        "half_home_score":
            half_home_score,

        "half_away_score":
            half_away_score
    }


# ============================================================
# 订单详情提取比赛赛果
# ============================================================

def extract_match_results(
    raw
):

    data = (
        raw.get("data")
        or {}
    )


    message = (
        data.get("order_message")
        or {}
    )


    league = str(
        message.get("cate_name")
        or
        "竞彩足球"
    ).strip()


    lottery_list = (
        message.get("lottery_list")
        or []
    )


    results = []


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


        if (
            not home
            or
            not away
        ):
            continue


        candidates = []


        for play in (
            match.get("playing")
            or []
        ):

            is_status = to_int(
                play.get(
                    "is_status"
                ),
                0
            )


            #
            # 鸿瑞：
            #
            # is_status=1
            # 表示已经开奖并且有正式赛果
            #

            if is_status != 1:
                continue


            score = parse_score_text(
                play.get(
                    "result"
                )
            )


            if not score:
                continue


            candidate = (

                score[
                    "home_score"
                ],

                score[
                    "away_score"
                ],

                score[
                    "half_home_score"
                ],

                score[
                    "half_away_score"
                ]
            )


            if candidate not in candidates:

                candidates.append(
                    candidate
                )


        #
        # 还没有正式比分
        #

        if not candidates:
            continue


        #
        # 不同玩法返回不同比分时，
        # 禁止自动写入
        #

        if len(candidates) != 1:

            print(
                "⚠ 比分冲突，跳过:",
                home,
                "vs",
                away,
                candidates
            )

            continue


        (
            home_score,
            away_score,
            half_home_score,
            half_away_score
        ) = candidates[0]


        results.append({

            "week_name":
                week_name,

            "league":
                league,

            "home_team":
                home,

            "away_team":
                away,

            "match_name":
                home
                +
                ":"
                +
                away,

            "home_score":
                home_score,

            "away_score":
                away_score,

            "half_home_score":
                half_home_score,

            "half_away_score":
                half_away_score
        })


    return results


# ============================================================
# 找需要继续检查的鸿瑞订单
#
# 条件：
#
# 1. 还有拆单待开奖
#
# 或
#
# 2. 平台还没有同步到“已派奖”
#
# ============================================================

def get_orders_to_check(
    cursor,
    limit=100
):

    cursor.execute(
        """
        SELECT DISTINCT

            o.id,

            o.platform_order_id,

            o.nickname,

            o.stake,

            o.result,

            o.settlement_status


        FROM orders o


        LEFT JOIN order_matches om

            ON om.order_id = o.id


        WHERE

            o.platform_id = %s

            AND o.platform_order_id IS NOT NULL

            AND o.platform_order_id <> ''

            AND
            (
                om.result = '待开奖'

                OR

                IFNULL(
                    o.settlement_status,
                    ''
                ) <> '已派奖'
            )


        ORDER BY o.id DESC


        LIMIT %s
        """,
        (
            PLATFORM_ID,
            limit
        )
    )


    return cursor.fetchall()


# ============================================================
# 保存比赛赛果
# ============================================================

def save_match_result(
    cursor,
    item,
    alias_map=None,
    identity_v2=False,
):
    identity = build_match_identity(
        PLATFORM_ID,
        source_match_code=item.get("week_name"),
        match_name=item.get("match_name"),
        home_team=item.get("home_team"),
        away_team=item.get("away_team"),
        alias_map=alias_map,
    )

    if identity_v2:
        cursor.execute(
            """
            SELECT id
            FROM match_results
            WHERE platform_id=%s
              AND match_date IS NULL
              AND match_code=%s
              AND match_key=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                PLATFORM_ID,
                item.get("week_name") or "",
                identity["match_key"],
            ),
        )
        existing = cursor.fetchone()

        if not existing:
            cursor.execute(
                """
                SELECT id
                FROM match_results
                WHERE match_name=%s
                  AND (platform_id IS NULL OR platform_id=%s)
                ORDER BY
                    CASE WHEN platform_id=%s THEN 0 ELSE 1 END,
                    id ASC
                LIMIT 1
                FOR UPDATE
                """,
                (
                    item["match_name"],
                    PLATFORM_ID,
                    PLATFORM_ID,
                ),
            )
            existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE match_results
                SET
                    platform_id=%s,
                    match_date=NULL,
                    match_code=%s,
                    match_key=%s,
                    normalized_home=%s,
                    normalized_away=%s,
                    match_identity=%s,
                    identity_quality='incomplete',
                    league=%s,
                    home_team=%s,
                    away_team=%s,
                    home_score=%s,
                    away_score=%s,
                    half_home_score=COALESCE(%s,half_home_score),
                    half_away_score=COALESCE(%s,half_away_score),
                    status='已结束',
                    finished_time=COALESCE(finished_time,NOW())
                WHERE id=%s
                """,
                (
                    PLATFORM_ID,
                    item.get("week_name") or "",
                    identity["match_key"],
                    identity["normalized_home"],
                    identity["normalized_away"],
                    identity["match_identity"],
                    item["league"],
                    item["home_team"],
                    item["away_team"],
                    item["home_score"],
                    item["away_score"],
                    item["half_home_score"],
                    item["half_away_score"],
                    existing["id"],
                ),
            )
            return

        cursor.execute(
            """
            INSERT INTO match_results
            (
                platform_id,
                match_date,
                match_code,
                match_key,
                normalized_home,
                normalized_away,
                match_identity,
                identity_quality,
                match_name,
                league,
                home_team,
                away_team,
                home_score,
                away_score,
                half_home_score,
                half_away_score,
                status,
                finished_time
            )
            VALUES
            (
                %s,NULL,%s,%s,%s,%s,%s,'incomplete',
                %s,%s,%s,%s,%s,%s,%s,%s,'已结束',NOW()
            )
            """,
            (
                PLATFORM_ID,
                item.get("week_name") or "",
                identity["match_key"],
                identity["normalized_home"],
                identity["normalized_away"],
                identity["match_identity"],
                item["match_name"],
                item["league"],
                item["home_team"],
                item["away_team"],
                item["home_score"],
                item["away_score"],
                item["half_home_score"],
                item["half_away_score"],
            ),
        )
        return

    cursor.execute(
        """
        INSERT INTO match_results
        (
            match_name,
            league,
            home_team,
            away_team,
            home_score,
            away_score,
            half_home_score,
            half_away_score,
            status,
            finished_time
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,'已结束',NOW())
        ON DUPLICATE KEY UPDATE
            league=VALUES(league),
            home_team=VALUES(home_team),
            away_team=VALUES(away_team),
            home_score=VALUES(home_score),
            away_score=VALUES(away_score),
            half_home_score=COALESCE(
                VALUES(half_home_score),
                half_home_score
            ),
            half_away_score=COALESCE(
                VALUES(half_away_score),
                half_away_score
            ),
            status='已结束',
            finished_time=COALESCE(finished_time,NOW())
        """,
        (
            item["match_name"],
            item["league"],
            item["home_team"],
            item["away_team"],
            item["home_score"],
            item["away_score"],
            item["half_home_score"],
            item["half_away_score"],
        ),
    )

def sync_platform_settlement(
    cursor,
    local_order,
    raw
):

    data = (
        raw.get("data")
        or {}
    )


    head = (
        data.get("head")
        or {}
    )


    status = to_int(
        head.get(
            "status"
        ),
        0
    )


    status_msg = str(
        head.get(
            "status_msg"
        )
        or ""
    ).strip()


    bonus = to_float(
        head.get(
            "bonus"
        ),
        0
    )


    commission_total = to_float(
        head.get(
            "commission_total"
        ),
        0
    )


    stake = to_float(
        local_order.get(
            "stake"
        ),
        0
    )


    #
    # 无论是否已经派奖，
    # 都同步当前平台状态
    #

    cursor.execute(
        """
        UPDATE orders

        SET
            settlement_status=%s,
            platform_bonus=%s,
            commission_total=%s

        WHERE id=%s
        """,
        (
            status_msg,

            bonus,

            commission_total,

            local_order[
                "id"
            ]
        )
    )


    #
    # 鸿瑞样本：
    #
    # status=8
    # status_msg=已派奖
    #
    # bonus 是平台最终实际派奖金额。
    #
    # 实际净盈亏：
    #
    # profit = bonus - 本金
    #
    # commission_total 不再次扣除。
    #

    if (
        status == 8
        or
        status_msg == "已派奖"
    ):

        actual_profit = round(
            bonus
            -
            stake,
            2
        )


        cursor.execute(
            """
            UPDATE orders

            SET
                platform_bonus=%s,

                commission_total=%s,

                settlement_status='已派奖',

                profit=%s,

                settled_time=NOW()

            WHERE id=%s
            """,
            (
                bonus,

                commission_total,

                actual_profit,

                local_order[
                    "id"
                ]
            )
        )


        return {

            "paid":
                True,

            "bonus":
                bonus,

            "commission":
                commission_total,

            "profit":
                actual_profit
        }


    return {

        "paid":
            False,

        "bonus":
            bonus,

        "commission":
            commission_total,

        "profit":
            None
    }


# ============================================================
# 主程序
# ============================================================

def main():

    conn = None

    cursor = None


    try:

        conn = get_conn()


        cursor = conn.cursor(
            pymysql.cursors.DictCursor
        )
        alias_map = load_team_aliases(cursor)
        identity_v2 = supports_identity_v2(
            table_columns(cursor, "match_results")
        )


        orders = get_orders_to_check(
            cursor,
            limit=100
        )


        print(
            "鸿瑞待检查订单:",
            len(orders)
        )


        checked = 0

        result_count = 0

        paid_count = 0

        failed = 0


        for order in orders:

            platform_order_id = str(
                order.get(
                    "platform_order_id"
                )
                or ""
            )


            nickname = str(
                order.get(
                    "nickname"
                )
                or "-"
            )


            try:

                raw = get_follow_detail(
                    platform_order_id
                )


                checked += 1


                # =================================================
                # 同步平台派奖
                # =================================================

                settlement = sync_platform_settlement(
                    cursor,
                    order,
                    raw
                )


                if settlement[
                    "paid"
                ]:

                    paid_count += 1


                    print()
                    print(
                        "💰 已派奖:",
                        platform_order_id,
                        nickname
                    )


                    print(
                        "本金:",
                        order.get(
                            "stake"
                        )
                    )


                    print(
                        "实际奖金:",
                        settlement[
                            "bonus"
                        ]
                    )


                    print(
                        "佣金:",
                        settlement[
                            "commission"
                        ]
                    )


                    print(
                        "实际盈亏:",
                        settlement[
                            "profit"
                        ]
                    )


                # =================================================
                # 同步真实比赛赛果
                # =================================================

                results = extract_match_results(
                    raw
                )


                if not results:

                    if not settlement[
                        "paid"
                    ]:

                        print(
                            "○ 暂未开奖:",
                            platform_order_id,
                            nickname
                        )


                    conn.commit()

                    continue


                for item in results:

                    save_match_result(
                        cursor,
                        item,
                        alias_map=alias_map,
                        identity_v2=identity_v2,
                    )


                    result_count += 1


                    print(
                        "✓ 赛果:",
                        item[
                            "match_name"
                        ],
                        item[
                            "home_score"
                        ],
                        ":",
                        item[
                            "away_score"
                        ],
                        "| 半场",
                        (
                            item[
                                "half_home_score"
                            ]
                            if
                            item[
                                "half_home_score"
                            ]
                            is not None
                            else "-"
                        ),
                        ":",
                        (
                            item[
                                "half_away_score"
                            ]
                            if
                            item[
                                "half_away_score"
                            ]
                            is not None
                            else "-"
                        )
                    )


                conn.commit()


            except Exception as e:

                conn.rollback()

                failed += 1


                print()
                print(
                    "✗ 鸿瑞订单失败:",
                    platform_order_id
                )


                print(
                    "原因:",
                    str(e)
                )


        print()
        print("=" * 70)


        print(
            "鸿瑞状态同步完成"
        )


        print(
            "查询订单:",
            checked
        )


        print(
            "赛果数量:",
            result_count
        )


        print(
            "已派奖订单:",
            paid_count
        )


        print(
            "失败:",
            failed
        )


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


if __name__ == "__main__":

    main()
