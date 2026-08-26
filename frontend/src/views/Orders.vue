<template>
  <section class="page-shell">
    <header class="page-header"><div><h1>方案大厅</h1><p>聚合各平台真实订单、拆分比赛与结算状态</p></div><div class="page-actions"><span class="page-time">共 {{ number(total) }} 条</span><button class="primary-button" type="button" @click="load">刷新</button></div></header>
    <section class="toolbar app-card">
      <select v-model="platform" aria-label="平台" @change="resetLoad"><option value="">全部平台</option><option v-for="item in platforms" :key="item.platform_id" :value="String(item.platform_id)">{{ item.name }}</option></select>
      <select v-model="result" aria-label="状态" @change="resetLoad"><option value="">全部状态</option><option value="待开奖">待开奖</option><option value="赢">已中奖</option><option value="输">未中奖</option></select>
      <input v-model.trim="keyword" class="search" type="search" placeholder="发单人、用户 ID、订单号或比赛" @keyup.enter="resetLoad">
      <select v-model="sort" aria-label="排序"><option value="publish_time">按发单时间</option></select>
      <button class="primary-button" type="button" @click="resetLoad">查询</button><button class="secondary-button" type="button" @click="resetFilters">重置</button>
    </section>

    <section class="orders-card app-card">
      <LoadingSkeleton v-if="loading" :count="7" />
      <ErrorState v-else-if="error" :description="error" @retry="load" />
      <EmptyState v-else-if="!orders.length" title="暂无方案" description="当前筛选条件下没有方案数据" />
      <div v-else class="table-wrap">
        <table class="data-table orders-table"><thead><tr><th>发单人</th><th>平台</th><th>发单时间</th><th>历史战绩</th><th>自购</th><th>跟单</th><th>串关</th><th>方案详情</th><th>状态</th><th>操作</th></tr></thead>
          <tbody><template v-for="order in orders" :key="order.id"><tr>
            <td><button class="user-cell" type="button" @click="openUser(order)"><span class="avatar-fallback">{{ avatarText(order.nickname) }}</span><span><b>{{ order.nickname || "--" }}</b><small>ID {{ order.user_id || "--" }}</small></span></button></td>
            <td><span class="platform-tag">{{ order.platform_name || "--" }}</span></td><td>{{ time(order.publish_time) }}</td><td>{{ order.history_record || "--" }}</td><td class="money">¥{{ money(order.stake) }}</td><td>{{ number(order.follow_num) }}</td><td>{{ order.pass_composition || passText(order) }}</td>
            <td class="match-summary"><b>{{ firstMatch(order) }}</b><small v-if="(order.matches||[]).length>1">另有 {{ order.matches.length-1 }} 场</small><small>{{ deadlineMeta(order) }}</small></td>
            <td><span :class="resultClass(order.result)">{{ resultText(order.result) }}</span></td><td><div class="row-actions"><button class="secondary-button" type="button" @click="toggleOrder(order.id)">{{ isExpanded(order.id)?"收起":"展开" }}</button><button class="primary-button" type="button" @click="openOrder(order.id)">查看详情</button></div></td>
          </tr><tr v-if="isExpanded(order.id)" class="expanded-row"><td colspan="10"><div v-if="(order.matches||[]).length" class="match-grid"><div v-for="match in order.matches" :key="match.id"><b>{{ match.match_code || "--" }} · {{ match.home || "--" }} VS {{ match.away || "--" }}</b><span>{{ match.play_type || "--" }} · {{ match.selection || "--" }}</span><small>{{ match.result || "待开奖" }} {{ scoreText(match) }}</small></div></div><EmptyState v-else title="比赛明细待同步" description="当前订单尚未生成拆分比赛数据" /></td></tr></template></tbody>
        </table>
      </div>
    </section>
    <AppPagination :page="page" :pages="pages" :disabled="loading" @change="changePage" />
  </section>
