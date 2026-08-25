import os
import sys
import time
import argparse
import subprocess
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


from database.mysql import get_conn


PLATFORM_ID = 1


# ============================================================
# 执行命令
# ============================================================

def run_command(
    title,
    command
):

    print()
    print("=" * 100)
    print(title)
    print("=" * 100)

    print(
        "执行:",
        " ".join(command)
    )

    start = time.time()

    process = subprocess.run(
        command,
        cwd=BASE_DIR
    )

    seconds = round(
        time.time() - start,
        2
    )

    if process.returncode != 0:

        print()
        print(
            f"✗ {title} 失败"
        )

        print(
            "返回码:",
            process.returncode
        )

        print(
            "耗时:",
            seconds,
            "秒"
        )

        return False

    print()
    print(
        f"✓ {title} 完成"
    )

    print(
        "耗时:",
        seconds,
        "秒"
    )

    return True


# ============================================================
# 检查数据库字段
# ============================================================

def check_columns():

    required = {
        "selection",
        "bet_code",
        "odds_text",
        "pass_summary",
        "pass_composition",
        "bet_count",
        "lot_multi"
    }

    conn = get_conn()

    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )

    try:

        cursor.execute(
            """
            SHOW COLUMNS
            FROM orders
            """
        )

        existing = {
            row["Field"]
            for row in cursor.fetchall()
        }

        missing = (
            required -
            existing
        )

        if missing:

            print()
            print(
                "✗ orders 缺少字段："
            )

            for field in sorted(
                missing
            ):

                print(
                    "-",
                    field
                )

            return False

        print()
        print(
            "✓ orders 数据库结构正常"
        )

        return True

    finally:

        cursor.close()
        conn.close()


# ============================================================
# 获取当前订单映射
#
# platform_order_id -> orders.id
# ============================================================

def get_order_map():

    conn = get_conn()

    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )

    try:

        cursor.execute(
            """
            SELECT
                id,
                platform_order_id

            FROM orders

            WHERE platform_id = %s

              AND platform_order_id
                  IS NOT NULL

              AND platform_order_id
                  <> ''
            """,
            (
                PLATFORM_ID,
            )
        )

        result = {}

        for row in cursor.fetchall():

            platform_order_id = str(
                row["platform_order_id"]
            )

            result[
                platform_order_id
            ] = int(
                row["id"]
            )

        return result

    finally:

        cursor.close()
        conn.close()


# ============================================================
# 找数据不完整的订单
#
# 注意：
# pass_summary 不作为必填判断条件。
#
# 因为某些接口编码例如500，
# 本身可能无法仅凭前缀确定过关方式。
# ============================================================

def get_incomplete_order_ids(
    limit=30
):

    conn = get_conn()

    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )

    try:

        cursor.execute(
            """
            SELECT id

            FROM orders

            WHERE platform_id = %s

              AND platform_order_id
                  IS NOT NULL

              AND platform_order_id
                  <> ''

              AND
              (
                    selection IS NULL
                    OR selection = ''

                    OR bet_code IS NULL
                    OR bet_code = ''

                    OR bet_count IS NULL

                    OR lot_multi IS NULL
              )

            ORDER BY id DESC

            LIMIT %s
            """,
            (
                PLATFORM_ID,
                limit
            )
        )

        return [
            int(row["id"])
            for row in cursor.fetchall()
        ]

    finally:

        cursor.close()
        conn.close()


# ============================================================
# 去重并保持顺序
# ============================================================

def unique_ids(values):

    result = []

    seen = set()

    for value in values:

        value = int(
            value
        )

        if value in seen:
            continue

        seen.add(
            value
        )

        result.append(
            value
        )

    return result


# ============================================================
# 处理一个订单
# ============================================================

def enrich_order(
    order_id,
    python_bin
):

    print()
    print(
        "#" * 100
    )

    print(
        "开始处理订单:",
        order_id
    )

    print(
        "#" * 100
    )

    # ========================================================
    # 中文投注内容 + 比赛 + 赔率
    # ========================================================

    ok = run_command(
        f"订单 {order_id}：详情/投注内容解码",
        [
            python_bin,
            "spider/caizhanyun_enrich.py",
            "--id",
            str(order_id),
            "--write"
        ]
    )

    if not ok:

        print(
            f"✗ 订单 {order_id} 详情解码失败"
        )

        return False

    # ========================================================
    # 串关 / 注数 / 倍数
    # ========================================================

    ok = run_command(
        f"订单 {order_id}：串关/注数/倍数",
        [
            python_bin,
            "spider/caizhanyun_pass_enrich.py",
            "--id",
            str(order_id),
            "--write"
        ]
    )

    if not ok:

        print(
            f"✗ 订单 {order_id} 串关解析失败"
        )

        return False

    print()
    print(
        f"✓ 订单 {order_id} 完整处理完成"
    )

    return True


# ============================================================
# 最终数据库检查
# ============================================================

