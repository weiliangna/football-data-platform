<template>
  <section class="page-shell heatmap-page">
    <header class="heatmap-hero app-card">
      <router-link class="back-button" to="/">← 返回数据看板</router-link>
      <div><span class="eyebrow">Football betting heatmap</span><h1>足球场次比赛投注热力图</h1><p>仅统计今日未截止方案 · 四类玩法 · 独立投注项占比</p></div>
      <span class="hero-spacer" aria-hidden="true"></span>
    </header>

    <section class="filter-band app-card">
      <nav class="play-tabs" aria-label="玩法筛选"><button v-for="play in plays" :key="play" type="button" :class="{ active: playType === play }" @click="changePlay(play)">{{ play }}</button></nav>
      <p>占比 = 单场同一玩法下该投注项数量 ÷ 该玩法全部投注项数量。</p>
    </section>

    <LoadingSkeleton v-if="loading" class="section-gap" type="cards" :count="4" />
    <ErrorState v-else-if="error" class="app-card section-gap" :description="error" @retry="load" />
    <template v-else>
      <section class="focus-card app-card section-gap">
        <header class="section-header"><div><span class="eyebrow">Center picks · {{ playType }}</span><h2>各玩法重心分析</h2></div><p>按投注数量最多项自动提取前 4 场比赛</p></header>
        <div v-if="focus.length" class="focus-grid">
          <article v-for="item in focus.slice(0, 4)" :key="`${item.match_code}-${item.match_name}`">
            <h3>{{ item.match_code || "--" }} {{ item.match_name || "--" }}</h3>
            <div><strong>{{ item.option || "--" }}</strong><b>{{ number(item.count) }} 次投注</b><small>占该场该玩法 {{ item.share ?? "--" }}%</small></div>
          </article>
        </div>
        <EmptyState v-else title="暂无重心数据" description="当前玩法没有可提取的比赛" />
      </section>

      <section v-if="platformSummary.length" class="platform-strip app-card section-gap">
        <article v-for="item in platformSummary" :key="item.platform_id" :style="platformStyle(item.platform_id)"><span>{{ item.platform_name || "--" }}</span><strong>{{ number(item.total_items) }}</strong><small>投注项</small></article>
      </section>

      <section class="matrix-card app-card section-gap">
        <header class="matrix-header"><div><span class="eyebrow">{{ playType }}</span><h2>赛事投注冷热矩阵</h2></div><div class="matrix-tools"><span>共 {{ number(matches.length) }} 场</span><div class="legend"><i></i><i></i><i></i><i></i><span>热度</span></div></div></header>
        <div v-if="matches.length" class="matrix-table-wrap">
          <table class="matrix-table">
            <thead><tr><th>赛事</th><th v-for="option in optionColumns" :key="option">{{ option }}</th></tr></thead>
            <tbody>
              <tr v-for="match in matches" :key="`${match.match_code}-${match.match_name}`">
                <th><b>{{ match.home || "--" }} VS {{ match.away || "--" }}</b><span>{{ match.match_code || "--" }} · {{ match.league || "--" }} · {{ number(match.total_items) }} 项</span></th>
                <td v-for="option in optionColumns" :key="option" :style="heatStyle(optionItem(match, option)?.share)">
                  <template v-if="optionItem(match, option)"><strong>{{ optionItem(match, option).share ?? "--" }}%</strong><small>{{ number(optionItem(match, option).count) }} 次</small></template>
                  <span v-else>—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="暂无热力数据" description="今日未截止订单暂无该玩法数据" />
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import axios from "axios"
import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"
import EmptyState from "../components/ui/EmptyState.vue"
import ErrorState from "../components/ui/ErrorState.vue"

const plays = ["胜平负", "让球胜平负", "半全场", "比分"]
const playType = ref("胜平负")
const data = ref({})
const loading = ref(true)
const error = ref("")
const focus = computed(() => data.value.focus || [])
const platformSummary = computed(() => data.value.platform_summary || [])
const matches = computed(() => data.value.matches || [])
const optionColumns = computed(() => {
  const values = []
  matches.value.forEach((match) => (match.options || []).forEach((item) => {
    if (item.option && !values.includes(item.option)) values.push(item.option)
  }))
  return values
})

const platformColors = { 1: [239, 108, 19], 2: [126, 61, 232], 3: [220, 37, 112], 4: [39, 103, 232], 5: [8, 145, 178], 6: [25, 156, 85] }

async function load() {
  loading.value = true
  error.value = ""
  try {
    const response = await axios.get("/api/portal/heatmap", { params: { play_type: playType.value } })
    if (!response.data || response.data.code !== 200) throw new Error()
    data.value = response.data.data || {}
  } catch {
    data.value = {}
    error.value = "热力数据暂时无法读取，请稍后重试或检查接口连接状态"
  } finally { loading.value = false }
}

function changePlay(value) { playType.value = value; load() }
function number(value) { return Math.round(Number(value || 0)).toLocaleString("zh-CN") }
function optionItem(match, option) { return (match.options || []).find((item) => item.option === option) }
function platformStyle(id) { const color = platformColors[Number(id)] || [98, 98, 104]; return { color: `rgb(${color.join(",")})`, backgroundColor: `rgba(${color.join(",")},.12)`, borderColor: `rgba(${color.join(",")},.24)` } }
function heatStyle(value) { const share = Math.max(0, Math.min(Number(value || 0), 100)); const alpha = Math.max(.04, share / 100 * .28); return { backgroundColor: `rgba(116,102,239,${alpha})` } }

