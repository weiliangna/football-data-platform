<template>
<section class="page-view platform-dashboard">
  <header class="platform-page-head">
    <div>
      <p class="eyebrow">DATA OVERVIEW</p>
      <h1>{{platformName}} · 数据看板</h1>
      <p>汇总方案、投注热度与赛果表现，掌握今日业务动态。</p>
    </div>
    <div class="action-row">
      <button class="button" @click="goAnalysis">进行中场次</button>
      <button class="button" :class="{primary:collection.spider_enabled}" @click="toggleCollection">
        {{collection.spider_enabled?'暂停自动采集':'开启自动采集'}}
      </button>
      <button class="button" @click="chooseImport">导入 JSON</button>
      <button class="button primary" @click="exportJson">导出 JSON</button>
      <button class="button danger" @click="clearRecords">清空记录</button>
      <input ref="fileInput" type="file" accept="application/json,.json" hidden @change="importJson">
    </div>
  </header>

  <div class="platform-dashboard-grid">
    <aside class="platform-metrics">
      <div class="metric-mini-grid">
        <article class="metric-mini"><span>昨日方案</span><strong>{{m.yesterday_plans||0}}</strong><small>份</small></article>
        <article class="metric-mini"><span>已中奖</span><strong>{{m.yesterday_wins||0}}</strong><small>份</small></article>
        <article class="metric-mini"><span>今日方案</span><strong>{{m.today_plans||0}}</strong><small>份</small></article>
        <article class="metric-mini"><span>今日跟单人数</span><strong>{{number(m.today_followers)}}</strong><small>人次</small></article>
      </div>
      <article class="total-amount-card">
        <span>发单总金额</span>
        <strong>¥{{money(m.total_amount)}}</strong>
      </article>
    </aside>

    <article class="section-card platform-analysis-card">
      <header class="card-title-row">
        <div><p class="eyebrow">DATA ANALYSIS</p><h2>昨日数据分析</h2></div>
        <span>{{data.day||'--'}}</span>
      </header>
      <div class="platform-analysis-body">
        <div class="result-body compact">
          <div class="donut" :style="{'--win':winPct+'%'}">
            <div><strong>{{m.yesterday_settled||0}}</strong><small>已开奖</small></div>
          </div>
          <div class="legend">
            <span><i class="win"></i>中奖数量 <b>{{m.yesterday_wins||0}}</b></span>
            <span><i class="lose"></i>未中奖数量 <b>{{m.yesterday_lost||0}}</b></span>
          </div>
        </div>

        <div class="trend-side">
          <div class="trend-title"><b>发单数量趋势</b><small>00:00 — 24:00 / 最近 7 日</small></div>
          <div class="platform-line-chart">
            <svg viewBox="0 0 720 175" preserveAspectRatio="none">
              <defs>
                <linearGradient id="platformTrend" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stop-color="#7466ef" />
                  <stop offset="55%" stop-color="#aa64e8" />
                  <stop offset="100%" stop-color="#38bca8" />
                </linearGradient>
                <linearGradient id="platformArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#896fe4" stop-opacity=".18" />
                  <stop offset="100%" stop-color="#896fe4" stop-opacity="0" />
                </linearGradient>
              </defs>
              <line v-for="y in [25,65,105,145]" :key="y" x1="14" :y1="y" x2="706" :y2="y" class="chart-grid" />
              <path v-if="trendPoints.length" :d="trendArea" class="chart-area" />
              <path v-if="trendPoints.length" :d="trendPath" class="chart-line" />
              <circle v-for="(point,index) in trendPoints" :key="'p'+index" :cx="point.x" :cy="point.y" r="3.5" class="chart-dot" />
              <text v-for="(point,index) in trendPoints" :key="'t'+index" :x="point.x" y="171" text-anchor="middle" class="chart-label">{{point.label}}</text>
            </svg>
          </div>
        </div>
      </div>
    </article>
  </div>

  <section class="section-card hot-section">
    <header class="card-title-row">
      <div><p class="eyebrow">TOP BETTING PLAY</p><h2>今日热门玩法</h2></div>
      <span>按今日未截止方案具体投注项统计 Top 3</span>
    </header>
    <div class="four-market-grid">
      <article class="market-top-card" v-for="market in fixedMarkets" :key="market">
        <header><b>{{market}}</b><small>TOP 3</small></header>
        <div v-for="(item,index) in topByMarket(market)" :key="index" class="market-top-row">
          <i>{{index+1}}</i>
          <div><b>{{item.match_code?item.match_code+' · ':''}}{{item.match_name}}</b><small>{{item.option}}</small></div>
          <strong>{{item.count}}<small>次</small></strong>
        </div>
        <div v-if="!topByMarket(market).length" class="market-top-empty">暂无采集数据</div>
      </article>
    </div>
  </section>

  <section class="section-card live-orders">
    <header class="card-title-row"><div><p class="eyebrow">LIVE ORDERS</p><h2>实时方案明细</h2></div><span>最近 {{(data.recent||[]).length}} 条</span></header>
    <div class="table-host">
      <table class="reference-table">
        <thead><tr><th>发单人</th><th>比赛</th><th>过关</th><th>推荐</th><th>SP</th><th>自购金额</th><th>跟单</th><th>结果</th><th>盈利</th></tr></thead>
        <tbody>
          <tr v-for="x in data.recent||[]" :key="x.id">
            <td><b>{{x.nickname||'-'}}</b></td>
            <td>{{x.match_name||'-'}}</td>
            <td>{{x.pass_summary||'-'}}</td>
            <td class="detail">{{x.selection||'-'}}</td>
            <td>{{x.odds_text||'-'}}</td>
            <td>¥{{money(x.stake)}}</td>
            <td>{{number(x.follow_num)}}人</td>
            <td :class="statusClass(x.result)">{{x.result||'待开奖'}}</td>
            <td :class="Number(x.profit)>=0?'positive':'negative'">{{signed(x.profit)}}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</section>
