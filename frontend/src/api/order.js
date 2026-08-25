export async function getOrderList() {

    const response = await fetch(
        '/api/order/latest'
    )


    if (!response.ok) {

        throw new Error(
            `HTTP ${response.status}`
        )

    }


    const result =
        await response.json()


    if (result.code !== 200) {

        throw new Error(
            result.msg ||
            '订单数据读取失败'
        )

    }


    return result.data || []

}
