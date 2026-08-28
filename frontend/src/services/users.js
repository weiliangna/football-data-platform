import { apiClient, unwrap } from "../api/client.js"
import { apiEndpoints } from "../types/api.js"
import { adaptUser } from "../types/domain.js"

export async function getUsers(params = {}) {
  const payload = unwrap(await apiClient.get(apiEndpoints.users, { params })) || {}
  const rows = Array.isArray(payload) ? payload : payload.data || payload.items || []
  return {
    data: rows.map(adaptUser),
    page: payload.page ?? params.page ?? 1,
    pageSize: payload.page_size ?? params.page_size ?? 20,
    total: payload.total ?? rows.length,
    source: "live",
  }
}
