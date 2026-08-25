import pymysql

from database.mysql import get_conn


def save_order(order):
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.Cursor)

    cursor.execute(
        """
        SELECT id
        FROM orders
        WHERE
            platform_id=%s
            AND platform_order_id=%s
        """,
        (
            order["platform_id"],
            order["platform_order_id"],
        ),
    )

    exists = cursor.fetchone()

    if exists:
        print("重复订单，跳过:", order["nickname"])
        cursor.close()
        conn.close()
        return False

    sql = """
    INSERT INTO orders
    (
        platform_id,
        user_id,
        nickname,
        platform_order_id,
        stake,
        hit_rate,
        profitability,
        follow_num,
        result
    )
    VALUES
    (%s,%s,%s,%s,%s,%s,%s,%s,'待开奖')
    """

    cursor.execute(
        sql,
        (
            order["platform_id"],
            order["user_id"],
            order["nickname"],
            order["platform_order_id"],
            order.get("stake", 0),
            order.get("hit_rate", 0),
            order.get("profitability", 0),
            order.get("follow_num", 0),
        ),
    )

    conn.commit()

    print("订单新增:", order["nickname"])

    cursor.close()
    conn.close()

    return True
