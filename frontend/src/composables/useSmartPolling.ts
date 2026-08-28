import { onMounted, onUnmounted, ref } from "vue"

export function useSmartPolling(fetcher, options = {}) {
  const interval = Number(options.interval || 60000)
  const timeout = Number(options.timeout || 8000)
  const maxRetries = Number(options.maxRetries ?? 2)
  const backoff = Number(options.backoff || 2)
  const visibilityAware = options.visibilityAware !== false
  const enabled = options.enabled !== false
  const immediate = options.immediate !== false
  const refreshing = ref(false)
  const paused = ref(false)
  const lastSuccessAt = ref(null)
  const lastErrorAt = ref(null)
  let timer = null
  let retryTimer = null
  let controller = null
  let retryCount = 0
  let stopped = false

  function clearTimers() {
    if (timer) clearTimeout(timer)
    if (retryTimer) clearTimeout(retryTimer)
    timer = null
    retryTimer = null
  }

  function schedule(delay = interval) {
    clearTimeout(timer)
    if (stopped || paused.value || !enabled) return
    timer = setTimeout(() => run(false), Math.max(0, delay))
  }

  async function run(isRetry = false) {
    if (stopped || paused.value || !enabled || refreshing.value) return
    refreshing.value = true
    controller?.abort()
    controller = new AbortController()
    const timeoutId = setTimeout(() => controller?.abort(), timeout)
    try {
      await fetcher({ signal: controller.signal })
      retryCount = 0
      lastSuccessAt.value = Date.now()
      schedule()
    } catch (error) {
      lastErrorAt.value = Date.now()
      if (!stopped && !paused.value && retryCount < maxRetries) {
        retryCount += 1
        retryTimer = setTimeout(() => run(true), interval * Math.pow(backoff, retryCount - 1))
      } else {
        schedule(interval)
      }
    } finally {
      clearTimeout(timeoutId)
      refreshing.value = false
    }
  }

  function pause() {
    paused.value = true
    clearTimers()
    controller?.abort()
  }

  function resume() {
    paused.value = false
    if (!stopped) run(false)
  }

  function stop() {
    stopped = true
    clearTimers()
    controller?.abort()
  }

  function onVisibilityChange() {
    if (!visibilityAware) return
    if (document.visibilityState === "hidden") pause()
    else resume()
  }

  onMounted(() => {
    stopped = false
    if (visibilityAware) document.addEventListener("visibilitychange", onVisibilityChange)
    if (immediate) run(false)
    else schedule()
  })

  onUnmounted(() => {
    stop()
    if (visibilityAware) document.removeEventListener("visibilitychange", onVisibilityChange)
  })

  return { refreshing, paused, lastSuccessAt, lastErrorAt, run, pause, resume, stop }
}

