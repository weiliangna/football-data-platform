import os
import sys

import pymysql


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if BASE_DIR not in sys.path:
    sys.path.insert(
        0,
        BASE_DIR
    )


from database.mysql import get_conn
from spider.caizhanyun_detail import get_detail


PLATFORM_ID = 1


def get_orders(limit=50):

    conn = get_conn()

    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )

    try:

        cursor.execute(
            """
            SELECT
                id,
                platform_order_id,
                nickname,
                play_type,
                match_name,
                selection,
                bet_code

            FROM orders

            WHERE platform_id = %s
              AND platform_order_id IS NOT NULL
              AND platform_order_id <> ''

            ORDER BY id DESC

            LIMIT %s
            """,
            (
                PLATFORM_ID,
                limit
            )
        )

        return cursor.fetchall()

    finally:

        cursor.close()
        conn.close()


def build_match_map(matches):

    result = {}

    for item in matches:

        team_id = str(
            item.get("teamId") or ""
        ).strip()

        if not team_id:
            continue

        result[team_id] = {
            "team":
                item.get("team"),

            "league":
                item.get("league"),

            "letpoint":
                item.get("letpoint"),

            "result":
                item.get("result"),

            "peilvs":
                item.get("peilvs"),

            "matchId":
                item.get("matchId")
        }

    return result


def parse_bet_groups(
    bet_code,
    match_map
):

    if not bet_code:
        return []


    groups = []


    for raw_group in str(
        bet_code
    ).split("!"):

        raw_group = raw_group.strip()

        if not raw_group:
            continue


        if "@" in raw_group:

            group_play, body = (
                raw_group.split(
                    "@",
                    1
                )
            )

        else:

            group_play = ""
            body = raw_group


        group_play = group_play.strip()


        group_data = {
            "play":
                group_play,

            "segments":
                []
        }


        for segment in body.split("^"):

            segment = segment.strip()

            if not segment:
                continue


            parts = segment.split("|")


            data = {
                "raw":
                    segment,

                "day":
                    None,

                "week":
                    None,

                "team_id":
                    None,

                "market_code":
                    None,

                "selection_code":
                    None,

                "team":
                    None,

                "league":
                    None,

                "letpoint":
                    None,

                "peilvs":
                    None
            }


            if len(parts) >= 4:

                data["day"] = parts[0]

                data["week"] = parts[1]

                data["team_id"] = parts[2]


                # --------------------------------------------
                # 4段结构：
                #
                # 日期|周|场次|选项
                #
                # 例如：
                # 20260824|1|008|3
                # --------------------------------------------

                if len(parts) == 4:

                    data["selection_code"] = (
                        parts[3]
                    )


                # --------------------------------------------
                # 5段结构：
                #
                # 日期|周|场次|市场代码|选项代码
                #
                # 例如：
                # 20260824|1|004|J00003|23
                # --------------------------------------------

                elif len(parts) >= 5:

                    data["market_code"] = (
                        parts[3]
                    )

                    data["selection_code"] = (
                        parts[4]
                    )


                match_info = match_map.get(
                    data["team_id"],
                    {}
                )


                data["team"] = (
                    match_info.get("team")
                )

                data["league"] = (
                    match_info.get("league")
                )

                data["letpoint"] = (
                    match_info.get("letpoint")
                )

                data["peilvs"] = (
                    match_info.get("peilvs")
                )


            group_data[
                "segments"
            ].append(
                data
            )


        groups.append(
            group_data
        )


    return groups


