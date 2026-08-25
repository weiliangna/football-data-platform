export async function getExpertDetail(userId) {

    const response = await fetch(
        `/api/expert/detail/${userId}`
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
            '专家详情读取失败'
        )

    }


    return result.data

}
