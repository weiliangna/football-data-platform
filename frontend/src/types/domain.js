/**
 * Domain factories normalize snake_case API fields before they reach UI.
 * Missing values remain null/empty rather than becoming undefined or NaN.
 */
export function toNumber(value, fallback = 0) {
  const result = Number(value)
  return Number.isFinite(result) ? result : fallback
}

export function adaptPlan(row = {}) {
  return {
    id: row.id ?? row.order_id ?? null,
    userId: row.user_id ?? null,
    username: row.nickname ?? row.username ?? "--",
    platformId: row.platform_id ?? null,
    platformName: row.platform_name ?? "--",
    amount: toNumber(row.stake ?? row.amount),
    publishTime: row.publish_time ?? row.created_time ?? null,
    deadlineTime: row.deadline_time ?? null,
    result: row.result ?? "待开奖",
    matches: Array.isArray(row.matches) ? row.matches : [],
  }
}

export function adaptUser(row = {}) {
  return {
    id: row.user_id ?? row.id ?? null,
    platformId: row.platform_id ?? null,
    platformName: row.platform_name ?? "--",
    name: row.nickname ?? row.username ?? "--",
    avatarUrl: row.avatar_url ?? "",
    hitRate: row.history_hit_rate ?? null,
    roi: row.history_roi ?? null,
    todayOrders: toNumber(row.today_orders ?? row.order_count),
    followers: toNumber(row.followers ?? row.follow_num),
  }
}
