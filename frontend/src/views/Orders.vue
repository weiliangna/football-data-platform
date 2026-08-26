<template>
  <section class="page-shell orders-page">
    <header class="page-title">
      <div>
        <p>SCHEME HALL</p>
        <h1>多平台方案大厅</h1>
        <span>真实订单、拆分比赛、投注玩法与截止状态统一呈现</span>
      </div>

      <div class="order-total">
        <small>当前筛选</small>
        <b>{{ number(total) }}</b>
        <span>条方案</span>
      </div>
    </header>

    <section class="filter-panel panel">
      <div class="filter-topline">
        <label class="search-field">
          <span>⌕</span>
          <input
            v-model.trim="keyword"
            type="search"
            placeholder="搜索发单人、用户 ID、订单号或比赛"
            @keyup.enter="resetLoad"
          >
        </label>

        <select v-model="result" aria-label="方案结果" @change="resetLoad">
          <option value="">全部状态</option>
          <option value="待开奖">待开奖</option>
          <option value="赢">已中奖</option>
          <option value="输">未中奖</option>
        </select>

        <button class="primary-button" type="button" @click="resetLoad">
          查找方案
        </button>

        <button class="ghost-button" type="button" @click="resetFilters">
          重置
        </button>
      </div>

      <div class="platform-filters" aria-label="平台筛选">
        <button
          type="button"
          :class="{ active: platform === '' }"
          @click="selectPlatform('')"
        >
          全部平台
        </button>

        <button
          v-for="item in platforms"
          :key="item.platform_id"
          type="button"
          :class="{ active: platform === String(item.platform_id) }"
          @click="selectPlatform(String(item.platform_id))"
        >
          <i>{{ item.short || shortName(item.name) }}</i>
          {{ item.name }}
        </button>
      </div>
    </section>

    <section class="scheme-table panel">
      <header class="table-head">
        <span>平台 / 发单人</span>
        <span>方案与比赛</span>
        <span>自购金额</span>
        <span>跟单人数</span>
        <span>截止状态</span>
        <span>赛果</span>
        <span>操作</span>
      </header>

      <section v-if="loading" class="loading-state">
        <div class="state-stack">
          <span class="state-symbol loading-symbol">◌</span>
          <span>正在加载方案数据…</span>
        </div>
      </section>

      <section v-else-if="error" class="error-state">
        <div class="state-stack">
          <span class="state-symbol">!</span>
          <b>{{ error }}</b>
          <button class="secondary-button" type="button" @click="load">
            重新加载
          </button>
        </div>
      </section>

      <template v-else>
        <article
          v-for="order in orders"
          :key="order.id"
          class="scheme-row"
          :class="{ expanded: isExpanded(order.id) }"
        >
          <div class="scheme-summary">
            <div class="sender-cell">
              <span class="platform-badge">
                {{ shortName(order.platform_name) }}
              </span>

              <div class="sender-info">
                <button type="button" @click="openUser(order)">
                  {{ order.nickname || "未知用户" }}
                </button>
                <small>{{ order.platform_name }} · ID {{ order.user_id }}</small>
              </div>
            </div>

            <div class="scheme-cell">
              <b>{{ order.pass_composition || passText(order) }}</b>
              <span>
                {{ firstMatch(order) }}
                <i v-if="order.matches && order.matches.length > 1">
                  +{{ order.matches.length - 1 }} 场
                </i>
              </span>
              <small>{{ time(order.publish_time) }}</small>
            </div>

            <div class="money-cell">
              <b>¥{{ money(order.stake) }}</b>
              <small>SP {{ order.odds_text || "-" }}</small>
            </div>

            <div class="follow-cell">
              <b>{{ number(order.follow_num) }}</b>
              <small>人</small>
            </div>

            <div class="deadline-cell">
              <b :class="deadlineClass(order)">{{ deadlineText(order) }}</b>
              <small>{{ deadlineMeta(order) }}</small>
            </div>

            <div class="result-cell">
              <span :class="resultClass(order.result)">
                {{ resultText(order.result) }}
              </span>
              <small v-if="Number(order.bonus || 0) > 0">
                ¥{{ money(order.bonus) }}
              </small>
            </div>

            <div class="action-cell">
              <button
                class="expand-button"
                type="button"
                :aria-expanded="isExpanded(order.id)"
                @click="toggleOrder(order.id)"
              >
                {{ isExpanded(order.id) ? "收起" : "展开" }}
              </button>

              <button
                class="detail-button"
                type="button"
                @click="openOrder(order.id)"
              >
                详情 ↗
              </button>
            </div>
          </div>

          <div v-if="isExpanded(order.id)" class="match-drawer">
            <header>
              <span>场次</span>
              <span>对阵</span>
              <span>玩法</span>
              <span>投注项</span>
              <span>赛果</span>
            </header>

            <div
              v-for="match in order.matches || []"
              :key="match.id"
              class="match-row"
            >
              <span>{{ match.match_code || "-" }}</span>
              <b>{{ match.home || "-" }} <i>VS</i> {{ match.away || "-" }}</b>
              <span>{{ match.play_type || "-" }}</span>
              <strong>{{ match.selection || "-" }}</strong>
              <span :class="resultClass(match.result)">
                {{ match.result || "待开奖" }}
                <small>{{ scoreText(match) }}</small>
              </span>
            </div>

            <div v-if="!(order.matches || []).length" class="drawer-empty">
              当前订单尚未生成拆分比赛数据
            </div>
          </div>
        </article>

        <div v-if="!orders.length" class="empty-state">
          <div class="state-stack">
            <img class="empty-logo" src="/football-ai-logo.png" alt="">
            <b>没有符合当前条件的方案</b>
            <span>调整平台、状态或关键词后重新查询。</span>
          </div>
        </div>
      </template>
    </section>

    <div class="pager">
      <button
        class="secondary-button"
        type="button"
        :disabled="page <= 1 || loading"
        @click="changePage(page - 1)"
      >
        ← 上一页
      </button>

      <span>
        第 <b>{{ page }}</b> / {{ pages }} 页 · 共 {{ number(total) }} 条
      </span>

      <button
        class="secondary-button"
        type="button"
        :disabled="page >= pages || loading"
        @click="changePage(page + 1)"
      >
        下一页 →
      </button>
    </div>
  </section>
