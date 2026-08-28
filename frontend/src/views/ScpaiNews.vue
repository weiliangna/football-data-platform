<template>
  <section class="page-shell scpai-news-page">
    <header class="scpai-report-head">
      <div><span class="scpai-kicker">MATCH NEWS DESK</span><h1>绿茵智核比赛新闻</h1><p>按比赛整理公开资讯、球队影响与发布时间</p></div>
      <div class="scpai-report-actions"><span :class="['scpai-live-pill',news.status]">{{ newsRefreshing ? "数据同步中" : newsStatus }}</span></div>
    </header>
    <nav class="scpai-page-tabs" aria-label="赛事数据二级导航"><router-link to="/match-data">水位看板</router-link><router-link to="/match-news">比赛新闻</router-link></nav>

    <section class="scpai-news-layout">
      <aside class="scpai-news-match-panel">
        <header><div><h2>比赛队列</h2><p>选择比赛后按需加载对应新闻</p></div><span>{{ matches.length }} 场</span></header>
        <LoadingSkeleton v-if="matchesLoading" type="rows" :count="5" />
        <ErrorState v-else-if="matchesError && !matches.length" :description="matchesError" />
        <div v-else-if="matches.length" class="scpai-news-match-list">
          <button v-for="item in matches" :key="item.externalId" type="button" :class="{selected:item.externalId===selectedId}" @click="selectMatch(item.externalId)"><i :class="{movement:Number(item.strength||0)>=70}"></i><div><small>{{ item.code || "--" }} · {{ item.competition || "赛事" }}</small><strong>{{ teamNames(item) }}</strong><footer><span>{{ shortTime(item.kickoffAt || item.kickoff) }}</span><em>{{ item.classification || item.status || "监测中" }}</em></footer></div></button>
        </div>
        <EmptyState v-else title="暂无公开比赛" description="比赛队列当前没有可展示的数据" />
      </aside>

      <article class="scpai-news-detail">
        <LoadingSkeleton v-if="newsLoading" type="rows" :count="5" />
        <ErrorState v-else-if="newsError && !items.length" :description="newsError" />
        <template v-else-if="selectedId">
          <header class="scpai-news-hero"><div><span>{{ currentMatch.code || "比赛新闻" }}</span><h2>{{ currentMatch.home || "主队" }} <em>VS</em> {{ currentMatch.away || "客队" }}</h2><p>{{ currentMatch.competition || "赛事待同步" }} · {{ shortTime(currentMatch.kickoffAt || currentMatch.kickoff) }}</p></div><aside><b>{{ items.length }}</b><span>条公开资讯</span></aside></header>
          <section v-if="news.analysis" class="scpai-news-analysis"><span class="scpai-kicker">NEWS ANALYSIS</span><p>{{ analysisText }}</p></section>
          <nav v-if="categories.length" class="scpai-news-filters" aria-label="新闻分类"><button type="button" :class="{active:category===''}" @click="category=''">全部 <b>{{ items.length }}</b></button><button v-for="item in categories" :key="item" type="button" :class="{active:category===item}" @click="category=item">{{ item }} <b>{{ categoryCount(item) }}</b></button></nav>
          <div v-if="visibleItems.length" class="scpai-news-list">
            <article v-for="(item,index) in visibleItems" :key="item.url||index"><span :class="['scpai-news-tag',{important:item.important}]">{{ item.category || "比赛资讯" }}</span><div class="scpai-news-copy"><header><time>{{ formatTime(item.publishedAt) }}</time><small v-if="cleanSource(item.source)">{{ cleanSource(item.source) }}</small></header><h3>{{ item.title || "新闻标题待同步" }}</h3><p>{{ item.summary || "暂无新闻摘要" }}</p><div v-if="item.teamImpact?.label" class="scpai-impact"><b>{{ item.teamImpact.label }}</b><span>{{ item.teamImpact.reason || "球队影响待进一步确认" }}</span></div></div><a v-if="safeUrl(item.url)" :href="item.url" target="_blank" rel="noopener noreferrer">原文 ↗</a></article>
          </div>
          <EmptyState v-else title="暂无比赛新闻" description="当前比赛或所选分类暂无公开资讯" />
          <p v-if="newsError" class="scpai-inline-warning">{{ newsError }}，当前继续显示最近一次成功数据。</p>
        </template>
        <EmptyState v-else title="请选择比赛" description="从左侧公开比赛队列选择一场比赛" />
      </article>
    </section>
  </section>
