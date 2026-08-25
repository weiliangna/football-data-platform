<template>
<section class="page-view report-page">
  <header class="report-topbar section-card">
    <button class="button" @click="backDashboard">← 返回数据看板</button>
    <div class="report-title-center">
      <p>SAME CONTENT REPORT</p>
      <h1>{{mode==='duplicates'?'方案相同内容统计报告':'全部方案总览'}}</h1>
      <small>{{platformName}} · 完整比赛队伍与单个玩法选项严格比对</small>
    </div>
    <div class="action-row">
      <button class="button primary" @click="analyze">一键分析</button>
      <button class="button primary" @click="savePng">保存 PNG</button>
      <button class="button" @click="saveExcel">保存 Excel</button>
    </div>
  </header>

  <div class="pill-tabs report-tabs">
    <button :class="{active:mode==='duplicates'}" @click="setMode('duplicates')">方案相同内容统计</button>
    <button :class="{active:mode==='overview'}" @click="setMode('overview')">全部方案总览</button>
  </div>

  <section class="report-banner">
    <div>
      <h2>{{platformName}}方案相同内容统计报告</h2>
      <p>针对完整比赛队伍与单个玩法选项进行严格比对</p>
    </div>
  </section>

  <div class="soft-note report-summary">
    <b>核心发现：</b>
    本次共采集 <strong>{{total}}</strong> 条记录，当前页面共 <strong>{{rows.length}}</strong> 条；
    <template v-if="mode==='duplicates'">发现 <strong>{{total}}</strong> 组相同内容。</template>
    <template v-else>可切换到“方案相同内容统计”查看重复组合。</template>
  </div>

  <div v-if="analysisVisible" class="analysis-cards">
    <article><span>当前样本</span><strong>{{rows.length}}</strong><small>条</small></article>
    <article><span>平均自购</span><strong>¥{{money(analysis.avgStake)}}</strong><small>每方案</small></article>
    <article><span>累计跟单</span><strong>{{number(analysis.followers)}}</strong><small>人次</small></article>
    <article><span>最高重复</span><strong>{{analysis.maxDuplicate}}</strong><small>组内方案</small></article>
  </div>

  <section class="report-section">
    <div class="section-title"><i></i><h2>{{mode==='duplicates'?'一、相同方案详细比较':`一、全部 ${total} 个方案总览`}}</h2></div>

    <div class="report-filter section-card">
      <input class="toolbar-input" v-model="keyword" placeholder="搜索发单人、订单号、球队或方案内容" @keyup.enter="resetLoad">
      <button class="button primary" @click="resetLoad">查找</button>
    </div>

    <div class="report-table-card">
      <template v-if="mode==='duplicates'">
        <div v-for="(r,index) in rows" :key="r.id" class="duplicate-block">
          <div class="duplicate-title">相同组合 #{{(page-1)*pageSize+index+1}} · {{r.duplicate_count}} 个方案 · {{r.user_count}} 位用户</div>
          <div class="duplicate-meta">
            <span><b>代表发单人</b>{{r.nickname||'-'}}</span>
            <span><b>过关</b>{{r.pass_summary||'-'}}</span>
            <span><b>累计自购</b>¥{{money(r.total_stake)}}</span>
            <span><b>累计跟单</b>{{number(r.total_follow)}}人</span>
          </div>
          <div class="duplicate-detail">{{r.selection||'-'}}</div>
        </div>
        <div v-if="!rows.length" class="empty">目前没有内容完全相同的方案</div>
      </template>

      <div v-else class="table-host">
        <table class="reference-table overview-table">
          <thead><tr><th>序号</th><th>发单人</th><th>历史战绩</th><th>自购金额</th><th>跟单人数</th><th>SP</th><th>注数</th><th>方案详情</th><th>结果</th></tr></thead>
          <tbody>
            <tr v-for="(r,index) in rows" :key="r.id">
              <td>{{(page-1)*pageSize+index+1}}</td>
              <td><b>{{r.nickname||'-'}}</b><small>{{r.platform_order_id||''}}</small></td>
              <td>{{historyText(r)}}</td>
              <td>¥{{money(r.stake)}}</td>
              <td>{{number(r.follow_num)}}人</td>
              <td>{{r.odds_text||'-'}}</td>
              <td>{{r.pass_summary||'-'}}</td>
              <td class="detail">{{r.selection||'-'}}</td>
              <td :class="statusClass(r.result)">{{r.result||'待开奖'}}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="pager">
      <button :disabled="page<=1" @click="changePage(page-1)">上一页</button>
      <span>第 {{page}} / {{pages}} 页 · 共 {{total}} 条</span>
      <button :disabled="page>=pages" @click="changePage(page+1)">下一页</button>
    </div>
  </section>
</section>
</template>

<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import axios from 'axios'
import {downloadExcel,downloadTextPng,stamp} from '../utils/export'

