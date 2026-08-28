<template>
  <section class="page-shell results-page">
    <header class="archive-hero app-card">
      <router-link class="back-button" to="/orders">← 返回方案大厅</router-link>
      <div><span class="eyebrow">Result archive</span><h1>赛果统计</h1><p>按方案业务日期归档 · 比赛编号与队名优先使用彩站云口径</p></div>
      <span class="hero-spacer"></span>
    </header>

    <section class="date-navigator app-card">
      <button type="button" @click="stepDay(-1)">‹ 前一日</button>
      <div class="date-picker">
        <button class="date-trigger" type="button" @click="calendarOpen = !calendarOpen"><span>▦</span><b><small>比赛日</small>{{ selectedDay || `${monthLabel} · 全月` }}</b><i>⌄</i></button>
        <div v-if="calendarOpen" class="calendar-popover">
          <header><div><span class="eyebrow">Date navigator</span><strong>选择比赛日</strong></div></header>
          <nav><button type="button" @click="shiftMonth(-1)">‹</button><b>{{ monthLabel }}</b><button type="button" @click="shiftMonth(1)">›</button></nav>
          <div class="weekdays"><span v-for="name in weekdays" :key="name">{{ name }}</span></div>
          <div class="calendar-grid"><button v-for="cell in calendarCells" :key="cell.key" type="button" :class="{ muted: !cell.current, selected: selectedDay === cell.date, available: cell.count > 0 }" @click="selectDay(cell)"><span>{{ cell.day }}</span><small v-if="cell.count">{{ number(cell.count) }}</small></button></div>
          <footer><span>{{ selectedDay ? `当前选择 ${selectedDay}` : "当前显示整月方案" }}</span><button type="button" @click="selectToday">今天</button></footer>
        </div>
      </div>
      <button type="button" @click="stepDay(1)">后一日 ›</button>
      <button v-if="selectedDay" class="month-reset" type="button" @click="showWholeMonth">查看整月</button>
    </section>

    <section class="search-bar app-card">
      <input v-model.trim="keyword" type="search" placeholder="搜索发单人、订单号、球队或方案内容" @keyup.enter="resetLoad">
      <button class="secondary-button" type="button" @click="resetLoad">查找</button>
    </section>

    <section class="archive-summary app-card">
      <div><span>本月方案</span><strong>{{ number(summary.total) }}</strong></div><div><span>已中奖</span><strong>{{ number(summary.won) }}</strong></div><div><span>未中奖</span><strong>{{ number(summary.lost) }}</strong></div><div><span>待开奖</span><strong>{{ number(summary.pending) }}</strong></div><div><span>发单总金额</span><strong>¥{{ money(summary.total_stake) }}</strong></div><div><span>跟单人数</span><strong>{{ number(summary.followers) }}</strong></div>
    </section>

    <section class="archive-note">{{ selectedDay || monthLabel }} · 共 {{ number(total) }} 个方案 · 当前显示 {{ pageStart }}-{{ pageEnd }} · 日期严格按订单 `_date` 筛选</section>

    <section class="date-card app-card">
      <header class="date-header"><strong>{{ selectedDay || monthLabel }}</strong><span>{{ number(total) }} 个方案</span><div><button type="button" :class="{ active: status === 'pending' }" @click="setStatus('pending')">未开奖</button><button type="button" :class="{ active: status === 'won' }" @click="setStatus('won')">已中奖</button><button type="button" :class="{ active: !status }" @click="setStatus('')">全部</button></div></header>
      <LoadingSkeleton v-if="loading" :count="8"/>
      <ErrorState v-else-if="error" :description="error"/>
      <EmptyState v-else-if="!rows.length" title="暂无赛果记录" description="当前日期或筛选条件下没有方案数据"/>
      <div v-else class="table-wrap"><table class="archive-table"><thead><tr><th>发单人</th><th>历史战绩</th><th>自购金额</th><th>跟单人数</th><th>中奖金额</th><th>注数</th><th>方案详情 / SP</th><th>赛果</th></tr></thead><tbody><tr v-for="item in rows" :key="item.id"><td><div class="sender"><img v-if="item.avatar_url" :src="item.avatar_url" alt=""><span v-else>{{ avatarText(item.nickname) }}</span><b>{{ item.nickname || "--" }}<small>{{ item.platform_name }} · {{ item.platform_order_id }} · {{ item._date || "日期待同步" }}</small></b></div></td><td><strong class="purple">{{ item.history_record || "--" }}</strong></td><td>¥{{ money(item.stake) }}</td><td>{{ number(item.follow_num) }} 人</td><td>{{ item.result === "待开奖" ? "待开奖" : `¥${money(item.platform_bonus)}` }}</td><td>{{ passText(item) }}</td><td class="details"><div v-for="match in item.matches || []" :key="match.id"><b>{{ match.match_code || "--" }} · {{ match.home || "--" }} VS {{ match.away || "--" }}</b><span>[{{ match.play_type || "--" }}：{{ match.selection || "--" }}]<em>SP {{ match.odds || "--" }}</em></span></div><span v-if="!(item.matches || []).length">比赛明细待同步 · SP {{ item.odds_text || "--" }}</span></td><td><span :class="resultClass(item.result)">{{ resultText(item.result) }}</span></td></tr></tbody></table></div>
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

