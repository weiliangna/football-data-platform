from database.mysql import get_conn


def main():

    conn = None

    cursor = None


    try:

        conn = get_conn()

        cursor = conn.cursor()


        cursor.execute(
            "SELECT DATABASE() AS db, NOW() AS now_time"
        )


        row = cursor.fetchone()


        print(
            "MySQL连接成功"
        )

        print(
            "Database:",
            row.get(
                "db"
            )
        )

        print(
            "Server Time:",
            row.get(
                "now_time"
            )
        )


    except Exception as e:

        print(
            "MySQL连接失败:",
            e
        )

        raise


    finally:

        if cursor:

            cursor.close()


        if conn:

            conn.close()



if __name__ == "__main__":

    main()
