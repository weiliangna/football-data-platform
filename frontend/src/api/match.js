export async function getMatchList(){

    const res = await fetch(
        "/api/match/today"
    )


    const data = await res.json()


    return data.data || []

}
