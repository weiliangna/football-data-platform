import { getUsers } from "./users.js"

/** Hybrid until a dedicated ranking endpoint is available. */
export async function getRanking(params = {}) {
  const result = await getUsers({ ...params, sort_by: params.sort_by || "roi", order: params.order || "desc" })
  return { ...result, source: "hybrid" }
}
