import argparse

import pymysql

from common.platform_registry import STOPPED_PLATFORM_IDS
from database.mysql import get_conn


CONFIRMATION = "DELETE-STOPPED-PLATFORMS"


def table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.tables
        WHERE table_schema=DATABASE() AND table_name=%s
        """,
        (table_name,),
    )
    return int((cursor.fetchone() or {}).get("c") or 0) > 0


def table_has_column(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.columns
        WHERE table_schema=DATABASE()
          AND table_name=%s
          AND column_name=%s
        """,
        (table_name, column_name),
    )
    return int((cursor.fetchone() or {}).get("c") or 0) > 0


def purge_stopped_platform_data(connection_factory=get_conn):
    platform_ids = tuple(sorted(STOPPED_PLATFORM_IDS))
    placeholders = ",".join(["%s"] * len(platform_ids))
    conn = connection_factory()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    deleted = {}

    try:
        cursor.execute(
            f"SELECT id FROM orders WHERE platform_id IN ({placeholders})",
            platform_ids,
        )
        order_ids = [int(row["id"]) for row in cursor.fetchall() or []]

        if order_ids:
            order_marks = ",".join(["%s"] * len(order_ids))
            if table_exists(cursor, "settlement_logs"):
                cursor.execute(
                    f"DELETE FROM settlement_logs WHERE order_id IN ({order_marks})",
                    tuple(order_ids),
                )
                deleted["settlement_logs"] = cursor.rowcount
            cursor.execute(
                f"DELETE FROM order_matches WHERE order_id IN ({order_marks})",
                tuple(order_ids),
            )
            deleted["order_matches"] = cursor.rowcount

        cursor.execute(
            f"DELETE FROM orders WHERE platform_id IN ({placeholders})",
            platform_ids,
        )
        deleted["orders"] = cursor.rowcount

        platform_tables = (
            "order_sync_log",
            "spider_logs",
            "sync_log",
            "user_daily_stats",
            "user_grade_overrides",
            "user_profiles_ext",
            "user_statistics",
            "users",
            "expert_profile",
            "expert_rank",
            "expert_score",
            "team_aliases",
            "match_results",
        )
        for table_name in platform_tables:
            if not table_exists(cursor, table_name):
                continue
            if not table_has_column(cursor, table_name, "platform_id"):
                continue
            cursor.execute(
                f"DELETE FROM `{table_name}` WHERE platform_id IN ({placeholders})",
                platform_ids,
            )
            deleted[table_name] = cursor.rowcount

        if table_exists(cursor, "platform_config"):
            cursor.execute(
                f"""
                UPDATE platform_config
                SET enabled=0,
                    spider_enabled=0,
                    result_enabled=0,
                    settlement_enabled=0
                WHERE platform_id IN ({placeholders})
                """,
                platform_ids,
            )
            deleted["platform_config_disabled"] = cursor.rowcount

        conn.commit()
        return deleted
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="删除已停用平台 5/6 的历史业务数据",
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args(argv)

    if not args.execute or args.confirm != CONFIRMATION:
        parser.error(
            "必须同时提供 --execute 和 "
            f"--confirm {CONFIRMATION}"
        )

    deleted = purge_stopped_platform_data()
    print("已停用平台历史数据清理完成")
    for table_name in sorted(deleted):
        print(f"{table_name}: {deleted[table_name]}")


if __name__ == "__main__":
    main()
