def _default_connection_factory():
    from database.mysql import get_conn

    return get_conn()


def load_pending_order_refs(
    platform_id,
    limit=200,
    connection_factory=None,
):
    factory = connection_factory or _default_connection_factory
    conn = factory()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                platform_order_id,
                user_id,
                nickname
            FROM orders
            WHERE platform_id=%s
              AND result='待开奖'
              AND platform_order_id IS NOT NULL
              AND platform_order_id<>''
            ORDER BY id DESC
            LIMIT %s
            """,
            (int(platform_id), max(int(limit), 0)),
        )
        return [
            dict(row)
            for row in cursor.fetchall() or []
            if isinstance(row, dict)
        ]
    finally:
        cursor.close()
        conn.close()
