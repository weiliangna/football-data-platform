import os
import sys
import json
import argparse

from datetime import datetime
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


from common.match_identity import (
    build_match_identity,
    load_team_aliases,
    supports_identity_v2,
    table_columns,
)
from common.match_utils import parse_match_name
from common.platform_field_mapping import (
    database_datetime,
    extract_caizhanyun_match_fields,
    extract_caizhanyun_order_fields,
    parse_caizhanyun_kickoff,
    parse_epoch_milliseconds_beijing,
    select_avatar,
)
from database.mysql import get_conn
from spider.caizhanyun_detail import get_detail


PLATFORM_ID = 1


# ============================================================
# 完全按照用户提供的彩站云 JS 解码规则
# ============================================================


# 胜平负
S = {
    "3": "主胜",
    "1": "平",
    "0": "主负"
}


# 让球胜平负
R = {
    "3": "让胜",
    "1": "让平",
    "0": "让负"
}


# 半全场
H = {
    "3": "胜",
    "1": "平",
    "0": "负"
}


# 总进球
G = {
    "0": "0球",
    "1": "1球",
    "2": "2球",
    "3": "3球",
    "4": "4球",
    "5": "5球",
    "6": "6球",
    "7": "7+球"
}


# 特殊比分
C = {
    "90": "胜其他",
    "99": "平其他",
    "09": "负其他"
}


# J玩法映射
J = {
    "J00001": "胜平负",
    "J00002": "比分",
    "J00003": "总进球",
    "J00004": "半全场",
    "J00013": "让球胜平负"
}


# ============================================================
# 时间转换
# ============================================================


def timestamp_to_datetime(value):
    return database_datetime(
        parse_epoch_milliseconds_beijing(value)
    )


# ============================================================
# 赔率区间
# ============================================================

def parse_odds_text(info):

    raw = info.get(
        "preAmtRecord"
    )

    if not raw:
        return None


    try:

        record = raw

        for _ in range(2):

            if not isinstance(
                record,
                str
            ):
                break

            record = json.loads(
                record
            )

    except Exception:

        return None


    if not isinstance(
        record,
        dict
    ):
        return None


    min_odds = str(
        record.get(
            "minPeilv"
        )
        or
        record.get(
            "minOdds"
        )
        or ""
    ).strip()


    max_odds = str(
        record.get(
            "maxPeilv"
        )
        or
        record.get(
            "maxOdds"
        )
        or ""
    ).strip()


    if min_odds and max_odds:

        if min_odds == max_odds:
            return min_odds

        return (
            f"{min_odds}~{max_odds}"
        )


    if min_odds:
        return min_odds


    if max_odds:
        return max_odds


    return None


# ============================================================
# 比赛时间
# ============================================================


def parse_match_time(item):
    return parse_caizhanyun_kickoff(
        item.get("day"),
        item.get("enddate"),
    )


# ============================================================
# 比赛映射
#
# JS 同时使用：
#
# day + teamId
#
# 和：
#
# teamId
#
# 进行匹配
# ============================================================

def build_match_maps(matches):

    teams = {}

    match_meta = {}


    for item in matches:

        if (
            item.get("teamId")
            is None
        ):
            continue


        team_id = str(
            item.get("teamId")
        )


        day = str(
            item.get("day")
            or ""
        )


        source_fields = extract_caizhanyun_match_fields(
            item
        )


        meta = {

            "team":
                source_fields["match_name"]
                or team_id,

            "league":
                source_fields["league"],

            "teamId":
                source_fields["team_id"],

            "day":
                source_fields["day"],

            "week":
                source_fields["week"],

            "letpoint":
                source_fields["letpoint"],

            "matchId":
                source_fields["match_id"],

            "enddate":
                source_fields["enddate"],

            "kickoff_time":
                source_fields["kickoff_time"],

            "identity_candidate":
                source_fields["identity_candidate"]

        }


        teams[
            team_id
        ] = meta

        if day:

            match_meta[
                f"{day}|{team_id}"
            ] = meta


    return (
        teams,
        match_meta
    )


# ============================================================
# 胜平负 / 让球胜平负
#
# JS 会自动去掉同一个code里的重复项
#
# 例如：
#
# 11
#
# 不显示：
#
# 平/平
#
# 而只显示：
#
# 平
# ============================================================

def decode_three_way(
    code,
    mapping
):

    result = []


    for char in str(
        code or ""
    ):

        value = mapping.get(
            char,
            char
        )


        if value not in result:

            result.append(
                value
            )


    return result


# ============================================================
# 总进球
# ============================================================

