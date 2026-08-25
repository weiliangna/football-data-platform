<template>
<div class="page">
  <div class="header"><div><h1>用户管理</h1><div class="subtitle">{{total}} 位用户</div></div></div>
  <div class="toolbar">
    <select v-model="platform" @change="resetAndLoad"><option value="1">彩站云</option><option value="3">鸿瑞</option></select>
    <input v-model="keyword" placeholder="搜索昵称 / 用户ID" @keyup.enter="resetAndLoad">
    <select v-model="sort" @change="resetAndLoad">
      <option value="latest">最近发单</option><option value="orders">方案数</option><option value="hit">命中率</option>
      <option value="profit">盈利</option><option value="roi">ROI</option><option value="follow">跟单</option><option value="score">综合分</option>
    </select>
    <button @click="resetAndLoad">查询</button>
  </div>

  <div class="list">
    <div class="user-card" v-for="item in users" :key="platform+'-'+item.user_id">
      <div class="top"><div><h2>{{item.nickname}}</h2><span>ID：{{item.user_id}}</span></div><span class="level">{{item.level}}</span></div>
      <div class="info">
        <div><span>方案</span><strong>{{item.order_count}}</strong></div>
        <div><span>已开奖</span><strong>{{item.settled_orders}}</strong></div>
        <div><span>命中率</span><strong>{{percent(item.avg_hit_rate)}}</strong></div>
        <div><span>ROI</span><strong>{{percent(item.avg_profitability)}}</strong></div>
        <div><span>投注</span><strong>¥{{money(item.total_amount)}}</strong></div>
        <div><span>盈利</span><strong>{{profit(item.total_profit)}}</strong></div>
        <div><span>跟单</span><strong>{{integer(item.follow_num)}}</strong></div>
        <div><span>综合分</span><strong>{{Number(item.expert_score||0).toFixed(2)}}</strong></div>
      </div>
      <div class="recent"><span>近7单</span><b v-for="(r,index) in item.recent7" :key="index" :class="r==='赢'?'win':r==='输'?'loss':'pending'">{{r==='待开奖'?'待':r}}</b></div>
      <button class="detail" @click="detail(item.user_id)">查看详情</button>
    </div>
  </div>

  <div class="pager">
    <button :disabled="page<=1" @click="changePage(page-1)">上一页</button>
    <span>第 {{page}} / {{pages||1}} 页</span>
    <button :disabled="page>=pages" @click="changePage(page+1)">下一页</button>
  </div>
</div>
</template>

<script setup>
import {ref,onMounted} from 'vue'
import axios from 'axios'
import {useRouter} from 'vue-router'
const router=useRouter()
const platform=ref('1'),keyword=ref(''),sort=ref('latest'),users=ref([]),page=ref(1),pages=ref(1),total=ref(0)
async function loadUsers(){
  const res=await axios.get('/api/user/list',{params:{platform_id:Number(platform.value),keyword:keyword.value,sort:sort.value,page:page.value,page_size:20}})
  if(res.data?.code===200){users.value=res.data.data||[];pages.value=res.data.pages||1;total.value=res.data.total||0}
}
function resetAndLoad(){page.value=1;loadUsers()}
function changePage(v){page.value=v;loadUsers()}
function detail(id){router.push('/user/detail/'+platform.value+'/'+id)}
function money(v){return Number(v||0).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})}
function integer(v){return Math.round(Number(v||0)).toLocaleString('zh-CN')}
function percent(v){return Number(v||0).toFixed(2)+'%'}
function profit(v){const n=Number(v||0);return n>0?'+¥'+money(n):n<0?'-¥'+money(Math.abs(n)):'¥0.00'}
onMounted(loadUsers)
</script>

<style scoped>
.page{padding:22px;background:#f5f7fa;min-height:100vh}.header{margin-bottom:18px}.header h1{margin:0}.subtitle{color:#8c96a6;margin-top:5px}.toolbar{background:white;padding:16px;border-radius:10px;display:flex;gap:10px;margin-bottom:18px}select,input,button{padding:9px 13px;border-radius:6px}select,input{border:1px solid #ddd;background:white}input{min-width:220px}button{border:0;background:#30343b;color:white;cursor:pointer}.list{display:grid;gap:15px}.user-card{background:white;padding:20px;border-radius:12px}.top{display:flex;justify-content:space-between}.top h2{margin:0}.top span{color:#999;font-size:12px}.level{background:#fff5e6;padding:4px 10px;border-radius:20px}.info{display:grid;grid-template-columns:repeat(8,minmax(90px,1fr));gap:10px;margin:20px 0}.info div{background:#fafafa;padding:12px;border-radius:8px}.info span{display:block;color:#8994a3;font-size:12px;margin-bottom:6px}.recent{display:flex;gap:5px;align-items:center;color:#8994a3}.recent b{width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;border-radius:50%;font-size:11px}.win{background:#fff1f0;color:#e63946}.loss{background:#eef7f2;color:#248f54}.pending{background:#fff7df;color:#d49300}.detail{margin-top:15px;background:#1677ff}.pager{margin-top:20px;display:flex;justify-content:center;gap:15px;align-items:center}.pager button:disabled{opacity:.4}@media(max-width:1100px){.info{grid-template-columns:repeat(4,1fr)}}
</style>
