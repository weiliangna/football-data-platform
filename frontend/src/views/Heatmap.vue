<template>
  <section class="page-shell heatmap-page">
    <header class="heatmap-hero app-card">
      <router-link class="back-button" to="/">← 返回今日总览</router-link>
      <div><span class="eyebrow">Football betting heatmap</span><h1>足球场次比赛投注热力图</h1><p>仅统计今日仍未截止的比赛 · 相同比赛与投注内容跨平台合并</p></div>
      <span class="refresh-note">每 30 秒自动更新</span>
    </header>

    <section class="filter-band app-card">
      <div class="play-tabs">
        <button v-for="play in plays" :key="play" type="button" :class="{ active: playType === play }" @click="changePlay(play)">{{ play }}</button>
      </div>
      <label class="match-filter"><span>赛事筛选</span><select v-model="selectedMatch"><option value="">全部赛事</option><option v-for="match in matches" :key="matchKey(match)" :value="matchKey(match)">{{ match.match_code || "--" }} · {{ match.home || "--" }} VS {{ match.away || "--" }}</option></select></label>
      <p>次数表示符合截止条件的不同方案数量；同一方案内相同比赛、玩法和投注组合只计算一次。</p>
    </section>

    <LoadingSkeleton v-if="loading" type="cards" :count="4" />
    <ErrorState v-else-if="error" class="app-card section-gap" :description="error" />
    <template v-else>
      <section class="focus-card app-card section-gap">
        <header class="section-header"><div><span class="eyebrow">Center picks · {{ playType }}</span><h2>各玩法重心分析</h2></div><p>按方案出现次数排序</p></header>
        <div v-if="focus.length" class="focus-grid">
          <article v-for="item in focus" :key="matchKey(item)">
            <h3>{{ item.match_code || "--" }} {{ item.match_name || "--" }}</h3>
            <div><strong>{{ item.option || "--" }}</strong><b>{{ number(item.count) }} 次</b><small>占该场玩法 {{ percent(item.share) }}</small></div>
          </article>
        </div>
        <EmptyState v-else title="今日暂无该玩法数据" description="没有符合今日截止且尚未截止条件的方案" />
      </section>

      <section class="matrix-card app-card section-gap">
        <header class="matrix-header"><div><span class="eyebrow">{{ playType }}</span><h2>赛事投注冷热矩阵</h2></div><span>{{ number(displayedMatches.length) }} 场赛事</span></header>
        <div v-if="displayedMatches.length" class="matrix-table-wrap">
          <table class="matrix-table">
            <thead><tr><th>赛事</th><th v-for="option in optionNames" :key="option">{{ option }}</th></tr></thead>
            <tbody><tr v-for="match in displayedMatches" :key="matchKey(match)"><th><b>{{ match.home || "--" }} VS {{ match.away || "--" }}</b><span>{{ match.match_code || "--" }} · {{ match.league || "--" }} · {{ number(match.total_items) }} 次</span></th><td v-for="option in optionNames" :key="option" :style="heatStyle(cell(match, option), match.total_items)"><template v-if="cell(match, option)"><strong>{{ percent(cell(match, option).share) }}</strong><small>{{ number(cell(match, option).count) }} 次</small></template><span v-else>—</span></td></tr></tbody>
          </table>
        </div>
        <EmptyState v-else title="没有符合筛选条件的赛事" description="请选择其他赛事或玩法" />
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue"
import axios from "axios"
import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"
import EmptyState from "../components/ui/EmptyState.vue"
import ErrorState from "../components/ui/ErrorState.vue"
import { readCached, writeCached } from "../utils/cache.js"

const plays = ["胜平负", "让球胜平负", "半全场", "比分"]
const playType = ref("胜平负")
const selectedMatch = ref("")
const data = ref({})
const loading = ref(true)
const error = ref("")
let refreshTimer
let requestController = null
let requestInFlight = false
let activePlay = ""
const playCache = new Map()

const matches = computed(() => data.value.matches || [])
const displayedMatches = computed(() => selectedMatch.value ? matches.value.filter((item) => matchKey(item) === selectedMatch.value) : matches.value)
const focus = computed(() => displayedMatches.value.slice(0, 4).map((item) => ({ ...item, ...(item.options?.[0] || {}) })))
const optionNames = computed(() => [...new Set(displayedMatches.value.flatMap((item) => (item.options || []).map((option) => option.option)))])

async function load() {
  const requestedPlay = playType.value
  if (requestInFlight && activePlay === requestedPlay) return
  const cached = playCache.get(requestedPlay) || readCached(`heatmap:${requestedPlay}`)?.payload
  if (cached) data.value = cached
  requestController?.abort()
  requestController = new AbortController()
  requestInFlight = true
  activePlay = requestedPlay
  const initialLoad = !Object.keys(data.value).length
  if (initialLoad) loading.value = true
  error.value = ""
  try {
    const response = await axios.get("/api/portal/heatmap", { params: { play_type: requestedPlay }, signal: requestController.signal, timeout: 25000 })
    if (response.data?.code !== 200) throw new Error()
    const next = response.data.data || {}
    playCache.set(requestedPlay, next)
    writeCached(`heatmap:${requestedPlay}`, next)
    if (playType.value !== requestedPlay) return
    data.value = next
    if (selectedMatch.value && !matches.value.some((item) => matchKey(item) === selectedMatch.value)) selectedMatch.value = ""
  } catch (requestError) {
    if (requestError?.code === "ERR_CANCELED") return
    if (initialLoad && !Object.keys(data.value).length) error.value = "热力数据暂时不可用"
  } finally { if (activePlay === requestedPlay) { requestInFlight = false; loading.value = false } }
}