</template>

<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import axios from 'axios'
import {downloadJson,stamp} from '../utils/export'

const route=useRoute(); const router=useRouter(); const fileInput=ref(null); const data=ref({})
const names={1:'彩站云',2:'州运宝',3:'鸿瑞',4:'云彩'}
const platformId=computed(()=>Number(route.params.platformId||0))
const platformName=computed(()=>names[platformId.value]||'平台')
const m=computed(()=>data.value.metrics||{})
const collection=computed(()=>data.value.collection||{spider_enabled:true,result_enabled:true})
const fixedMarkets=['胜平负','让球胜平负','半全场','比分']
const winPct=computed(()=>{const s=Number(m.value.yesterday_settled||0);return s?Math.round(Number(m.value.yesterday_wins||0)/s*100):0})
const trendPoints=computed(()=>{const rows=data.value.trend||[];if(!rows.length)return[];const max=Math.max(1,...rows.map(x=>Number(x.count||0)));const left=14,width=692,top=18,bottom=145,step=rows.length>1?width/(rows.length-1):0;return rows.map((row,index)=>({x:left+step*index,y:bottom-(Number(row.count||0)/max)*(bottom-top),label:String(row.date||'')}))})
const trendPath=computed(()=>trendPoints.value.map((p,i)=>`${i?'L':'M'} ${p.x} ${p.y}`).join(' '))
const trendArea=computed(()=>{const points=trendPoints.value;if(!points.length)return'';return `${trendPath.value} L ${points[points.length-1].x} 145 L ${points[0].x} 145 Z`})

async function load(){const r=await axios.get(`/api/hub/platform/${platformId.value}`);if(r.data?.code===200)data.value=r.data.data||{}}
function topByMarket(market){return (data.value.hot_plays||[]).filter(x=>x.play_type===market).slice(0,3)}
function money(v){return Number(v||0).toLocaleString('zh-CN',{maximumFractionDigits:2})}
function number(v){return Math.round(Number(v||0)).toLocaleString('zh-CN')}
function signed(v){const n=Number(v||0);return `${n>0?'+':''}¥${money(n)}`}

