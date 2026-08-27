<template>
  <section class="page-shell">
    <header class="page-header">
      <div><h1>方案大厅</h1><p>聚合各平台真实订单、拆分比赛与结算状态</p></div>
      <div class="page-actions"><span class="page-time">共 {{ number(total) }} 条</span><button class="primary-button" type="button" @click="load">刷新</button></div>
    </header>

    <section class="toolbar app-card">
      <select v-model="platform" aria-label="平台" @change="resetLoad"><option value="">全部平台</option><option v-for="item in platforms" :key="item.platform_id" :value="String(item.platform_id)">{{ item.name }}</option></select>
      <select v-model="result" aria-label="状态" @change="resetLoad"><option value="">全部状态</option><option value="待开奖">待开奖</option><option value="赢">已中奖</option><option value="输">未中奖</option></select>
      <input v-model.trim="keyword" class="search" type="search" placeholder="发单人、用户 ID、订单号或比赛" @keyup.enter="resetLoad">
      <select v-model="sort" aria-label="排序"><option value="publish_time">按发单时间</option></select>
      <button class="primary-button" type="button" @click="resetLoad">查询</button>
      <button class="secondary-button" type="button" @click="resetFilters">重置</button>
    </section>

    <section class="orders-card app-card">
      <LoadingSkeleton v-if="loading" :count="7" />
      <ErrorState v-else-if="error" :description="error" @retry="load" />
      <EmptyState v-else-if="!orders.length" title="暂无方案" description="当前筛选条件下没有方案数据" />
      <div v-else class="table-wrap">
        <table class="data-table orders-table">
          <thead><tr><th>发单人</th><th>平台</th><th>发单时间</th><th>历史战绩</th><th>自购</th><th>跟单</th><th>串关</th><th>方案详情</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            <template v-for="order in orders" :key="order.id">
              <tr>
                <td>
                  <button class="user-cell" type="button" @click="openUser(order)">
                    <img v-if="order.avatar_url" class="table-avatar" :src="order.avatar_url" alt="">
                    <span v-else class="avatar-fallback">{{ avatarText(order.nickname) }}</span>
                    <span><b>{{ order.nickname || "--" }}</b><small>ID {{ order.user_id || "--" }}</small></span>
                  </button>
                </td>
                <td><span class="platform-tag" :style="platformStyle(order.platform_id)"><i></i>{{ order.platform_name || "--" }}</span></td>
                <td>{{ time(order.publish_time) }}</td>
                <td><span class="record-value">{{ order.history_record || "--" }}</span><small class="record-rate">{{ percent(order.history_hit_rate) }}</small></td>
                <td class="money">¥{{ money(order.stake) }}</td>
                <td>{{ number(order.follow_num) }}</td>
                <td>{{ order.pass_composition || passText(order) }}</td>
                <td class="match-summary"><b>{{ firstMatch(order) }}</b><small v-if="(order.matches || []).length > 1">另有 {{ order.matches.length - 1 }} 场</small><small>{{ deadlineMeta(order) }}</small></td>
                <td><span :class="resultClass(order.result)">{{ resultText(order.result) }}</span></td>
                <td><div class="row-actions"><button class="secondary-button" type="button" @click="toggleOrder(order.id)">{{ isExpanded(order.id) ? "收起" : "展开" }}</button><button class="primary-button" type="button" @click="openOrder(order.id)">详情</button></div></td>
              </tr>
              <tr v-if="isExpanded(order.id)" class="expanded-row">
                <td colspan="10">
                  <div v-if="(order.matches || []).length" class="match-grid">
                    <div v-for="match in order.matches" :key="match.id || match.match_code"><b>{{ match.match_code || "--" }} · {{ match.home || "--" }} VS {{ match.away || "--" }}</b><span>{{ match.play_type || "--" }} · {{ match.selection || "--" }} · SP {{ match.odds || "--" }}</span><small>{{ match.result || "待开奖" }} {{ scoreText(match) }}</small></div>
                  </div>
                  <EmptyState v-else title="比赛明细待同步" description="当前订单尚未生成拆分比赛数据" />
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </section>
    <AppPagination :page="page" :pages="pages" :disabled="loading" @change="changePage" />

    <div v-if="userModalOpen" class="modal-backdrop" role="presentation" @mousedown.self="closeUser">
      <section class="user-modal" role="dialog" aria-modal="true" aria-labelledby="user-modal-title">
        <button class="modal-close" type="button" aria-label="关闭" @click="closeUser">×</button>
        <LoadingSkeleton v-if="userLoading" :count="4" />
        <ErrorState v-else-if="userError" :description="userError" @retry="reloadUser" />
        <template v-else-if="userDetail.user">
          <header class="modal-profile">
            <img v-if="userDetail.user.avatar_url" class="modal-avatar" :src="userDetail.user.avatar_url" alt="">
            <span v-else class="modal-avatar avatar-fallback">{{ avatarText(userDetail.user.nickname) }}</span>
            <div><span class="eyebrow">Sender profile</span><h2 id="user-modal-title">{{ userDetail.user.nickname || "--" }}</h2><p>{{ userDetail.user.platform_name || "--" }} · ID {{ userDetail.user.user_id || "--" }}</p></div>
          </header>
          <div class="modal-kpis"><div><span>总方案</span><b>{{ number(userDetail.user.total_orders) }}</b></div><div><span>命中率</span><b>{{ percent(userDetail.user.hit_rate) }}</b></div><div><span>跟单人数</span><b>{{ number(userDetail.user.follow_num) }}</b></div></div>
          <div class="modal-orders-title"><h3>最近方案</h3><span>{{ (userDetail.orders || []).length }} 条</span></div>
          <div class="modal-orders">
            <button v-for="item in (userDetail.orders || []).slice(0, 10)" :key="item.id" type="button" @click="openOrder(item.id)"><span><b>{{ item.platform_order_id || item.id }}</b><small>{{ time(item.publish_time) }}</small></span><span>{{ item.pass_composition || passText(item) }}</span><strong>¥{{ money(item.stake) }}</strong></button>
            <EmptyState v-if="!(userDetail.orders || []).length" title="暂无方案" description="该用户还没有可展示方案" />
          </div>
        </template>
      </section>
    </div>
  </section>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue"
