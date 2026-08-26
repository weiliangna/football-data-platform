<template>
  <section class="page-shell users-page">
    <header class="page-title">
      <div>
        <p>SENDER LEADERBOARD</p>
        <h1>发单用户英雄榜</h1>
        <span>六平台用户统一排行，综合发单、命中、盈利与跟单表现</span>
      </div>
    </header>

    <section class="user-filters panel">
      <select v-model="platform" aria-label="平台" @change="resetLoad">
        <option value="">全部平台</option>
        <option v-for="item in platforms" :key="item.platform_id" :value="String(item.platform_id)">{{ item.name }}</option>
      </select>
      <input v-model.trim="keyword" placeholder="用户名 / 用户 ID" @keyup.enter="resetLoad">
      <select v-model="sort" aria-label="排序" @change="resetLoad">
        <option value="score">综合分</option><option value="orders">发单数</option>
        <option value="hit">命中率</option><option value="profit">盈利</option>
        <option value="roi">ROI</option><option value="follow">跟单人数</option>
      </select>
      <button class="primary-button" type="button" @click="resetLoad">查询用户</button>
    </section>

    <section class="users-panel panel">
      <header class="users-head">
        <span>排名</span><span>用户</span><span>平台</span><span>发单</span><span>命中率</span>
        <span>自购金额</span><span>跟单人数</span><span>盈利</span><span>ROI</span><span>综合分</span>
      </header>

      <article
        v-for="item in users"
        :key="item.platform_id + '-' + item.user_id"
        class="user-row"
        tabindex="0"
        @click="openUser(item)"
        @keyup.enter="openUser(item)"
      >
        <strong class="rank">{{ rankLabel(item.rank) }}</strong>
        <div class="user-name">
          <img v-if="item.avatar_url" class="avatar" :src="item.avatar_url" alt="">
          <span v-else class="avatar-fallback">{{ avatarText(item.nickname) }}</span>
          <div><b>{{ item.nickname }}</b><small>ID {{ item.user_id }}</small></div>
        </div>
        <span class="platform-chip">{{ item.platform_name }}</span>
        <span>{{ number(item.total_orders) }}</span>
        <b>{{ percent(item.hit_rate) }}</b>
        <span>¥{{ money(item.total_stake) }}</span>
        <span>{{ number(item.follow_num) }}</span>
        <b :class="Number(item.total_profit) >= 0 ? 'money-positive' : 'money-negative'">{{ profit(item.total_profit) }}</b>
        <span>{{ percent(item.roi) }}</span>
        <strong class="score">{{ Number(item.expert_score || 0).toFixed(2) }}</strong>
      </article>

      <div v-if="error" class="error-state">
        <div class="state-stack"><span class="state-symbol">!</span><b>{{ error }}</b></div>
      </div>
      <div v-else-if="!users.length" class="empty-state">暂无用户数据</div>
    </section>

    <div class="pager">
      <button class="secondary-button" type="button" :disabled="page <= 1" @click="changePage(page - 1)">← 上一页</button>
      <span>第 <b>{{ page }}</b> / {{ pages }} 页</span>
      <button class="secondary-button" type="button" :disabled="page >= pages" @click="changePage(page + 1)">下一页 →</button>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"

const router = useRouter()
const platform = ref("")
const keyword = ref("")
const sort = ref("score")
const users = ref([])
const platforms = ref([])
const page = ref(1)
const pages = ref(1)
const error = ref("")

const fallbackPlatforms = [
  { platform_id: 1, name: "彩站云" }, { platform_id: 2, name: "州运宝" },
  { platform_id: 3, name: "鸿瑞" }, { platform_id: 4, name: "云彩" },
  { platform_id: 5, name: "好店主" }, { platform_id: 6, name: "启示录" }
]

async function loadPlatforms() {
  try {
    const response = await axios.get("/api/platform/list")
    const rows = response.data && response.data.data
    platforms.value = Array.isArray(rows) && rows.length ? rows : fallbackPlatforms
  } catch {
    platforms.value = fallbackPlatforms
  }
}

async function load() {
  error.value = ""
  const params = { keyword: keyword.value, sort: sort.value, page: page.value, page_size: 30 }
  if (platform.value) {
    params.platform_id = Number(platform.value)
  }

  try {
    const response = await axios.get("/api/portal/users", { params })
    if (!response.data || response.data.code !== 200) {
      throw new Error("users unavailable")
    }
    users.value = response.data.data || []
    page.value = response.data.page || 1
    pages.value = response.data.pages || 1
  } catch {
    users.value = []
    error.value = "用户数据暂时无法读取，请稍后重试。"
  }
}

function resetLoad() { page.value = 1; load() }
function changePage(value) { page.value = value; load() }
function openUser(item) { router.push("/user/detail/" + item.platform_id + "/" + item.user_id) }
function avatarText(name) { return String(name || "球").slice(-1) }
function rankLabel(value) { return String(Number(value || 0)).padStart(2, "0") }
function number(value) { return Math.round(Number(value || 0)).toLocaleString("zh-CN") }
function money(value) { return Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 2 }) }
function percent(value) { return Number(value || 0).toFixed(2) + "%" }
function profit(value) {
  const amount = Number(value || 0)
  if (amount > 0) return "+¥" + money(amount)
  if (amount < 0) return "-¥" + money(Math.abs(amount))
  return "¥0"
}

onMounted(() => { loadPlatforms(); load() })
</script>

<style scoped>
.user-filters { padding: 13px; display: grid; grid-template-columns: 160px minmax(280px,1fr) 170px auto; gap: 8px; }
.user-filters select,
.user-filters input { height: 42px; border: 1px solid var(--line); border-radius: 999px; padding: 0 14px; color: var(--text-soft); background: #0d120e; font-size: 10px; }
.user-filters input::placeholder { color: var(--muted-2); }
.users-panel { margin-top: 15px; overflow-x: auto; }
.users-head,
.user-row { min-width: 1130px; display: grid; grid-template-columns: 55px minmax(210px,1.25fr) 90px repeat(7,minmax(78px,.6fr)); gap: 10px; align-items: center; text-align: center; }
.users-head { min-height: 42px; padding: 0 14px; color: var(--muted-2); background: #0e130f; font-size: 8px; font-weight: 900; }
.user-row { min-height: 67px; padding: 10px 14px; border-top: 1px solid var(--line); color: #aab5ab; font-size: 9px; cursor: pointer; }
.user-row:hover,
.user-row:focus-visible { background: rgba(184,255,56,.035); }
.rank { color: var(--lime); font-size: 11px; }
.user-name { display: flex; align-items: center; gap: 9px; text-align: left; }
.user-name b,
.user-name small { display: block; }
.user-name b { color: var(--text-soft); font-size: 10px; }
.user-name small { margin-top: 3px; color: var(--muted); font-size: 8px; }
.platform-chip { width: fit-content; margin: auto; padding: 5px 8px; border-radius: 999px; color: var(--mint); background: var(--mint-soft); font-size: 8px; font-weight: 900; }
.score { color: var(--lime); font-size: 13px; }
.pager { margin-top: 16px; display: flex; justify-content: center; align-items: center; gap: 10px; color: var(--muted); font-size: 9px; }
.pager b { color: var(--lime); }

@media (max-width: 820px) {
  .user-filters { grid-template-columns: 1fr; }
}
</style>
