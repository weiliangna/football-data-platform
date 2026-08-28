import { apiClient, unwrap } from "../api/client.js"
import { apiEndpoints } from "../types/api.js"

export async function getAnalysis(params = {}) {
  const data = unwrap(await apiClient.get(apiEndpoints.analysis, { params }))
  return { data: data && typeof data === "object" ? data : {}, source: "live" }
}
