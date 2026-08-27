<template>
  <section class="page-shell home-page">
    <header class="page-header">
      <div>
        <h1>今日总览</h1>
        <p>多平台足球方案与投注数据实时聚合 · {{ data.day || "日期待同步" }}</p>
      </div>
      <div class="page-actions">
        <span class="page-time">{{ currentDate }} {{ currentTime }}</span>
        <button class="primary-button" type="button" @click="load">刷新</button>
      </div>
    </header>

    <LoadingSkeleton v-if="loading" type="cards" :count="4" />
    <ErrorState v-else-if="error" class="app-card" :description="error" @retry="load" />
    <template v-else>
      <section class="overview-analysis">
        <aside class="overview-metrics">
          <div class="metric-mini-grid">
            <article class="metric-mini lift-card"><span>昨日方案</span><strong>{{ number(metrics.yesterday_plans) }}</strong><small>份</small></article>
            <article class="metric-mini lift-card"><span>已中奖</span><strong>{{ number(metrics.yesterday_wins) }}</strong><small>份</small></article>
            <article class="metric-mini lift-card"><span>今日方案</span><strong>{{ number(metrics.today_plans) }}</strong><small>份</small></article>
            <article class="metric-mini lift-card"><span>今日跟单人数</span><strong>{{ number(metrics.today_followers) }}</strong><small>人次</small></article>
          </div>
          <article class="total-amount-card lift-card"><span>今日跟单金额</span><strong>¥{{ money(metrics.today_amount) }}</strong><small>按真实方案投注金额汇总</small></article>
        </aside>

        <article class="analysis-card app-card">
          <header class="analysis-header"><div><span class="eyebrow">Data analysis</span><h2>昨日数据分析</h2></div><time>{{ data.day || "--" }}</time></header>
          <div class="analysis-body">
            <div class="result-overview">
              <div class="donut" :style="{ '--win': winPercent + '%' }"><div><strong>{{ number(metrics.yesterday_settled) }}</strong><small>已开奖</small></div></div>
              <div class="result-legend"><span><i class="won"></i>中奖数量 <b>{{ number(metrics.yesterday_wins) }}</b></span><span><i class="lost"></i>未中奖数量 <b>{{ number(metrics.yesterday_lost) }}</b></span></div>
            </div>
            <div class="trend-panel">
              <header><b>今日各平台发单分布</b><small>使用实时采集数量</small></header>
              <svg viewBox="0 0 700 175" preserveAspectRatio="none" role="img" aria-label="今日各平台发单数量">
                <defs><linearGradient id="homeTrend" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7466ef"/><stop offset="55%" stop-color="#aa64e8"/><stop offset="100%" stop-color="#38bca8"/></linearGradient><linearGradient id="homeArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#896fe4" stop-opacity=".18"/><stop offset="1" stop-color="#896fe4" stop-opacity="0"/></linearGradient></defs>
                <line v-for="y in [25,65,105,145]" :key="y" x1="15" :y1="y" x2="685" :y2="y" class="chart-grid"/>
                <path v-if="platformPoints.length" :d="platformArea" class="chart-area"/>
                <path v-if="platformPoints.length" :d="platformPath" class="chart-line"/>
                <g v-for="point in platformPoints" :key="point.id"><circle :cx="point.x" :cy="point.y" r="4" class="chart-dot"><title>{{ point.name }}：{{ number(point.count) }} 份</title></circle><text :x="point.x" y="171" text-anchor="middle" class="chart-label">{{ point.name }}</text></g>
              </svg>
            </div>
          </div>
        </article>
      </section>

      <section class="hot-plays app-card">
        <header class="section-header"><div><span class="eyebrow">Today hot picks</span><h2>今日热门玩法</h2><p>仅统计今天截止且当前仍未截止的方案，每 30 秒自动更新</p></div></header>
        <div class="hot-grid">
          <article v-for="group in hotPlays" :key="group.play_type" class="hot-card lift-card">
            <header><span>{{ group.play_type }}</span><small>TOP 3</small></header>
            <ol v-if="group.items?.length">
              <li v-for="(item, index) in group.items" :key="`${item.match_code}-${item.match_name}-${item.selection}`"><b>{{ index + 1 }}</b><div><strong>{{ item.match_code || "--" }} · {{ item.home || "--" }} VS {{ item.away || "--" }}</strong><span>{{ time(item.deadline_time) }} · {{ item.league || "--" }}</span><em>{{ item.selection }}</em></div><i>{{ number(item.count) }} 次</i></li>
            </ol>
            <p v-else>今日暂无该玩法数据</p>
          </article>
        </div>
      </section>

      <section class="sender-section">
        <article class="ranking-card app-card">
          <header class="section-header">
            <div><h2>当日发单排行</h2><p>默认展示 5 位，其余向下滑动查看</p></div>
            <router-link to="/users">全部用户 →</router-link>
          </header>
          <div v-if="ranking.length" class="ranking-list">
            <button
              v-for="person in ranking"
              :key="personKey(person)"
              type="button"
              :class="{ selected: personKey(person) === selectedKey }"
              @mouseenter="select(person)"
              @focus="select(person)"
              @click="select(person)"
            >
              <span class="rank" :class="'rank-' + person.rank">{{ person.rank }}</span>
              <img v-if="person.avatar_url" class="avatar" :src="person.avatar_url" alt="">
              <span v-else class="avatar-fallback">{{ avatarText(person.nickname) }}</span>
              <span class="person"><b>{{ person.nickname || "--" }}</b><small>{{ person.platform_name || "--" }} · {{ number(person.order_count) }} 单</small></span>
              <span class="person-meta"><b>¥{{ money(person.amount) }}</b><small>{{ number(person.followers) }} 人跟单</small></span>
            </button>
          </div>
          <EmptyState v-else title="暂无发单排行" description="今日未截止方案尚未形成用户排行" />
        </article>

        <article class="sender-panel app-card">
          <template v-if="selected">
            <header class="sender-profile">
              <img v-if="selected.avatar_url" class="profile-avatar" :src="selected.avatar_url" alt="">
              <span v-else class="profile-avatar avatar-fallback">{{ avatarText(selected.nickname) }}</span>
              <div><span class="eyebrow">Sender profile</span><h2>{{ selected.nickname || "--" }}</h2><p>{{ selected.platform_name || "--" }} · 用户 ID {{ selected.user_id || "--" }}</p></div>
              <button class="secondary-button" type="button" @click="openUser(selected)">用户详情</button>
            </header>
            <div class="sender-kpis">
              <div><span>命中率</span><strong>{{ percent(selected.history_hit_rate) }}</strong></div>
              <div><span>今日自购</span><strong>¥{{ money(selected.amount) }}</strong></div>
              <div><span>跟单人数</span><strong>{{ number(selected.followers) }}</strong></div>
            </div>
            <div class="orders-title"><h3>当日方案</h3><span>{{ selected.orders?.length || 0 }} 条</span></div>
            <div v-if="selected.orders?.length" class="scheme-list">
              <article v-for="order in selected.orders" :key="order.id" class="scheme-sheet" tabindex="0" @click="openOrder(order.id)" @keyup.enter="openOrder(order.id)">
                <header><strong>投注方案详情</strong><span>{{ order.platform_order_id || order.id || "--" }} · {{ time(order.publish_time) }}</span></header>
                <div class="scheme-meta"><span>过关玩法 <b>{{ order.pass_composition || passText(order) }}</b></span><span>跟单金额 <b>¥{{ money(order.stake) }}</b></span><span :class="resultClass(order.result)">{{ resultText(order.result) }}</span></div>
                <div class="scheme-table-wrap">
                  <table>
                    <thead><tr><th>比赛</th><th>玩法</th><th>投注</th><th>SP</th></tr></thead>
                    <tbody>
                      <tr v-for="match in order.matches || []" :key="match.id || match.match_code">
                        <td>{{ match.match_code || "--" }} · {{ match.home || "--" }} VS {{ match.away || "--" }}</td>
                        <td>{{ match.play_type || "--" }}</td>
                        <td>{{ match.selection || "--" }}</td>
                        <td>{{ match.odds || match.odds_text || "--" }}</td>
                      </tr>
                      <tr v-if="!(order.matches || []).length"><td colspan="4">比赛明细待同步</td></tr>
                    </tbody>
                  </table>
                </div>
              </article>
            </div>
            <EmptyState v-else title="暂无当日方案" description="该用户当前没有未截止方案" />
          </template>
          <EmptyState v-else title="暂无发单人信息" description="选择排行用户后在此查看投注信息" />
        </article>
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"
import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"
import EmptyState from "../components/ui/EmptyState.vue"
import ErrorState from "../components/ui/ErrorState.vue"