function statusClass(v){return v==='赢'?'status-win':v==='输'?'status-loss':'status-pending'}
function goAnalysis(){router.push({path:'/analysis',query:{platform:String(platformId.value)}})}
function adminToken(){let token=localStorage.getItem('football-admin-token-v1')||'';if(!token){token=window.prompt('此操作需要后台管理 Token，请输入：')||'';if(token)localStorage.setItem('football-admin-token-v1',token)}return token}
async function toggleCollection(){const token=adminToken();if(!token)return;try{await axios.put(`/api/hub/platform/${platformId.value}/collection`,null,{params:{enabled:!collection.value.spider_enabled},headers:{'X-Admin-Token':token}});await load()}catch(e){alert(e.response?.data?.detail||e.response?.data?.msg||e.message)}}
async function exportJson(){const r=await axios.get(`/api/hub/platform/${platformId.value}/export`);downloadJson(r.data,stamp(`${platformName.value}-数据导出`)+'.json')}
function chooseImport(){fileInput.value?.click()}
async function importJson(ev){const file=ev.target.files?.[0];ev.target.value='';if(!file)return;const token=adminToken();if(!token)return;try{const parsed=JSON.parse(await file.text());const records=parsed.records||parsed.data||parsed;if(!Array.isArray(records))throw new Error('JSON 中未找到 records 数组');const r=await axios.post(`/api/hub/platform/${platformId.value}/import`,{records},{headers:{'X-Admin-Token':token}});alert(`导入完成：${r.data.imported||0} 条`);await load()}catch(e){alert(e.response?.data?.detail||e.response?.data?.msg||e.message)}}
async function clearRecords(){if(!confirm(`确定清空 ${platformName.value} 的订单记录吗？此操作会删除数据库中的该平台订单与拆单。`))return;const token=adminToken();if(!token)return;try{const r=await axios.delete(`/api/hub/platform/${platformId.value}/records`,{headers:{'X-Admin-Token':token}});alert(`已清空 ${r.data.deleted||0} 条记录`);await load()}catch(e){alert(e.response?.data?.detail||e.response?.data?.msg||e.message)}}
watch(()=>route.params.platformId,load);onMounted(load)
</script>

<style scoped>
.platform-dashboard-grid{display:grid;grid-template-columns:326px minmax(0,1fr);gap:16px}.platform-metrics{display:grid;gap:12px}.metric-mini-grid{grid-template-columns:repeat(2,1fr)}.metric-mini{min-height:94px;text-align:center;position:relative;overflow:hidden}.metric-mini:after{content:'';position:absolute;width:64px;height:64px;border-radius:50%;right:-16px;bottom:-22px;background:#f3efff}.metric-mini:nth-child(2):after{background:#fff0f4}.metric-mini:nth-child(3):after{background:#eef6ff}.metric-mini:nth-child(4):after{background:#e9faf4}.metric-mini small{color:#9b94a7}.total-amount-card{background:#fff;border:1px solid #e9e7f1;border-radius:15px;min-height:94px;padding:19px;text-align:center;display:grid;align-content:center}.total-amount-card span{color:#8a8496;font-size:12px}.total-amount-card strong{font-size:25px;margin-top:7px}.card-title-row{display:flex;align-items:flex-start;justify-content:space-between;gap:15px}.card-title-row .eyebrow{margin:0 0 6px;font-size:10px;font-weight:900;letter-spacing:1.7px;color:#8d70e5}.card-title-row h2{margin:0;font-size:19px}.card-title-row>span{color:#9a94a5;font-size:12px}.platform-analysis-body{display:grid;grid-template-columns:340px 1fr;gap:20px;align-items:center;margin-top:14px}.result-body.compact{padding:8px 0}.trend-title{display:flex;align-items:center;justify-content:space-between}.trend-title small{color:#9a94a5}.platform-line-chart{height:185px;margin-top:10px}.platform-line-chart svg{width:100%;height:100%;display:block}.chart-grid{stroke:#eceaf2;stroke-width:1}.chart-line{fill:none;stroke:url(#platformTrend);stroke-width:3}.chart-area{fill:url(#platformArea)}.chart-dot{fill:#fff;stroke:#8067e8;stroke-width:2}.chart-label{fill:#aaa5b3;font-size:9px}.hot-section,.live-orders{margin-top:16px}.four-market-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:14px}.market-top-card{border:1px solid #e9e7f1;border-radius:14px;overflow:hidden}.market-top-card>header{height:52px;padding:0 14px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #eceaf2}.market-top-card>header small{color:#aaa5b3}.market-top-row{display:grid;grid-template-columns:26px 1fr auto;gap:8px;align-items:center;padding:10px 12px;border-bottom:1px solid #f0eef4}.market-top-row>i{width:23px;height:23px;border-radius:7px;background:#f0ecff;color:#7660dc;display:grid;place-items:center;font-style:normal;font-size:11px}.market-top-row div b,.market-top-row div small{display:block}.market-top-row div b{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.market-top-row div small{font-size:11px;color:#7d68e7;margin-top:3px}.market-top-row>strong{color:#8068e5}.market-top-row>strong small{font-size:10px;color:#aaa4b2}.market-top-empty{padding:32px;text-align:center;color:#aaa5b3}.live-orders .table-host{margin-top:14px}@media(max-width:1200px){.platform-dashboard-grid{grid-template-columns:1fr}.platform-analysis-body{grid-template-columns:300px 1fr}.four-market-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:800px){.platform-analysis-body{grid-template-columns:1fr}.four-market-grid{grid-template-columns:1fr}.platform-page-head{align-items:flex-start;flex-direction:column}}
</style>
