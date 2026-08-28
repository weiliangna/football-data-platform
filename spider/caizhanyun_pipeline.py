import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

import pymysql


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from database.mysql import get_conn


PLATFORM_ID = 1

REQUIRED_ORDER_COLUMNS = {
    "selection",
    "bet_code",
    "odds_text",
    "pass_summary",
    "pass_composition",
    "bet_count",
    "lot_multi",
}
_orders_columns_cache = None


def run_command(title, command):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)
    print("执行:", " ".join(command))

    started = time.time()
    process = subprocess.run(
        command,
        cwd=BASE_DIR,
    )
    seconds = round(time.time() - started, 2)

    if process.returncode != 0:
        print(f"✗ {title} 失败")
        print("返回码:", process.returncode)
        print("耗时:", seconds, "秒")
        return False

    print(f"✓ {title} 完成")
    print("耗时:", seconds, "秒")
    return True


def check_columns():
    global _orders_columns_cache
    if _orders_columns_cache is not None:
        return not (REQUIRED_ORDER_COLUMNS - _orders_columns_cache)
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("SHOW COLUMNS FROM orders")
        existing = {
            row["Field"]
            for row in cursor.fetchall()
        }
        _orders_columns_cache = frozenset(existing)
        missing = REQUIRED_ORDER_COLUMNS - existing

        if missing:
            print("✗ orders 缺少字段：")
            for field in sorted(missing):
                print("-", field)
            return False

        print("✓ orders 数据库结构正常")
        return True
    finally:
        cursor.close()
        conn.close()


def get_order_map():
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute(
            """
            SELECT id,platform_order_id
            FROM orders
            WHERE platform_id=%s
              AND platform_order_id IS NOT NULL
              AND platform_order_id<>''
            """,
            (PLATFORM_ID,),
        )

        return {
            str(row["platform_order_id"]): int(row["id"])
            for row in cursor.fetchall()
        }
    finally:
        cursor.close()
        conn.close()


