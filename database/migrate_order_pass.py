import os
import sys


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if BASE_DIR not in sys.path:
    sys.path.insert(
        0,
        BASE_DIR
    )


from database.mysql import get_conn


def column_exists(
    cursor,
    column_name
):

    cursor.execute(
        """
        SELECT COUNT(*)

        FROM information_schema.COLUMNS

        WHERE TABLE_SCHEMA = DATABASE()

          AND TABLE_NAME = 'orders'

          AND COLUMN_NAME = %s
        """,
        (
            column_name,
        )
    )


    row = cursor.fetchone()


    return bool(
        row[0]
    )


def main():

    conn = get_conn()

    cursor = conn.cursor()


    try:

        print()
        print(
            "===== 开始检查 orders 字段 ====="
        )


        # ====================================================
        # pass_summary
        # ====================================================

        if not column_exists(
            cursor,
            "pass_summary"
        ):

            cursor.execute(
                """
                ALTER TABLE orders

                ADD COLUMN pass_summary
                VARCHAR(100)
                NULL

                AFTER play_type
                """
            )

            print(
                "✓ 新增 pass_summary"
            )

        else:

            print(
                "已存在 pass_summary"
            )


        # ====================================================
        # pass_composition
        # ====================================================

        if not column_exists(
            cursor,
            "pass_composition"
        ):

            cursor.execute(
                """
                ALTER TABLE orders

                ADD COLUMN pass_composition
                VARCHAR(255)
                NULL

                AFTER pass_summary
                """
            )

            print(
                "✓ 新增 pass_composition"
            )

        else:

            print(
                "已存在 pass_composition"
            )


        # ====================================================
        # bet_count
        # ====================================================

        if not column_exists(
            cursor,
            "bet_count"
        ):

            cursor.execute(
                """
                ALTER TABLE orders

                ADD COLUMN bet_count
                INT
                NULL

                AFTER pass_composition
                """
            )

            print(
                "✓ 新增 bet_count"
            )

        else:

            print(
                "已存在 bet_count"
            )


        # ====================================================
        # lot_multi
        # ====================================================

        if not column_exists(
            cursor,
            "lot_multi"
        ):

            cursor.execute(
                """
                ALTER TABLE orders

                ADD COLUMN lot_multi
                DECIMAL(12,2)
                NULL

                AFTER bet_count
                """
            )

            print(
                "✓ 新增 lot_multi"
            )

        else:

            print(
                "已存在 lot_multi"
            )


        conn.commit()


        print()
        print(
            "===== 数据库迁移完成 ====="
        )


        cursor.execute(
            """
            SHOW COLUMNS
            FROM orders
            """
        )


        wanted = {
            "play_type",
            "pass_summary",
            "pass_composition",
            "bet_count",
            "lot_multi",
            "selection",
            "bet_code",
            "odds_text",
            "stake"
        }


        print()


        for row in cursor.fetchall():

            if row[0] in wanted:

                print(row)


    except Exception as e:

        conn.rollback()

        print(
            "迁移失败:",
            e
        )

        raise


    finally:

        cursor.close()

        conn.close()


if __name__ == "__main__":

    main()