def verify(
    show=5
):

    conn = get_conn()

    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )

    try:

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN selection IS NOT NULL
                         AND selection <> ''
                        THEN 1
                        ELSE 0
                    END
                ) AS decoded,

                SUM(
                    CASE
                        WHEN bet_count IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS counted,

                SUM(
                    CASE
                        WHEN lot_multi IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS multi_count

            FROM orders

            WHERE platform_id = %s
            """,
            (
                PLATFORM_ID,
            )
        )

        stats = cursor.fetchone()

        print()
        print("=" * 100)
        print("数据库校验")
        print("=" * 100)

        print(
            "订单总数:",
            stats.get(
                "total"
            )
            or 0
        )

        print(
            "已中文解码:",
            stats.get(
                "decoded"
            )
            or 0
        )

        print(
            "已有注数:",
            stats.get(
                "counted"
            )
            or 0
        )

        print(
            "已有倍数:",
            stats.get(
                "multi_count"
            )
            or 0
        )

        cursor.execute(
            """
            SELECT
                id,
                nickname,
                result,

                pass_summary,
                pass_composition,

                bet_count,
                lot_multi,

                stake,
                odds_text,

                selection,

                publish_time

            FROM orders

            WHERE platform_id = %s

            ORDER BY
                COALESCE(
                    publish_time,
                    created_time
                ) DESC,
                id DESC

            LIMIT %s
            """,
            (
                PLATFORM_ID,
                show
            )
        )

        rows = cursor.fetchall()

        print()
        print(
            "===== 最新订单 ====="
        )

        for row in rows:

            print()
            print(
                "-" * 90
            )

            print(
                "ID:",
                row.get(
                    "id"
                )
            )

            print(
                "专家:",
                row.get(
                    "nickname"
                )
            )

            print(
                "结果:",
                row.get(
                    "result"
                )
            )

            print(
                "过关:",
                row.get(
                    "pass_summary"
                )
            )

            print(
                "组成:",
                row.get(
                    "pass_composition"
                )
            )

            print(
                "注数:",
                row.get(
                    "bet_count"
                )
            )

            print(
                "倍数:",
                row.get(
                    "lot_multi"
                )
            )

            print(
                "金额:",
                row.get(
                    "stake"
                )
            )

            print(
                "赔率:",
                row.get(
                    "odds_text"
                )
            )

            print(
                "推荐:",
                row.get(
                    "selection"
                )
            )

            print(
                "时间:",
                row.get(
                    "publish_time"
                )
            )

    finally:

        cursor.close()
        conn.close()


# ============================================================
# main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=
        "彩站云增量抓取流水线"
    )

    parser.add_argument(
        "--repair-limit",
        type=int,
        default=20,
        help=
        "每轮最多修复多少条历史不完整订单"
    )

    parser.add_argument(
        "--show",
        type=int,
        default=5,
        help=
        "完成后显示最新几条"
    )

    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help=
        "跳过推荐列表抓取"
    )

    args = parser.parse_args()

    python_bin = (
        sys.executable
    )

    print()
    print("=" * 100)

    print(
        "彩站云增量流水线"
    )

    print(
        "启动时间:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print(
        "Python:",
        python_bin
    )

    print("=" * 100)

    if not check_columns():

        sys.exit(1)

    # ========================================================
    # 抓取前数据库订单
    # ========================================================

    before = (
        get_order_map()
    )

    print()
    print(
        "抓取前订单数量:",
        len(before)
    )

    # ========================================================
    # 抓推荐列表
    # ========================================================

    if not args.skip_fetch:

        ok = run_command(
            "第一步：抓取推荐列表",
            [
                python_bin,
                "spider/caizhanyun.py"
            ]
        )

        if not ok:

            sys.exit(1)

    else:

        print()
        print(
            "跳过推荐列表抓取"
        )

    # ========================================================
    # 抓取后数据库
    # ========================================================

    after = (
        get_order_map()
    )

    print()
    print(
        "抓取后订单数量:",
        len(after)
    )

    # ========================================================
    # 找真正新增订单
    # ========================================================

    new_ids = []

    for platform_order_id, db_id in (
        after.items()
    ):

        if (
            platform_order_id
            not in before
        ):

            new_ids.append(
                db_id
            )

    new_ids.sort(
        reverse=True
    )

    print()
    print(
        "本轮新增订单:",
        len(new_ids)
    )

    if new_ids:

        print(
            "新增ID:",
            new_ids
        )

    # ========================================================
    # 找历史缺字段订单
    #
    # 这样即使某一次接口失败，
    # 下一轮也能自动补回来。
    # ========================================================

    incomplete_ids = (
        get_incomplete_order_ids(
            args.repair_limit
        )
    )

    print()
    print(
        "需要补全订单:",
        len(
            incomplete_ids
        )
    )

    if incomplete_ids:

        print(
            "补全ID:",
            incomplete_ids
        )

    # ========================================================
    # 合并
    # 新订单优先
    # ========================================================

    target_ids = (
        unique_ids(
            new_ids
            +
            incomplete_ids
        )
    )

    print()
    print(
        "=" * 100
    )

    print(
        "本轮需要请求详情:",
        len(target_ids)
    )

    print(
        "=" * 100
    )

    # ========================================================
    # 没有新单/缺失单
    # 直接结束
    # ========================================================

    if not target_ids:

        print()
        print(
            "✓ 没有需要详情解码的订单"
        )

        print(
            "本轮跳过所有详情接口请求"
        )

        verify(
            args.show
        )

        print()
        print(
            "✓ 增量流水线完成"
        )

        return

    # ========================================================
    # 真正详情处理
    # ========================================================

    success = 0

    failed = []

    for order_id in target_ids:

        if enrich_order(
            order_id,
            python_bin
        ):

            success += 1

        else:

            failed.append(
                order_id
            )

    print()
    print("=" * 100)

    print(
        "详情处理完成"
    )

    print(
        "成功:",
        success
    )

    print(
        "失败:",
        len(failed)
    )

    if failed:

        print(
            "失败ID:",
            failed
        )

    print("=" * 100)

    verify(
        args.show
    )

    print()
    print("=" * 100)

    print(
        "✓ 彩站云增量流水线全部完成"
    )

    print(
        "完成时间:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("=" * 100)


    return {
        "new_count": len(new_ids),
        "duplicate_count": len(after) - len(new_ids)
    }


if __name__ == "__main__":

    main()