const route=useRoute();const router=useRouter();const mode=ref(route.query.mode==='overview'?'overview':'duplicates');const keyword=ref('');const rows=ref([]);const page=ref(1);const pages=ref(1);const total=ref(0);const pageSize=30;const analysisVisible=ref(false)
const names={1:'彩站云',2:'州运宝',3:'鸿瑞',4:'云彩'};const platformId=computed(()=>Number(route.params.platformId));const platformName=computed(()=>names[platformId.value]||'平台')
const analysis=computed(()=>{const stake=rows.value.reduce((s,r)=>s+Number(r.stake||r.total_stake||0),0);const followers=rows.value.reduce((s,r)=>s+Number(r.follow_num||r.total_follow||0),0);const maxDuplicate=Math.max(0,...rows.value.map(r=>Number(r.duplicate_count||1)));return{avgStake:rows.value.length?stake/rows.value.length:0,followers,maxDuplicate}})
async function load(){const r=await axios.get('/api/hub/schemes',{params:{platform_id:platformId.value,mode:mode.value,keyword:keyword.value,page:page.value,page_size:pageSize}});if(r.data?.code===200){rows.value=r.data.data||[];pages.value=r.data.pages||1;total.value=r.data.total||0}}
function setMode(v){mode.value=v;page.value=1;router.replace({query:{...route.query,mode:v}});load()}
function resetLoad(){page.value=1;load()}
function changePage(v){page.value=v;load()}
function backDashboard(){router.push(`/platform/${platformId.value}/dashboard`)}
function analyze(){analysisVisible.value=!analysisVisible.value}
function money(v){return Number(v||0).toLocaleString('zh-CN',{maximumFractionDigits:2})}
function number(v){return Math.round(Number(v||0)).toLocaleString('zh-CN')}
function statusClass(v){return v==='赢'?'status-win':v==='输'?'status-loss':'status-pending'}
function historyText(r){return r.result==='赢'?'已命中':r.result==='输'?'未命中':'--'}
function exportRows(){return rows.value.map((r,index)=>[(page.value-1)*pageSize+index+1,r.nickname||'',r.platform_order_id||'',r.pass_summary||'',r.selection||'',r.odds_text||'',r.stake||r.total_stake||0,r.follow_num||r.total_follow||0,r.result||'',r.profit||0])}
function saveExcel(){downloadExcel(`${platformName.value}方案内容统计`,['序号','发单人','订单号','过关','方案详情','SP','自购金额','跟单人数','结果','盈利'],exportRows(),stamp(`${platformName.value}-方案统计`)+'.xls')}
function savePng(){const lines=exportRows().map(r=>r.join('  |  '));downloadTextPng(`${platformName.value}方案相同内容统计报告`,lines,stamp(`${platformName.value}-方案统计`)+'.png')}
watch(()=>route.params.platformId,()=>{page.value=1;load()});onMounted(load)
</script>

<style scoped>
.report-topbar{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:20px;padding:16px}.report-title-center{text-align:center}.report-title-center p{margin:0;color:#8d70e5;font-size:10px;font-weight:900;letter-spacing:1.8px}.report-title-center h1{margin:4px 0;font-size:23px}.report-title-center small{color:#8e8899}.report-tabs{justify-content:center;margin:16px 0}.report-banner{margin-top:16px;border-radius:22px 22px 0 0;background:linear-gradient(100deg,#966df8,#6684fb);padding:28px 32px;color:#fff}.report-banner h2{margin:0;font-size:28px}.report-banner p{margin:7px 0 0;color:#ffffffd9}.report-summary{margin:22px 28px}.report-summary strong{color:#5d4ddd}.analysis-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 28px 22px}.analysis-cards article{background:#fff;border:1px solid #e7e4ef;border-radius:13px;padding:15px}.analysis-cards span,.analysis-cards small{display:block;color:#8d8797}.analysis-cards strong{font-size:22px;display:block;margin:5px 0}.report-section{padding:18px 28px 30px;background:#f7f7fa;border-radius:0 0 20px 20px}.section-title{display:flex;align-items:center;gap:10px;margin-bottom:12px}.section-title i{display:block;width:6px;height:27px;background:#8068e5;border-radius:5px}.section-title h2{margin:0}.report-filter{display:flex;gap:8px;padding:10px;margin-bottom:12px}.report-filter input{flex:1}.report-table-card{background:#fff;border:1px solid #e4e1ec;border-radius:14px;overflow:hidden}.duplicate-block{border-bottom:1px solid #ece9f2}.duplicate-title{padding:13px 17px;background:linear-gradient(90deg,#f3efff,#fff4e9);color:#654de0;font-weight:800}.duplicate-meta{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#ece9f2}.duplicate-meta span{background:#fff;padding:12px;text-align:center}.duplicate-meta b{display:block;color:#8f8999;font-size:11px;margin-bottom:4px}.duplicate-detail{padding:14px 18px;color:#5e4bdd;line-height:1.7}.overview-table td small{display:block;color:#aaa4b2;margin-top:3px}.pager{display:flex;justify-content:center;gap:12px;align-items:center;margin-top:16px}.pager button{border:1px solid #ddd9e8;background:#fff;color:#7058d7;border-radius:9px;padding:8px 15px}.pager button:disabled{opacity:.4}@media(max-width:900px){.report-topbar{grid-template-columns:1fr}.report-title-center{text-align:left}.analysis-cards,.duplicate-meta{grid-template-columns:repeat(2,1fr)}}
</style>