</template>

<script setup>
import {
  onMounted,
  ref
} from "vue"

import {
  useRouter
} from "vue-router"

import axios from "axios"


const router = useRouter()

const platform = ref("")
const keyword = ref("")
const result = ref("")
const platforms = ref([])
const orders = ref([])
const expandedOrders = ref(new Set())
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const loading = ref(true)
const error = ref("")


const fallbackPlatforms = [
  { platform_id: 1, name: "彩站云", short: "彩" },
  { platform_id: 2, name: "州运宝", short: "州" },
  { platform_id: 3, name: "鸿瑞", short: "鸿" },
  { platform_id: 4, name: "云彩", short: "云" },
  { platform_id: 5, name: "好店主", short: "店" },
  { platform_id: 6, name: "启示录", short: "启" }
]


async function loadPlatforms() {
  try {
    const response = await axios.get("/api/platform/list")
    const rows = response.data && response.data.data
    platforms.value = Array.isArray(rows) && rows.length
      ? rows
      : fallbackPlatforms
  } catch {
    platforms.value = fallbackPlatforms
  }
}


async function load() {
  loading.value = true
  error.value = ""

  const params = {
    page: page.value,
    page_size: 30,
    keyword: keyword.value,
    result: result.value
  }

  if (platform.value) {
    params.platform_id = Number(platform.value)
  }

  try {
    const response = await axios.get("/api/portal/schemes", { params })

    if (!response.data || response.data.code !== 200) {
      throw new Error("schemes unavailable")
    }

    orders.value = response.data.data || []
    page.value = response.data.page || 1
    pages.value = response.data.pages || 1
    total.value = response.data.total || 0
    expandedOrders.value = new Set()
  } catch {
    orders.value = []
    total.value = 0
    error.value = "方案数据暂时无法读取，请确认 API 服务与数据库连接状态。"
  } finally {
    loading.value = false
  }
}


