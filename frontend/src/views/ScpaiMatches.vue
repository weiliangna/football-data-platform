<template>
  <section class="page-shell scpai-dashboard">
    <header class="scpai-report-head">
      <div><span class="scpai-kicker">FOOTBALL MARKET MONITOR</span><h1>绿茵智核水位实时看板</h1><p>赛前盘口变化、多市场同步监测与真实水位曲线</p></div>
      <div class="scpai-report-actions"><span :class="['scpai-live-pill',dashboard.status]">{{ dashboardRefreshing ? "数据同步中" : statusText }}</span></div>
    </header>

    <nav class="scpai-page-tabs" aria-label="赛事数据二级导航"><router-link to="/match-data">水位看板</router-link><router-link to="/match-news">比赛新闻</router-link></nav>

    <LoadingSkeleton v-if="dashboardLoading" class="scpai-section-gap" type="cards" :count="4" />
    <ErrorState v-else-if="dashboardError && !matches.length" class="app-card scpai-section-gap" :description="dashboardError" />
    <template v-else>
      <section class="scpai-summary-grid">
        <article v-for="item in summaryCards" :key="item.label" :class="item.tone"><span>{{ item.label }}</span><b>{{ number(item.value) }}</b><small>{{ item.note }}</small></article>
      </section>

      <section v-if="focusMatches.length" class="scpai-focus-section">
        <header class="scpai-section-head"><div><span class="scpai-kicker">LIVE FOCUS</span><h2>重点变化比赛</h2></div><p>按照强度与市场共识排列</p></header>
        <div class="scpai-focus-grid"><button v-for="item in focusMatches" :key="item.externalId" type="button" :class="{selected:item.externalId===selectedId}" @click="selectMatch(item.externalId)"><small>{{ item.code || "--" }} · {{ item.competition || "赛事" }}</small><strong>{{ teamNames(item) }}</strong><span>{{ item.direction || "等待形成方向" }}</span><p>{{ item.explanation || item.classification || "持续监测盘口变化" }}</p><footer><em>强度 {{ number(item.strength) }}</em><em>{{ number(consensus(item)) }}/{{ number(marketsOf(item)) }} 同步</em></footer></button></div>
      </section>

      <section class="scpai-workspace-grid">
        <aside class="scpai-match-panel">
          <header><div><h2>比赛队列</h2><p>点击比赛切换右侧真实盘口详情</p></div><span>{{ matches.length }} 场</span></header>
          <div v-if="matches.length" class="scpai-match-list">
            <button v-for="item in matches" :key="item.externalId" type="button" :class="{selected:item.externalId===selectedId}" @click="selectMatch(item.externalId)">
              <i :class="{movement:Number(item.strength||0)>=70}"></i><div><div class="scpai-match-kicker"><b>{{ item.code || "--" }}</b><span>{{ shortTime(item.kickoffAt || item.kickoff) }}</span></div><strong>{{ teamNames(item) }}</strong><span class="scpai-status-chip">{{ item.classification || item.status || "监测中" }}</span><footer><em>{{ item.direction || "观察" }}</em><small>{{ number(consensus(item)) }}/{{ number(marketsOf(item)) }} 市场</small></footer></div>
            </button>
          </div>
          <EmptyState v-else title="暂无公开比赛" description="当前没有可展示的比赛队列" />
        </aside>

        <article class="scpai-detail-panel">
          <LoadingSkeleton v-if="detailLoading && !selectedMatch.externalId" type="cards" :count="3" />
          <ErrorState v-else-if="detailError && !selectedMatch.externalId" :description="detailError" />
          <template v-else-if="selectedMatch.externalId">
            <header class="scpai-detail-top">
              <div class="scpai-detail-identity"><span>{{ selectedMatch.code || "比赛" }}</span><h2>{{ selectedMatch.home || "主队" }} <em>VS</em> {{ selectedMatch.away || "客队" }}</h2><p>{{ selectedMatch.competition || "赛事待同步" }} · {{ formatTime(selectedMatch.kickoffAt || selectedMatch.kickoff) }}</p></div>
              <section class="scpai-context-mini">
                <header><b>球队基本面</b><span v-if="contextLoading">同步中</span><span v-else-if="contextError">暂不可用</span><span v-else>{{ contextStatus }}</span></header>
                <div v-if="!contextError" class="scpai-context-grid">
                  <div><small>排名与积分</small><p><b>{{ context.home?.team || selectedMatch.home || "主队" }}</b> {{ context.home?.position ?? "--" }}位 / {{ context.home?.points ?? "--" }}分</p><p><b>{{ context.away?.team || selectedMatch.away || "客队" }}</b> {{ context.away?.position ?? "--" }}位 / {{ context.away?.points ?? "--" }}分</p></div>
                  <div><small>战意</small><b>{{ motivationLabel }}</b><p>{{ motivationDetail }}</p></div>
                  <div><small>伤停</small><b>{{ absenceTitle }}</b><p>{{ absenceSummary }}</p></div>
                </div>
                <p v-else class="scpai-context-error">基本面暂时不可用，盘口数据不受影响。</p>
              </section>
              <div class="scpai-detail-score"><b>{{ number(selectedMatch.strength) }}</b><span>监测强度 / 100</span></div>
            </header>

            <div v-if="alerts.length" class="scpai-alarm-strip"><strong>市场提醒</strong><span>{{ alertText(alerts[0]) }}</span></div>
            <div class="scpai-evidence-strip"><span class="scpai-status-chip">{{ selectedMatch.classification || "实时观察" }}</span><p>{{ selectedMatch.explanation || "根据公开水位样本持续判断市场方向，单点数据不形成趋势。" }}</p><small>{{ detailUpdatedText }}</small></div>
            <section class="scpai-interpretation-grid"><article><span>当前方向</span><b>{{ selectedMatch.direction || "观察" }}</b><p>{{ number(consensus(selectedMatch)) }} 个市场形成共识</p></article><article><span>监测状态</span><b>{{ selectedMatch.status || "持续采集" }}</b><p>{{ number(markets.length) }} 类盘口已展示</p></article><article><span>盘口解释</span><b>{{ synchronizedCount }} 个同步变化</b><p>变化值与曲线保持原始时间顺序</p></article></section>

            <header class="scpai-section-head compact"><div><span class="scpai-kicker">MARKET SERIES</span><h2>盘口变化</h2></div><p>五类盘口统一组件渲染</p></header>
            <div v-if="markets.length" class="scpai-market-grid">
              <article v-for="market in markets" :key="market.id" class="scpai-market-card">
                <header><div><h3>{{ market.name || marketName(market.type) }}</h3><small>{{ market.selection || "当前选择待同步" }}</small></div><b :class="{sync:market.synchronized}">{{ delta(market.delta) }}</b></header>
                <ScpaiMiniChart :values="market.values" :labels="market.labels" />
                <div class="scpai-market-values"><span>盘口 <b>{{ market.line ?? "--" }}</b></span><span>初赔 <b>{{ market.openingOdd ?? "--" }}</b></span><span>现赔 <b>{{ market.currentOdd ?? "--" }}</b></span><span>概率 <b>{{ probability(market.currentProbability) }}</b></span></div>
                <p>{{ market.directionLabel || market.explanation || "持续观察市场方向" }}</p>
                <footer><span>{{ compactTime(market.openingAt) }} → {{ compactTime(market.currentAt) }}</span><em :class="{sync:market.synchronized}">{{ market.synchronized ? "同步变化" : "独立观察" }}</em></footer>
              </article>
            </div>
            <EmptyState v-else title="暂无盘口序列" description="当前比赛尚未返回公开盘口曲线" />
          </template>
          <EmptyState v-else title="请选择比赛" description="从左侧公开比赛队列选择一场比赛" />
        </article>
      </section>

      <section class="scpai-priority-panel">
        <header class="scpai-section-head"><div><span class="scpai-kicker">LOW ODDS INDEX</span><h2>低赔指数</h2></div><p>保留接口返回的低赔排序，不推测缺失指标</p></header>
        <div v-if="favoriteRows.length" class="scpai-priority-list"><div v-for="(item,index) in favoriteRows" :key="item.label+index"><span>{{ item.label }}</span><i><b :style="{width:item.width+'%'}"></b></i><strong>{{ item.value }}</strong></div></div>
        <EmptyState v-else title="暂无低赔指数" description="当前比赛未返回可展示的低赔统计" />
      </section>
      <p v-if="dashboardError" class="scpai-inline-warning">{{ dashboardError }}，当前继续显示最近一次成功数据。</p>
    </template>
  </section>
