import { apiClient, unwrap } from "../api/client.js"
import { apiEndpoints } from "../types/api.js"

function pageResult(payload, params) {
  const value = payload || {}
  const rows = Array.isArray(value) ? value : value.data || value.items || []
  return { data: rows, page: value.page ?? params.page ?? 1, pageSize: value.page_size ?? params.page_size ?? 20, total: value.total ?? rows.length, source: "live" }
}

export async function getMatches(params = {}) {
  return pageResult(unwrap(await apiClient.get(apiEndpoints.matches, { params })), params)
}

export async function getMatchContext(matchId, params = {}) {
  const endpoint = `${apiEndpoints.matches}/${encodeURIComponent(matchId)}/context`
  return { data: unwrap(await apiClient.get(endpoint, { params })), source: "live" }
}

export async function getMatchNews(params = {}) {
  return pageResult(unwrap(await apiClient.get(apiEndpoints.news, { params })), params)
}
