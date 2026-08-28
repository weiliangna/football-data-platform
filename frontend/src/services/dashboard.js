import { apiClient, unwrap } from "../api/client.js"
import { apiEndpoints } from "../types/api.js"

export async function getDashboard(params = {}) {
  const data = unwrap(await apiClient.get(apiEndpoints.dashboard, { params }))
  return { data: data && typeof data === "object" ? data : {}, source: "live" }
}
