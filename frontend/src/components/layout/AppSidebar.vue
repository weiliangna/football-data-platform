<template>
  <div class="sidebar-layer">
    <aside class="app-sidebar" :class="{ open }">
      <router-link class="sidebar-brand" to="/" @click="$emit('close')">
        <img src="/football-ai-logo.png" alt="绿茵智核足球 AI 标识">
        <span><strong>绿茵智核</strong><small>FOOTBALL AI</small></span>
      </router-link>
      <nav aria-label="主导航">
        <template v-for="item in navigation" :key="item.to">
          <router-link :to="item.to" :class="{ active: isActive(item) }" @click="$emit('close')">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="item.icon" /></svg><span>{{ item.name }}</span>
          </router-link>
          <div v-if="item.children" class="sub-navigation" :class="{ visible: isActive(item) }">
            <router-link v-for="child in item.children" :key="child.to" :to="child.to" :class="{ active: isChildActive(child) }" @click="$emit('close')"><span>{{ child.name }}</span></router-link>
          </div>
        </template>
      </nav>
      <section class="sidebar-status">
        <header><b>平台连接</b><span v-if="!platformError">{{ platforms.length }}</span></header>
        <p v-if="platformError">状态暂不可用</p>
        <template v-else-if="platforms.length"><div v-for="item in platforms" :key="item.platform_id"><i :class="statusClass(item)"></i><span>{{ item.name || ('平台 ' + item.platform_id) }}</span><small>{{ statusLabel(item) }}</small></div></template>
        <p v-else>暂无平台配置</p>
      </section>
      <footer><span>数据聚合控制台</span><small>Production UI · v1</small></footer>
    </aside>
    <button v-if="open" class="sidebar-overlay" type="button" aria-label="关闭菜单" @click="$emit('close')"></button>
  </div>
