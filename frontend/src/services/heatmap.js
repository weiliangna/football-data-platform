import { apiClient, unwrap } from "../api/client.js"
import { apiEndpoints } from "../types/api.js"

export async function getHeatmap(params = {}) {
  const payload = unwrap(await apiClient.get(apiEndpoints.heatmap, { params })) || {}
  const rows = Array.isArray(payload) ? payload : payload.data || payload.items || []
  return { data: rows, page: payload.page ?? params.page ?? 1, pageSize: payload.page_size ?? params.page_size ?? 50, total: payload.total ?? rows.length, source: "live" }
}
