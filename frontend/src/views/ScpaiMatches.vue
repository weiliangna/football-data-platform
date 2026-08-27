<template>
  <section class="page-shell match-data-page">
    <header class="page-header">
      <div><span class="eyebrow">Public match intelligence</span><h1>赛事数据</h1><p>公开比赛、水位方向与市场变化集中查看</p></div>
      <button class="primary-button" type="button" :disabled="loading" @click="load">刷新数据</button>
    </header>
    <nav class="sub-nav app-card" aria-label="赛事数据二级导航"><router-link to="/match-data">水位看板</router-link><router-link to="/match-news">比赛新闻</router-link></nav>
    <section class="source-bar app-card"><div><i :class="statusClass"></i><b>{{ statusText }}</b><span v-if="data.updatedAt">更新于 {{ formatTime(data.updatedAt) }}</span></div><small>数据来源：公开网络数据 / scpai.top</small></section>
    <LoadingSkeleton v-if="loading" class="section-gap" type="cards" :count="4" />
    <ErrorState v-else-if="error" class="app-card section-gap" :description="error" @retry="load" />
    <template v-else-if="matches.length">
      <section class="summary-grid section-gap"><article class="app-card"><span>公开比赛</span><strong>{{ matches.length }}</strong></article><article class="app-card"><span>市场数量</span><strong>{{ number(data.summary?.markets) }}</strong></article><article class="app-card"><span>盘口类型</span><strong>{{ number(data.summary?.marketTypes) }}</strong></article><article class="app-card"><span>选择项</span><strong>{{ number(data.summary?.selections) }}</strong></article></section>
      <section class="match-grid section-gap">
        <router-link v-for="match in matches" :key="match.externalId" class="match-item app-card lift-card" :to="`/match-data/${encodeURIComponent(match.externalId)}`">
          <header><div><span class="match-code">{{ match.code || "--" }}</span><small>{{ match.competition || "赛事待同步" }}</small></div><span class="status-chip">{{ match.status || "公开数据" }}</span></header>
          <p class="kickoff">{{ formatTime(match.kickoffAt || match.kickoff) }}</p>
          <div class="teams"><div><b>{{ match.home || "主队待同步" }}</b><small>排名 {{ match.homeRank ?? "--" }}</small></div><em>VS</em><div><b>{{ match.away || "客队待同步" }}</b><small>排名 {{ match.awayRank ?? "--" }}</small></div></div>
          <footer><span>市场 {{ number(match.marketCount) }}</span><span>共识 {{ number(match.consensusCount) }}</span><strong>{{ match.direction || match.classification || "查看详情" }} →</strong></footer>
        </router-link>
      </section>
    </template>
    <EmptyState v-else class="app-card section-gap" title="暂无公开比赛数据" :description="data.message || '数据源暂时没有返回可展示的比赛'" />
  </section>
</template>
<script setup>
import { computed, onMounted, ref } from "vue"
import axios from "axios"
import EmptyState from "../components/ui/EmptyState.vue"
import ErrorState from "../components/ui/ErrorState.vue"
import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"

const data=ref({}),loading=ref(true),error=ref("")
const matches=computed(()=>Array.isArray(data.value.matches)?data.value.matches:[])
const statusText=computed(()=>({fresh:"数据已更新",cached:"使用缓存数据",stale:"数据源暂不可用，显示最近缓存",unavailable:"数据源暂不可用"}[data.value.status]||"等待数据"))
const statusClass=computed(()=>data.value.status==="stale"?"warning":data.value.status==="unavailable"?"failed":"active")
async function load(){loading.value=true;error.value="";try{const response=await axios.get("/api/matches");data.value=response.data?.data||{}}catch{data.value={};error.value="赛事数据暂时无法读取，请稍后重试"}finally{loading.value=false}}
function number(value){return Number(value||0).toLocaleString("zh-CN")}
function formatTime(value){if(!value)return "时间待同步";const date=new Date(value);return Number.isNaN(date.getTime())?String(value):date.toLocaleString("zh-CN",{hour12:false})}
onMounted(load)
</script>
<style scoped>
.sub-nav{padding:7px;display:flex;gap:6px}.sub-nav a{padding:10px 18px;border-radius:9px;color:var(--text-secondary);font-size:13px;font-weight:700}.sub-nav a.router-link-exact-active{color:var(--text-main);background:var(--accent-soft)}.source-bar{margin-top:12px;padding:12px 15px;display:flex;align-items:center;justify-content:space-between;gap:12px;color:var(--text-muted);font-size:11px}.source-bar>div{display:flex;align-items:center;gap:8px}.source-bar i{width:7px;height:7px;border-radius:50%;background:#999}.source-bar i.active{background:var(--success)}.source-bar i.warning{background:var(--warning)}.source-bar i.failed{background:var(--danger)}.source-bar b{color:var(--text-secondary)}.section-gap{margin-top:14px}.summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.summary-grid article{padding:17px}.summary-grid span,.summary-grid strong{display:block}.summary-grid span{color:var(--text-muted);font-size:11px}.summary-grid strong{margin-top:7px;font-size:26px}.match-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.match-item{padding:18px;color:inherit}.match-item>header,.match-item>footer{display:flex;align-items:center;justify-content:space-between;gap:10px}.match-item header>div{display:flex;align-items:center;gap:8px}.match-code{padding:5px 8px;border-radius:7px;color:#61730b;background:var(--accent-soft);font-size:11px;font-weight:800}.match-item header small,.kickoff{color:var(--text-muted);font-size:11px}.kickoff{margin:15px 0 8px}.teams{display:grid;grid-template-columns:1fr 40px 1fr;align-items:center;gap:10px}.teams div:last-child{text-align:right}.teams b,.teams small{display:block}.teams b{font-size:16px}.teams small{margin-top:5px;color:var(--text-muted);font-size:10px}.teams em{color:var(--text-muted);font-size:10px;font-style:normal;text-align:center}.match-item>footer{margin-top:18px;padding-top:12px;border-top:1px solid var(--border);color:var(--text-muted);font-size:10px}.match-item>footer strong{margin-left:auto;color:var(--text-main)}@media(max-width:900px){.summary-grid{grid-template-columns:repeat(2,1fr)}.match-grid{grid-template-columns:1fr}}@media(max-width:560px){.source-bar{align-items:flex-start;flex-direction:column}.summary-grid{grid-template-columns:1fr 1fr}.teams b{font-size:14px}}
</style>
