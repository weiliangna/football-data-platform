import os
import sys
import json


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(0, BASE_DIR)


from database.mysql import get_conn
from spider.caizhanyun_detail import get_detail


def print_json(title, value):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str
        )
    )


def main():

    order_id = None

    if len(sys.argv) >= 2:

        try:
            order_id = int(sys.argv[1])

        except ValueError:
            print("订单ID必须是数字")
            return


    conn = get_conn()

    cursor = conn.cursor()


    if order_id:

        cursor.execute(
            """
            SELECT
                id,
                platform_order_id,
                user_id,
                nickname
            FROM orders
            WHERE id = %s
              AND platform_id = 1
            LIMIT 1
            """,
            (order_id,)
        )

    else:

        cursor.execute(
            """
            SELECT
                id,
                platform_order_id,
                user_id,
                nickname
            FROM orders
            WHERE platform_id = 1
              AND platform_order_id IS NOT NULL
              AND platform_order_id <> ''
            ORDER BY id DESC
            LIMIT 1
            """
        )


    row = cursor.fetchone()


    cursor.close()

    conn.close()


    if not row:

        print("没有找到彩站云订单")
        return


    db_id = row[0]

    platform_order_id = row[1]

    user_id = row[2]

    nickname = row[3]


    print()
    print("数据库订单ID:", db_id)
    print("专家:", nickname)
    print("user_id:", user_id)
    print("platform_order_id:", platform_order_id)


    response = get_detail(
        platform_order_id
    )


    print_json(
        "接口顶层返回",
        {
            key: value
            for key, value in response.items()
            if key != "data"
        }
    )


    data = response.get(
        "data",
        {}
    )


    print_json(
        "data.keys",
        list(data.keys())
        if isinstance(data, dict)
        else data
    )


    if not isinstance(data, dict):

        print("data 不是字典结构")
        return


    prescient_info = data.get(
        "prescientInfo",
        {}
    )


    print_json(
        "prescientInfo 完整内容",
        prescient_info
    )


    if isinstance(
        prescient_info,
        dict
    ):

        print_json(
            "prescientInfo.keys",
            list(
                prescient_info.keys()
            )
        )


        result_list = (
            prescient_info.get(
                "jingcaiResultList"
            )
            or
            prescient_info.get(
                "resultList"
            )
            or
            []
        )


        print_json(
            "比赛结果列表",
            result_list
        )


        if result_list:

            print_json(
                "第一场比赛完整字段",
                result_list[0]
            )


    starter_info = data.get(
        "starterInfo",
        {}
    )


    print_json(
        "starterInfo",
        starter_info
    )


if __name__ == "__main__":

    main()
