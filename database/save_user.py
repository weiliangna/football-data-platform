import pymysql

from database.mysql import get_conn


def save_user(order):
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.Cursor)

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

    conn.commit()
    cursor.close()
    conn.close()