function resetLoad() {
  page.value = 1
  load()
}


function resetFilters() {
  platform.value = ""
  keyword.value = ""
  result.value = ""
  resetLoad()
}


function selectPlatform(value) {
  platform.value = value
  resetLoad()
}


function changePage(value) {
  page.value = value
  load()
  window.scrollTo({ top: 0, behavior: "smooth" })
}


function toggleOrder(id) {
  const next = new Set(expandedOrders.value)

  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }

  expandedOrders.value = next
}


function isExpanded(id) {
  return expandedOrders.value.has(id)
}


function openUser(order) {
  router.push("/user/detail/" + order.platform_id + "/" + order.user_id)
}


function openOrder(id) {
  router.push("/order/detail/" + id)
}


function shortName(name) {
  return String(name || "平").slice(0, 1)
}


function firstMatch(order) {
  const match = (order.matches || [])[0]

  if (!match) {
    return "比赛明细待同步"
  }

  return (match.match_code || "-") + " · " + (match.home || "-") + " VS " + (match.away || "-")
}


function money(value) {
  return Number(value || 0).toLocaleString(
    "zh-CN",
    { maximumFractionDigits: 2 }
  )
}


function number(value) {
  return Math.round(Number(value || 0)).toLocaleString("zh-CN")
}


function time(value) {
  if (!value) {
    return "-"
  }

  return String(value).replace("T", " ").replace("Z", "")
}


function shortTime(value) {
  if (!value) {
    return ""
  }

  const text = time(value)
  return text.length > 16 ? text.slice(5, 16) : text
}


function passText(order) {
  const count = Number(order.bet_count || 0)
  const pass = order.pass_summary || "-"
  return count > 0 ? count + "注" + pass : pass
}


function resultText(value) {
  if (value === "赢") {
    return "已中奖"
  }

  if (value === "输") {
    return "未中奖"
  }

  return value || "待开奖"
}


function resultClass(value) {
  if (value === "赢") {
    return "result-chip result-win"
  }

  if (value === "输") {
    return "result-chip result-loss"
  }

  return "result-chip result-pending"
}


function deadlineText(order) {
  if (order.deadline_time) {
    return shortTime(order.deadline_time)
  }

  if (order.deadline_source === "pending_fallback") {
    return "状态参考"
  }

  return "未提供"
}


function deadlineMeta(order) {
  if (order.deadline_source === "deadline" && order.deadline_exact) {
    return "精确截止时间"
  }

  if (order.deadline_source === "kickoff_proxy") {
    return "开赛时间参考"
  }

  if (order.deadline_source === "pending_fallback") {
    return "待开奖状态回退"
  }

  return "截止语义未知"
}


function deadlineClass(order) {
  return order.deadline_exact ? "deadline-exact" : "deadline-proxy"
}


function scoreText(match) {
  if (
    match.home_score === null
    || match.home_score === undefined
    || match.away_score === null
    || match.away_score === undefined
  ) {
    return ""
  }

  return match.home_score + ":" + match.away_score
}


onMounted(() => {
  loadPlatforms()
  load()
})
</script>

<style scoped>
.order-total {
  min-width: 118px;
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: 17px;
  text-align: right;
  background: var(--surface);
}

.order-total small,
.order-total b,
.order-total span {
  display: inline-block;
}

.order-total small {
  display: block;
  color: var(--muted);
  font-size: 8px;
}

.order-total b {
  margin-top: 3px;
  color: var(--lime);
  font-size: 20px;
}

.order-total span {
  margin-left: 4px;
  color: var(--muted);
  font-size: 8px;
}

.filter-panel {
  padding: 14px;
}

.filter-topline {
  display: grid;
  grid-template-columns: minmax(290px, 1fr) 150px auto auto;
  gap: 9px;
}