</template>
<script setup>
import { useRoute } from "vue-router"
defineProps({open:Boolean,platforms:{type:Array,default:()=>[]},platformError:Boolean});defineEmits(["close"]);const route=useRoute()
const navigation=[
  {name:"今日总览",to:"/",exact:true,icon:"M3 3h8v8H3V3m10 0h8v5h-8V3M3 13h8v8H3v-8m10-3h8v11h-8V10Z"},
  {name:"方案大厅",to:"/orders",icon:"M4 3h16a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1m3 4v2h10V7H7m0 4v2h10v-2H7m0 4v2h7v-2H7Z"},
  {name:"赛事分析",to:"/analysis",icon:"M4 19h16v2H4v-2m1-2V9h3v8H5m5 0V3h3v14h-3m5 0v-6h3v6h-3Z"},
  {name:"赛事数据",to:"/match-data",icon:"M4 4h16v3H4V4m0 5h16v11H4V9m3 3v2h4v-2H7m0 4v2h7v-2H7Z",children:[{name:"水位看板",to:"/match-data"},{name:"比赛新闻",to:"/match-news"}]},
  {name:"投注热力",to:"/heatmap",icon:"M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20m0 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12m0 3a3 3 0 1 1 0 6 3 3 0 0 1 0-6Z"},
  {name:"赛果统计",to:"/results",icon:"m9 16.2-3.5-3.5L4.1 14.1 9 19 20.3 7.7l-1.4-1.4L9 16.2Z"},
  {name:"用户中心",to:"/users",icon:"M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10m0 2c-5.52 0-10 2.24-10 5v3h20v-3c0-2.76-4.48-5-10-5Z"}
]
function isActive(item){if(item.exact)return route.path===item.to;if(item.children)return route.path.startsWith("/match-data")||route.path==="/match-news";if(item.to==="/orders")return route.path===item.to||route.path.startsWith("/order/detail/");if(item.to==="/users")return route.path===item.to||route.path.startsWith("/user/detail/");return route.path===item.to}
function isChildActive(item){return item.to==="/match-data"?route.path.startsWith("/match-data"):route.path===item.to}
const statusLabels={success:"正常",partial:"部分成功",failed:"采集失败",waiting_config:"缺少配置",waiting_contract:"契约待补",external_scheduler:"独立调度",disabled:"已停用",not_run:"等待同步"}
function runtimeStatus(item){if(Number(item.enabled)!==1)return "disabled";return String(item.runtime_status||"not_run")}
function statusLabel(item){return statusLabels[runtimeStatus(item)]||"状态未知"}
function statusClass(item){const status=runtimeStatus(item);return{active:["success","external_scheduler"].includes(status),warning:status==="partial"||status==="waiting_contract",failed:status==="failed"||status==="waiting_config"}}
</script>
<style scoped>
.app-sidebar{position:fixed;inset:0 auto 0 0;z-index:1000;width:204px;padding:18px 13px;display:flex;flex-direction:column;color:var(--sidebar-text);background:var(--sidebar-bg)}.sidebar-brand{min-height:58px;padding:0 7px 15px;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(255,255,255,.08)}.sidebar-brand img{width:43px;height:43px;flex:0 0 43px;object-fit:contain}.sidebar-brand strong,.sidebar-brand small{display:block;white-space:nowrap}.sidebar-brand strong{color:#fff;font-size:15px}.sidebar-brand small{margin-top:3px;color:var(--accent);font-size:8px;font-weight:700;letter-spacing:.14em}nav{margin-top:20px;display:grid;gap:4px}nav>a{position:relative;min-height:43px;padding:0 12px;border-radius:10px;display:flex;align-items:center;gap:12px;color:var(--sidebar-text);font-size:13px;font-weight:600;transition:color 150ms ease,background 150ms ease}nav>a::before{content:"";position:absolute;left:-13px;width:3px;height:22px;border-radius:0 3px 3px 0;background:transparent}nav>a:hover{color:#fff;background:var(--sidebar-bg-hover)}nav>a.active{color:#fff;background:#2b2b2d}nav>a.active::before{background:var(--accent)}nav svg{width:19px;height:19px;flex:0 0 19px;fill:currentColor}nav>a.active svg{color:var(--accent)}.sub-navigation{display:none;margin:-1px 0 2px 42px;padding-left:10px;border-left:1px solid rgba(255,255,255,.1)}.sub-navigation.visible{display:grid}.sub-navigation a{padding:6px 4px;color:#85858a;font-size:10px}.sub-navigation a:hover,.sub-navigation a.active{color:var(--accent)}.sidebar-status{margin-top:auto;padding:13px;border:1px solid rgba(255,255,255,.08);border-radius:13px;background:#29292b}.sidebar-status header{margin-bottom:9px;display:flex;justify-content:space-between;color:#fff;font-size:11px}.sidebar-status header span{color:var(--accent)}.sidebar-status>div{min-height:25px;display:grid;grid-template-columns:8px minmax(0,1fr) auto;gap:7px;align-items:center;font-size:9px}.sidebar-status i{width:6px;height:6px;border-radius:50%;background:#66666b}.sidebar-status i.active{background:var(--accent)}.sidebar-status i.warning{background:#f4a62a}.sidebar-status i.failed{background:#ef5a67}.sidebar-status small{color:#8c8c92}.sidebar-status p{margin:7px 0 0;color:#85858a;font-size:9px}footer{padding:14px 5px 0;display:grid;gap:3px;font-size:9px}footer small{color:#66666b}.sidebar-overlay{display:none}@media(max-height:720px){.sidebar-status{display:none}footer{margin-top:auto}}@media(max-width:1199px) and (min-width:768px){.app-sidebar{width:72px;padding:14px 10px}.sidebar-brand{padding:0 4px 13px;justify-content:center}.sidebar-brand img{width:42px;height:42px}.sidebar-brand span,nav>a span,.sub-navigation,.sidebar-status,footer{display:none}nav>a{padding:0;justify-content:center}nav>a::before{left:-10px}}@media(max-width:767px){.app-sidebar{width:min(280px,86vw);transform:translateX(-102%);transition:transform 180ms ease;box-shadow:0 0 50px rgba(0,0,0,.18)}.app-sidebar.open{transform:translateX(0)}.sidebar-overlay{position:fixed;inset:0;z-index:900;display:block;border:0;background:rgba(0,0,0,.38)}}
</style>
