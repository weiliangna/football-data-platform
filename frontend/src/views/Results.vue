<template>
  <section class="page-shell results-page">
    <header class="archive-hero app-card">
      <router-link class="back-button" to="/">← 返回数据看板</router-link>
      <div><span class="eyebrow">Result archive</span><h1>赛果统计</h1><p>投注结算时间归档 · 球队与赛事编号统一使用鸿瑞展示口径</p></div>
      <div class="archive-actions">
        <button class="primary-button" type="button" @click="load">刷新赛果</button>
        <button class="secondary-button" type="button" :disabled="!rows.length" @click="savePng">保存图片</button>
        <button class="secondary-button" type="button" :disabled="!rows.length" @click="saveExcel">保存 Excel</button>
        <button class="secondary-button" type="button" @click="collapsed = !collapsed">{{ collapsed ? "展开" : "收起" }}</button>
        <button class="danger-button" type="button" @click="clearArchive">一键清空</button>
      </div>
    </header>

    <section class="search-bar app-card">
      <input v-model.trim="keyword" type="search" placeholder="搜索发单人、订单号、球队或方案内容" @keyup.enter="resetLoad">
      <button class="secondary-button" type="button" @click="resetLoad">查找</button>
    </section>

    <section v-if="!collapsed" class="calendar-shell app-card">
      <header class="month-tools">
        <button class="month-primary" type="button" @click="shiftMonth(-1)">‹ {{ previousMonthLabel }}</button>
        <strong>{{ monthLabel }}</strong>
        <button class="month-secondary" type="button" @click="shiftMonth(1)">{{ nextMonthLabel }} ›</button>
      </header>
      <div class="calendar-grid weekdays"><span v-for="name in weekdays" :key="name">{{ name }}</span></div>
      <div class="calendar-grid calendar-days">
        <button v-for="cell in calendarCells" :key="cell.key" type="button" :class="{ muted: !cell.current, selected: selectedDay === cell.date, available: cell.count > 0 }" @click="selectDay(cell)">
          <span>{{ cell.day }}</span><i v-if="cell.count > 0">✓</i><small>{{ cell.count > 0 ? `${number(cell.count)} 个方案` : "暂无数据" }}</small>
        </button>
      </div>
    </section>

    <section class="archive-summary app-card">
      <div><span>本月方案</span><strong>{{ number(summary.total) }}</strong></div>
      <div><span>已中奖</span><strong>{{ number(summary.won) }}</strong></div>
      <div><span>未中奖</span><strong>{{ number(summary.lost) }}</strong></div>
      <div><span>待开奖</span><strong>{{ number(summary.pending) }}</strong></div>
      <div><span>发单总金额</span><strong>¥{{ money(summary.total_stake) }}</strong></div>
      <div><span>跟单人数</span><strong>{{ number(summary.followers) }}</strong></div>
    </section>

    <section class="archive-note">{{ monthLabel }} · 共 {{ number(total) }} 个方案 · 当前显示 {{ pageStart }}-{{ pageEnd }} · 按发单时间倒序</section>

    <section class="date-card app-card">
      <header class="date-header"><strong>{{ selectedDay || month }}</strong><span>{{ number(total) }} 个方案</span><div><button type="button" :class="{ active: status === 'pending' }" @click="setStatus('pending')">未开奖</button><button type="button" :class="{ active: status === 'won' }" @click="setStatus('won')">已中奖</button><button type="button" :class="{ active: !status }" @click="setStatus('')">全部</button></div></header>
      <LoadingSkeleton v-if="loading" :count="8"/>
      <ErrorState v-else-if="error" :description="error" @retry="load"/>
      <EmptyState v-else-if="!rows.length" title="暂无赛果记录" description="当前日期或筛选条件下没有方案数据"/>
      <div v-else class="table-wrap">
        <table class="archive-table">
          <thead><tr><th>发单人</th><th>历史战绩</th><th>自购金额</th><th>跟单人数</th><th>中奖金额</th><th>注数</th><th>方案详情 / SP</th><th>赛果</th></tr></thead>
          <tbody><tr v-for="item in rows" :key="item.id">
            <td><div class="sender"><img v-if="item.avatar_url" :src="item.avatar_url" alt=""><span v-else>{{ avatarText(item.nickname) }}</span><b>{{ item.nickname || "--" }}<small>{{ item.platform_name }} · {{ item.platform_order_id }}</small></b></div></td>
            <td><strong class="purple">{{ item.history_record || "--" }}</strong></td>
            <td>¥{{ money(item.stake) }}</td>
            <td>{{ number(item.follow_num) }} 人</td>
            <td>{{ item.result === "待开奖" ? "待开奖" : `¥${money(item.platform_bonus)}` }}</td>
            <td>{{ passText(item) }}</td>
            <td class="details"><div v-for="match in item.matches || []" :key="match.id"><b>{{ match.match_code || "--" }} · {{ match.home || "--" }} VS {{ match.away || "--" }}</b><span>[{{ match.play_type || "--" }}：{{ match.selection || "--" }}]<em>SP {{ match.odds || "--" }}</em></span></div><span v-if="!(item.matches || []).length">比赛明细待同步 · SP {{ item.odds_text || "--" }}</span></td>
            <td><span :class="resultClass(item.result)">{{ resultText(item.result) }}</span></td>
          </tr></tbody>
        </table>
      </div>
    </section>
    <AppPagination :page="page" :pages="pages" :disabled="loading" @change="changePage"/>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import axios from "axios"