</template>
<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { useRoute } from "vue-router"
import axios from "axios"
import EmptyState from "../components/ui/EmptyState.vue"
import ErrorState from "../components/ui/ErrorState.vue"
import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue"
import ScpaiMiniChart from "../components/scpai/ScpaiMiniChart.vue"
import "../assets/scpai.css"

const REFRESH_MS=30000,route=useRoute(),dashboard=ref({}),selectedId=ref(""),selectedMatch=ref({}),markets=ref([]),favoriteIndex=ref(null),alerts=ref([]),context=ref({}),dashboardLoading=ref(true),dashboardRefreshing=ref(false),dashboardError=ref(""),detailLoading=ref(false),detailError=ref(""),contextLoading=ref(false),contextError=ref("");let timer=null,requestSerial=0,detailController=null,contextController=null;const detailCache=new Map(),contextCache=new Map()
const matches=computed(()=>Array.isArray(dashboard.value.matches)?dashboard.value.matches:[]),focusMatches=computed(()=>[...matches.value].sort((a,b)=>Number(b.strength||0)-Number(a.strength||0)).slice(0,3)),summaryCards=computed(()=>[{label:"监测比赛",value:dashboard.value.summary?.matches??matches.value.length,note:"公开比赛队列",tone:"green"},{label:"盘口数量",value:dashboard.value.summary?.markets,note:"当前采集市场",tone:"orange"},{label:"盘口类型",value:dashboard.value.summary?.marketTypes,note:"统一市场模型",tone:"violet"},{label:"选择项",value:dashboard.value.summary?.selections,note:"公开水位选择",tone:"blue"}]),statusText=computed(()=>({fresh:"实时数据",cached:"缓存命中",stale:"最近缓存",unavailable:"暂不可用"}[dashboard.value.status]||"等待数据")),synchronizedCount=computed(()=>markets.value.filter(item=>item.synchronized).length),contextStatus=computed(()=>context.value.dataStatus||context.value.absenceStatus||"基本面已同步"),motivationLabel=computed(()=>context.value.motivation?.label||context.value.home?.motivation?.label||context.value.away?.motivation?.label||"战意待同步"),motivationDetail=computed(()=>context.value.motivation?.detail||context.value.home?.motivation?.detail||context.value.away?.motivation?.detail||"暂无补充说明"),absenceTitle=computed(()=>context.value.absences?.length?`${context.value.absences.length} 条已确认`:(context.value.absenceStatus==="verified-empty"?"暂无已确认伤停":"伤停待同步")),absenceSummary=computed(()=>context.value.absences?.slice(0,2).map(item=>item.player||item.team).filter(Boolean).join("、")||"未发现可展示的伤停记录"),detailUpdatedText=computed(()=>selectedMatch.value.updatedAt||dashboard.value.updatedAt?`更新 ${compactTime(selectedMatch.value.updatedAt||dashboard.value.updatedAt)}`:"更新时间待同步"),favoriteRows=computed(()=>normalizeFavorite(favoriteIndex.value))
async function loadDashboard(silent=false){if(dashboardRefreshing.value)return;dashboardRefreshing.value=true;if(!silent&&!matches.value.length)dashboardLoading.value=true;dashboardError.value="";try{const response=await axios.get("/api/matches",{timeout:25000});const next=response.data?.data||{};dashboard.value=next;const requested=String(route.query.match||"");const preferred=[requested,selectedId.value,next.match?.externalId,next.matches?.[0]?.externalId].find(id=>id&&next.matches?.some(item=>item.externalId===id));if(preferred&&preferred!==selectedId.value){selectedId.value=preferred;if(next.match?.externalId===preferred){applyDetail(next);loadContext(preferred)}else{loadSelected()}}else if(preferred){if(next.match?.externalId===preferred){applyDetail(next);loadContext(preferred,true)}else loadSelected(true)}}catch{dashboardError.value="比赛看板暂时无法更新"}finally{dashboardLoading.value=false;dashboardRefreshing.value=false}}
function applyDetail(value){selectedMatch.value={...(value.match||{}),updatedAt:value.updatedAt};markets.value=Array.isArray(value.markets)?value.markets:[];favoriteIndex.value=value.favoriteIndex??null;alerts.value=Array.isArray(value.alerts)?value.alerts:[];detailError.value=""}
function selectMatch(id){if(!id||id===selectedId.value)return;selectedId.value=id;const cached=detailCache.get(id);if(cached)applyDetail(cached);const cachedContext=contextCache.get(id);if(cachedContext)context.value=cachedContext;loadSelected(Boolean(cached))}
function loadSelected(silent=false){const id=selectedId.value;if(!id)return;detailController?.abort();detailController=new AbortController();const serial=++requestSerial;const cached=detailCache.get(id);if(cached)applyDetail(cached);if(!silent&&!cached)detailLoading.value=true;detailError.value="";axios.get(`/api/matches/${encodeURIComponent(id)}`,{signal:detailController.signal,timeout:12000}).then(response=>{if(serial!==requestSerial)return;const next=response.data?.data||{};detailCache.set(id,next);applyDetail(next)}).catch(error=>{if(serial!==requestSerial||error?.code==="ERR_CANCELED")return;detailError.value=error.response?.data?.msg||"盘口详情暂时不可用"}).finally(()=>{if(serial===requestSerial)detailLoading.value=false});loadContext(id,silent||Boolean(contextCache.get(id)),serial)}
function loadContext(id=selectedId.value,silent=false,serial=requestSerial){if(!id)return;contextController?.abort();contextController=new AbortController();const cached=contextCache.get(id);if(cached)context.value=cached;if(!silent&&!cached)contextLoading.value=true;contextError.value="";axios.get(`/api/matches/${encodeURIComponent(id)}/context`,{signal:contextController.signal,timeout:12000}).then(response=>{if(serial!==requestSerial)return;const next=response.data?.data||{};contextCache.set(id,next);context.value=next}).catch(error=>{if(serial!==requestSerial||error?.code==="ERR_CANCELED")return;if(!cached)context.value={};contextError.value=error.response?.data?.msg||"基本面暂时不可用"}).finally(()=>{if(serial===requestSerial)contextLoading.value=false})}
async function refreshPage(){await loadDashboard(true)}
function number(value){const n=Number(value);return Number.isFinite(n)?n.toLocaleString("zh-CN"):"--"} function consensus(item){return item.consensusCount??item.consensus??0} function marketsOf(item){return item.marketCount??item.totalMarkets??0} function teamNames(item){return item.match||`${item.home||"主队"} VS ${item.away||"客队"}`} function delta(value){const n=Number(value);return Number.isFinite(n)?`${n>0?"+":""}${n.toFixed(2)}`:"--"} function probability(value){const n=Number(value);return Number.isFinite(n)?`${n.toFixed(1)}%`:"--"} function formatTime(value){if(!value)return"时间待同步";const d=new Date(value);return Number.isNaN(d.getTime())?String(value):d.toLocaleString("zh-CN",{hour12:false})} function shortTime(value){if(!value)return"待定";const d=new Date(value);return Number.isNaN(d.getTime())?String(value):d.toLocaleString("zh-CN",{month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hour12:false})} function compactTime(value){if(!value)return"--";const d=new Date(value);return Number.isNaN(d.getTime())?String(value):d.toLocaleString("zh-CN",{hour:"2-digit",minute:"2-digit",hour12:false})} function marketName(type){return({WIN_DRAW_LOSS:"胜平负",HANDICAP_1X2:"让球胜平负",ASIAN_HANDICAP:"亚洲让球",OVER_UNDER:"大小球",BOTH_TEAMS_TO_SCORE:"双方进球",UNKNOWN:"其他盘口"}[type]||"盘口")} function alertText(value){return String(value?.message||value?.title||value?.text||"检测到盘口同步变化")} function normalizeFavorite(value){let rows=[];if(Array.isArray(value))rows=value;else if(Array.isArray(value?.items))rows=value.items;else if(value&&typeof value==="object")rows=Object.entries(value).filter(([,item])=>["string","number"].includes(typeof item)).map(([label,item])=>({label,value:item}));return rows.slice(0,8).map((item,index)=>{const raw=typeof item==="object"?item:{label:`指标 ${index+1}`,value:item},numeric=Number(raw.value??raw.score??raw.count??0);return{label:String(raw.label||raw.name||raw.selection||`指标 ${index+1}`),value:String(raw.displayValue??raw.value??raw.score??raw.count??"--"),width:Number.isFinite(numeric)?Math.max(4,Math.min(100,numeric)):20}})}
onMounted(()=>{loadDashboard();timer=setInterval(refreshPage,REFRESH_MS)});onBeforeUnmount(()=>{if(timer)clearInterval(timer);detailController?.abort();contextController?.abort();requestSerial+=1})
</script>
