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
        (table_name, column_name)
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
        (table_name, index_name)
    )
    return int(cursor.fetchone()["c"] or 0) > 0


def add_column(cursor, table_name, column_name, definition):
    if column_exists(cursor, table_name, column_name):
        print("字段已存在:", f"{table_name}.{column_name}")
        return
    cursor.execute(
        f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {definition}"
    )
    print("新增字段:", f"{table_name}.{column_name}")


def add_index(cursor, table_name, index_name, columns):
    if index_exists(cursor, table_name, index_name):
        print("索引已存在:", f"{table_name}.{index_name}")
        return
    cursor.execute(
        f"ALTER TABLE `{table_name}` ADD INDEX `{index_name}` ({columns})"
    )
    print("新增索引:", f"{table_name}.{index_name}")


def split_match_name(value):
    text = str(value or "").strip()
    for sep in (":", "：", " VS ", " vs ", " V ", " v "):
        if sep in text:
            a, b = text.split(sep, 1)
            return a.strip(), b.strip()
    return text, ""


def main():
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles_ext
            (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                platform_id INT NOT NULL,
                user_id BIGINT NOT NULL,
                nickname VARCHAR(100) DEFAULT '',
                avatar_url TEXT NULL,
                source VARCHAR(50) DEFAULT '',
                updated_time DATETIME DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_platform_user (platform_id,user_id),
                KEY idx_profile_nickname (nickname)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS team_aliases
            (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                platform_id INT DEFAULT 0,
                canonical_name VARCHAR(120) NOT NULL,
                alias_name VARCHAR(120) NOT NULL,
                updated_time DATETIME DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_platform_alias (platform_id,alias_name),
                KEY idx_team_canonical (canonical_name)
            )
            """
        )

        add_column(
            cursor,
            "order_matches",
            "deadline_time",
            "DATETIME NULL COMMENT '比赛/销售截止时间'"
        )
        add_index(cursor, "order_matches", "idx_om_deadline", "`deadline_time`")
        add_index(cursor, "order_matches", "idx_om_code", "`match_code`")

        names = set()

        cursor.execute(
            "SELECT DISTINCT home_team,away_team FROM match_results"
        )
        for row in cursor.fetchall():
            for key in ("home_team", "away_team"):
                value = str(row.get(key) or "").strip()
                if value:
                    names.add(value)

        cursor.execute(
            """
            SELECT DISTINCT match_name
            FROM order_matches
            WHERE match_name IS NOT NULL AND match_name<>''
            """
        )
        for row in cursor.fetchall():
            home, away = split_match_name(row.get("match_name"))
            if home:
                names.add(home)
            if away:
                names.add(away)

        for name in names:
            cursor.execute(
                """
                INSERT INTO team_aliases
                (platform_id,canonical_name,alias_name)
                VALUES (0,%s,%s)
                ON DUPLICATE KEY UPDATE
                    canonical_name=VALUES(canonical_name)
                """,
                (name, name)
            )

        conn.commit()
        print("V6 数据库迁移完成，基础球队名称:", len(names))
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