const today = new Date()
const rows = ref([]), summary = ref({}), dateCounts = ref([])
const month = ref("")
const selectedDay = ref("")
const keyword = ref(""), status = ref("")
const page = ref(1), pages = ref(1), total = ref(0)
const loading = ref(true), error = ref(""), calendarOpen = ref(false)
const pageSize = 100
const weekdays = ["一", "二", "三", "四", "五", "六", "日"]
const currentMonth = () => `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`
const activeMonth = computed(() => month.value || currentMonth())
const monthDate = computed(() => { const [year, value] = activeMonth.value.split("-").map(Number); return new Date(year, value - 1, 1) })
const monthLabel = computed(() => `${monthDate.value.getFullYear()}年${monthDate.value.getMonth() + 1}月`)
const countMap = computed(() => Object.fromEntries(dateCounts.value.map((item) => [item.day, Number(item.count || 0)])))
const pageStart = computed(() => total.value ? (page.value - 1) * pageSize + 1 : 0)
const pageEnd = computed(() => Math.min(page.value * pageSize, total.value))
const calendarCells = computed(() => { const base = monthDate.value; const offset = (base.getDay() + 6) % 7; const start = new Date(base.getFullYear(), base.getMonth(), 1 - offset); return Array.from({ length: 42 }, (_, index) => { const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + index); const value = localDate(date); return { key: value, date: value, day: date.getDate(), current: date.getMonth() === base.getMonth(), count: countMap.value[value] || 0 } }) })

async function load() {
  loading.value = true; error.value = ""
  try {
    const params = { day: selectedDay.value, keyword: keyword.value, status: status.value, page: page.value, page_size: pageSize }
    if (month.value) params.month = month.value
    const response = await axios.get("/api/hub/results", { params, timeout: 25000 })
    if (response.data?.code !== 200) throw new Error()
    const data = response.data.data || {}; rows.value = data.rows || []; summary.value = data.summary || {}; dateCounts.value = data.date_counts || []; pages.value = data.pages || 1; total.value = data.total || 0; month.value = data.month || month.value || currentMonth()
  } catch { rows.value = []; error.value = "赛果数据暂时不可用" } finally { loading.value = false }
}

function localDate(date) { const two = (value) => String(value).padStart(2, "0"); return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}` }
function shiftMonth(offset) { const date = new Date(monthDate.value.getFullYear(), monthDate.value.getMonth() + offset, 1); month.value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`; selectedDay.value = ""; page.value = 1; load() }
function selectDay(cell) { if (!cell.current) month.value = cell.date.slice(0, 7); selectedDay.value = cell.date; calendarOpen.value = false; page.value = 1; load() }
function stepDay(offset) { const base = selectedDay.value ? new Date(`${selectedDay.value}T00:00:00`) : new Date(`${activeMonth.value}-01T00:00:00`); base.setDate(base.getDate() + offset); month.value = localDate(base).slice(0, 7); selectedDay.value = localDate(base); page.value = 1; load() }
function selectToday() { month.value = currentMonth(); selectedDay.value = localDate(today); calendarOpen.value = false; page.value = 1; load() }
function showWholeMonth() { selectedDay.value = ""; page.value = 1; load() }
function resetLoad() { page.value = 1; load() }
function changePage(value) { page.value = value; load() }
function setStatus(value) { status.value = status.value === value ? "" : value; page.value = 1; load() }
function number(value) { return Math.round(Number(value || 0)).toLocaleString("zh-CN") }
function money(value) { return Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 2 }) }
function avatarText(value) { return String(value || "球").slice(-1) }
function passText(item) { return `${Number(item.bet_count || 0) ? `${item.bet_count}注 ` : ""}${item.pass_summary || "--"}` }
function resultText(value) { return value === "赢" ? "已中奖" : value === "输" ? "未中奖" : (value || "待开奖") }
function resultClass(value) { return `status-chip ${value === "赢" ? "success" : value === "输" ? "danger" : "warning"}` }
onMounted(load)
</script>