</template>
<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { useRoute } from "vue-router"
import axios from "axios"
import EmptyState from "../components/ui/EmptyState.vue"
import ErrorState from "../components/ui/ErrorState.vue"
import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"
import "../assets/scpai.css"

const REFRESH_MS=30000,NEWS_REFRESH_MS=180000,route=useRoute(),matches=ref([]),selectedId=ref(""),news=ref({}),category=ref(""),matchesLoading=ref(true),matchesError=ref(""),newsLoading=ref(false),newsRefreshing=ref(false),newsError=ref("");let timer=null,requestSerial=0,newsController=null;const newsCache=new Map()
const items=computed(()=>Array.isArray(news.value.items)?news.value.items:[]),categories=computed(()=>Array.isArray(news.value.categories)?news.value.categories:[]),visibleItems=computed(()=>category.value?items.value.filter(item=>item.category===category.value):items.value),currentMatch=computed(()=>news.value.match||matches.value.find(item=>item.externalId===selectedId.value)||{}),newsStatus=computed(()=>({fresh:"新闻已更新",cached:"缓存命中",stale:"最近缓存",unavailable:"暂不可用"}[news.value.status]||"等待选择")),analysisText=computed(()=>typeof news.value.analysis==="string"?news.value.analysis:(news.value.analysis?.summary||news.value.analysis?.text||"新闻影响分析已同步"))
async function loadMatches(silent=false){if(!silent&&!matches.value.length)matchesLoading.value=true;matchesError.value="";let changed=false;try{const response=await axios.get("/api/matches",{timeout:25000});const next=response.data?.data?.matches||[];matches.value=next;const requested=String(route.query.match||"");const preferred=[requested,selectedId.value,next[0]?.externalId].find(id=>id&&next.some(item=>item.externalId===id));if(preferred&&preferred!==selectedId.value){selectedId.value=preferred;changed=true;loadNews()}}catch{matchesError.value="比赛队列暂时无法更新"}finally{matchesLoading.value=false}return changed}
function selectMatch(id){if(!id||id===selectedId.value)return;selectedId.value=id;category.value="";const cached=newsCache.get(id);if(cached)news.value=cached;loadNews(Boolean(cached))}
function loadNews(silent=false){const id=selectedId.value;if(!id)return;const cached=newsCache.get(id);if(cached)news.value=cached;newsController?.abort();newsController=new AbortController();const serial=++requestSerial;if(!silent&&!cached)newsLoading.value=true;newsRefreshing.value=true;newsError.value="";axios.get(`/api/matches/${encodeURIComponent(id)}/news`,{signal:newsController.signal,timeout:12000}).then(response=>{if(serial!==requestSerial)return;const next=response.data?.data||{};newsCache.set(id,next);news.value=next}).catch(error=>{if(serial!==requestSerial||error?.code==="ERR_CANCELED")return;newsError.value=error.response?.data?.msg||"比赛新闻暂时不可用"}).finally(()=>{if(serial===requestSerial){newsLoading.value=false;newsRefreshing.value=false}})}
async function refreshPage(){const changed=await loadMatches(true);if(!changed)loadNews(true)}
function categoryCount(value){return items.value.filter(item=>item.category===value).length} function teamNames(item){return item.match||`${item.home||"主队"} VS ${item.away||"客队"}`} function shortTime(value){if(!value)return"时间待同步";const date=new Date(value);return Number.isNaN(date.getTime())?String(value):date.toLocaleString("zh-CN",{month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hour12:false})} function formatTime(value){if(!value)return"时间待同步";const date=new Date(value);return Number.isNaN(date.getTime())?String(value):date.toLocaleString("zh-CN",{hour12:false})} function safeUrl(value){try{return["http:","https:"].includes(new URL(value).protocol)}catch{return false}} function cleanSource(value){const text=String(value||"");return /scpai\.top/i.test(text)?"":text}
function scheduleRefresh(){if(timer)clearInterval(timer);timer=document.visibilityState==="visible"?setInterval(refreshPage,NEWS_REFRESH_MS):null}
function handleVisibilityChange(){scheduleRefresh();if(document.visibilityState==="visible")refreshPage()}
onMounted(()=>{loadMatches();document.addEventListener("visibilitychange",handleVisibilityChange);scheduleRefresh()});onBeforeUnmount(()=>{if(timer)clearInterval(timer);document.removeEventListener("visibilitychange",handleVisibilityChange);newsController?.abort();requestSerial+=1})
</script>
