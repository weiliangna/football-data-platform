<template>
  <section class="page-shell news-page">
    <header class="page-header"><div><span class="eyebrow">Public match news</span><h1>比赛新闻</h1><p>按公开比赛聚合新闻、球队影响与数据来源</p></div><button class="primary-button" type="button" :disabled="loading" @click="loadNews">刷新当前比赛</button></header>
    <nav class="sub-nav app-card" aria-label="赛事数据二级导航"><router-link to="/match-data">水位看板</router-link><router-link to="/match-news">比赛新闻</router-link></nav>
    <section class="toolbar app-card section-gap"><label>选择比赛<select v-model="selectedId" class="field" @change="loadNews"><option value="">请选择公开比赛</option><option v-for="match in matches" :key="match.externalId" :value="match.externalId">{{ match.code || "--" }} · {{ match.home || "主队" }} VS {{ match.away || "客队" }}</option></select></label><small>数据来源：公开网络数据 / scpai.top</small></section>
    <LoadingSkeleton v-if="loading" class="section-gap" type="rows" :count="5" />
    <ErrorState v-else-if="error" class="app-card section-gap" :description="error" @retry="loadNews" />
    <template v-else-if="selectedId">
      <section class="news-head app-card section-gap"><div><span class="eyebrow">{{ currentMatch.competition || "公开赛事" }}</span><h2>{{ currentMatch.home || "主队" }} VS {{ currentMatch.away || "客队" }}</h2><p>生成于 {{ formatTime(news.generatedAt || news.updatedAt) }}</p></div><span class="status-chip">{{ statusText }}</span></section>
      <div v-if="categories.length" class="category-tabs"><button type="button" :class="{active:category===''}" @click="category=''">全部 {{ items.length }}</button><button v-for="item in categories" :key="item" type="button" :class="{active:category===item}" @click="category=item">{{ item }} {{ categoryCount(item) }}</button></div>
      <section v-if="visibleItems.length" class="news-list"><article v-for="(item,index) in visibleItems" :key="item.url||index" class="app-card lift-card"><header><span class="status-chip" :class="{warning:item.important}">{{ item.category || "比赛资讯" }}</span><time>{{ formatTime(item.publishedAt) }}</time></header><h2>{{ item.title || "新闻标题待同步" }}</h2><p>{{ item.summary || "暂无摘要" }}</p><footer><span>{{ item.source || "公开来源" }}</span><span v-if="item.teamImpact?.label" class="impact">{{ item.teamImpact.label }}</span><a v-if="safeUrl(item.url)" :href="item.url" target="_blank" rel="noopener noreferrer">查看原文 ↗</a></footer></article></section>
      <EmptyState v-else class="app-card section-gap" title="暂无比赛新闻" description="该比赛当前没有公开新闻，或当前分类暂无内容" />
    </template>
    <EmptyState v-else class="app-card section-gap" title="请选择一场比赛" description="比赛 ID 仅来自公开比赛列表，不支持手工枚举" />
  </section>
</template>
<script setup>
import { computed, onMounted, ref } from "vue"
import { useRoute } from "vue-router"
import axios from "axios"
import EmptyState from "../components/ui/EmptyState.vue"
import ErrorState from "../components/ui/ErrorState.vue"
import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"
const route=useRoute(),matches=ref([]),selectedId=ref(""),news=ref({}),category=ref(""),loading=ref(true),error=ref("")
const items=computed(()=>Array.isArray(news.value.items)?news.value.items:[]),categories=computed(()=>Array.isArray(news.value.categories)?news.value.categories:[]),visibleItems=computed(()=>category.value?items.value.filter(item=>item.category===category.value):items.value),currentMatch=computed(()=>news.value.match||matches.value.find(item=>item.externalId===selectedId.value)||{}),statusText=computed(()=>({fresh:"数据已更新",cached:"使用缓存数据",stale:"显示最近缓存",unavailable:"暂不可用"}[news.value.status]||"公开新闻"))
async function loadMatches(){const response=await axios.get("/api/matches");matches.value=response.data?.data?.matches||[];const requested=String(route.query.match||"");selectedId.value=matches.value.some(item=>item.externalId===requested)?requested:(matches.value[0]?.externalId||"")}
async function loadNews(){if(!selectedId.value){news.value={};loading.value=false;return}loading.value=true;error.value="";category.value="";try{const response=await axios.get(`/api/matches/${encodeURIComponent(selectedId.value)}/news`);news.value=response.data?.data||{}}catch(errorValue){news.value={};error.value=errorValue.response?.data?.msg||"比赛新闻暂时无法读取"}finally{loading.value=false}}
async function initialize(){loading.value=true;error.value="";try{await loadMatches();await loadNews()}catch{matches.value=[];news.value={};error.value="公开比赛列表暂时无法读取";loading.value=false}}
function categoryCount(value){return items.value.filter(item=>item.category===value).length} function safeUrl(value){try{const url=new URL(value);return ["http:","https:"].includes(url.protocol)}catch{return false}} function formatTime(value){if(!value)return "时间待同步";const date=new Date(value);return Number.isNaN(date.getTime())?String(value):date.toLocaleString("zh-CN",{hour12:false})}
onMounted(initialize)
</script>
<style scoped>
.sub-nav{padding:7px;display:flex;gap:6px}.sub-nav a{padding:10px 18px;border-radius:9px;color:var(--text-secondary);font-size:13px;font-weight:700}.sub-nav a.router-link-exact-active{color:var(--text-main);background:var(--accent-soft)}.section-gap{margin-top:14px}.toolbar{justify-content:space-between}.toolbar label{display:flex;align-items:center;gap:10px;color:var(--text-secondary);font-size:11px}.toolbar select{min-width:420px}.toolbar small{color:var(--text-muted)}.news-head{padding:20px;display:flex;align-items:center;justify-content:space-between}.news-head h2{margin:0;font-size:22px}.news-head p{margin:7px 0 0;color:var(--text-muted);font-size:11px}.category-tabs{margin:14px 0;display:flex;flex-wrap:wrap;gap:7px}.category-tabs button{padding:9px 13px;border:1px solid var(--border);border-radius:999px;color:var(--text-secondary);background:#fff;font-size:11px}.category-tabs button.active{color:var(--accent-text);border-color:var(--accent);background:var(--accent)}.news-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.news-list article{padding:18px}.news-list header,.news-list footer{display:flex;align-items:center;gap:10px}.news-list header{justify-content:space-between}.news-list time{color:var(--text-muted);font-size:10px}.news-list h2{margin:15px 0 8px;font-size:17px}.news-list p{min-height:42px;margin:0;color:var(--text-secondary);font-size:12px;line-height:1.7}.news-list footer{margin-top:15px;padding-top:12px;border-top:1px solid var(--border);color:var(--text-muted);font-size:10px}.news-list footer a{margin-left:auto;color:#71840e;font-weight:700}.impact{color:var(--text-secondary)}@media(max-width:760px){.toolbar,.toolbar label{align-items:flex-start;flex-direction:column}.toolbar select{min-width:0;width:100%}.news-list{grid-template-columns:1fr}}
</style>
