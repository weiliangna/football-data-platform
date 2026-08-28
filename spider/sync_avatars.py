import os
import sys
import pymysql

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.mysql import get_conn

AVATAR_CANDIDATES = (
    "avatar_url","avatar","user_pic","head_img","headimg",
    "head_image","photo","pic"
)
_schema_cache = {}


def table_columns(cursor, table_name):
    cached = _schema_cache.get(str(table_name))
    if cached is not None:
        return set(cached)
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        """,
        (table_name,)
    )
    columns = {row["COLUMN_NAME"] for row in cursor.fetchall()}
    _schema_cache[str(table_name)] = frozenset(columns)
    return columns


def sync_from_table(cursor, table_name):
    columns = table_columns(cursor, table_name)
    if not columns or "user_id" not in columns:
        return 0

    avatar_col = next(
        (name for name in AVATAR_CANDIDATES if name in columns),
        None
    )
    if not avatar_col:
        return 0

    platform_expr = "platform_id" if "platform_id" in columns else "1 AS platform_id"
    nickname_col = next(
        (name for name in ("nickname","user_name","name") if name in columns),
        None
    )
    nickname_expr = f"`{nickname_col}` AS nickname" if nickname_col else "'' AS nickname"

    cursor.execute(
        f"""
        SELECT user_id,{platform_expr},{nickname_expr},
               `{avatar_col}` AS avatar_url
        FROM `{table_name}`
        WHERE `{avatar_col}` IS NOT NULL AND `{avatar_col}`<>''
        """
    )

    count = 0
    for row in cursor.fetchall():
        cursor.execute(
            """
            INSERT INTO user_profiles_ext
            (platform_id,user_id,nickname,avatar_url,source)
            VALUES (%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                nickname=CASE
                    WHEN VALUES(nickname)<>'' THEN VALUES(nickname)
                    ELSE nickname
                END,
                avatar_url=VALUES(avatar_url),
                source=VALUES(source),
                updated_time=NOW()
            """,
            (
                int(row.get("platform_id") or 1),
                int(row.get("user_id") or 0),
                str(row.get("nickname") or ""),
                str(row.get("avatar_url") or ""),
                table_name
            )
        )
        count += 1
    return count


def sync_hongrui(cursor):
    try:
        from spider.hongrui import get_follow_detail
    except Exception as exc:
        print("鸿瑞头像同步跳过:", exc)
        return 0

    cursor.execute(
        """
        SELECT platform_order_id,user_id,nickname
        FROM orders
        WHERE platform_id=3
          AND platform_order_id IS NOT NULL
          AND platform_order_id<>''
        ORDER BY id DESC
        LIMIT 80
        """
    )

    seen = set()
    count = 0

    for order in cursor.fetchall():
        user_id = int(order.get("user_id") or 0)
        if user_id in seen:
            continue
        try:
            raw = get_follow_detail(order.get("platform_order_id"))
            head = ((raw.get("data") or {}).get("head") or {})
            uid = int(head.get("user_id") or user_id or 0)
            avatar = str(head.get("user_pic") or "").strip()
            nickname = str(
                head.get("user_name") or order.get("nickname") or ""
            ).strip()
            if uid:
                seen.add(uid)
            if not (uid and avatar):
                continue
            cursor.execute(
                """
                INSERT INTO user_profiles_ext
                (platform_id,user_id,nickname,avatar_url,source)
                VALUES (3,%s,%s,%s,'hongrui')
                ON DUPLICATE KEY UPDATE
                    nickname=VALUES(nickname),
                    avatar_url=VALUES(avatar_url),
                    source='hongrui',
                    updated_time=NOW()
                """,
                (uid, nickname, avatar)
            )
            count += 1
        except Exception as exc:
            print("鸿瑞头像获取失败:", order.get("platform_order_id"), exc)
    return count


def main():
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        total = 0
        for table in ("users","expert_profile","expert_rank"):
            try:
                n = sync_from_table(cursor, table)
                total += n
                if n:
                    print(table, "头像同步:", n)
            except Exception as exc:
                print(table, "同步跳过:", exc)

        total += sync_hongrui(cursor)
        conn.commit()
        print("头像同步完成:", total)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