import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"
import EmptyState from "../components/ui/EmptyState.vue"
import ErrorState from "../components/ui/ErrorState.vue"
import AppPagination from "../components/ui/AppPagination.vue"
import { downloadExcel, downloadTextPng, stamp } from "../utils/export.js"

const now = new Date()
const rows = ref([])
const summary = ref({})
const dateCounts = ref([])
const month = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`)
const selectedDay = ref("")
const keyword = ref("")
const status = ref("")
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const loading = ref(true)
const error = ref("")
const collapsed = ref(false)
const pageSize = 100
const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
const countMap = computed(() => Object.fromEntries(dateCounts.value.map((item) => [item.day, Number(item.count || 0)])))
const monthDate = computed(() => { const [year, value] = month.value.split("-").map(Number); return new Date(year, value - 1, 1) })
const monthLabel = computed(() => `${monthDate.value.getFullYear()}年${String(monthDate.value.getMonth() + 1).padStart(2, "0")}月`)
const previousMonthLabel = computed(() => monthText(-1))
const nextMonthLabel = computed(() => monthText(1))
const pageStart = computed(() => total.value ? (page.value - 1) * pageSize + 1 : 0)
const pageEnd = computed(() => Math.min(page.value * pageSize, total.value))
const calendarCells = computed(() => {
  const base = monthDate.value
  const start = new Date(base.getFullYear(), base.getMonth(), 1 - base.getDay())
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + index)
    const value = localDate(date)
    return { key: value, date: value, day: date.getDate(), current: date.getMonth() === base.getMonth(), count: countMap.value[value] || 0 }
  })
})

async function load() {
  loading.value = true
  error.value = ""
  try {
    const response = await axios.get("/api/hub/results", { params: { month: month.value, day: selectedDay.value, keyword: keyword.value, status: status.value, page: page.value, page_size: pageSize } })
    if (response.data?.code !== 200) throw new Error()
    const data = response.data.data || {}
    rows.value = data.rows || []
    summary.value = data.summary || {}
    dateCounts.value = data.date_counts || []
    pages.value = data.pages || 1
    total.value = data.total || 0
  } catch {
    rows.value = []
    error.value = "赛果数据暂时无法读取，请稍后重试或检查接口连接状态"
  } finally { loading.value = false }
}

function localDate(date) { const two = (value) => String(value).padStart(2, "0"); return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}` }
function monthText(offset) { const date = new Date(monthDate.value.getFullYear(), monthDate.value.getMonth() + offset, 1); return `${date.getFullYear()}年${date.getMonth() + 1}月` }
function shiftMonth(offset) { const date = new Date(monthDate.value.getFullYear(), monthDate.value.getMonth() + offset, 1); month.value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`; selectedDay.value = ""; page.value = 1; load() }
function selectDay(cell) { if (!cell.current) { month.value = cell.date.slice(0, 7) }; selectedDay.value = selectedDay.value === cell.date ? "" : cell.date; page.value = 1; load() }
function resetLoad() { page.value = 1; load() }
function changePage(value) { page.value = value; load() }
function setStatus(value) { status.value = status.value === value ? "" : value; page.value = 1; load() }
function number(value) { return Math.round(Number(value || 0)).toLocaleString("zh-CN") }
function money(value) { return Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 2 }) }
function avatarText(value) { return String(value || "球").slice(-1) }
function passText(item) { return `${Number(item.bet_count || 0) ? `${item.bet_count}注 ` : ""}${item.pass_summary || "--"}` }
function resultText(value) { return value === "赢" ? "已中奖" : value === "输" ? "未中奖" : (value || "待开奖") }
function resultClass(value) { return `status-chip ${value === "赢" ? "success" : value === "输" ? "danger" : "warning"}` }
function exportRows() { return rows.value.map((item) => [item.nickname, item.history_record, item.stake, item.follow_num, item.platform_bonus, passText(item), (item.matches || []).map((match) => `${match.match_code} ${match.home} VS ${match.away} ${match.play_type} ${match.selection} SP ${match.odds || "--"}`).join("；"), resultText(item.result)]) }
function saveExcel() { downloadExcel("赛果统计", ["发单人", "历史战绩", "自购金额", "跟单人数", "中奖金额", "注数", "方案详情 / SP", "赛果"], exportRows(), stamp("football-results") + ".xls") }
function savePng() { downloadTextPng(`赛果统计 · ${selectedDay.value || monthLabel.value}`, exportRows().map((item) => item.join(" | ")), stamp("football-results") + ".png") }
function adminToken() { let token = localStorage.getItem("football-admin-token-v1") || ""; if (!token) { token = window.prompt("此操作需要后台管理 Token，请输入：") || ""; if (token) localStorage.setItem("football-admin-token-v1", token) }; return token }
async function clearArchive() {
  const phrase = `DELETE_RESULTS_${month.value}`
  if (!window.confirm(`将永久删除 ${monthLabel.value} 的全部方案和拆单数据，且无法由页面撤销。确定继续吗？`)) return
  if (window.prompt(`请输入 ${phrase} 进行二次确认：`) !== phrase) return
  const token = adminToken()
  if (!token) return
  try { const response = await axios.delete("/api/hub/results", { params: { month: month.value, confirm: phrase }, headers: { "X-Admin-Token": token } }); alert(`已删除 ${response.data.deleted_orders || 0} 个方案`); selectedDay.value = ""; page.value = 1; await load() } catch (requestError) { alert(requestError.response?.data?.detail || requestError.message) }
}

onMounted(load)
</script>

<style scoped>
.results-page{padding-bottom:32px}.archive-hero{min-height:86px;padding:15px;display:grid;grid-template-columns:180px minmax(220px,1fr) auto;gap:18px;align-items:center;text-align:center}.archive-hero h1{margin:4px 0 1px;font-size:24px}.archive-hero p{margin:0;color:var(--text-muted);font-size:10px}.back-button{justify-self:start;padding:10px 13px;border:1px solid var(--border);border-radius:10px;color:var(--text-secondary);background:var(--surface-soft);font-size:11px;font-weight:650}.archive-actions{display:flex;gap:7px}.archive-actions button{white-space:nowrap}.danger-button{min-height:38px;padding:0 14px;border:1px solid #ffdce4;border-radius:10px;color:#dc4768;background:#fff0f4;font-weight:700}.search-bar{margin-top:12px;padding:9px;display:flex;gap:8px}.search-bar input{min-height:38px;flex:1;border:1px solid #ded9ed;border-radius:10px;padding:0 13px}.calendar-shell{margin-top:12px;padding:12px}.month-tools{display:grid;grid-template-columns:1fr auto 1fr;align-items:center}.month-tools strong{text-align:center}.month-tools button{justify-self:start;padding:8px 13px;border:1px solid #ded9ed;border-radius:999px;color:#6f58d9;background:#f8f6ff;font-weight:700}.month-tools .month-secondary{justify-self:end}.calendar-grid{display:grid;grid-template-columns:repeat(7,1fr)}.weekdays{margin-top:10px}.weekdays span{padding:7px;text-align:center;color:#6f6a7c;font-size:10px;font-weight:700}.calendar-days{border-top:1px solid #e8e5ef;border-left:1px solid #e8e5ef}.calendar-days button{position:relative;min-height:66px;padding:8px;border:0;border-right:1px solid #e8e5ef;border-bottom:1px solid #e8e5ef;color:#34303e;background:#fff;text-align:left}.calendar-days button:hover,.calendar-days button.selected{background:#f2efff}.calendar-days button.muted{color:#c5c1cd;background:#fafafa}.calendar-days button>span{font-size:11px;font-weight:700}.calendar-days button>i{position:absolute;left:8px;bottom:18px;color:#2cbd80;font-style:normal}.calendar-days button>small{position:absolute;right:6px;bottom:6px;padding:3px 6px;border-radius:8px;color:#b5b1bc;background:#f3f3f5;font-size:8px}.calendar-days button.available>small{color:#5e83de;background:#edf6ff}.archive-summary{margin-top:12px;padding:12px;display:grid;grid-template-columns:repeat(6,1fr);gap:1px;background:#ebe8f1}.archive-summary div{padding:11px;background:#fff;text-align:center}.archive-summary span,.archive-summary strong{display:block}.archive-summary span{color:var(--text-muted);font-size:9px}.archive-summary strong{margin-top:5px;font-size:17px}.archive-note{margin-top:12px;padding:12px 14px;border:1px solid #ffd7bb;border-radius:12px;color:#69594d;background:#fff3e9;font-size:11px;font-weight:650}.date-card{margin-top:12px;overflow:hidden}.date-header{min-height:48px;padding:8px 14px;display:flex;align-items:center;gap:14px;border-bottom:1px solid var(--border)}.date-header>span{color:var(--text-muted);font-size:10px}.date-header>div{margin-left:auto;display:flex;gap:7px}.date-header button{padding:7px 12px;border:1px solid #ddd7f0;border-radius:10px;color:#745fe0;background:#fff}.date-header button.active{color:#fff;background:#7968ee}.archive-table{width:100%;min-width:1120px;border-collapse:collapse}.archive-table th,.archive-table td{padding:11px;border-right:1px solid #e7e4ed;border-bottom:1px solid #e7e4ed;text-align:center;font-size:11px}.archive-table th{color:#6f6a7b;background:#f6f5fa}.archive-table tr>*:last-child{border-right:0}.sender{display:flex;align-items:center;gap:8px;text-align:left}.sender>img,.sender>span{width:34px;height:34px;flex:0 0 34px;border-radius:50%;object-fit:cover}.sender>span{display:grid;place-items:center;color:#fff;background:#8070e9}.sender b,.sender small{display:block}.sender small{margin-top:3px;color:var(--text-muted);font-size:8px;font-weight:500}.purple{color:#684ee0}.details{text-align:left!important}.details>div{margin:3px 0}.details b,.details span{display:block}.details span{margin-top:2px;color:#6552d7}.details em{margin-left:7px;color:#258b77;font-style:normal;font-weight:700}@media(max-width:1180px){.archive-hero{grid-template-columns:1fr;text-align:left}.back-button{justify-self:start}.archive-actions{flex-wrap:wrap}.archive-summary{grid-template-columns:repeat(3,1fr)}}@media(max-width:700px){.archive-summary{grid-template-columns:repeat(2,1fr)}.calendar-days button{min-height:58px}.calendar-days button>small{display:none}.date-header{align-items:flex-start;flex-wrap:wrap}.date-header>div{width:100%;margin-left:0}.search-bar{flex-direction:column}}
</style>
