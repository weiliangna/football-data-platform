<template>
  <section class="page-shell">
    <header class="page-header"><div><h1>赛事分析</h1><p>仅使用未截止方案作为分析证据</p></div><button class="primary-button" type="button" @click="load">刷新分析</button></header>
    <section class="toolbar app-card"><input class="field" :value="data.day || ''" placeholder="赛事日期待同步" readonly aria-label="赛事日期"><select v-model="selectedPlay" aria-label="玩法筛选"><option value="">全部玩法</option><option v-for="play in plays" :key="play" :value="play">{{ play }}</option></select><select disabled aria-label="等级筛选"><option>等级字段未提供</option></select></section>
    <LoadingSkeleton v-if="loading" class="section-gap" type="cards" :count="3" />
    <ErrorState v-else-if="error" class="app-card section-gap" :description="error" @retry="load" />
    <template v-else>
      <section class="stats-grid section-gap"><article class="app-card"><span>未截止方案</span><strong>{{ number(data.unexpired_orders) }}</strong></article><article class="app-card"><span>分析场次</span><strong>{{ number((data.matches||[]).length) }}</strong></article><article class="app-card"><span>覆盖玩法</span><strong>{{ playCount }}</strong></article></section>
      <section v-if="(data.matches||[]).length" class="match-list">
        <article v-for="match in data.matches" :key="match.match_code+match.match_name" class="match-card app-card lift-card">
          <header><div><span class="match-code">{{ match.match_code || "--" }}</span><small>{{ match.league || "--" }}</small></div><h2>{{ match.match_name || "--" }}</h2><div class="match-meta"><span>让球 {{ match.handicap ?? "--" }}</span><span>状态 {{ match.status || "--" }}</span></div></header>
          <div class="play-grid"><article v-for="play in visiblePlays" :key="play"><h3>{{ play }}</h3><div v-if="match.plays&&match.plays[play]&&match.plays[play].length" class="options"><div v-for="option in match.plays[play]" :key="option.option" :class="{peak:isPeak(match.plays[play],option)}"><header><span>{{ option.option || "--" }}</span><b>{{ option.share ?? "--" }}%</b></header><div><i :style="{width:Math.min(100,Number(option.share||0))+'%'}"></i></div><small>{{ number(option.count) }} 次 · SP {{ option.odds || "--" }}</small></div></div><EmptyState v-else title="暂无采集数据" description="该玩法暂无可用投注项" /></article></div>
        </article>
      </section>
      <EmptyState v-else class="app-card section-gap" title="暂无赛事分析" description="今日没有可分析的未截止方案" />
    </template>
  </section>
</template>
<script setup>
import { computed,onMounted,ref } from "vue";import axios from "axios";import LoadingSkeleton from "../components/ui/LoadingSkeleton.vue";import EmptyState from "../components/ui/EmptyState.vue";import ErrorState from "../components/ui/ErrorState.vue"
const plays=["胜平负","让球胜平负","半全场","比分"],selectedPlay=ref(""),data=ref({}),loading=ref(true),error=ref("")
const visiblePlays=computed(()=>selectedPlay.value?[selectedPlay.value]:plays),playCount=computed(()=>{const set=new Set();(data.value.matches||[]).forEach(m=>Object.keys(m.plays||{}).forEach(p=>{if((m.plays[p]||[]).length)set.add(p)}));return set.size})
async function load(){loading.value=true;error.value="";try{const r=await axios.get("/api/portal/analysis");if(!r.data||r.data.code!==200)throw new Error();data.value=r.data.data||{}}catch{data.value={};error.value="赛事分析暂时无法读取，请稍后重试或检查接口连接状态"}finally{loading.value=false}}
function number(v){return Math.round(Number(v||0)).toLocaleString("zh-CN")} function isPeak(rows,item){return Number(item.share||0)===Math.max(...rows.map(r=>Number(r.share||0)))} onMounted(load)
</script>
<style scoped>
.section-gap{margin-top:14px}.stats-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.stats-grid article{padding:18px}.stats-grid span,.stats-grid strong{display:block}.stats-grid span{color:var(--text-muted);font-size:11px}.stats-grid strong{margin-top:8px;font-size:28px}.match-list{margin-top:14px;display:grid;gap:12px}.match-card{padding:20px}.match-card>header{display:grid;grid-template-columns:minmax(120px,.5fr) minmax(260px,1fr) minmax(180px,.6fr);gap:15px;align-items:center}.match-card>header h2{margin:0;font-size:18px;text-align:center}.match-code{padding:5px 8px;border-radius:8px;background:var(--accent-soft);font-size:11px;font-weight:700}.match-card>header small{margin-left:8px;color:var(--text-muted)}.match-meta{display:flex;justify-content:flex-end;gap:8px}.match-meta span{padding:6px 8px;border-radius:8px;background:var(--surface-soft);color:var(--text-secondary);font-size:10px}.play-grid{margin-top:18px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.play-grid>article{min-height:175px;padding:13px;border:1px solid var(--border);border-radius:13px;background:var(--surface-soft)}.play-grid h3{margin:0 0 10px;font-size:13px}.options{display:grid;gap:7px}.options>div{padding:9px;border-radius:9px;background:#fff}.options>div.peak{background:var(--accent-soft)}.options header{display:flex;justify-content:space-between;font-size:11px}.options>div>div{height:5px;margin:7px 0;border-radius:5px;overflow:hidden;background:#e8e8e3}.options i{display:block;height:100%;background:#7e9214}.options small{color:var(--text-muted);font-size:9px}@media(max-width:1050px){.play-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:650px){.stats-grid,.play-grid{grid-template-columns:1fr}.match-card>header{grid-template-columns:1fr}.match-card>header h2{text-align:left}.match-meta{justify-content:flex-start}}
</style>