import { useRouter } from "vue-router"
import axios from "axios"
import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"
import EmptyState from "../components/ui/EmptyState.vue"
import ErrorState from "../components/ui/ErrorState.vue"
import AppPagination from "../components/ui/AppPagination.vue"

const router = useRouter()
const platform = ref("")
const keyword = ref("")
const result = ref("")
const sort = ref("publish_time")
const platforms = ref([])
const orders = ref([])
const expandedOrders = ref(new Set())
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const loading = ref(true)
const error = ref("")
const userModalOpen = ref(false)
const userLoading = ref(false)
const userError = ref("")
const userDetail = ref({})
const activeUser = ref(null)

const platformColors = {
  1: [239, 108, 19],
  2: [126, 61, 232],
  3: [220, 37, 112],
  4: [39, 103, 232],
  5: [8, 145, 178],
  6: [25, 156, 85],
}

async function loadPlatforms() {
  try {
    const response = await axios.get("/api/platform/list")
    platforms.value = Array.isArray(response.data?.data) ? response.data.data : []
  } catch { platforms.value = [] }
}

async function load() {
  loading.value = true
  error.value = ""
  const params = { page: page.value, page_size: 30, keyword: keyword.value, result: result.value }
  if (platform.value) params.platform_id = Number(platform.value)
  try {
    const response = await axios.get("/api/portal/schemes", { params })
    if (!response.data || response.data.code !== 200) throw new Error()
    orders.value = response.data.data || []
    page.value = response.data.page || 1
    pages.value = response.data.pages || 1
    total.value = response.data.total || 0
    expandedOrders.value = new Set()
  } catch {
    orders.value = []
    total.value = 0
    error.value = "方案数据暂时无法读取，请稍后重试或检查接口连接状态"
  } finally { loading.value = false }
}