onMounted(load)
</script>

<style scoped>
.heatmap-page{padding-bottom:32px}.heatmap-hero{min-height:94px;padding:16px;display:grid;grid-template-columns:180px 1fr 180px;align-items:center;text-align:center}.heatmap-hero h1{margin:4px 0 2px;font-size:25px}.heatmap-hero p{margin:0;color:var(--text-muted);font-size:11px}.heatmap-hero>.primary-button{justify-self:end}.back-button{justify-self:start;padding:10px 13px;border:1px solid var(--border);border-radius:10px;color:var(--text-secondary);background:var(--surface-soft);font-size:11px;font-weight:650}.filter-band{margin-top:14px;padding:16px 20px}.play-tabs{display:flex;justify-content:center;gap:8px}.play-tabs button{min-width:96px;min-height:40px;padding:0 15px;border:1px solid #e1e1dc;border-radius:999px;color:var(--text-secondary);background:#fff;font-size:12px;font-weight:700}.play-tabs button.active{border-color:#252527;color:#fff;background:#252527;box-shadow:0 8px 18px rgba(32,32,35,.16)}.filter-band p{margin:14px 0 0;color:var(--text-muted);font-size:10px}.section-gap{margin-top:14px}.focus-card,.matrix-card{padding:20px}.focus-card .section-header>p{color:var(--text-muted);font-size:10px}.focus-grid{margin-top:16px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.focus-grid article{border:1px solid var(--border);border-radius:13px;overflow:hidden;background:#fff}.focus-grid h3{min-height:49px;margin:0;padding:12px;display:grid;place-items:center;color:#59651d;background:#f7f9ed;font-size:11px;text-align:center}.focus-grid article>div{padding:18px 12px;text-align:center}.focus-grid strong,.focus-grid b,.focus-grid small{display:block}.focus-grid strong{font-size:14px}.focus-grid b{margin-top:6px;color:#697b0c;font-size:12px}.focus-grid small{margin-top:7px;color:var(--text-muted);font-size:10px}.platform-strip{padding:12px;display:grid;grid-template-columns:repeat(6,1fr);gap:8px}.platform-strip article{padding:10px 12px;border:1px solid;border-radius:11px}.platform-strip span,.platform-strip strong,.platform-strip small{display:block}.platform-strip span{font-size:10px;font-weight:700}.platform-strip strong{margin-top:4px;color:var(--text-main);font-size:20px}.platform-strip small{color:var(--text-muted);font-size:9px}.matrix-header{display:flex;align-items:flex-end;justify-content:space-between}.matrix-header h2{margin:4px 0 0;font-size:20px}.matrix-tools{display:flex;align-items:center;gap:14px;color:var(--text-muted);font-size:10px}.legend{display:flex;align-items:center;gap:3px}.legend i{width:18px;height:9px;border-radius:2px}.legend i:nth-child(1){background:#fafaf8}.legend i:nth-child(2){background:#f2f9c8}.legend i:nth-child(3){background:#e5f587}.legend i:nth-child(4){background:#d9ff35}.matrix-table-wrap{margin:16px -20px -20px;overflow-x:auto}.matrix-table{width:100%;min-width:820px;border-collapse:collapse;table-layout:fixed}.matrix-table th,.matrix-table td{padding:13px 12px;border-top:1px solid var(--border);border-right:1px solid var(--border);text-align:center}.matrix-table thead th{color:#626f24;background:#f7f9ed;font-size:11px}.matrix-table thead th:first-child{width:230px}.matrix-table tr>*:last-child{border-right:0}.matrix-table tbody th{text-align:left;background:#fff}.matrix-table tbody th b,.matrix-table tbody th span{display:block}.matrix-table tbody th b{font-size:11px}.matrix-table tbody th span{margin-top:4px;color:var(--text-muted);font-size:9px;font-weight:500}.matrix-table td strong,.matrix-table td small{display:block}.matrix-table td strong{color:#66780b;font-size:14px}.matrix-table td small{margin-top:3px;color:var(--text-muted);font-size:9px}.matrix-table td>span{color:#b1b1b3}@media(max-width:1050px){.focus-grid{grid-template-columns:repeat(2,1fr)}.platform-strip{grid-template-columns:repeat(3,1fr)}}@media(max-width:700px){.heatmap-hero{grid-template-columns:1fr;gap:12px;text-align:left}.heatmap-hero>.primary-button,.back-button{justify-self:stretch;text-align:center}.play-tabs{justify-content:flex-start;overflow-x:auto}.play-tabs button{white-space:nowrap}.focus-grid{grid-template-columns:1fr}.platform-strip{grid-template-columns:repeat(2,1fr)}.matrix-header{align-items:flex-start;flex-direction:column;gap:10px}}
.hero-spacer{display:block}.focus-grid h3{color:#6551d9;background:#f2efff}.focus-grid b{color:#6551d9}.legend i:nth-child(1){background:#faf9ff}.legend i:nth-child(2){background:#eeeaff}.legend i:nth-child(3){background:#dcd4ff}.legend i:nth-child(4){background:#b9a9ff}.matrix-table thead th{color:#6551d9;background:#f2efff}.matrix-table td strong{color:#6551d9}@media(max-width:700px){.hero-spacer{display:none}}
</style>
