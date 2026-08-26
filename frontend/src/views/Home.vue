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
      <section class="kpi-grid">
        <article class="kpi-card featured lift-card"><span>今日入库方案</span><strong>{{ number(metrics.today_plans) }}</strong><small>今日累计</small><i>↗</i></article>
        <article class="kpi-card lift-card"><span>今日跟单</span><strong>{{ number(metrics.today_followers) }}</strong><small>聚合跟单人次</small><i>◎</i></article>
        <article class="kpi-card lift-card"><span>今日跟单金额</span><strong>--</strong><small>接口暂未提供跟单金额</small><i>¥</i></article>
        <article class="kpi-card lift-card"><span>昨日中奖</span><strong>{{ number(metrics.yesterday_wins) }}</strong><small>已结算中奖方案</small><i>✓</i></article>
      </section>

      <section class="activity-card app-card">
        <header class="section-header">
          <div><span class="eyebrow">Platform activity</span><h2>各平台投注活跃度</h2><p>今日各平台方案活跃情况；横轴为平台，不伪造 24 小时趋势</p></div>
          <span class="activity-total">{{ number(metrics.today_plans) }}<small>今日方案</small></span>
        </header>
        <PlatformActivityChart :rows="platformBets" />
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
import PlatformActivityChart from "../components/dashboard/PlatformActivityChart.vue"

const router = useRouter()
const data = ref({})
const selectedKey = ref("")
const loading = ref(true)
const error = ref("")
const now = ref(new Date())
let timer

const metrics = computed(() => data.value.metrics || {})
const platformBets = computed(() => data.value.platform_bets || [])
const ranking = computed(() => data.value.sender_ranking || [])
const selected = computed(() => ranking.value.find((item) => personKey(item) === selectedKey.value) || ranking.value[0] || null)
const currentDate = computed(() => now.value.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit", weekday: "short" }))
const currentTime = computed(() => now.value.toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit" }))

async function load() {
  loading.value = true
  error.value = ""
  try {
    const response = await axios.get("/api/portal/dashboard")
    if (!response.data || response.data.code !== 200) throw new Error()
    data.value = response.data.data || {}
    const first = (data.value.sender_ranking || [])[0]
    selectedKey.value = first ? personKey(first) : ""
  } catch {
    data.value = {}
    error.value = "实时数据暂时无法读取，请稍后重试或检查接口连接状态"
  } finally {
    loading.value = false
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
  timer = setInterval(() => { now.value = new Date() }, 30000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.kpi-card{position:relative;min-height:126px;padding:19px;border:1px solid var(--border);border-radius:var(--radius-lg);background:#fff;box-shadow:var(--shadow-card)}.kpi-card>span,.kpi-card>small,.kpi-card>strong{display:block}.kpi-card>span{color:var(--text-secondary);font-size:12px}.kpi-card>strong{margin-top:12px;font-size:31px;line-height:1}.kpi-card>small{margin-top:10px;color:var(--text-muted);font-size:11px}.kpi-card>i{position:absolute;right:18px;top:18px;width:28px;height:28px;border-radius:9px;display:grid;place-items:center;color:#6f810e;background:var(--accent-soft);font-style:normal;font-weight:700}.kpi-card.featured{color:#fff;border-color:#262628;background:#262628}.kpi-card.featured>span,.kpi-card.featured>small{color:#aaaab0}.kpi-card.featured>i{color:var(--accent);background:#343436}.activity-card{margin-top:14px;padding:21px}.activity-total{color:var(--text-main);font-size:27px;font-weight:700;text-align:right}.activity-total small{display:block;color:var(--text-muted);font-size:10px;font-weight:500}.sender-section{margin-top:14px;display:grid;grid-template-columns:minmax(330px,.4fr) minmax(0,.6fr);gap:14px}.ranking-card,.sender-panel{min-height:478px;padding:18px}.ranking-card .section-header a{color:#68790e;font-size:11px;font-weight:650}.ranking-list{height:350px;margin-top:13px;overflow-y:auto;overscroll-behavior:contain}.ranking-list button{width:100%;height:68px;padding:8px;border:1px solid transparent;border-radius:12px;display:grid;grid-template-columns:28px 40px minmax(0,1fr) auto;gap:9px;align-items:center;color:var(--text-main);background:transparent;text-align:left}.ranking-list button:hover,.ranking-list button.selected{border-color:#e2e9bc;background:#fafcef}.rank{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;color:var(--text-muted);background:#f1f1ee;font-size:10px;font-weight:700}.rank-1{color:var(--accent-text);background:var(--accent)}.rank-2{background:#e9e9e5}.rank-3{color:#8b6033;background:#f0e2d3}.person,.person-meta{min-width:0}.person b,.person small,.person-meta b,.person-meta small{display:block}.person b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}.person small,.person-meta small{margin-top:3px;color:var(--text-muted);font-size:10px}.person-meta{text-align:right}.person-meta b{font-size:12px}.sender-profile{padding-bottom:15px;display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--border)}.profile-avatar{width:55px;height:55px;flex:0 0 55px;border-radius:50%;object-fit:cover}.sender-profile>div{min-width:0;flex:1}.sender-profile h2{margin:0;font-size:20px}.sender-profile p{margin:4px 0 0;color:var(--text-muted);font-size:11px}.sender-kpis{margin-top:12px;display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.sender-kpis>div{padding:12px;border-radius:11px;background:var(--surface-soft)}.sender-kpis span,.sender-kpis strong{display:block}.sender-kpis span{color:var(--text-muted);font-size:10px}.sender-kpis strong{margin-top:6px;font-size:15px}.orders-title{margin:16px 0 9px;display:flex;align-items:center;justify-content:space-between}.orders-title h3{margin:0;font-size:15px}.orders-title span{color:var(--text-muted);font-size:11px}.scheme-list{max-height:330px;display:grid;gap:9px;overflow-y:auto}.scheme-sheet{border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#fff;cursor:pointer}.scheme-sheet>header{min-height:36px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);background:#fafafa}.scheme-sheet>header strong{font-size:12px}.scheme-sheet>header span{color:var(--text-muted);font-size:9px}.scheme-meta{padding:7px 12px;display:flex;gap:18px;align-items:center;border-bottom:1px solid var(--border);font-size:10px}.scheme-meta span:last-child{margin-left:auto}.scheme-table-wrap{overflow-x:auto}.scheme-sheet table{width:100%;border-collapse:collapse;font-size:10px}.scheme-sheet th,.scheme-sheet td{padding:7px 10px;border-right:1px solid var(--border);border-bottom:1px solid var(--border);text-align:left}.scheme-sheet th:last-child,.scheme-sheet td:last-child{border-right:0}.scheme-sheet tbody tr:last-child td{border-bottom:0}.scheme-sheet th{color:var(--text-muted);font-weight:600;background:#fcfcfb}@media(max-width:1100px){.kpi-grid{grid-template-columns:repeat(2,1fr)}.sender-section{grid-template-columns:1fr}.sender-panel{min-height:auto}}@media(max-width:700px){.sender-kpis{grid-template-columns:1fr}.sender-profile{align-items:flex-start;flex-wrap:wrap}.sender-profile .secondary-button{margin-left:67px}.scheme-sheet>header,.scheme-meta{align-items:flex-start;flex-direction:column;gap:4px}.scheme-meta span:last-child{margin-left:0}}@media(max-width:479px){.kpi-grid{grid-template-columns:1fr}.ranking-list button{grid-template-columns:25px 40px minmax(0,1fr)}.person-meta{display:none}.sender-profile .secondary-button{margin-left:0;width:100%}}
</style>
