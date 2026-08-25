import os
import sys
import re
import math
import argparse

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


# ============================================================
# 单个投注码包含几个选择
#
# JS规则：
# J00002 比分       每2字符一个选择
# J00004 半全场     每2字符一个选择
#
# 其它玩法每1字符一个选择
# ============================================================

def get_code_selection_count(parts):

    if not parts:
        return 1

    code = str(
        parts[-1] or ""
    )

    market_type = ""

    if (
        len(parts) > 1
        and
        str(parts[-2]).startswith("J")
    ):

        market_type = str(
            parts[-2]
        )

    if market_type in (
        "J00002",
        "J00004"
    ):

        return max(
            1,
            len(code) // 2
        )

    return max(
        1,
        len(code)
    )


# ============================================================
# 串关注数计算
# ============================================================

def get_combination_bet_count(
    weights,
    pass_size
):

    if (
        pass_size <= 0
        or
        pass_size > len(weights)
    ):
        return 0

    dp = [
        0
    ] * (
        pass_size + 1
    )

    dp[0] = 1

    for index, weight in enumerate(
        weights
    ):

        upper = min(
            pass_size,
            index + 1
        )

        for j in range(
            upper,
            0,
            -1
        ):

            dp[j] += (
                dp[j - 1]
                *
                weight
            )

    return dp[
        pass_size
    ]


# ============================================================
# 解析一个 502@ / 503@ / 504@ 组
# ============================================================

def parse_pass_group(raw_part):

    part = str(
        raw_part or ""
    ).strip()

    if not part:
        return None

    prefix = re.match(
        r"^(\d+)@([\s\S]*)$",
        part
    )

    if not prefix:
        return None

    pass_code = str(
        prefix.group(1)
    )

    body = (
        prefix.group(2)
        or ""
    )

    segments = body.split("^")

    suffix = (
        segments[-1]
        if segments
        else ""
    )

    has_suffix = (
        str(suffix).startswith("_")
    )

    if has_suffix:
        bet_segments = segments[:-1]
    else:
        bet_segments = segments

    matches = {}
    match_order = []

    for segment in bet_segments:

        segment = str(
            segment or ""
        ).strip()

        if not segment:
            continue

        q = segment.split("|")

        if len(q) < 4:
            continue

        match_id = str(
            q[-2]
        )

        if match_id.startswith("J"):

            if len(q) < 5:
                continue

            match_id = str(
                q[-3]
            )

        if not match_id:

            match_id = "|".join(
                q[:-1]
            )

        if match_id not in matches:

            matches[
                match_id
            ] = 0

            match_order.append(
                match_id
            )

        matches[
            match_id
        ] += (
            get_code_selection_count(
                q
            )
        )

    if not matches:
        return None

    # ========================================================
    # 501 -> 单关
    # 502 -> 2串1
    # 503 -> 3串1
    # ...
    #
    # 500 -> 0，因此不能直接解释
    # ========================================================

    pass_size = None

    if re.match(
        r"^5\d{2}$",
        pass_code
    ):

        value = (
            int(pass_code)
            -
            500
        )

        if value > 0:

            pass_size = value

    # 老接口尾部兜底
    if (
        not pass_size
        or
        pass_size > len(matches)
    ):

        legacy_size = 0

        if has_suffix:

            legacy = re.match(
                r"^_(\d+)(?:_|$)",
                str(suffix)
            )

            if legacy:

                legacy_size = int(
                    legacy.group(1)
                )

        if (
            legacy_size > 0
            and
            legacy_size <= len(matches)
        ):

            pass_size = (
                legacy_size
            )

    if (
        not pass_size
        or
        pass_size <= 0
        or
        pass_size > len(matches)
    ):

        return None

    weights = []

    for match_id in match_order:

        weights.append(
            max(
                1,
                matches[
                    match_id
                ]
            )
        )

    theoretical_count = (
        get_combination_bet_count(
            weights,
            pass_size
        )
    )

    if theoretical_count <= 0:
        return None

    return {

        "pass_code":
            pass_code,

        "pass_size":
            pass_size,

        "bet_count":
            theoretical_count,

        "weights":
            weights,

        "match_count":
            len(matches)

    }


