<template>
  <section class="page-shell">
    <header class="page-header">
      <div><h1>用户中心</h1><p>跨平台发单用户表现与近七日真实统计</p></div>
      <button class="primary-button" type="button" :disabled="loading" @click="load">{{ loading ? "加载中" : "刷新" }}</button>
    </header>

    <section class="toolbar app-card section-gap">
      <select v-model="platform" aria-label="平台" @change="resetLoad"><option value="">全部平台</option><option v-for="item in platforms" :key="item.platform_id" :value="String(item.platform_id)">{{ item.name }}</option></select>
      <input v-model.trim="keyword" class="search" placeholder="用户名 / 用户 ID" @keyup.enter="resetLoad">
      <select v-model="sort" aria-label="排序" @change="resetLoad"><option value="score">综合分</option><option value="orders">累计发单</option><option value="hit">命中率</option><option value="profit">累计盈利</option><option value="roi">ROI</option><option value="follow">累计跟单</option></select>
      <button class="primary-button" type="button" @click="resetLoad">查询</button>
    </section>

    <section class="users-card app-card section-gap">
      <LoadingSkeleton v-if="loading" :count="8" />
      <ErrorState v-else-if="error" :description="error" @retry="load" />
      <EmptyState v-else-if="!users.length" title="暂无用户" description="当前筛选条件下没有用户数据" />
      <div v-else class="table-wrap">
        <table class="data-table users-table">
          <thead><tr><th>排名</th><th>用户</th><th>平台</th><th>评分</th><th>7日自购</th><th>7日跟单</th><th>7日发单</th><th>7日盈利</th><th>命中率</th><th>近期战绩</th></tr></thead>
          <tbody>
            <tr v-for="item in users" :key="`${item.platform_id}-${item.user_id}`" tabindex="0" @click="openUser(item)" @keyup.enter="openUser(item)">
              <td><span class="rank" :class="{ first: item.rank === 1 }">{{ item.rank }}</span></td>
              <td><div class="user-name"><img v-if="item.avatar_url" class="avatar" :src="item.avatar_url" alt=""><span v-else class="avatar-fallback">{{ avatarText(item.nickname) }}</span><span><b>{{ item.nickname || "--" }}</b><small>ID {{ item.user_id || "--" }}</small></span></div></td>
              <td>{{ item.platform_name || "--" }}</td>
              <td><strong>{{ fixed(item.expert_score) }}</strong></td>
              <td>¥{{ money(item.self_buy7d) }}</td>
              <td>{{ number(item.followers7d) }}</td>
              <td>{{ number(item.orders7d) }}</td>
              <td :class="Number(item.profit7d) >= 0 ? 'money-positive' : 'money-negative'">{{ profit(item.profit7d) }}</td>
              <td>{{ percent(item.hit_rate) }}</td>
              <td><div v-if="item.recent5?.length" class="recent-results"><i v-for="(result, index) in item.recent5" :key="index" :class="result === '赢' ? 'win' : 'loss'">{{ result }}</i></div><span v-else>--</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <AppPagination :page="page" :pages="pages" :disabled="loading" @change="changePage" />
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"
import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"
import EmptyState from "../components/ui/EmptyState.vue"
import ErrorState from "../components/ui/ErrorState.vue"
import AppPagination from "../components/ui/AppPagination.vue"

const router = useRouter()
const platform = ref("")
const keyword = ref("")
const sort = ref("score")
const users = ref([])
const platforms = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const loading = ref(true)
const error = ref("")

async function loadPlatforms() {
  try {
    const response = await axios.get("/api/platform/list", { timeout: 25000 })
    platforms.value = Array.isArray(response.data?.data) ? response.data.data : []
  } catch { platforms.value = [] }
}

async function load() {
  loading.value = true
  error.value = ""
  const params = { keyword: keyword.value, sort: sort.value, page: page.value, page_size: 30 }
  if (platform.value) params.platform_id = Number(platform.value)
  try {
    const response = await axios.get("/api/portal/users", { params, timeout: 25000 })
    if (response.data?.code !== 200) throw new Error()
    users.value = response.data.data || []
    page.value = response.data.page || 1
    pages.value = response.data.pages || 1
    total.value = response.data.total || 0
  } catch {
    users.value = []
    total.value = 0
    error.value = "用户数据暂时无法读取，请稍后重试或检查接口连接状态"
  } finally { loading.value = false }
}

function resetLoad() { page.value = 1; load() }
function changePage(value) { page.value = value; load() }
function openUser(item) { router.push(`/user/detail/${item.platform_id}/${item.user_id}`) }
function avatarText(value) { return String(value || "球").slice(-1) }
function number(value) { return Math.round(Number(value || 0)).toLocaleString("zh-CN") }
function fixed(value) { return value === null || value === undefined ? "--" : Number(value).toFixed(2) }
function percent(value) { return value === null || value === undefined ? "--" : `${Number(value).toFixed(2)}%` }
function money(value) { return Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 2 }) }
function profit(value) { const amount = Number(value || 0); return `${amount > 0 ? "+¥" : amount < 0 ? "-¥" : "¥"}${money(Math.abs(amount))}` }

onMounted(() => { loadPlatforms(); load() })
</script>

<style scoped>
.section-gap{margin-top:14px}.toolbar .search{min-width:260px;flex:1}.users-card{overflow:hidden}.users-table{min-width:1080px}.users-table tbody tr{cursor:pointer}.rank{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;background:#f1f1ee;font-size:10px;font-weight:700}.rank.first{background:var(--accent)}.user-name{display:flex;align-items:center;gap:9px;min-width:190px}.user-name>span:last-child{min-width:0}.user-name b,.user-name small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.user-name b{color:var(--text-main)}.user-name small{margin-top:3px;color:var(--text-muted);font-size:10px}.recent-results{display:flex;gap:4px}.recent-results i{width:24px;height:24px;border-radius:7px;display:grid;place-items:center;font-size:9px;font-style:normal;font-weight:750}.recent-results .win{color:var(--success);background:var(--success-soft)}.recent-results .loss{color:var(--danger);background:var(--danger-soft)}@media(max-width:520px){.toolbar>*{width:100%}.toolbar .search{min-width:0}}
</style>