const router = useRouter()
const data = ref({})
const selectedKey = ref("")
const loading = ref(true)
const error = ref("")
let requestInFlight = false
const now = ref(new Date())
let timer

const metrics = computed(() => data.value.metrics || {})
const platformBets = computed(() => data.value.platform_bets || [])
const winPercent = computed(() => {
  const settled = Number(metrics.value.yesterday_settled || 0)
  return settled ? Math.round(Number(metrics.value.yesterday_wins || 0) / settled * 100) : 0
})
const platformPoints = computed(() => {
  const rows = platformBets.value
  const max = Math.max(1, ...rows.map((item) => Number(item.order_count || 0)))
  const step = rows.length > 1 ? 630 / (rows.length - 1) : 0
  return rows.map((item, index) => ({ id: item.platform_id, name: item.platform_name, count: Number(item.order_count || 0), x: 35 + index * step, y: 145 - Number(item.order_count || 0) / max * 115 }))
})
const platformPath = computed(() => platformPoints.value.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" "))
const platformArea = computed(() => platformPoints.value.length ? `${platformPath.value} L ${platformPoints.value.at(-1).x} 145 L ${platformPoints.value[0].x} 145 Z` : "")
const ranking = computed(() => data.value.sender_ranking || [])
const hotPlays = computed(() => data.value.hot_plays || ["胜平负", "让球胜平负", "半全场", "比分"].map((play_type) => ({ play_type, items: [] })))
const selected = computed(() => ranking.value.find((item) => personKey(item) === selectedKey.value) || ranking.value[0] || null)
const currentDate = computed(() => now.value.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit", weekday: "short" }))
const currentTime = computed(() => now.value.toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit" }))

async function load() {
  if (requestInFlight) return
  requestInFlight = true
  loading.value = true
  error.value = ""
  try {
    const response = await axios.get("/api/portal/dashboard", { timeout: 25000 })
    if (!response.data || response.data.code !== 200) throw new Error()
    data.value = response.data.data || {}
    const first = (data.value.sender_ranking || [])[0]
    selectedKey.value = first ? personKey(first) : ""
  } catch {
    data.value = {}
    error.value = "实时数据暂时无法读取，请稍后重试或检查接口连接状态"
  } finally {
    loading.value = false
    requestInFlight = false
  }
}

function personKey(person) { return `${person.platform_id}-${person.user_id}` }
function select(person) { selectedKey.value = personKey(person) }
function openUser(person) { router.push(`/user/detail/${person.platform_id}/${person.user_id}`) }
function openOrder(id) { router.push(`/order/detail/${id}`) }
function avatarText(value) { return String(value || "球").slice(-1) }
function number(value) { return Math.round(Number(value || 0)).toLocaleString("zh-CN") }
function money(value) { return Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 2 }) }
function percent(value) { return value === null || value === undefined ? "--" : `${Number(value).toFixed(2)}%` }
function time(value) { return value ? String(value).replace("T", " ").replace("Z", "") : "--" }
function passText(order) { return Number(order.bet_count || 0) > 0 ? `${order.bet_count}注 ${order.pass_summary || "--"}` : (order.pass_summary || "--") }
function resultText(value) { return value === "赢" ? "已中奖" : value === "输" ? "未中奖" : (value || "待开奖") }
function resultClass(value) { return `status-chip ${value === "赢" ? "success" : value === "输" ? "danger" : "warning"}` }