<style scoped>
.results-page{padding-bottom:32px}.archive-hero{min-height:86px;padding:15px;display:grid;grid-template-columns:180px minmax(220px,1fr) 180px;gap:18px;align-items:center;text-align:center}.archive-hero h1{margin:4px 0 1px;font-size:24px}.archive-hero p{margin:0;color:var(--text-muted);font-size:10px}.back-button{justify-self:start;padding:10px 13px;border:1px solid var(--border);border-radius:10px;color:var(--text-secondary);background:var(--surface-soft);font-size:11px;font-weight:650}.date-navigator{position:relative;margin-top:12px;padding:9px;display:flex;align-items:center;gap:8px}.date-navigator>button,.date-trigger{min-height:42px;padding:0 14px;border:1px solid #d8ddeb;border-radius:9px;color:#59657a;background:#fff}.date-picker{position:relative}.date-trigger{min-width:178px;display:flex;align-items:center;gap:10px;border-color:#2b7de9;box-shadow:0 0 0 2px rgba(43,125,233,.1);text-align:left}.date-trigger>span{color:#2b7de9;font-size:18px}.date-trigger>b{min-width:0;flex:1;font-size:12px}.date-trigger small{display:block;color:#718097;font-size:8px}.date-trigger i{font-style:normal}.month-reset{margin-left:auto}.calendar-popover{position:absolute;left:0;top:50px;z-index:20;width:312px;border:1px solid #d7deea;border-radius:12px;background:#fff;box-shadow:0 18px 45px rgba(31,48,78,.2);overflow:hidden}.calendar-popover>header{padding:15px;border-bottom:1px solid #dfe4ed;background:#f1f6fc}.calendar-popover>header span,.calendar-popover>header strong{display:block}.calendar-popover>header strong{margin-top:5px}.calendar-popover nav{padding:13px;display:grid;grid-template-columns:36px 1fr 36px;align-items:center;text-align:center}.calendar-popover nav button{border:0;color:#2875d2;background:transparent;font-size:20px}.weekdays,.calendar-grid{display:grid;grid-template-columns:repeat(7,1fr)}.weekdays span{padding:5px;text-align:center;color:#98a3b3;font-size:9px}.calendar-grid{padding:3px 12px 12px}.calendar-grid button{position:relative;height:38px;border:0;border-radius:9px;color:#33445f;background:#fff;font-size:10px}.calendar-grid button:hover{background:#eef5ff}.calendar-grid button.muted{color:#b9c1ce}.calendar-grid button.selected{color:#fff;background:#2875d2;box-shadow:0 6px 14px rgba(40,117,210,.28)}.calendar-grid button>small{position:absolute;right:2px;bottom:1px;color:#28aa75;font-size:7px}.calendar-grid button.selected>small{color:#fff}.calendar-popover footer{padding:10px 13px;border-top:1px solid #e1e6ee;display:flex;align-items:center;justify-content:space-between;color:#718097;background:#f8fafc;font-size:8px}.calendar-popover footer button{padding:6px 10px;border:1px solid #b9d3f5;border-radius:8px;color:#2875d2;background:#fff}.search-bar{margin-top:12px;padding:9px;display:flex;gap:8px}.search-bar input{min-height:38px;flex:1;border:1px solid #ded9ed;border-radius:10px;padding:0 13px}.archive-summary{margin-top:12px;padding:12px;display:grid;grid-template-columns:repeat(6,1fr);gap:1px;background:#ebe8f1}.archive-summary div{padding:11px;background:#fff;text-align:center}.archive-summary span,.archive-summary strong{display:block}.archive-summary span{color:var(--text-muted);font-size:9px}.archive-summary strong{margin-top:5px;font-size:17px}.archive-note{margin-top:12px;padding:12px 14px;border:1px solid #dce2f0;border-radius:12px;color:#59657a;background:#f7f9fc;font-size:11px;font-weight:650}.date-card{margin-top:12px;overflow:hidden}.date-header{min-height:48px;padding:8px 14px;display:flex;align-items:center;gap:14px;border-bottom:1px solid var(--border)}.date-header>span{color:var(--text-muted);font-size:10px}.date-header>div{margin-left:auto;display:flex;gap:7px}.date-header button{padding:7px 12px;border:1px solid #ddd7f0;border-radius:10px;color:#745fe0;background:#fff}.date-header button.active{color:#fff;background:#7968ee}.archive-table{width:100%;min-width:1120px;border-collapse:collapse}.archive-table th,.archive-table td{padding:11px;border-right:1px solid #e7e4ed;border-bottom:1px solid #e7e4ed;text-align:center;font-size:11px}.archive-table th{color:#6f6a7b;background:#f6f5fa}.archive-table tr>*:last-child{border-right:0}.sender{display:flex;align-items:center;gap:8px;text-align:left}.sender>img,.sender>span{width:34px;height:34px;flex:0 0 34px;border-radius:50%;object-fit:cover}.sender>span{display:grid;place-items:center;color:#fff;background:#8070e9}.sender b,.sender small{display:block}.sender small{margin-top:3px;color:var(--text-muted);font-size:8px;font-weight:500}.purple{color:#684ee0}.details{text-align:left!important}.details>div{margin:3px 0}.details b,.details span{display:block}.details span{margin-top:2px;color:#6552d7}.details em{margin-left:7px;color:#258b77;font-style:normal;font-weight:700}@media(max-width:900px){.archive-hero{grid-template-columns:1fr;text-align:left}.date-navigator{flex-wrap:wrap}.archive-summary{grid-template-columns:repeat(3,1fr)}}@media(max-width:700px){.archive-summary{grid-template-columns:repeat(2,1fr)}.date-picker{order:-1;width:100%}.date-trigger{width:100%}.calendar-popover{width:min(312px,calc(100vw - 44px))}.date-header{align-items:flex-start;flex-wrap:wrap}.date-header>div{width:100%;margin-left:0}.search-bar{flex-direction:column}}
</style>
