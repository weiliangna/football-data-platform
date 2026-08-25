import pymysql

from database.mysql import get_conn


def save_user(order):
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.Cursor)

    try:
        sql = """
        INSERT INTO users
        (
            platform_id,
            platform_user_id,
            username,
            nickname,
            total_orders
        )
        VALUES
        (%s,%s,%s,%s,0)

        ON DUPLICATE KEY UPDATE
            nickname=VALUES(nickname)
        """

        cursor.execute(
            sql,
            (
                order["platform_id"],
                order["user_id"],
                str(order["user_id"]),
                order["nickname"],
            ),
        )

        avatar_url = str(
            order.get("avatar_url")
            or ""
        ).strip()
        avatar_source = str(
            order.get("avatar_source")
            or "platform_list"
        ).strip()
        user_id = order.get("user_id")

        if user_id not in (None, "", 0) and avatar_url:
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
                (%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    nickname=CASE
                        WHEN VALUES(nickname)<>''
                        THEN VALUES(nickname)
                        ELSE nickname
                    END,
                    avatar_url=CASE
                        WHEN avatar_url IS NULL OR avatar_url=''
                        THEN VALUES(avatar_url)
                        WHEN source='caizhanyun_detail'
                             AND VALUES(source)='caizhanyun_list'
                        THEN avatar_url
                        WHEN VALUES(avatar_url)<>''
                        THEN VALUES(avatar_url)
                        ELSE avatar_url
                    END,
                    source=CASE
                        WHEN source='caizhanyun_detail'
                             AND VALUES(source)='caizhanyun_list'
                        THEN source
                        ELSE VALUES(source)
                    END,
                    updated_time=NOW()
                """,
                (
                    order["platform_id"],
                    user_id,
                    str(order.get("nickname") or ""),
                    avatar_url,
                    avatar_source,
                ),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