def decode_goals(code):

    result = []


    for char in str(
        code or ""
    ):

        result.append(
            G.get(
                char,
                f"{char}球"
            )
        )


    return result


# ============================================================
# 比分
#
# 每两个字符一组
#
# 10 = 1:0
# 21 = 2:1
#
# 特殊：
#
# 90 = 胜其他
# 99 = 平其他
# 09 = 负其他
# ============================================================

def decode_score(code):

    result = []


    value = str(
        code or ""
    )


    for i in range(
        0,
        len(value),
        2
    ):

        part = value[
            i:i + 2
        ]


        if len(part) < 2:
            break


        if part in C:

            result.append(
                C[part]
            )

        else:

            result.append(
                f"{part[0]}:{part[1]}"
            )


    return result


# ============================================================
# 半全场
#
# 每两个字符一组
#
# 33 = 胜胜
# 31 = 胜平
# 30 = 胜负
#
# 13 = 平胜
# 11 = 平平
# 10 = 平负
#
# 03 = 负胜
# 01 = 负平
# 00 = 负负
# ============================================================

def decode_half_full(code):

    result = []


    value = str(
        code or ""
    )


    for i in range(
        0,
        len(value),
        2
    ):

        part = value[
            i:i + 2
        ]


        if len(part) < 2:
            break


        first = H.get(
            part[0],
            part[0]
        )


        second = H.get(
            part[1],
            part[1]
        )


        result.append(
            f"{first}{second}"
        )


    return result


# ============================================================
# 单个市场解码
# ============================================================

def decode_market(
    market_name,
    code
):

    if market_name == "半全场":

        return decode_half_full(
            code
        )


    if market_name == "比分":

        return decode_score(
            code
        )


    if market_name == "总进球":

        return decode_goals(
            code
        )


    if market_name == "让球胜平负":

        return decode_three_way(
            code,
            R
        )


    # JS 默认兜底：
    #
    # 胜平负
    return decode_three_way(
        code,
        S
    )


# ============================================================
# 过关代码
#
# JS规则：
#
# 501 = 1串1
# 502 = 2串1
# 503 = 3串1
# 504 = 4串1
# ...
#
# 500 不强行翻译
# ============================================================

def decode_pass_code(code):

    value = str(
        code or ""
    ).strip()


    if (
        len(value) == 3
        and
        value.startswith("5")
        and
        value.isdigit()
    ):

        pass_size = (
            int(value) -
            500
        )


        if pass_size > 0:

            if pass_size == 1:

                return "单关"

            return (
                f"{pass_size}串1"
            )


    return value


# ============================================================
# JS核心decode逻辑
#
# 完全参考：
#
# code = q最后一项
# tid = q倒数第二项
#
# 如果tid以J开头：
#
# type = tid
# tid = q倒数第三项
#
# 玩法：
#
# J[type] || J[lotNo]
#
# 如果仍不存在：
#
# 默认 胜平负
# ============================================================

def decode_primary_bet(
    bet_code,
    lot_no,
    matches
):

    if not bet_code:

        return []


    raw = str(
        bet_code
    )


    # ========================================================
    # JS validateBetCodeForResult 会在 ! 处截断。
    #
    # 第一部分是实际投注选项的权威来源。
    #
    # 后面的 503/504 等主要用于串关组成。
    # ========================================================

    if "!" in raw:

        raw = raw.split(
            "!",
            1
        )[0]


    if "@" not in raw:

        return []


    pass_code, option_body = (
        raw.split(
            "@",
            1
        )
    )


    teams, match_meta = (
        build_match_maps(
            matches
        )
    )


    result_items = []


    for segment in (
        option_body
        .split("^")
    ):

        segment = (
            segment.strip()
        )


        if not segment:
            continue


        q = segment.split("|")


        if len(q) < 4:
            continue


        code = str(
            q[-1]
        )


        tid = str(
            q[-2]
        )


        market_code = None


        # ====================================================
        # 带J玩法
        # ====================================================

        if (
            tid
            and
            tid.startswith("J")
        ):

            market_code = tid


            if len(q) < 5:
                continue


            tid = str(
                q[-3]
            )


        # ====================================================
        # JS:
        #
        # J[type] || J[ln]
        #
        # 找不到则默认胜平负
        # ====================================================

        market_name = (
            J.get(
                market_code
            )
            or
            J.get(
                str(lot_no or "")
            )
            or
            "胜平负"
        )


        labels = decode_market(
            market_name,
            code
        )


        bet_day = str(
            q[0]
            if q
            else ""
        )


        meta = (
            match_meta.get(
                f"{bet_day}|{tid}"
            )
            or
            teams.get(
                tid
            )
            or
            {
                "team":
                    tid,

                "league":
                    "",

                "teamId":
                    tid,

                "day":
                    bet_day,

                "week":
                    q[1]
                    if len(q) > 1
                    else "",

                "letpoint":
                    None,

                "matchId":
                    None,

                "enddate":
                    "",

                "kickoff_time":
                    None,

                "identity_candidate":
                    ""
            }
        )


        result_items.append({

            "team":
                meta.get(
                    "team"
                )
                or tid,

            "league":
                meta.get(
                    "league"
                )
                or "",

            "team_id":
                meta.get("teamId")
                or tid,

            "match_id":
                meta.get("matchId")
                or "",

            "day":
                meta.get("day")
                or bet_day,

            "week":
                meta.get("week")
                or "",

            "enddate":
                meta.get("enddate")
                or "",

            "kickoff_time":
                meta.get("kickoff_time"),

            "identity_candidate":
                meta.get("identity_candidate")
                or "",

            "market_code":
                market_code,

            "market_name":
                market_name,

            "selection_code":
                code,

            "labels":
                labels,

            "peilvs":
                meta.get("peilvs")
                or [],

            "letpoint":
                meta.get(
                    "letpoint"
                ),

            "pass_code":
                pass_code,

            "pass_name":
                decode_pass_code(
                    pass_code
                )

        })


    return result_items