async function openUser(order) {
  activeUser.value = order
  userModalOpen.value = true
  document.body.style.overflow = "hidden"
  await reloadUser()
}

async function reloadUser() {
  if (!activeUser.value) return
  userLoading.value = true
  userError.value = ""
  try {
    const response = await axios.get(`/api/portal/user/${activeUser.value.platform_id}/${activeUser.value.user_id}`)
    if (!response.data || response.data.code !== 200) throw new Error()
    userDetail.value = response.data.data || {}
  } catch {
    userDetail.value = {}
    userError.value = "发单人主页数据暂时无法读取"
  } finally { userLoading.value = false }
}

function closeUser() { userModalOpen.value = false; document.body.style.overflow = "" }
function onKeydown(event) { if (event.key === "Escape" && userModalOpen.value) closeUser() }
function resetLoad() { page.value = 1; load() }
function resetFilters() { platform.value = ""; keyword.value = ""; result.value = ""; resetLoad() }
function changePage(value) { page.value = value; load(); window.scrollTo({ top: 0, behavior: "smooth" }) }
function toggleOrder(id) { const next = new Set(expandedOrders.value); next.has(id) ? next.delete(id) : next.add(id); expandedOrders.value = next }
function isExpanded(id) { return expandedOrders.value.has(id) }
function openOrder(id) { closeUser(); router.push(`/order/detail/${id}`) }
function platformStyle(id) { const color = platformColors[Number(id)] || [98, 98, 104]; return { color: `rgb(${color.join(",")})`, backgroundColor: `rgba(${color.join(",")},.2)` } }
function avatarText(value) { return String(value || "球").slice(-1) }
function firstMatch(order) { const match = (order.matches || [])[0]; return match ? `${match.match_code || "--"} · ${match.home || "--"} VS ${match.away || "--"}` : "比赛明细待同步" }
function money(value) { return Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 2 }) }
function number(value) { return Math.round(Number(value || 0)).toLocaleString("zh-CN") }
function percent(value) { return value === null || value === undefined ? "--" : `${Number(value).toFixed(2)}%` }
function time(value) { return value ? String(value).replace("T", " ").replace("Z", "") : "--" }
function passText(order) { return Number(order.bet_count || 0) > 0 ? `${order.bet_count}注 ${order.pass_summary || "--"}` : (order.pass_summary || "--") }
function resultText(value) { return value === "赢" ? "已中奖" : value === "输" ? "未中奖" : (value || "待开奖") }
function resultClass(value) { return `status-chip ${value === "赢" ? "success" : value === "输" ? "danger" : "warning"}` }
function deadlineMeta(order) { if (order.deadline_source === "deadline" && order.deadline_exact) return `精确截止：${time(order.deadline_time)}`; if (order.deadline_source === "kickoff_proxy") return `开赛时间参考：${time(order.deadline_time)}`; if (order.deadline_source === "pending_fallback") return "待开奖状态参考"; return "截止信息未提供" }
function scoreText(match) { return match.home_score === null || match.home_score === undefined || match.away_score === null || match.away_score === undefined ? "" : `· ${match.home_score}:${match.away_score}` }

onMounted(() => { loadPlatforms(); load(); window.addEventListener("keydown", onKeydown) })
onUnmounted(() => { window.removeEventListener("keydown", onKeydown); document.body.style.overflow = "" })
</script>