# ============================================================
# 完整解析 betCode
# ============================================================

def parse_bet_code_pass_data(source):

    if not source:
        return None

    if not isinstance(
        source,
        str
    ):
        return None

    pass_groups = {}

    raw_groups = []

    for raw_part in source.split("!"):

        group = parse_pass_group(
            raw_part
        )

        if not group:
            continue

        raw_groups.append(
            group
        )

        pass_size = (
            group[
                "pass_size"
            ]
        )

        bet_count = (
            group[
                "bet_count"
            ]
        )

        if pass_size not in pass_groups:

            pass_groups[
                pass_size
            ] = 0

        pass_groups[
            pass_size
        ] += bet_count

    if not pass_groups:
        return None

    groups = []

    total_bet_count = 0

    composition = []

    pass_text = []

    for pass_size in sorted(
        pass_groups.keys()
    ):

        bet_count = (
            pass_groups[
                pass_size
            ]
        )

        pass_name = (
            "单关"
            if pass_size == 1
            else f"{pass_size}串1"
        )

        groups.append(
            {
                "pass_size":
                    pass_size,

                "bet_count":
                    bet_count
            }
        )

        total_bet_count += (
            bet_count
        )

        composition.append(
            f"{bet_count}注"
            f"{pass_name}"
        )

        pass_text.append(
            pass_name
        )

    return {

        "groups":
            groups,

        "raw_groups":
            raw_groups,

        "total_bet_count":
            total_bet_count,

        "composition":
            "+".join(
                composition
            ),

        "pass_text":
            "+".join(
                pass_text
            )

    }


# ============================================================
# selection解析
#
# 示例：
#
# 罗马:佛罗伦萨 → 半全场：平胜
# 富勒姆:切尔西 → 半全场：平负
# ============================================================

def parse_selection_data(selection):

    if not selection:

        return {
            "item_counts": [],
            "match_weights": [],
            "match_count": 0
        }

    lines = []

    seen = set()

    for raw in str(
        selection
    ).split("；"):

        line = raw.strip()

        if not line:
            continue

        if line in seen:
            continue

        seen.add(line)

        lines.append(
            line
        )

    item_counts = []

    match_map = {}

    match_order = []

    for line in lines:

        if " → " in line:

            team = (
                line
                .split(" → ", 1)[0]
                .strip()
            )

            content = (
                line
                .split(" → ", 1)[1]
                .strip()
            )

        else:

            team = line

            content = ""

        if "：" in content:

            value = (
                content
                .split("：", 1)[1]
                .strip()
            )

        else:

            value = content

        choices = [
            x
            for x in value.split("/")
            if x.strip()
        ]

        count = max(
            1,
            len(choices)
        )

        item_counts.append(
            count
        )

        if team not in match_map:

            match_map[
                team
            ] = 0

            match_order.append(
                team
            )

        match_map[
            team
        ] += count

    match_weights = [

        max(
            1,
            match_map[
                key
            ]
        )

        for key in match_order

    ]

    return {

        "item_counts":
            item_counts,

        "match_weights":
            match_weights,

        "match_count":
            len(match_order)

    }


# ============================================================
# 根据betnum判断单关/串关
#
# 对应JS getPassMode()
# ============================================================

def infer_pass_mode(
    selection,
    bet_count
):

    parsed = (
        parse_selection_data(
            selection
        )
    )

    item_counts = (
        parsed[
            "item_counts"
        ]
    )

    match_count = (
        parsed[
            "match_count"
        ]
    )

    if (
        match_count <= 1
        or
        not bet_count
        or
        not item_counts
    ):

        return "unknown"

    single_count = sum(
        item_counts
    )

    parlay_count = 1

    for count in item_counts:

        parlay_count *= count

    if (
        bet_count == single_count
        and
        bet_count != parlay_count
    ):

        return "single"

    if (
        bet_count == parlay_count
        and
        bet_count != single_count
    ):

        return "parlay"

    return "unknown"