# ============================================================
# 生成网站selection文本
# ============================================================

def build_selection_text(
    info,
    matches
):

    bet_code = str(
        info.get(
            "betCodeForResult"
        )
        or
        info.get(
            "betCode"
        )
        or ""
    ).strip()


    if not bet_code:

        order_info = info.get(
            "orderInfo"
        )


        if isinstance(
            order_info,
            str
        ):

            bet_code = (
                order_info
                .split(
                    "_",
                    1
                )[0]
            )


    if not bet_code:

        return (
            None,
            None,
            []
        )


    lot_no = info.get(
        "lotNo"
    )


    items = decode_primary_bet(
        bet_code,
        lot_no,
        matches
    )


    texts = []


    for item in items:

        labels = (
            item.get(
                "labels"
            )
            or []
        )


        label_text = "/".join(
            labels
        )


        market_name = (
            item.get(
                "market_name"
            )
            or "胜平负"
        )


        team = (
            item.get(
                "team"
            )
            or ""
        )


        texts.append(
            f"{team} → "
            f"{market_name}："
            f"{label_text}"
        )


    return (
        "；".join(texts)
        if texts
        else None,

        bet_code,

        items
    )


# ============================================================
# 保存比赛
# ============================================================

def save_match(
    cursor,
    item,
    alias_map=None,
    identity_v2=False,
):
    match_id = str(
        item.get("matchId")
        or ""
    ).strip()

    if not match_id:
        return

    team = str(item.get("team") or "")
    parsed_match = parse_match_name(team)
    home_team = parsed_match["home_team"] or ""
    away_team = parsed_match["away_team"] or ""
    league = item.get("league")
    match_time = parse_match_time(item)
    identity = build_match_identity(
        PLATFORM_ID,
        match_date=item.get("day"),
        source_match_code=match_id,
        match_name=team,
        home_team=home_team,
        away_team=away_team,
        alias_map=alias_map,
    )

    if item.get("cancel"):
        status = "取消"
    elif item.get("result"):
        status = "已结束"
    else:
        status = "未结束"

    if identity_v2:
        cursor.execute(
            """
            SELECT id
            FROM matches
            WHERE platform_id=%s
              AND match_date=%s
              AND match_id=%s
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE
            """,
            (
                PLATFORM_ID,
                identity["match_date"],
                match_id,
            ),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE matches
                SET
                    platform_id=%s,
                    match_date=%s,
                    normalized_home=%s,
                    normalized_away=%s,
                    match_identity=%s,
                    identity_quality=%s,
                    league=%s,
                    home_team=%s,
                    away_team=%s,
                    match_time=COALESCE(%s,match_time),
                    status=%s
                WHERE id=%s
                """,
                (
                    PLATFORM_ID,
                    identity["match_date"],
                    identity["normalized_home"],
                    identity["normalized_away"],
                    identity["match_identity"],
                    identity["identity_quality"],
                    league,
                    home_team,
                    away_team,
                    match_time,
                    status,
                    existing["id"],
                ),
            )
            return

        cursor.execute(
            """
            INSERT INTO matches
            (
                platform_id,
                match_id,
                match_date,
                normalized_home,
                normalized_away,
                match_identity,
                identity_quality,
                league,
                home_team,
                away_team,
                match_time,
                status
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                PLATFORM_ID,
                match_id,
                identity["match_date"],
                identity["normalized_home"],
                identity["normalized_away"],
                identity["match_identity"],
                identity["identity_quality"],
                league,
                home_team,
                away_team,
                match_time,
                status,
            ),
        )
        return

    cursor.execute(
        """
        INSERT INTO matches
        (
            match_id,
            league,
            home_team,
            away_team,
            match_time,
            status
        )
        VALUES
        (%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            league=VALUES(league),
            home_team=VALUES(home_team),
            away_team=VALUES(away_team),
            match_time=COALESCE(VALUES(match_time),match_time),
            status=VALUES(status)
        """,
        (
            match_id,
            league,
            home_team,
            away_team,
            match_time,
            status,
        ),
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
        (%s,%s,%s,%s,'caizhanyun_detail')
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
            source='caizhanyun_detail',
            updated_time=NOW()
        """,
        (
            PLATFORM_ID,
            user_id,
            str(nickname or ""),
            avatar,
        ),
    )
    return True


# ============================================================
# 字段检查
# ============================================================

def check_columns(cursor):

    cursor.execute(
        """
        SHOW COLUMNS
        FROM orders
        """
    )


    columns = {

        row["Field"]

        for row in cursor.fetchall()

    }


    required = {

        "selection",
        "bet_code",
        "odds_text",
        "follow_num",
        "publish_time"

    }


    return (
        required -
        columns
    )


# ============================================================
# 单订单
# ============================================================

def enrich_order(
    cursor,
    order,
    write=False,
    alias_map=None,
    matches_identity_v2=False,
):

    order_id = (
        order["id"]
    )


    platform_order_id = (
        order.get(
            "platform_order_id"
        )
    )


    print()
    print(
        "=" * 100
    )


    print(
        "数据库订单ID:",
        order_id
    )


    print(
        "专家:",
        order.get(
            "nickname"
        )
    )


    print(
        "方案ID:",
        platform_order_id
    )


    if not platform_order_id:

        print(
            "跳过：没有platform_order_id"
        )

        return False


    try:

        response = get_detail(
            platform_order_id
        )


    except Exception as e:

        print(
            "接口请求失败:",
            e
        )

        return False


    if str(
        response.get(
            "errorCode"
        )
    ) != "0":

        print(
            "接口返回失败:",
            response.get(
                "value"
            )
        )

        return False


    data = (
        response.get(
            "data"
        )
        or {}
    )


    info = (
        data.get(
            "prescientInfo"
        )
        or {}
    )


    starter = (
        data.get(
            "starterInfo"
        )
        or {}
    )


    matches = (
        info.get(
            "jingcaiResultList"
        )
        or []
    )


    # ========================================================
    # 正式JS解码
    # ========================================================

    (
        selection_text,
        bet_code,
        decoded_items
    ) = build_selection_text(
        info,
        matches
    )


    odds_text = (
        parse_odds_text(
            info
        )
    )


    order_source_fields = (
        extract_caizhanyun_order_fields(info)
    )


    publish_time = order_source_fields[
        "publish_time"
    ]


    end_time_candidate = order_source_fields[
        "end_time_candidate"
    ]

       # ================================
    # 提取让球盘口
    # ================================

    handicap = 0

    for item in decoded_items:

        if item.get("letpoint") is not None:

            try:
                handicap = int(
                    item.get("letpoint")
                )

            except:

                handicap = 0

            break
    play_type = str(
        info.get(
            "playType"
        )
        or
        order.get(
            "play_type"
        )
        or ""
    )


    follow_num = int(
        info.get(
            "followerNumber"
        )
        or 0
    )


    stake = float(
        info.get(
            "selfBuyAmt"
        )
        or 0
    ) / 100


    declaration = (
        info.get(
            "description"
        )
        or
        order.get(
            "declaration"
        )
    )


    user_id = (
        starter.get(
            "id"
        )
        or
        info.get(
            "starter"
        )
        or
        order.get(
            "user_id"
        )
    )


    nickname = (
        starter.get(
            "nickname"
        )
        or
        order.get(
            "nickname"
        )
    )


    avatar_url = select_avatar(
        detail_avatar=starter.get("headPic"),
    )


    first_match = (
        matches[0]
        if matches
        else {}
    )


    match_id = (
        first_match.get(
            "matchId"
        )
        or
        order.get(
            "match_id"
        )
    )


    match_name = (
        first_match.get(
            "team"
        )
        or
        order.get(
            "match_name"
        )
    )


    league = (
        first_match.get(
            "league"
        )
        or
        order.get(
            "league"
        )
    )


    print(
        "接口playType:",
        play_type
    )


    print(
        "正式解码推荐:",
        selection_text
    )


    print(
        "原始投注码:",
        bet_code
    )


    print(
        "赔率区间:",
        odds_text
    )


    print(
        "投注金额:",
        stake
    )


    print(
        "跟单人数:",
        follow_num
    )


    print(
        "发布时间:",
        publish_time
    )


    print(
        "方案截止候选（非逐腿deadline）:",
        end_time_candidate
    )


    print()
    print(
        "===== JS规则解码详情 ====="
    )


    for index, item in enumerate(
        decoded_items,
        start=1
    ):

        print()

        print(
            f"第{index}项"
        )

        print(
            "比赛:",
            item.get(
                "team"
            )
        )

        print(
            "玩法:",
            item.get(
                "market_name"
            )
        )

        print(
            "J代码:",
            item.get(
                "market_code"
            )
        )

        print(
            "选项代码:",
            item.get(
                "selection_code"
            )
        )

        print(
            "中文:",
            "/".join(
                item.get(
                    "labels"
                )
                or []
            )
        )

        print(
            "让球:",
            item.get(
                "letpoint"
            )
        )

        print(
            "过关代码:",
            item.get(
                "pass_code"
            )
        )

        print(
            "过关:",
            item.get(
                "pass_name"
            )
        )


    if not write:

        print()
        print(
            "当前为预览模式，不写数据库。"
        )

        return True


    cursor.execute(
        """
        UPDATE orders

        SET
            user_id = %s,

            nickname = %s,

            match_id = %s,

            match_name = %s,

            league = %s,

            play_type = %s,

            selection = %s,

            bet_code = %s,

            odds_text = %s,

            stake = %s,

            declaration = %s,

            follow_num = %s,

            publish_time = %s,

            handicap = %s

            WHERE id = %s
        """,
        (
            user_id,

            nickname,

            match_id,

            match_name,

            league,

            play_type,

            selection_text,

            bet_code,

            odds_text,

            stake,

            declaration,

            follow_num,

            publish_time,

            handicap,
 
            order_id
        )
    )


    for item in matches:

        save_match(
            cursor,
            item,
            alias_map=alias_map,
            identity_v2=matches_identity_v2,
        )


    save_user_avatar(
        cursor,
        user_id,
        nickname,
        avatar_url,
    )


    print()
    print(
        "✓ 数据库更新完成"
    )


    return True


# ============================================================
# 主程序
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=
        "彩站云订单详情JS规则解码"
    )

    parser.add_argument(
        "--id",
        type=int,
        default=None
    )


    parser.add_argument(
        "--write",
        action="store_true"
    )


    parser.add_argument(
        "--limit",
        type=int,
        default=50
    )


    args = parser.parse_args()


    conn = get_conn()


    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )


    try:
        alias_map = load_team_aliases(cursor)
        match_columns = table_columns(
            cursor,
            "matches",
        )
        matches_identity_v2 = supports_identity_v2(
            match_columns
        )

        if args.write:

            missing = check_columns(
                cursor
            )


            if missing:

                print(
                    "orders缺少字段:"
                )


                for item in sorted(
                    missing
                ):

                    print(
                        "-",
                        item
                    )


                return


        if args.id:

            cursor.execute(
                """
                SELECT *
                FROM orders

                WHERE platform_id = %s
                  AND id = %s

                LIMIT 1
                """,
                (
                    PLATFORM_ID,
                    args.id
                )
            )


        else:

            cursor.execute(
                """
                SELECT *
                FROM orders

                WHERE platform_id = %s

                  AND platform_order_id
                      IS NOT NULL

                  AND platform_order_id
                      <> ''

                ORDER BY id DESC

                LIMIT %s
                """,
                (
                    PLATFORM_ID,
                    args.limit
                )
            )


        orders = cursor.fetchall()


        print()
        print(
            "准备解析订单数量:",
            len(orders)
        )


        success = 0


        for order in orders:

            if enrich_order(
                cursor,
                order,
                write=args.write,
                alias_map=alias_map,
                matches_identity_v2=matches_identity_v2,
            ):

                success += 1


        if args.write:

            conn.commit()

        else:

            conn.rollback()


        print()
        print(
            "=" * 100
        )

        print(
            "处理完成"
        )

        print(
            "成功:",
            success
        )

        print(
            "总数:",
            len(orders)
        )


        if not args.write:

            print(
                "当前未修改数据库。"
            )


    except Exception as e:

        conn.rollback()

        print(
            "运行失败:",
            e
        )

        raise


    finally:

        cursor.close()
        conn.close()


if __name__ == "__main__":

    main()