.search-field {
  height: 42px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  display: flex;
  align-items: center;
  gap: 9px;
  background: #0d120e;
}

.search-field > span {
  color: var(--lime);
  font-size: 17px;
}

.search-field input {
  width: 100%;
  border: 0;
  outline: 0;
  color: var(--text);
  background: transparent;
  font-size: 11px;
}

.search-field input::placeholder {
  color: var(--muted-2);
}

.filter-topline select {
  min-height: 42px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0 14px;
  color: var(--text-soft);
  background: #0d120e;
  font-size: 11px;
}

.platform-filters {
  margin-top: 13px;
  padding-top: 13px;
  border-top: 1px solid var(--line);
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.platform-filters button {
  min-height: 33px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--muted);
  background: var(--surface-2);
  font-size: 9px;
  font-weight: 800;
}

.platform-filters button:hover,
.platform-filters button.active {
  color: #07110b;
  border-color: var(--lime);
  background: var(--lime);
}

.platform-filters i {
  width: 19px;
  height: 19px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  color: var(--lime);
  background: var(--lime-soft);
  font-size: 7px;
  font-style: normal;
}

.platform-filters button.active i,
.platform-filters button:hover i {
  color: #07110b;
  background: rgba(7, 17, 11, .1);
}

.scheme-table {
  margin-top: 15px;
  overflow: hidden;
}

.table-head,
.scheme-summary {
  display: grid;
  grid-template-columns:
    minmax(185px, 1.05fr)
    minmax(250px, 1.5fr)
    minmax(95px, .56fr)
    minmax(80px, .45fr)
    minmax(135px, .76fr)
    minmax(95px, .52fr)
    minmax(115px, .6fr);
  gap: 14px;
  align-items: center;
}

.table-head {
  min-height: 42px;
  padding: 0 16px;
  color: var(--muted-2);
  background: #0e130f;
  font-size: 8px;
  font-weight: 900;
  letter-spacing: .05em;
}

.scheme-row {
  border-top: 1px solid var(--line);
  transition: background .17s ease;
}

.scheme-row:hover,
.scheme-row.expanded {
  background: rgba(184, 255, 56, .025);
}

.scheme-summary {
  min-height: 82px;
  padding: 13px 16px;
}

.sender-cell {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 9px;
}

.platform-badge {
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  border: 1px solid rgba(184, 255, 56, .24);
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: var(--lime);
  background: var(--lime-soft);
  font-size: 11px;
  font-weight: 900;
}

.sender-info {
  min-width: 0;
}