def print_order(
    order,
    mapping_stats
):

    print()
    print("=" * 100)

    print(
        "数据库订单ID:",
        order["id"]
    )

    print(
        "专家:",
        order.get(
            "nickname"
        )
    )

    print(
        "数据库玩法:",
        order.get(
            "play_type"
        )
    )

    print(
        "方案ID:",
        order.get(
            "platform_order_id"
        )
    )


    try:

        response = get_detail(
            order[
                "platform_order_id"
            ]
        )

    except Exception as e:

        print(
            "请求失败:",
            e
        )

        return


    if (
        response.get(
            "errorCode"
        )
        !=
        "0"
    ):

        print(
            "接口失败:",
            response.get(
                "value"
            )
        )

        return


    data = (
        response.get("data")
        or {}
    )


    info = (
        data.get(
            "prescientInfo"
        )
        or {}
    )


    matches = (
        info.get(
            "jingcaiResultList"
        )
        or []
    )


    match_map = build_match_map(
        matches
    )


    bet_code = (
        info.get(
            "betCodeForResult"
        )
        or ""
    ).strip()


    if not bet_code:

        order_info = str(
            info.get(
                "orderInfo"
            )
            or ""
        )

        if order_info:

            bet_code = (
                order_info
                .split(
                    "_",
                    1
                )[0]
            )


    print()
    print(
        "playType:",
        info.get(
            "playType"
        )
    )

    print(
        "lotNo:",
        info.get(
            "lotNo"
        )
    )

    print(
        "eventCode:",
        info.get(
            "eventCode"
        )
    )

    print(
        "betnum:",
        info.get(
            "betnum"
        )
    )

    print(
        "lotmulti:",
        info.get(
            "lotmulti"
        )
    )

    print(
        "recommend:",
        info.get(
            "recommend"
        )
    )

    print()
    print(
        "betCodeForResult:"
    )

    print(
        bet_code
    )


    print()
    print(
        "===== 比赛信息 ====="
    )


    for item in matches:

        print()

        print(
            "teamId:",
            item.get(
                "teamId"
            )
        )

        print(
            "比赛:",
            item.get(
                "team"
            )
        )

        print(
            "联赛:",
            item.get(
                "league"
            )
        )

        print(
            "让球:",
            item.get(
                "letpoint"
            )
        )

        print(
            "赛果:",
            item.get(
                "result"
            )
        )

        print(
            "peilvs:",
            item.get(
                "peilvs"
            )
        )


    groups = parse_bet_groups(
        bet_code,
        match_map
    )


    print()
    print(
        "===== 投注编码拆解 ====="
    )


    for group_index, group in enumerate(
        groups,
        start=1
    ):

        print()

        print(
            f"方案组 {group_index}"
        )

        print(
            "组玩法:",
            group["play"]
        )


        for index, item in enumerate(
            group["segments"],
            start=1
        ):

            print(
                f"  第{index}项"
            )

            print(
                "    比赛:",
                item["team"]
            )

            print(
                "    联赛:",
                item["league"]
            )

            print(
                "    teamId:",
                item["team_id"]
            )

            print(
                "    让球:",
                item["letpoint"]
            )

            print(
                "    market_code:",
                item["market_code"]
            )

            print(
                "    selection_code:",
                item["selection_code"]
            )

            print(
                "    peilvs:",
                item["peilvs"]
            )


            market_key = (
                item["market_code"]
                or
                f"PLAY_{group['play']}"
            )


            stats_key = (
                group["play"],
                market_key,
                item["selection_code"]
            )


            if stats_key not in mapping_stats:

                mapping_stats[
                    stats_key
                ] = {
                    "count":
                        0,

                    "samples":
                        []
                }


            mapping_stats[
                stats_key
            ][
                "count"
            ] += 1


            if (
                len(
                    mapping_stats[
                        stats_key
                    ][
                        "samples"
                    ]
                )
                < 3
            ):

                mapping_stats[
                    stats_key
                ][
                    "samples"
                ].append(
                    {
                        "order_id":
                            order["id"],

                        "team":
                            item["team"],

                        "letpoint":
                            item["letpoint"]
                    }
                )


def main():

    orders = get_orders(
        limit=50
    )


    print()
    print(
        "读取订单数量:",
        len(orders)
    )


    mapping_stats = {}


    for order in orders:

        print_order(
            order,
            mapping_stats
        )


    print()
    print()
    print(
        "=" * 100
    )

    print(
        "===== 唯一编码统计 ====="
    )


    for key in sorted(
        mapping_stats.keys(),
        key=lambda x: (
            str(x[0]),
            str(x[1]),
            str(x[2])
        )
    ):

        play_code = key[0]

        market_code = key[1]

        selection_code = key[2]


        value = (
            mapping_stats[key]
        )


        print()

        print(
            "组玩法:",
            play_code
        )

        print(
            "市场代码:",
            market_code
        )

        print(
            "选项代码:",
            selection_code
        )

        print(
            "出现次数:",
            value["count"]
        )

        print(
            "样本:",
            value["samples"]
        )


    print()
    print(
        "=" * 100
    )

    print(
        "诊断结束。"
    )

    print(
        "本脚本只读取接口和数据库，"
        "不会修改任何数据。"
    )


if __name__ == "__main__":

    main()