# ============================================================
# 没有502/503前缀时，
# 根据真实总注数反推串关组合
# ============================================================

def infer_pass_composition(
    selection,
    total_bet_count
):

    parsed = (
        parse_selection_data(
            selection
        )
    )

    weights = (
        parsed[
            "match_weights"
        ]
    )

    match_count = (
        parsed[
            "match_count"
        ]
    )

    try:

        total = int(
            total_bet_count
            or 0
        )

    except Exception:

        total = 0

    if (
        match_count < 2
        or
        total <= 0
    ):

        return None

    candidates = []

    for size in range(
        2,
        match_count + 1
    ):

        count = (
            get_combination_bet_count(
                weights,
                size
            )
        )

        if (
            count > 0
            and
            count <= total
        ):

            candidates.append(
                {
                    "pass_size":
                        size,

                    "bet_count":
                        count
                }
            )

    solutions = []

    def search(
        index,
        remaining,
        selected
    ):

        if len(solutions) > 1:
            return

        if remaining == 0:

            if selected:

                solutions.append(
                    selected.copy()
                )

            return

        if (
            index >= len(candidates)
            or
            remaining < 0
        ):
            return

        selected.append(
            candidates[
                index
            ]
        )

        search(
            index + 1,
            remaining -
            candidates[index][
                "bet_count"
            ],
            selected
        )

        selected.pop()

        search(
            index + 1,
            remaining,
            selected
        )

    search(
        0,
        total,
        []
    )

    if len(solutions) != 1:

        return None

    groups = (
        solutions[0]
    )

    composition = []

    summary = []

    for group in groups:

        size = (
            group[
                "pass_size"
            ]
        )

        count = (
            group[
                "bet_count"
            ]
        )

        name = (
            "单关"
            if size == 1
            else f"{size}串1"
        )

        composition.append(
            f"{count}注{name}"
        )

        summary.append(
            name
        )

    return {

        "composition":
            "+".join(
                composition
            ),

        "summary":
            "+".join(
                summary
            )

    }


# ============================================================
# 真实betnum优先
# ============================================================

def resolve_bet_count(
    info,
    parsed_pass
):

    try:

        betnum = int(
            float(
                info.get(
                    "betnum"
                )
                or 0
            )
        )

    except Exception:

        betnum = 0

    if (
        betnum > 0
        and
        betnum < 10000
    ):

        return betnum

    if parsed_pass:

        count = int(
            parsed_pass.get(
                "total_bet_count"
            )
            or 0
        )

        if count > 0:
            return count

    return None


# ============================================================
# 倍数
# ============================================================

def normalize_lot_multi(value):

    if value is None:
        return None

    try:

        if isinstance(
            value,
            str
        ):

            value = (
                value
                .replace(
                    "倍",
                    ""
                )
                .strip()
            )

        number = float(
            value
        )

        if (
            not math.isfinite(
                number
            )
            or
            number <= 0
            or
            number > 100000
        ):

            return None

        rounded = round(
            number
        )

        if abs(
            number -
            rounded
        ) < 0.000001:

            return int(
                rounded
            )

        return round(
            number,
            2
        )

    except Exception:

        return None


def derive_lot_multi(
    self_buy_amt,
    bet_count
):

    try:

        money = float(
            self_buy_amt
            or 0
        ) / 100

        count = int(
            bet_count
            or 0
        )

        if (
            money <= 0
            or
            count <= 0
        ):

            return None

        derived = (
            money
            /
            (
                count * 2
            )
        )

        rounded = round(
            derived
        )

        if (
            abs(
                derived -
                rounded
            )
            < 0.000001
            and
            rounded > 0
        ):

            return int(
                rounded
            )

        return None

    except Exception:

        return None


