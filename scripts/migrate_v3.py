import os
import sys
import pymysql

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.mysql import get_conn


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME=%s
          AND COLUMN_NAME=%s
        """,
        (table_name, column_name),
    )
    return int(cursor.fetchone()["c"] or 0) > 0


def index_exists(cursor, table_name, index_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME=%s
          AND INDEX_NAME=%s
        """,
        (table_name, index_name),
    )
    return int(cursor.fetchone()["c"] or 0) > 0


def add_column(cursor, table_name, column_name, definition):
    if column_exists(cursor, table_name, column_name):
        print("字段已存在:", f"{table_name}.{column_name}")
        return
    cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {definition}")
    print("新增字段:", f"{table_name}.{column_name}")


def add_index(cursor, table_name, index_name, columns):
    if index_exists(cursor, table_name, index_name):
        print("索引已存在:", f"{table_name}.{index_name}")
        return
    cursor.execute(f"ALTER TABLE `{table_name}` ADD INDEX `{index_name}` ({columns})")
    print("新增索引:", f"{table_name}.{index_name}")


def main():
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        for name, definition in [
            ("expected_bonus", "DECIMAL(16,2) DEFAULT 0 COMMENT '预计回报'"),
            ("platform_bonus", "DECIMAL(16,2) DEFAULT 0 COMMENT '平台实际派奖'"),
            ("commission_total", "DECIMAL(16,2) DEFAULT 0 COMMENT '平台佣金'"),
            ("settlement_status", "VARCHAR(30) DEFAULT '' COMMENT '平台结算状态'"),
            ("settled_time", "DATETIME NULL COMMENT '平台结算同步时间'"),
        ]:
            add_column(cursor, "orders", name, definition)

        for name, definition in [
            ("match_code", "VARCHAR(50) DEFAULT '' COMMENT '周一001等场次'"),
            ("option_detail", "TEXT NULL COMMENT '选项赔率JSON'"),
            ("match_key", "VARCHAR(255) DEFAULT '' COMMENT '标准比赛键'"),
        ]:
            add_column(cursor, "order_matches", name, definition)

        for name, definition in [
            ("match_code", "VARCHAR(50) DEFAULT '' COMMENT '周一001等场次'"),
            ("match_key", "VARCHAR(255) DEFAULT '' COMMENT '标准比赛键'"),
            ("source", "VARCHAR(50) DEFAULT '' COMMENT '赛果来源'"),
        ]:
            add_column(cursor, "match_results", name, definition)

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_statistics (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                platform_id INT NOT NULL,
                user_id BIGINT NOT NULL,
                nickname VARCHAR(100) DEFAULT '',
                total_orders INT DEFAULT 0,
                settled_orders INT DEFAULT 0,
                win_orders INT DEFAULT 0,
                lose_orders INT DEFAULT 0,
                pending_orders INT DEFAULT 0,
                hit_rate DECIMAL(8,2) DEFAULT 0,
                total_stake DECIMAL(16,2) DEFAULT 0,
                total_profit DECIMAL(16,2) DEFAULT 0,
                roi DECIMAL(10,2) DEFAULT 0,
                follow_num BIGINT DEFAULT 0,
                current_streak INT DEFAULT 0,
                max_win_streak INT DEFAULT 0,
                recent_results VARCHAR(150) DEFAULT '',
                expert_score DECIMAL(10,2) DEFAULT 0,
                last_order_time DATETIME NULL,
                updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_platform_user (platform_id,user_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS spider_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                platform_id INT DEFAULT 0,
                spider_name VARCHAR(100) NOT NULL,
                started_time DATETIME NULL,
                finished_time DATETIME NULL,
                status VARCHAR(20) DEFAULT '',
                exit_code INT DEFAULT 0,
                message TEXT NULL,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                KEY idx_spider_name (spider_name,id),
                KEY idx_spider_platform (platform_id,id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settlement_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                order_id BIGINT NOT NULL,
                order_match_id BIGINT NOT NULL,
                match_name VARCHAR(200) DEFAULT '',
                play_type VARCHAR(50) DEFAULT '',
                selection TEXT NULL,
                handicap INT DEFAULT 0,
                home_score INT NULL,
                away_score INT NULL,
                half_home_score INT NULL,
                half_away_score INT NULL,
                old_result VARCHAR(30) DEFAULT '',
                new_result VARCHAR(30) DEFAULT '',
                reason VARCHAR(255) DEFAULT '',
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                KEY idx_settlement_order (order_id,id),
                KEY idx_settlement_match (match_name,id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_config (
                platform_id INT PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                enabled TINYINT DEFAULT 1,
                spider_enabled TINYINT DEFAULT 1,
                result_enabled TINYINT DEFAULT 1,
                settlement_enabled TINYINT DEFAULT 1,
                updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            INSERT INTO platform_config
                (platform_id,name,enabled,spider_enabled,result_enabled,settlement_enabled)
            VALUES
                (1,'彩站云',1,1,1,1),
                (3,'鸿瑞',1,1,1,1)
            ON DUPLICATE KEY UPDATE name=VALUES(name)
            """
        )

        for table_name, index_name, columns in [
            ("orders", "idx_orders_platform_user", "`platform_id`,`user_id`"),
            ("orders", "idx_orders_result", "`result`"),
            ("orders", "idx_orders_created", "`created_time`"),
            ("order_matches", "idx_om_match_key", "`match_key`"),
            ("order_matches", "idx_om_result", "`result`"),
            ("match_results", "idx_mr_match_key", "`match_key`"),
            ("match_results", "idx_mr_status", "`status`"),
        ]:
            add_index(cursor, table_name, index_name, columns)

        conn.commit()
        print("V3 数据库迁移完成")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
