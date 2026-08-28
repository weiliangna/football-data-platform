export const DATA_MODES = Object.freeze({ live: "live", mock: "mock", hybrid: "hybrid" })

export const featureDataMode = Object.freeze({
  dashboard: "hybrid",
  plans: "live",
  analysis: "hybrid",
  matches: "live",
  news: "hybrid",
  heatmap: "live",
  results: "live",
  users: "live",
  monitor: "mock",
  ranking: "hybrid",
})

export function serviceResponse(data, source = "live") {
  return { data, source }
}

export async function withFallback(loader, fallback, feature) {
  try {
    return serviceResponse(await loader(), "live")
  } catch (error) {
    if (featureDataMode[feature] !== DATA_MODES.hybrid) throw error
    if (import.meta.env.DEV) console.info(`[${feature}] API fallback to mock`)
    return serviceResponse(typeof fallback === "function" ? fallback(error) : fallback, "mock")
  }
}
