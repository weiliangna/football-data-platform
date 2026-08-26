<template>
  <section class="page-shell order-detail-page">
    <header class="page-title">
      <div>
        <p>ORDER DETAIL</p>
        <h1>订单详情</h1>
        <span>{{ order.platform_name || "-" }} · {{ order.nickname || "-" }} · {{ order.platform_order_id || order.id || "-" }}</span>
      </div>
      <button class="secondary-button" type="button" @click="router.back()">← 返回</button>
    </header>

    <section class="order-summary panel">
      <article><span>发单时间</span><strong>{{ time(order.publish_time) }}</strong></article>
      <article><span>串关</span><strong>{{ order.pass_composition || passText(order) }}</strong></article>
      <article><span>自购金额</span><strong>¥{{ money(order.stake) }}</strong></article>
      <article><span>跟单</span><strong>{{ number(order.follow_num) }} 人</strong></article>
      <article><span>中奖金额</span><strong class="money-positive">¥{{ money(order.bonus) }}</strong></article>
    </section>

    <section v-if="error" class="panel error-state detail-panel">
      <div class="state-stack"><span class="state-symbol">!</span><b>{{ error }}</b></div>
    </section>

    <section v-else class="detail-lines panel">
      <header class="detail-head"><span>场次与对阵</span><span>玩法与投注项</span><span>赛果</span></header>
      <div v-for="match in order.matches || []" :key="match.id" class="detail-line">
        <div><b>{{ match.match_code || "-" }} · {{ match.home }} <i>VS</i> {{ match.away }}</b><small>{{ match.league || "竞彩足球" }}</small></div>
        <div><span>{{ match.play_type }}：</span><b :class="resultClass(match.result)">{{ match.selection }}</b></div>
        <div class="detail-score"><b :class="resultClass(match.result)">{{ match.result || "待开奖" }}</b><small>{{ fullScore(match) }}</small></div>
      </div>
      <div v-if="!(order.matches || []).length" class="empty-state">当前订单没有拆场数据</div>
    </section>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import axios from "axios"

const route = useRoute()
const router = useRouter()
const order = ref({})
const error = ref("")

async function load() {
  error.value = ""
  try {
    const response = await axios.get("/api/portal/order/" + route.params.id)
    if (!response.data || response.data.code !== 200) {
      throw new Error("order unavailable")
    }
    order.value = response.data.data || {}
  } catch {
    error.value = "订单详情暂时无法读取，请稍后重试。"
  }
}

function money(value) { return Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 2 }) }
function number(value) { return Math.round(Number(value || 0)).toLocaleString("zh-CN") }
function time(value) { return value ? String(value).replace("T", " ").replace("Z", "") : "-" }
function passText(value) { const count = Number(value.bet_count || 0); const pass = value.pass_summary || "-"; return count > 0 ? count + "注" + pass : pass }
function resultClass(value) { return value === "赢" ? "option-win" : value === "输" ? "option-loss" : "option-pending" }
function fullScore(match) {
  if (match.home_score === null || match.home_score === undefined || match.away_score === null || match.away_score === undefined) return "赛果待同步"
  let text = "全场 " + match.home_score + ":" + match.away_score
  if (match.half_home_score !== null && match.half_home_score !== undefined && match.half_away_score !== null && match.half_away_score !== undefined) {
    text += " · 半场 " + match.half_home_score + ":" + match.half_away_score
  }
  return text
}

onMounted(load)
</script>

<style scoped>
.order-summary { padding: 13px; display: grid; grid-template-columns: repeat(5,1fr); gap: 9px; }
.order-summary article { padding: 14px; border: 1px solid rgba(184,255,56,.07); border-radius: 14px; background: var(--surface-2); }
.order-summary span,
.order-summary strong { display: block; }
.order-summary span { color: var(--muted); font-size: 8px; }
.order-summary strong { margin-top: 5px; font-size: 12px; }
.detail-panel,
.detail-lines { margin-top: 15px; }
.detail-lines { overflow: hidden; }
.detail-head,
.detail-line { display: grid; grid-template-columns: minmax(330px,1.4fr) minmax(260px,1fr) 190px; gap: 14px; align-items: center; }
.detail-head { min-height: 38px; padding: 0 15px; color: var(--muted-2); background: #0e130f; font-size: 8px; font-weight: 900; }
.detail-line { min-height: 66px; padding: 12px 15px; border-top: 1px solid var(--line); }
.detail-line > div:first-child b,
.detail-line > div:first-child small,
.detail-score b,
.detail-score small { display: block; }
.detail-line > div:first-child b { font-size: 11px; }
.detail-line > div:first-child b i { margin: 0 5px; color: var(--lime); font-size: 8px; font-style: normal; }
.detail-line > div:first-child small,
.detail-score small { margin-top: 4px; color: var(--muted); font-size: 8px; }
.detail-line > div:nth-child(2) { color: #aab5ab; font-size: 10px; }
.detail-score { text-align: right; }

@media (max-width: 900px) {
  .order-summary { grid-template-columns: repeat(2,1fr); }
  .detail-head { display: none; }
  .detail-line { grid-template-columns: 1fr; }
  .detail-score { text-align: left; }
}

@media (max-width: 520px) {
  .order-summary { grid-template-columns: 1fr; }
}
</style>