onMounted(() => {
  load()
  timer = setInterval(() => { now.value = new Date(); load() }, 30000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.kpi-card{position:relative;min-height:126px;padding:19px;border:1px solid var(--border);border-radius:var(--radius-lg);background:#fff;box-shadow:var(--shadow-card)}.kpi-card>span,.kpi-card>small,.kpi-card>strong{display:block}.kpi-card>span{color:var(--text-secondary);font-size:12px}.kpi-card>strong{margin-top:12px;font-size:31px;line-height:1}.kpi-card>small{margin-top:10px;color:var(--text-muted);font-size:11px}.kpi-card>i{position:absolute;right:18px;top:18px;width:28px;height:28px;border-radius:9px;display:grid;place-items:center;color:#6f810e;background:var(--accent-soft);font-style:normal;font-weight:700}.kpi-card.featured{color:#fff;border-color:#262628;background:#262628}.kpi-card.featured>span,.kpi-card.featured>small{color:#aaaab0}.kpi-card.featured>i{color:var(--accent);background:#343436}.activity-card{margin-top:14px;padding:21px}.activity-total{color:var(--text-main);font-size:27px;font-weight:700;text-align:right}.activity-total small{display:block;color:var(--text-muted);font-size:10px;font-weight:500}.sender-section{margin-top:14px;display:grid;grid-template-columns:minmax(330px,.4fr) minmax(0,.6fr);gap:14px}.ranking-card,.sender-panel{min-height:478px;padding:18px}.ranking-card .section-header a{color:#68790e;font-size:11px;font-weight:650}.ranking-list{height:350px;margin-top:13px;overflow-y:auto;overscroll-behavior:contain}.ranking-list button{width:100%;height:68px;padding:8px;border:1px solid transparent;border-radius:12px;display:grid;grid-template-columns:28px 40px minmax(0,1fr) auto;gap:9px;align-items:center;color:var(--text-main);background:transparent;text-align:left}.ranking-list button:hover,.ranking-list button.selected{border-color:#e2e9bc;background:#fafcef}.rank{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;color:var(--text-muted);background:#f1f1ee;font-size:10px;font-weight:700}.rank-1{color:var(--accent-text);background:var(--accent)}.rank-2{background:#e9e9e5}.rank-3{color:#8b6033;background:#f0e2d3}.person,.person-meta{min-width:0}.person b,.person small,.person-meta b,.person-meta small{display:block}.person b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}.person small,.person-meta small{margin-top:3px;color:var(--text-muted);font-size:10px}.person-meta{text-align:right}.person-meta b{font-size:12px}.sender-profile{padding-bottom:15px;display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--border)}.profile-avatar{width:55px;height:55px;flex:0 0 55px;border-radius:50%;object-fit:cover}.sender-profile>div{min-width:0;flex:1}.sender-profile h2{margin:0;font-size:20px}.sender-profile p{margin:4px 0 0;color:var(--text-muted);font-size:11px}.sender-kpis{margin-top:12px;display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.sender-kpis>div{padding:12px;border-radius:11px;background:var(--surface-soft)}.sender-kpis span,.sender-kpis strong{display:block}.sender-kpis span{color:var(--text-muted);font-size:10px}.sender-kpis strong{margin-top:6px;font-size:15px}.orders-title{margin:16px 0 9px;display:flex;align-items:center;justify-content:space-between}.orders-title h3{margin:0;font-size:15px}.orders-title span{color:var(--text-muted);font-size:11px}.scheme-list{max-height:330px;display:grid;gap:9px;overflow-y:auto}.scheme-sheet{border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#fff;cursor:pointer}.scheme-sheet>header{min-height:36px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);background:#fafafa}.scheme-sheet>header strong{font-size:12px}.scheme-sheet>header span{color:var(--text-muted);font-size:9px}.scheme-meta{padding:7px 12px;display:flex;gap:18px;align-items:center;border-bottom:1px solid var(--border);font-size:10px}.scheme-meta span:last-child{margin-left:auto}.scheme-table-wrap{overflow-x:auto}.scheme-sheet table{width:100%;border-collapse:collapse;font-size:10px}.scheme-sheet th,.scheme-sheet td{padding:7px 10px;border-right:1px solid var(--border);border-bottom:1px solid var(--border);text-align:left}.scheme-sheet th:last-child,.scheme-sheet td:last-child{border-right:0}.scheme-sheet tbody tr:last-child td{border-bottom:0}.scheme-sheet th{color:var(--text-muted);font-weight:600;background:#fcfcfb}@media(max-width:1100px){.kpi-grid{grid-template-columns:repeat(2,1fr)}.sender-section{grid-template-columns:1fr}.sender-panel{min-height:auto}}@media(max-width:700px){.sender-kpis{grid-template-columns:1fr}.sender-profile{align-items:flex-start;flex-wrap:wrap}.sender-profile .secondary-button{margin-left:67px}.scheme-sheet>header,.scheme-meta{align-items:flex-start;flex-direction:column;gap:4px}.scheme-meta span:last-child{margin-left:0}}@media(max-width:479px){.kpi-grid{grid-template-columns:1fr}.ranking-list button{grid-template-columns:25px 40px minmax(0,1fr)}.person-meta{display:none}.sender-profile .secondary-button{margin-left:0;width:100%}}
.overview-analysis{display:grid;grid-template-columns:316px minmax(0,1fr);gap:16px}.overview-metrics{display:grid;gap:12px}.metric-mini-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.metric-mini,.total-amount-card{position:relative;overflow:hidden;border:1px solid var(--border);border-radius:15px;background:#fff;box-shadow:var(--shadow-card)}.metric-mini{min-height:102px;padding:18px;text-align:center}.metric-mini::after{content:"";position:absolute;right:-20px;bottom:-30px;width:76px;height:76px;border-radius:50%;background:#f3efff}.metric-mini:nth-child(2)::after{background:#fff0f4}.metric-mini:nth-child(3)::after{background:#eef6ff}.metric-mini:nth-child(4)::after{background:#e9faf4}.metric-mini span,.metric-mini small,.total-amount-card span,.total-amount-card small{display:block;color:var(--text-muted);font-size:11px}.metric-mini strong{position:relative;z-index:1;display:inline-block;margin-top:7px;font-size:25px}.metric-mini small{position:relative;z-index:1;display:inline;margin-left:4px}.total-amount-card{min-height:96px;padding:17px;display:grid;place-content:center;text-align:center}.total-amount-card::after{content:"";position:absolute;right:-24px;bottom:-34px;width:90px;height:90px;border-radius:50%;background:#fff5e9}.total-amount-card strong{position:relative;z-index:1;margin:6px 0 3px;font-size:25px}.analysis-card{padding:20px}.analysis-header{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:13px;border-bottom:1px solid var(--border)}.analysis-header h2{margin:4px 0 0;font-size:20px}.analysis-header time{color:var(--text-muted);font-size:10px}.analysis-body{min-height:215px;display:grid;grid-template-columns:340px minmax(0,1fr);gap:24px;align-items:center}.result-overview{padding-right:22px;display:flex;align-items:center;gap:18px;border-right:1px solid var(--border)}.donut{--win:0%;width:132px;height:132px;flex:0 0 132px;padding:18px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#e451ad var(--win),#40c8b1 0)}.donut::before{content:"";grid-area:1/1;width:84px;height:84px;border-radius:50%;background:#fff}.donut>div{z-index:1;grid-area:1/1;text-align:center}.donut strong,.donut small{display:block}.donut strong{font-size:25px}.donut small{margin-top:3px;color:var(--text-muted);font-size:9px}.result-legend{min-width:145px;display:grid;gap:18px}.result-legend span{display:grid;grid-template-columns:8px minmax(0,1fr) auto;gap:8px;align-items:center;color:var(--text-secondary);font-size:10px}.result-legend i{width:7px;height:7px;border-radius:50%}.result-legend .won{background:#e451ad}.result-legend .lost{background:#40c8b1}.result-legend b{color:var(--text-main);font-size:13px}.trend-panel header{display:flex;align-items:center;justify-content:space-between}.trend-panel header b{font-size:11px}.trend-panel header small{color:var(--text-muted);font-size:9px}.trend-panel svg{width:100%;height:178px;margin-top:5px;overflow:visible}.chart-grid{stroke:#eceaf2;stroke-width:1}.chart-area{fill:url(#homeArea)}.chart-line{fill:none;stroke:url(#homeTrend);stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.chart-dot{fill:#fff;stroke:#8067e8;stroke-width:2;transition:r .16s ease}.chart-dot:hover{r:7}.chart-label{fill:#9d97a7;font-size:9px}@media(max-width:1150px){.overview-analysis{grid-template-columns:1fr}.overview-metrics{grid-template-columns:minmax(0,1fr) 250px}.sender-section{grid-template-columns:1fr}.sender-panel{min-height:auto}}@media(max-width:800px){.overview-metrics{grid-template-columns:1fr}.analysis-body{grid-template-columns:1fr}.result-overview{padding:18px 0;border-right:0;border-bottom:1px solid var(--border)}}@media(max-width:479px){.metric-mini-grid{grid-template-columns:1fr}.result-overview{align-items:flex-start;flex-direction:column}}
.hot-plays{margin-top:14px;padding:18px}.hot-plays .section-header p{margin:4px 0 0;color:var(--text-muted);font-size:10px}.hot-grid{margin-top:14px;display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.hot-card{min-width:0;border:1px solid var(--border);border-radius:13px;overflow:hidden;background:#fff}.hot-card>header{padding:11px 13px;display:flex;align-items:center;justify-content:space-between;color:#6551d9;background:#f2efff}.hot-card>header span{font-weight:750}.hot-card>header small{font-size:8px}.hot-card ol{margin:0;padding:6px 10px 10px;list-style:none}.hot-card li{padding:9px 0;display:grid;grid-template-columns:22px minmax(0,1fr) auto;gap:7px;align-items:center;border-bottom:1px solid var(--border)}.hot-card li:last-child{border-bottom:0}.hot-card li>b{width:20px;height:20px;border-radius:50%;display:grid;place-items:center;color:#fff;background:#7968ee;font-size:9px}.hot-card li div{min-width:0}.hot-card li strong,.hot-card li span,.hot-card li em{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.hot-card li strong{font-size:10px}.hot-card li span{margin-top:3px;color:var(--text-muted);font-size:8px}.hot-card li em{margin-top:4px;color:#6551d9;font-size:9px;font-style:normal;font-weight:700}.hot-card li>i{color:#2e876e;font-size:10px;font-style:normal;font-weight:750}.hot-card>p{min-height:155px;margin:0;display:grid;place-items:center;color:var(--text-muted);font-size:10px}@media(max-width:1150px){.hot-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:620px){.hot-grid{grid-template-columns:1fr}}
</style>
