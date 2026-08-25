import os
import sys

import pymysql


ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if ROOT not in sys.path:
    sys.path.insert(
        0,
        ROOT
    )


from database.mysql import get_conn


def index_exists(
    cursor,
    table_name,
    index_name
):
    cursor.execute(
        """
        SELECT COUNT(*) AS c

        FROM information_schema.STATISTICS

        WHERE
            TABLE_SCHEMA=DATABASE()
            AND TABLE_NAME=%s
            AND INDEX_NAME=%s
        """,
        (
            table_name,
            index_name
        )
    )

    return int(
        cursor.fetchone()["c"]
        or 0
    ) > 0


def add_index(
    cursor,
    table_name,
    index_name,
    columns
):
    if index_exists(
        cursor,
        table_name,
        index_name
    ):
        return

    cursor.execute(
        f"""
        ALTER TABLE `{table_name}`
        ADD INDEX `{index_name}` ({columns})
        """
    )

    print(
        "新增索引:",
        index_name
    )


def main():
    conn = get_conn()

    cursor = conn.cursor(
        pymysql.cursors.DictCursor
    )

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_grade_overrides
            (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,

                platform_id INT NOT NULL,

                user_id BIGINT NOT NULL,

                grade VARCHAR(1) NOT NULL,

                updated_time DATETIME
                    DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,

                UNIQUE KEY uk_grade_user
                (
                    platform_id,
                    user_id
                )
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_config
            (
                platform_id INT PRIMARY KEY,

                name VARCHAR(50) NOT NULL,

                enabled TINYINT DEFAULT 1,

                spider_enabled TINYINT DEFAULT 1,

                result_enabled TINYINT DEFAULT 1,

                settlement_enabled TINYINT DEFAULT 1,

                updated_time DATETIME
                    DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            INSERT INTO platform_config
            (
                platform_id,
                name,
                enabled,
                spider_enabled,
                result_enabled,
                settlement_enabled
            )
            VALUES
            (1,'彩站云',1,1,1,1),
            (2,'州运宝',1,1,1,1),
            (3,'鸿瑞',1,1,1,1),
            (4,'云彩',1,1,1,1)

            ON DUPLICATE KEY UPDATE
                name=VALUES(name)
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS spider_logs
            (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,

                platform_id INT DEFAULT 0,

                spider_name VARCHAR(100) NOT NULL,

                started_time DATETIME NULL,

                finished_time DATETIME NULL,

                status VARCHAR(20) DEFAULT '',

                exit_code INT DEFAULT 0,

                message TEXT NULL,

                created_time TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                KEY idx_spider_name
                (
                    spider_name,
                    id
                )
            )
            """
        )

        checks = [
            (
                "orders",
                "idx_orders_platform_time",
                "`platform_id`,`publish_time`"
            ),
            (
                "order_matches",
                "idx_om_order_play",
                "`order_id`,`play_type`"
            ),
            (
                "order_matches",
                "idx_om_match_name",
                "`match_name`"
            )
        ]

        for (
            table_name,
            index_name,
            columns
        ) in checks:
            add_index(
                cursor,
                table_name,
                index_name,
                columns
            )

        conn.commit()

        print(
            "V4.1 数据库校验完成"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