def resolve_lot_multi(
    info,
    bet_count
):

    explicit = (
        normalize_lot_multi(
            info.get(
                "lotmulti"
            )
        )
    )

    derived = (
        derive_lot_multi(
            info.get(
                "selfBuyAmt"
            ),
            bet_count
        )
    )

    if derived is not None:

        if explicit is None:
            return derived

        try:

            money = float(
                info.get(
                    "selfBuyAmt"
                )
                or 0
            ) / 100

            explicit_money = (
                int(
                    bet_count
                )
                *
                2
                *
                float(
                    explicit
                )
            )

            if abs(
                explicit_money -
                money
            ) > 0.01:

                return derived

        except Exception:

            return derived

    return explicit


# ============================================================
# 串关数据源
# ============================================================

def get_pass_source(info):

    bet_code = info.get(
        "betCode"
    )

    if (
        isinstance(
            bet_code,
            str
        )
        and
        bet_code.strip()
    ):

        return bet_code.strip()

    order_info = info.get(
        "orderInfo"
    )

    if (
        isinstance(
            order_info,
            str
        )
        and
        order_info.strip()
    ):

        return order_info.strip()

    if isinstance(
        order_info,
        dict
    ):

        nested = order_info.get(
            "betCode"
        )

        if (
            isinstance(
                nested,
                str
            )
            and
            nested.strip()
        ):

            return nested.strip()

    result_code = info.get(
        "betCodeForResult"
    )

    if (
        isinstance(
            result_code,
            str
        )
    ):

        return result_code.strip()

    return ""


# ============================================================
# 最终UI过关字段
#
# 重点：
#
# 1. betnum是真实总注数
# 2. betCode前缀决定串关方式
# 3. 理论组合注数和betnum不一致时，
#    UI不能拿理论组合数覆盖betnum
# ============================================================

def resolve_pass_display(
    order,
    info,
    parsed_pass,
    bet_count
):

    selection = (
        order.get(
            "selection"
        )
        or ""
    )

    # ========================================================
    # 有明确 502/503/504
    # ========================================================

    if parsed_pass:

        pass_summary = (
            parsed_pass.get(
                "pass_text"
            )
        )

        theoretical_total = int(
            parsed_pass.get(
                "total_bet_count"
            )
            or 0
        )

        # 理论组合与接口betnum完全一致
        # 可以展示详细拆分
        if (
            bet_count
            and
            theoretical_total ==
            int(bet_count)
        ):

            pass_composition = (
                parsed_pass.get(
                    "composition"
                )
            )

        # 不一致时严格跟随JS UI：
        # betnum只显示一次
        elif (
            bet_count
            and
            pass_summary
        ):

            pass_composition = (
                f"{bet_count}注"
                f"{pass_summary}"
            )

        else:

            pass_composition = (
                parsed_pass.get(
                    "composition"
                )
            )

        return (
            pass_summary,
            pass_composition
        )

    # ========================================================
    # betCode没拿到串关级别
    # 尝试playType数字
    # ========================================================

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

    if re.match(
        r"^5\d{2}$",
        play_type
    ):

        size = (
            int(play_type)
            -
            500
        )

        if size > 0:

            summary = (
                "单关"
                if size == 1
                else f"{size}串1"
            )

            composition = (
                f"{bet_count}注"
                f"{summary}"
                if bet_count
                else summary
            )

            return (
                summary,
                composition
            )

    # ========================================================
    # 先尝试根据总注数反推唯一组合
    # ========================================================

    inferred = (
        infer_pass_composition(
            selection,
            bet_count
        )
    )

    if inferred:

        return (
            inferred[
                "summary"
            ],
            inferred[
                "composition"
            ]
        )

    # ========================================================
    # 再判断单关/串关模式
    # ========================================================

    mode = (
        infer_pass_mode(
            selection,
            bet_count
        )
    )

    selection_data = (
        parse_selection_data(
            selection
        )
    )

    match_count = (
        selection_data[
            "match_count"
        ]
    )

    if mode == "single":

        return (
            "单关",
            (
                f"{bet_count}注单关"
                if bet_count
                else "单关"
            )
        )

    if mode == "parlay":

        if match_count > 1:

            summary = (
                f"{match_count}串1"
            )

            return (
                summary,
                (
                    f"{bet_count}注"
                    f"{summary}"
                    if bet_count
                    else summary
                )
            )

    # ========================================================
    # 单场默认单关
    # ========================================================

    if match_count == 1:

        return (
            "单关",
            (
                f"{bet_count}注单关"
                if bet_count
                else "单关"
            )
        )

    return (
        None,
        None
    )