</template>
<script setup>
import { onMounted, ref } from "vue"; import { useRouter } from "vue-router"; import axios from "axios"; import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"; import EmptyState from "../components/ui/EmptyState.vue"; import ErrorState from "../components/ui/ErrorState.vue"; import AppPagination from "../components/ui/AppPagination.vue"
const router=useRouter(),platform=ref(""),keyword=ref(""),result=ref(""),sort=ref("publish_time"),platforms=ref([]),orders=ref([]),expandedOrders=ref(new Set()),page=ref(1),pages=ref(1),total=ref(0),loading=ref(true),error=ref("")
async function loadPlatforms(){try{const r=await axios.get("/api/platform/list");const rows=r.data&&r.data.data;platforms.value=Array.isArray(rows)?rows:[]}catch{platforms.value=[]}}
async function load(){loading.value=true;error.value="";const params={page:page.value,page_size:30,keyword:keyword.value,result:result.value};if(platform.value)params.platform_id=Number(platform.value);try{const r=await axios.get("/api/portal/schemes",{params});if(!r.data||r.data.code!==200)throw new Error();orders.value=r.data.data||[];page.value=r.data.page||1;pages.value=r.data.pages||1;total.value=r.data.total||0;expandedOrders.value=new Set()}catch{orders.value=[];total.value=0;error.value="方案数据暂时无法读取，请稍后重试或检查接口连接状态"}finally{loading.value=false}}
function resetLoad(){page.value=1;load()} function resetFilters(){platform.value="";keyword.value="";result.value="";resetLoad()} function changePage(v){page.value=v;load();window.scrollTo({top:0,behavior:"smooth"})}
function toggleOrder(id){const n=new Set(expandedOrders.value);n.has(id)?n.delete(id):n.add(id);expandedOrders.value=n} function isExpanded(id){return expandedOrders.value.has(id)} function openUser(o){router.push("/user/detail/"+o.platform_id+"/"+o.user_id)} function openOrder(id){router.push("/order/detail/"+id)}
function avatarText(v){return String(v||"球").slice(-1)} function firstMatch(o){const m=(o.matches||[])[0];return m?(m.match_code||"--")+" · "+(m.home||"--")+" VS "+(m.away||"--"):"比赛明细待同步"} function money(v){return Number(v||0).toLocaleString("zh-CN",{maximumFractionDigits:2})} function number(v){return Math.round(Number(v||0)).toLocaleString("zh-CN")} function time(v){return v?String(v).replace("T"," ").replace("Z",""):"--"} function passText(o){const c=Number(o.bet_count||0),p=o.pass_summary||"--";return c>0?c+"注"+p:p}
function resultText(v){return v==="赢"?"已中奖":v==="输"?"未中奖":v||"待开奖"} function resultClass(v){return "status-chip "+(v==="赢"?"success":v==="输"?"danger":"warning")}
function deadlineMeta(o){if(o.deadline_source==="deadline"&&o.deadline_exact)return "精确截止："+time(o.deadline_time);if(o.deadline_source==="kickoff_proxy")return "开赛时间参考："+time(o.deadline_time);if(o.deadline_source==="pending_fallback")return "待开奖状态参考";return "截止信息未提供"} function scoreText(m){return m.home_score===null||m.home_score===undefined||m.away_score===null||m.away_score===undefined?"":"· "+m.home_score+":"+m.away_score}
onMounted(()=>{loadPlatforms();load()})
</script>
<style scoped>
.toolbar select{min-width:140px}.toolbar .search{min-width:260px;flex:1}.orders-card{margin-top:14px;overflow:hidden}.orders-table{min-width:1320px}.user-cell{max-width:190px;padding:0;border:0;display:flex;align-items:center;gap:9px;color:var(--text-main);background:transparent;text-align:left}.user-cell>span:last-child{min-width:0}.user-cell b,.user-cell small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.user-cell small{margin-top:3px;color:var(--text-muted);font-size:10px}.platform-tag{padding:5px 8px;border-radius:8px;background:var(--accent-soft);font-size:11px;font-weight:650}.match-summary{max-width:260px}.match-summary b,.match-summary small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.match-summary b{color:var(--text-main);font-size:12px}.match-summary small{margin-top:4px;color:var(--text-muted);font-size:10px}.row-actions{display:flex;gap:6px}.row-actions button{min-height:34px;padding:0 10px;font-size:11px}.expanded-row td{padding:12px 18px;background:#fafbf4}.match-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px}.match-grid>div{padding:11px;border:1px solid var(--border);border-radius:10px;background:#fff}.match-grid b,.match-grid span,.match-grid small{display:block}.match-grid b{font-size:11px}.match-grid span,.match-grid small{margin-top:4px;color:var(--text-muted);font-size:10px}@media(max-width:767px){.toolbar>*{width:100%}.toolbar .search{min-width:0}}
</style>