function changePlay(play) { playType.value = play; selectedMatch.value = "" }
function matchKey(item) { return `${item.match_date || ""}|${item.match_code || ""}|${item.home || ""}|${item.away || ""}` }
function cell(match, option) { return (match.options || []).find((item) => item.option === option) }
function heatStyle(value, total) { const ratio = value && total ? Number(value.count || 0) / Number(total) : 0; return ratio ? { background: `rgba(117, 94, 225, ${Math.min(.12 + ratio * .42, .54)})` } : {} }
function number(value) { return Math.round(Number(value || 0)).toLocaleString("zh-CN") }
function percent(value) { return `${Number(value || 0).toFixed(1)}%` }

watch(playType, load)
function scheduleRefresh() {
  clearInterval(refreshTimer)
  refreshTimer = document.visibilityState === "visible" ? setInterval(load, 30000) : null
}
function handleVisibilityChange() {
  scheduleRefresh()
  if (document.visibilityState === "visible") load()
}
onMounted(() => {
  load()
  document.addEventListener("visibilitychange", handleVisibilityChange)
  scheduleRefresh()
})
onUnmounted(() => {
  clearInterval(refreshTimer)
  document.removeEventListener("visibilitychange", handleVisibilityChange)
  requestController?.abort()
})
</script>

<style scoped>
.heatmap-page{padding-bottom:32px}.heatmap-hero{min-height:94px;padding:16px;display:grid;grid-template-columns:180px 1fr 180px;align-items:center;text-align:center}.heatmap-hero h1{margin:4px 0 2px;font-size:25px}.heatmap-hero p{margin:0;color:var(--text-muted);font-size:11px}.back-button{justify-self:start;padding:10px 13px;border:1px solid var(--border);border-radius:10px;color:var(--text-secondary);background:var(--surface-soft);font-size:11px;font-weight:650}.refresh-note{justify-self:end;color:var(--text-muted);font-size:10px}.filter-band{margin-top:14px;padding:16px 20px;display:grid;grid-template-columns:minmax(500px,1fr) minmax(260px,340px);gap:14px;align-items:center}.play-tabs{display:flex;justify-content:center;gap:8px}.play-tabs button{min-width:96px;min-height:40px;padding:0 15px;border:1px solid #ded9ed;border-radius:999px;color:var(--text-secondary);background:#fff;font-size:12px;font-weight:700;transition:.18s ease}.play-tabs button:hover{border-color:#8a79e8;transform:translateY(-1px)}.play-tabs button.active{border-color:#7562df;color:#fff;background:#7562df;box-shadow:0 8px 18px rgba(95,72,213,.2)}.match-filter{justify-self:end;display:flex;align-items:center;gap:8px;color:var(--text-secondary);font-size:11px;font-weight:650}.match-filter select{min-width:260px;height:40px;padding:0 34px 0 12px;border:1px solid #ded9ed;border-radius:10px;color:var(--text-main);background:#fff}.filter-band p{grid-column:1/-1;margin:0;color:var(--text-muted);font-size:10px;text-align:center}.section-gap{margin-top:14px}.focus-card,.matrix-card{padding:20px}.focus-card .section-header>p{color:var(--text-muted);font-size:10px}.focus-grid{margin-top:16px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.focus-grid article{border:1px solid var(--border);border-radius:13px;overflow:hidden;background:#fff}.focus-grid h3{min-height:49px;margin:0;padding:12px;display:grid;place-items:center;color:#6551d9;background:#f2efff;font-size:11px;text-align:center}.focus-grid article>div{padding:18px 12px;text-align:center}.focus-grid strong,.focus-grid b,.focus-grid small{display:block}.focus-grid strong{font-size:14px}.focus-grid b{margin-top:6px;color:#6551d9;font-size:12px}.focus-grid small{margin-top:7px;color:var(--text-muted);font-size:10px}.matrix-header{display:flex;align-items:flex-end;justify-content:space-between}.matrix-header h2{margin:4px 0 0;font-size:20px}.matrix-header>span{color:var(--text-muted);font-size:10px}.matrix-table-wrap{margin:16px -20px -20px;overflow-x:auto}.matrix-table{width:100%;min-width:820px;border-collapse:collapse;table-layout:fixed}.matrix-table th,.matrix-table td{padding:14px 12px;border-top:1px solid var(--border);border-right:1px solid var(--border);text-align:center}.matrix-table thead th{color:#6551d9;background:#f2efff;font-size:12px}.matrix-table thead th:first-child{width:280px}.matrix-table tr>*:last-child{border-right:0}.matrix-table tbody th{text-align:left;background:#fff}.matrix-table tbody th b,.matrix-table tbody th span{display:block}.matrix-table tbody th b{font-size:14px;line-height:1.45}.matrix-table tbody th span{margin-top:6px;color:var(--text-muted);font-size:11px;font-weight:550}.matrix-table td strong,.matrix-table td small{display:block}.matrix-table td strong{color:#4b3978;font-size:15px}.matrix-table td small{margin-top:4px;color:#5c4c7e;font-size:10px}.matrix-table td>span{color:#b1b1b3}@media(max-width:1120px){.filter-band{grid-template-columns:1fr}.match-filter{justify-self:center}.focus-grid{grid-template-columns:repeat(2,1fr)}.heatmap-hero{grid-template-columns:1fr;gap:12px;text-align:left}.refresh-note{justify-self:start}}@media(max-width:700px){.play-tabs{justify-content:flex-start;overflow-x:auto}.play-tabs button{white-space:nowrap}.match-filter{width:100%;align-items:stretch;flex-direction:column}.match-filter select{min-width:0;width:100%}.focus-grid{grid-template-columns:1fr}.matrix-header{align-items:flex-start;flex-direction:column;gap:10px}}
.play-tabs{justify-content:center}
</style>