# ============================================================
# 单订单
# ============================================================

def process_order(
    cursor,
    order,
    write=False
):

    print()
    print(
        "=" * 100
    )

    print(
        "订单ID:",
        order.get(
            "id"
        )
    )

    print(
        "专家:",
        order.get(
            "nickname"
        )
    )

    platform_order_id = (
        order.get(
            "platform_order_id"
        )
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

    source = (
        get_pass_source(
            info
        )
    )

    parsed_pass = (
        parse_bet_code_pass_data(
            source
        )
    )

    bet_count = (
        resolve_bet_count(
            info,
            parsed_pass
        )
    )

    if bet_count:

        lot_multi = (
            resolve_lot_multi(
                info,
                bet_count
            )
        )

    else:

        lot_multi = (
            normalize_lot_multi(
                info.get(
                    "lotmulti"
                )
            )
        )

    (
        pass_summary,
        pass_composition
    ) = resolve_pass_display(
        order,
        info,
        parsed_pass,
        bet_count
    )

    self_buy_money = float(
        info.get(
            "selfBuyAmt"
        )
        or 0
    ) / 100

    print()
    print(
        "===== 接口 ====="
    )

    print(
        "playType:",
        info.get(
            "playType"
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
        "selfBuyAmt:",
        self_buy_money
    )

    print()
    print(
        "===== 最终展示 ====="
    )

    print(
        "过关方式:",
        pass_summary
    )

    print(
        "串关组成:",
        pass_composition
    )

    print(
        "真实注数:",
        bet_count
    )

    print(
        "真实倍数:",
        lot_multi
    )

    if parsed_pass:

        print()
        print(
            "===== 理论解析，仅供校验 ====="
        )

        print(
            "理论组成:",
            parsed_pass.get(
                "composition"
            )
        )

        print(
            "理论注数:",
            parsed_pass.get(
                "total_bet_count"
            )
        )

        print(
            "串关组:",
            parsed_pass.get(
                "groups"
            )
        )

    if (
        bet_count
        and
        lot_multi
    ):

        calculated = (
            float(
                bet_count
            )
            *
            2
            *
            float(
                lot_multi
            )
        )

        difference = abs(
            calculated -
            self_buy_money
        )

        print()
        print(
            "===== 金额校验 ====="
        )

        print(
            "注数×2元×倍数:",
            calculated
        )

        print(
            "真实金额:",
            self_buy_money
        )

        print(
            "差额:",
            round(
                difference,
                2
            )
        )

        print(
            "金额校验:",
            (
                "✓ 一致"
                if difference <= 0.01
                else "⚠ 不一致"
            )
        )

    if not write:

        print()
        print(
            "预览模式，不写数据库。"
        )

        return True

    cursor.execute(
        """
        UPDATE orders

        SET
            pass_summary = %s,
            pass_composition = %s,
            bet_count = %s,
            lot_multi = %s

        WHERE id = %s
        """,
        (
            pass_summary,
            pass_composition,
            bet_count,
            lot_multi,
            order["id"]
        )
    )

    print()
    print(
        "✓ 数据库更新完成"
    )

    return True


# ============================================================
# main
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--id",
        type=int,
        default=None
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=50
    )

    parser.add_argument(
        "--write",
        action="store_true"
    )

    args = parser.parse_args()

    conn = get_conn()

    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )

    try:

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

        orders = (
            cursor.fetchall()
        )

        print()
        print(
            "准备处理:",
            len(orders)
        )

        success = 0

        for order in orders:

            if process_order(
                cursor,
                order,
                args.write
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
            "完成:",
            success,
            "/",
            len(orders)
        )

    except Exception:

        conn.rollback()
        raise

    finally:

        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
