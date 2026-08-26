<template>
  <section class="page-shell">
    <header class="page-header"><div><h1>赛果统计</h1><p>标准化球队名称、全场比分与半场比分</p></div><div class="page-actions"><button class="secondary-button" type="button" :disabled="!filteredRows.length" @click="exportRows">导出</button><button class="primary-button" type="button" @click="load">刷新</button></div></header>
    <section class="toolbar app-card"><input v-model="month" type="month" aria-label="月份"><input v-model.trim="keyword" class="search" type="search" placeholder="搜索场次或球队"><select v-model="status" aria-label="状态"><option value="">全部状态</option><option value="finished">已完赛</option></select></section>
    <section class="results-card app-card">
      <LoadingSkeleton v-if="loading" :count="8" /><ErrorState v-else-if="error" :description="error" @retry="load" /><EmptyState v-else-if="!filteredRows.length" title="暂无赛果" description="当前月份或搜索条件下没有赛果数据" />
      <div v-else class="table-wrap"><table class="data-table results-table"><thead><tr><th>场次</th><th>对阵</th><th>全场比分</th><th>半场比分</th><th>状态</th><th>结束时间</th></tr></thead><tbody><tr v-for="item in filteredRows" :key="item.id"><td><span class="match-code">{{ item.match_code || "--" }}</span></td><td><b class="teams">{{ item.home || "--" }} <i>VS</i> {{ item.away || "--" }}</b></td><td><strong class="score-value">{{ score(item) }}</strong></td><td>{{ halfScore(item) }}</td><td><span class="status-chip success">已完赛</span></td><td>{{ time(item.finished_time) }}</td></tr></tbody></table></div>
    </section><AppPagination :page="page" :pages="pages" :disabled="loading" @change="changePage" />
  </section>
</template>
<script setup>
import { computed,onMounted,ref } from "vue";import axios from "axios";import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue";import EmptyState from "../components/ui/EmptyState.vue";import ErrorState from "../components/ui/ErrorState.vue";import AppPagination from "../components/ui/AppPagination.vue";import { downloadExcel,stamp } from "../utils/export.js"
const rows=ref([]),page=ref(1),pages=ref(1),loading=ref(true),error=ref(""),month=ref(""),keyword=ref(""),status=ref("")
const filteredRows=computed(()=>{const q=keyword.value.toLowerCase();return rows.value.filter(item=>(!month.value||String(item.finished_time||"").startsWith(month.value))&&(!q||[item.match_code,item.home,item.away].some(v=>String(v||"").toLowerCase().includes(q))))})
async function load(){loading.value=true;error.value="";try{const r=await axios.get("/api/portal/results",{params:{page:page.value,page_size:50}});if(!r.data||r.data.code!==200)throw new Error();rows.value=r.data.data||[];pages.value=r.data.pages||1}catch{rows.value=[];error.value="赛果数据暂时无法读取，请稍后重试或检查接口连接状态"}finally{loading.value=false}}
function changePage(v){page.value=v;load()} function score(i){return i.home_score===null||i.home_score===undefined||i.away_score===null||i.away_score===undefined?"--":i.home_score+" : "+i.away_score} function halfScore(i){return i.half_home_score===null||i.half_home_score===undefined||i.half_away_score===null||i.half_away_score===undefined?"--":i.half_home_score+" : "+i.half_away_score} function time(v){return v?String(v).replace("T"," ").replace("Z",""):"--"}
function exportRows(){downloadExcel("赛果统计",["场次","主队","客队","全场比分","半场比分","结束时间"],filteredRows.value.map(i=>[i.match_code||"",i.home||"",i.away||"",score(i),halfScore(i),time(i.finished_time)]),stamp("football-results"))} onMounted(load)
</script>
<style scoped>
.toolbar .search{min-width:260px;flex:1}.results-card{margin-top:14px;overflow:hidden}.results-table{min-width:820px}.match-code{padding:5px 8px;border-radius:8px;color:#68790e;background:var(--accent-soft);font-size:11px;font-weight:700}.teams{color:var(--text-main);font-size:13px}.teams i{margin:0 6px;color:var(--text-muted);font-size:9px;font-style:normal}.score-value{color:var(--text-main);font-size:18px}@media(max-width:600px){.toolbar>*{width:100%}.toolbar .search{min-width:0}}
</style>