def get_incomplete_order_ids(limit=30):
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute(
            """
            SELECT o.id
            FROM orders o
            WHERE o.platform_id=%s
              AND o.platform_order_id IS NOT NULL
              AND o.platform_order_id<>''
              AND
              (
                    o.selection IS NULL
                    OR o.selection=''
                    OR o.bet_code IS NULL
                    OR o.bet_code=''
                    OR o.bet_count IS NULL
                    OR o.lot_multi IS NULL
                    OR NOT EXISTS
                    (
                        SELECT 1
                        FROM order_matches om
                        WHERE om.order_id=o.id
                    )
              )
            ORDER BY o.id DESC
            LIMIT %s
            """,
            (
                PLATFORM_ID,
                limit,
            ),
        )

        return [
            int(row["id"])
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()
        conn.close()


def unique_ids(values):
    result = []
    seen = set()

    for value in values:
        value = int(value)

        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


def build_enrichment_steps(order_id, python_bin):
    return (
        (
            f"订单 {order_id}：详情/投注内容解码",
            [
                python_bin,
                "-m",
                "spider.caizhanyun_enrich",
                "--id",
                str(order_id),
                "--write",
            ],
        ),
        (
            f"订单 {order_id}：串关/注数/倍数",
            [
                python_bin,
                "-m",
                "spider.caizhanyun_pass_enrich",
                "--id",
                str(order_id),
                "--write",
            ],
        ),
        (
            f"订单 {order_id}：生成比赛拆腿",
            [
                python_bin,
                "-m",
                "spider.build_order_matches",
                "--id",
                str(order_id),
            ],
        ),
    )


def enrich_order(order_id, python_bin):
    steps = build_enrichment_steps(order_id, python_bin)

    print()
    print("#" * 100)
    print("开始处理订单:", order_id)
    print("#" * 100)

    for title, command in steps:
        if not run_command(title, command):
            print(f"✗ 订单 {order_id} 在步骤“{title}”失败")
            return False

    print(f"✓ 订单 {order_id} 完整处理完成")
    return True


def verify(show=5):
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN selection IS NOT NULL
                         AND selection<>''
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
            WHERE platform_id=%s
            """,
            (PLATFORM_ID,),
        )
        stats = cursor.fetchone() or {}

        print()
        print("=" * 100)
        print("数据库校验")
        print("=" * 100)
        print("订单总数:", stats.get("total") or 0)
        print("已中文解码:", stats.get("decoded") or 0)
        print("已有注数:", stats.get("counted") or 0)
        print("已有倍数:", stats.get("multi_count") or 0)

        cursor.execute(
            """
            SELECT
                o.id,
                o.nickname,
                o.result,
                o.pass_summary,
                o.pass_composition,
                o.bet_count,
                o.lot_multi,
                o.stake,
                o.odds_text,
                o.selection,
                o.publish_time,
                COUNT(om.id) AS match_count
            FROM orders o
            LEFT JOIN order_matches om
                ON om.order_id=o.id
            WHERE o.platform_id=%s
            GROUP BY
                o.id,
                o.nickname,
                o.result,
                o.pass_summary,
                o.pass_composition,
                o.bet_count,
                o.lot_multi,
                o.stake,
                o.odds_text,
                o.selection,
                o.publish_time,
                o.created_time
            ORDER BY
                COALESCE(o.publish_time,o.created_time) DESC,
                o.id DESC
            LIMIT %s
            """,
            (
                PLATFORM_ID,
                show,
            ),
        )

        print("===== 最新订单 =====")

        for row in cursor.fetchall():
            print("-" * 90)
            print("ID:", row.get("id"))
            print("专家:", row.get("nickname"))
            print("结果:", row.get("result"))
            print("过关:", row.get("pass_summary"))
            print("组成:", row.get("pass_composition"))
            print("注数:", row.get("bet_count"))
            print("倍数:", row.get("lot_multi"))
            print("金额:", row.get("stake"))
            print("赔率:", row.get("odds_text"))
            print("推荐:", row.get("selection"))
            print("比赛腿:", row.get("match_count") or 0)
            print("时间:", row.get("publish_time"))
    finally:
        cursor.close()
        conn.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="彩站云增量抓取流水线"
    )
    parser.add_argument(
        "--repair-limit",
        type=int,
        default=20,
        help="每轮最多修复多少条历史不完整订单",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=5,
        help="完成后显示最新几条",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="跳过推荐列表抓取",
    )
    args = parser.parse_args(argv)

    python_bin = sys.executable

    print("=" * 100)
    print("彩站云增量流水线")
    print(
        "启动时间:",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    print("Python:", python_bin)
    print("=" * 100)

    if not check_columns():
        raise RuntimeError("orders 数据库结构不完整")

    before = get_order_map()
    print("抓取前订单数量:", len(before))

    if not args.skip_fetch:
        if not run_command(
            "第一步：抓取推荐列表",
            [
                python_bin,
                "spider/caizhanyun.py",
            ],
        ):
            raise RuntimeError("彩站云推荐列表抓取失败")
    else:
        print("跳过推荐列表抓取")

    after = get_order_map()
    print("抓取后订单数量:", len(after))

    new_ids = sorted(
        [
            db_id
            for platform_order_id, db_id in after.items()
            if platform_order_id not in before
        ],
        reverse=True,
    )
    incomplete_ids = get_incomplete_order_ids(
        args.repair_limit
    )
    target_ids = unique_ids(
        new_ids + incomplete_ids
    )

    print("本轮新增订单:", len(new_ids))
    print("需要补全订单:", len(incomplete_ids))
    print("本轮需要请求详情:", len(target_ids))

    if not target_ids:
        print("✓ 没有需要详情解码或拆腿的订单")
        verify(args.show)
        return {
            "new_count": len(new_ids),
            "duplicate_count": len(after) - len(new_ids),
            "success_count": 0,
            "failed_count": 0,
            "failed_ids": [],
        }

    success = 0
    failed_ids = []

    for order_id in target_ids:
        try:
            if enrich_order(order_id, python_bin):
                success += 1
            else:
                failed_ids.append(order_id)
        except Exception as exc:
            failed_ids.append(order_id)
            print("订单处理异常:", order_id, str(exc))

    print("=" * 100)
    print("详情及拆腿处理完成")
    print("成功:", success)
    print("失败:", len(failed_ids))

    if failed_ids:
        print("失败ID:", failed_ids)

    verify(args.show)

    print("=" * 100)
    print(
        "完成时间:",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    print("=" * 100)

    return {
        "new_count": len(new_ids),
        "duplicate_count": len(after) - len(new_ids),
        "success_count": success,
        "failed_count": len(failed_ids),
        "failed_ids": failed_ids,
    }


if __name__ == "__main__":
    result = main()

    if result.get("failed_count"):
        raise SystemExit(1)