<style scoped>
.toolbar select{min-width:140px}.toolbar .search{min-width:260px;flex:1}.orders-card{margin-top:14px;overflow:hidden}.orders-table{min-width:1260px}.user-cell{max-width:190px;padding:0;border:0;display:flex;align-items:center;gap:9px;color:var(--text-main);background:transparent;text-align:left}.user-cell>span:last-child{min-width:0}.user-cell b,.user-cell small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.user-cell small{margin-top:3px;color:var(--text-muted);font-size:10px}.table-avatar{width:36px;height:36px;flex:0 0 36px;border-radius:50%;object-fit:cover;background:var(--surface-soft)}.platform-tag{padding:5px 9px;border-radius:999px;display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:700}.platform-tag i{width:6px;height:6px;border-radius:50%;background:currentColor}.record-value,.record-rate{display:block}.record-value{font-size:11px;font-weight:650}.record-rate{margin-top:3px;color:var(--text-muted);font-size:9px}.match-summary{max-width:260px}.match-summary b,.match-summary small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.match-summary b{color:var(--text-main);font-size:12px}.match-summary small{margin-top:4px;color:var(--text-muted);font-size:10px}.row-actions{display:flex;gap:6px}.row-actions button{min-height:34px;padding:0 10px;font-size:11px}.expanded-row td{padding:12px 18px;background:#fafbf4}.match-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px}.match-grid>div{padding:11px;border:1px solid var(--border);border-radius:10px;background:#fff}.match-grid b,.match-grid span,.match-grid small{display:block}.match-grid b{font-size:11px}.match-grid span,.match-grid small{margin-top:4px;color:var(--text-muted);font-size:10px}.modal-backdrop{position:fixed;inset:0;z-index:1000;padding:20px;display:grid;place-items:center;background:rgba(17,17,18,.48);backdrop-filter:blur(3px)}.user-modal{position:relative;width:min(560px,100%);max-height:min(76vh,680px);padding:20px;border:1px solid var(--border);border-radius:18px;overflow-y:auto;background:#fff;box-shadow:0 28px 80px rgba(0,0,0,.22)}.modal-close{position:absolute;right:14px;top:12px;width:32px;height:32px;border:0;border-radius:50%;color:var(--text-secondary);background:var(--surface-soft);font-size:21px;line-height:1}.modal-profile{padding-right:38px;display:flex;align-items:center;gap:12px}.modal-avatar{width:54px;height:54px;flex:0 0 54px;border-radius:50%;object-fit:cover}.modal-profile h2{margin:1px 0 0;font-size:20px}.modal-profile p{margin:4px 0 0;color:var(--text-muted);font-size:11px}.modal-kpis{margin-top:16px;display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.modal-kpis div{padding:11px;border-radius:11px;background:var(--surface-soft)}.modal-kpis span,.modal-kpis b{display:block}.modal-kpis span{color:var(--text-muted);font-size:9px}.modal-kpis b{margin-top:5px;font-size:14px}.modal-orders-title{margin:18px 0 8px;display:flex;align-items:center;justify-content:space-between}.modal-orders-title h3{margin:0;font-size:14px}.modal-orders-title span{color:var(--text-muted);font-size:10px}.modal-orders{display:grid;gap:6px}.modal-orders>button{padding:10px;border:1px solid var(--border);border-radius:10px;display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:12px;align-items:center;color:var(--text-main);background:#fff;text-align:left}.modal-orders>button:hover{border-color:var(--border-strong);background:var(--surface-soft)}.modal-orders span b,.modal-orders span small{display:block}.modal-orders span small{margin-top:3px;color:var(--text-muted);font-size:9px}.modal-orders>button>span:nth-child(2){color:var(--text-secondary);font-size:10px}.modal-orders>button>strong{font-size:11px}@media(max-width:767px){.toolbar>*{width:100%}.toolbar .search{min-width:0}.modal-backdrop{padding:10px}.user-modal{max-height:88vh;padding:16px}.modal-kpis{grid-template-columns:1fr}.modal-orders>button{grid-template-columns:minmax(0,1fr) auto}.modal-orders>button>span:nth-child(2){display:none}}
</style>