.sender-info button {
  max-width: 100%;
  overflow: hidden;
  border: 0;
  padding: 0;
  color: var(--text);
  background: transparent;
  font-size: 11px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sender-info button:hover {
  color: var(--lime);
}

.sender-info small,
.scheme-cell span,
.scheme-cell small,
.money-cell small,
.follow-cell small,
.deadline-cell small,
.result-cell small {
  display: block;
  margin-top: 3px;
  color: var(--muted-2);
  font-size: 8px;
}

.scheme-cell {
  min-width: 0;
}

.scheme-cell > b {
  color: var(--text-soft);
  font-size: 11px;
}

.scheme-cell span {
  overflow: hidden;
  color: #aeb8ae;
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scheme-cell i {
  margin-left: 4px;
  color: var(--mint);
  font-style: normal;
}

.money-cell > b,
.follow-cell > b {
  color: #fff;
  font-size: 12px;
}

.deadline-cell > b {
  font-size: 9px;
  font-weight: 900;
}

.deadline-exact {
  color: var(--lime);
}

.deadline-proxy {
  color: var(--amber);
}

.result-chip {
  width: fit-content;
  min-height: 25px;
  padding: 0 9px;
  border: 1px solid var(--line);
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  font-size: 8px;
  font-weight: 900;
  white-space: nowrap;
}

.result-win {
  color: var(--lime);
  border-color: rgba(184, 255, 56, .24);
  background: var(--lime-soft);
}

.result-loss {
  color: #ff8b97;
  border-color: rgba(255, 97, 114, .24);
  background: rgba(255, 97, 114, .09);
}

.result-pending {
  color: var(--amber);
  border-color: rgba(255, 201, 92, .24);
  background: rgba(255, 201, 92, .08);
}

.action-cell {
  display: flex;
  align-items: center;
  gap: 5px;
}

.expand-button,
.detail-button {
  min-height: 31px;
  border-radius: 999px;
  padding: 0 10px;
  font-size: 8px;
  font-weight: 900;
}

.expand-button {
  border: 1px solid var(--line);
  color: var(--muted);
  background: var(--surface-2);
}

.detail-button {
  border: 1px solid rgba(184, 255, 56, .28);
  color: var(--lime);
  background: var(--lime-soft);
}

.match-drawer {
  margin: 0 16px 15px;
  border: 1px solid var(--line);
  border-radius: 15px;
  overflow: hidden;
  background: #0d120e;
}

.match-drawer > header,
.match-row {
  display: grid;
  grid-template-columns: 100px minmax(240px, 1.4fr) minmax(110px, .6fr) minmax(130px, .7fr) minmax(130px, .7fr);
  gap: 12px;
  align-items: center;
}

.match-drawer > header {
  min-height: 33px;
  padding: 0 13px;
  color: var(--muted-2);
  background: rgba(255, 255, 255, .025);
  font-size: 7px;
  font-weight: 900;
}

.match-row {
  min-height: 48px;
  padding: 8px 13px;
  border-top: 1px solid var(--line);
  color: #a7b1a8;
  font-size: 9px;
}

.match-row b {
  color: var(--text-soft);
  font-size: 10px;
}

.match-row b i {
  margin: 0 5px;
  color: var(--lime);
  font-size: 7px;
  font-style: normal;
}

.match-row > strong {
  color: var(--mint);
  font-size: 9px;
}

.match-row .result-chip {
  width: fit-content;
}

.match-row .result-chip small {
  margin-left: 5px;
  color: currentColor;
  opacity: .7;
}

.drawer-empty {
  min-height: 72px;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 9px;
}

.empty-logo {
  width: 82px;
  opacity: .74;
}

.empty-state b {
  color: var(--text-soft);
}

.empty-state span {
  font-size: 9px;
}

.pager {
  margin-top: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 13px;
  color: var(--muted);
  font-size: 9px;
}

.pager b {
  color: var(--lime);
}

.loading-symbol {
  animation: spin 1.1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1200px) {
  .scheme-table {
    overflow-x: auto;
  }

  .table-head,
  .scheme-summary {
    min-width: 1100px;
  }

  .match-drawer {
    min-width: 1040px;
  }
}

@media (max-width: 760px) {
  .order-total {
    text-align: left;
  }

  .filter-topline {
    grid-template-columns: 1fr 1fr;
  }

  .search-field {
    grid-column: 1 / -1;
  }

  .scheme-table {
    border-radius: 17px;
  }

  .table-head {
    display: none;
  }

  .scheme-row {
    padding: 14px;
  }

  .scheme-summary {
    min-width: 0;
    min-height: auto;
    padding: 0;
    grid-template-columns: 1fr 1fr;
  }

  .sender-cell,
  .scheme-cell,
  .deadline-cell,
  .action-cell {
    grid-column: 1 / -1;
  }

  .scheme-cell {
    padding: 11px 0;
    border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
  }

  .action-cell {
    justify-content: flex-end;
  }

  .match-drawer {
    min-width: 0;
    margin: 13px 0 0;
  }

  .match-drawer > header {
    display: none;
  }

  .match-row {
    grid-template-columns: 1fr;
    gap: 5px;
  }
}

@media (max-width: 480px) {
  .filter-topline {
    grid-template-columns: 1fr;
  }

  .search-field {
    grid-column: auto;
  }

  .pager {
    flex-wrap: wrap;
  }
}
</style>
