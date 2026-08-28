<template>
  <div class="sidebar-layer">
    <aside class="app-sidebar" :class="{ open }">
      <router-link class="sidebar-brand" to="/" @click="$emit('close')"><img src="/football-ai-logo.png" alt="足球数据中心"><span><strong>足球数据中心</strong><small>FOOTBALL DATA</small></span></router-link>
      <nav aria-label="主导航">
        <template v-for="item in navigation" :key="item.to">
          <router-link :to="item.to" :class="{ active: isActive(item) }" @click="$emit('close')"><span class="nav-icon">{{ item.icon }}</span><span>{{ item.name }}</span></router-link>
          <div v-if="item.children" class="sub-navigation" :class="{ visible: isActive(item) }"><router-link v-for="child in item.children" :key="child.to" :to="child.to" :class="{ active: isChildActive(child) }" @click="$emit('close')">{{ child.name }}</router-link></div>
        </template>
      </nav>
      <section class="sidebar-status"><header><b>平台连接</b><span v-if="!platformError">{{ platforms.length }}</span></header><p v-if="platformError">状态暂不可用</p><template v-else-if="platforms.length"><div v-for="item in platforms" :key="item.platform_id"><i :class="statusClass(item)"></i><span>{{ item.name || `平台 ${item.platform_id}` }}</span><small>{{ statusLabel(item) }}</small></div></template><p v-else>暂无平台配置</p></section>
      <footer><span>数据聚合控制台</span><small>Production UI · v2</small></footer>
    </aside><button v-if="open" class="sidebar-overlay" type="button" aria-label="关闭菜单" @click="$emit('close')"></button>
  </div>
</template>
<script setup>
import { useRoute } from "vue-router"
defineProps({ open: Boolean, platforms: { type: Array, default: () => [] }, platformError: Boolean })
defineEmits(["close"])
const route = useRoute()
const navigation = [
  { name: "今日总览", to: "/", exact: true, icon: "⌂" },
  { name: "方案大厅", to: "/orders", icon: "▤" },
  { name: "赛事分析", to: "/analysis", icon: "⌁" },
  { name: "赛事数据", to: "/match-data", icon: "▦", children: [{ name: "水位看板", to: "/match-data" }, { name: "比赛新闻", to: "/match-news" }] },
  { name: "投注热力", to: "/heatmap", icon: "◉" },
  { name: "赛果统计", to: "/results", icon: "✓" },
  { name: "用户中心", to: "/users", icon: "♙" },
  { name: "数据监控", to: "/monitor", icon: "◌" },
  { name: "排行榜", to: "/ranking", icon: "☆" },
]
function isActive(item) { if (item.exact) return route.path === item.to; if (item.children) return route.path.startsWith("/match-data") || route.path === "/match-news"; if (item.to === "/orders") return route.path === item.to || route.path.startsWith("/order/detail/"); if (item.to === "/users") return route.path === item.to || route.path.startsWith("/user/detail/"); return route.path === item.to }
function isChildActive(item) { return item.to === "/match-data" ? route.path.startsWith("/match-data") : route.path === item.to }
const statusLabels = { success: "正常", partial: "部分成功", failed: "采集失败", waiting_config: "缺少配置", waiting_contract: "契约待补", external_scheduler: "独立调度", disabled: "已停用", not_run: "等待同步" }
function runtimeStatus(item) { return Number(item.enabled) !== 1 ? "disabled" : String(item.runtime_status || "not_run") }
function statusLabel(item) { return statusLabels[runtimeStatus(item)] || "状态未知" }
function statusClass(item) { const status = runtimeStatus(item); return { active: ["success", "external_scheduler"].includes(status), warning: ["partial", "waiting_contract"].includes(status), failed: ["failed", "waiting_config"].includes(status) } }
</script>
<style scoped>
.app-sidebar{position:fixed;inset:0 auto 0 0;z-index:1000;width:204px;padding:18px 13px;display:flex;flex-direction:column;color:var(--sidebar-text);background:var(--sidebar-bg)}.sidebar-brand{min-height:58px;padding:0 7px 15px;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(255,255,255,.08)}.sidebar-brand img{width:43px;height:43px;object-fit:contain}.sidebar-brand strong,.sidebar-brand small{display:block;white-space:nowrap}.sidebar-brand strong{color:#fff;font-size:14px}.sidebar-brand small{margin-top:3px;color:var(--accent);font-size:8px;font-weight:700;letter-spacing:.14em}nav{margin-top:20px;display:grid;gap:4px}nav>a{position:relative;min-height:40px;padding:0 12px;border-radius:9px;display:flex;align-items:center;gap:11px;color:var(--sidebar-text);font-size:12px;font-weight:600;transition:color .15s,background .15s}nav>a::before{content:"";position:absolute;left:-13px;width:3px;height:20px;border-radius:0 3px 3px 0;background:transparent}nav>a:hover,nav>a.active{color:#fff;background:var(--sidebar-bg-hover)}nav>a.active::before{background:var(--accent)}.nav-icon{width:18px;text-align:center;font-size:15px;color:currentColor}.sub-navigation{display:none;margin:-1px 0 2px 41px;padding-left:10px;border-left:1px solid rgba(255,255,255,.1)}.sub-navigation.visible{display:grid}.sub-navigation a{padding:6px 4px;color:#85858a;font-size:10px}.sub-navigation a:hover,.sub-navigation a.active{color:var(--accent)}.sidebar-status{margin-top:auto;padding:13px;border:1px solid rgba(255,255,255,.08);border-radius:13px;background:#29292b}.sidebar-status header{margin-bottom:9px;display:flex;justify-content:space-between;color:#fff;font-size:11px}.sidebar-status header span{color:var(--accent)}.sidebar-status>div{min-height:25px;display:grid;grid-template-columns:8px minmax(0,1fr) auto;gap:7px;align-items:center;font-size:9px}.sidebar-status i{width:6px;height:6px;border-radius:50%;background:#66666b}.sidebar-status i.active{background:var(--accent)}.sidebar-status i.warning{background:#f4a62a}.sidebar-status i.failed{background:#ef5a67}.sidebar-status small,.sidebar-status p{color:#85858a;font-size:9px}.sidebar-status p{margin:7px 0 0}footer{padding:14px 5px 0;display:grid;gap:3px;font-size:9px}footer small{color:#66666b}.sidebar-overlay{display:none}@media(max-width:1199px) and (min-width:768px){.app-sidebar{width:72px;padding:14px 10px}.sidebar-brand{justify-content:center}.sidebar-brand span,nav>a>span:not(.nav-icon),.sub-navigation,.sidebar-status,footer{display:none}nav>a{padding:0;justify-content:center}}@media(max-width:767px){.app-sidebar{width:min(280px,86vw);transform:translateX(-102%);transition:transform .18s ease;box-shadow:0 0 50px rgba(0,0,0,.18)}.app-sidebar.open{transform:translateX(0)}.sidebar-overlay{position:fixed;inset:0;z-index:900;display:block;border:0;background:rgba(0,0,0,.38)}}
</style>
