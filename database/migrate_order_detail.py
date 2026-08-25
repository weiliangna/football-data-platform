import os
import sys


# ============================================================
# 自动加入项目根目录
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from database.mysql import get_conn


# ============================================================
# 检查字段是否存在
# ============================================================

def column_exists(cursor, column_name):

    cursor.execute(
        """
        SELECT COUNT(*)

        FROM information_schema.COLUMNS

        WHERE TABLE_SCHEMA = DATABASE()

          AND TABLE_NAME = 'orders'

          AND COLUMN_NAME = %s
        """,
        (column_name,)
    )

    result = cursor.fetchone()

    return result[0] > 0


# ============================================================
# 主程序
# ============================================================

def main():

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor()


        print()
        print("=" * 60)
        print("开始升级 orders 表")
        print("=" * 60)


        # ====================================================
        # 1. selection 改为 TEXT
        # ====================================================

        cursor.execute(
            """
            ALTER TABLE orders

            MODIFY COLUMN selection TEXT NULL
            """
        )

        print("✓ selection 已调整为 TEXT")


        # ====================================================
        # 2. odds_text
        #
        # 用于保存：
        # 5.15~5.93
        # ====================================================

        if not column_exists(
            cursor,
            "odds_text"
        ):

            cursor.execute(
                """
                ALTER TABLE orders

                ADD COLUMN odds_text
                VARCHAR(100)
                NULL

                AFTER odds
                """
            )

            print("✓ 新增字段 odds_text")

        else:

            print("✓ odds_text 已存在")


        # ====================================================
        # 3. bet_code
        #
        # 保存：
        # betCodeForResult 原始投注编码
        # ====================================================

        if not column_exists(
            cursor,
            "bet_code"
        ):

            cursor.execute(
                """
                ALTER TABLE orders

                ADD COLUMN bet_code
                TEXT
                NULL

                AFTER selection
                """
            )

            print("✓ 新增字段 bet_code")

        else:

            print("✓ bet_code 已存在")


        conn.commit()


        print()
        print("=" * 60)
        print("orders 表升级成功")
        print("=" * 60)


        # ====================================================
        # 4. 输出最终表结构
        # ====================================================

        cursor.execute(
            """
            DESC orders
            """
        )

        fields = cursor.fetchall()


        print()
        print("当前 orders 字段：")
        print()


        for field in fields:

            print(
                field[0],
                field[1]
            )


    except Exception as e:

        if conn:

            conn.rollback()


        print()
        print("升级失败：")
        print(e)

        raise


    finally:

        if cursor:

            cursor.close()


        if conn:

            conn.close()


if __name__ == "__main__":

    main()
