<template>
  <section class="page-shell monitor-page">
    <header class="page-header"><div><p class="eyebrow">DATA MONITOR</p><h1>数据监控</h1><p>查看各平台采集、同步与服务状态。</p></div><span class="updated">数据源状态 · {{ source }}</span></header>
    <section class="monitor-grid"><article v-for="item in cards" :key="item.name" class="monitor-card app-card"><div class="card-top"><span class="dot" :class="item.tone"></span><b>{{ item.name }}</b><span class="state" :class="item.tone">{{ item.state }}</span></div><strong>{{ item.value }}</strong><small>{{ item.note }}</small><div class="bar"><i :style="{ width: item.progress + '%' }"></i></div></article></section>
    <article class="app-card task-panel"><header><div><p class="eyebrow">RECENT TASKS</p><h2>最近任务</h2></div><span class="muted">自动更新</span></header><div class="task-row" v-for="task in tasks" :key="task.name"><span class="task-dot" :class="task.tone"></span><div><b>{{ task.name }}</b><small>{{ task.time }}</small></div><strong>{{ task.result }}</strong></div></article>
  </section>
</template>
<script setup>
import { ref } from "vue"
const source = "Mock / 待接入接口"
const cards = ref([
  { name: "彩站云", state: "正常", value: "1,725", note: "最近一轮重复方案", progress: 92, tone: "ok" },
  { name: "鸿瑞", state: "独立调度", value: "60s", note: "最近同步间隔", progress: 76, tone: "ok" },
  { name: "云彩", state: "待契约", value: "—", note: "等待动态签名接入", progress: 18, tone: "warn" },
  { name: "API 服务", state: "运行中", value: "99.9%", note: "最近 24 小时可用性", progress: 99, tone: "ok" },
])
const tasks = [
  { name: "平台采集 pipeline", time: "刚刚 · 6 个平台", result: "完成", tone: "ok" },
  { name: "赛果同步", time: "2 分钟前 · 128 场", result: "完成", tone: "ok" },
  { name: "用户统计", time: "5 分钟前 · 2,381 用户", result: "部分完成", tone: "warn" },
]
</script>
<style scoped>
.monitor-page{max-width:1360px}.page-header p:not(.eyebrow){margin:6px 0 0;color:var(--text-muted);font-size:12px}.updated{color:var(--text-muted);font-size:11px}.monitor-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin-top:16px}.monitor-card{padding:17px}.card-top{display:flex;align-items:center;gap:8px;font-size:12px}.dot,.task-dot{width:7px;height:7px;border-radius:50%;background:#9ca3af}.dot.ok,.task-dot.ok{background:#20a76a}.dot.warn,.task-dot.warn{background:#e59b36}.state{margin-left:auto;font-size:10px;color:#20a76a}.state.warn{color:#c47a1e}.monitor-card>strong{display:block;margin:18px 0 4px;font-size:25px}.monitor-card>small{color:var(--text-muted);font-size:10px}.bar{height:4px;margin-top:17px;border-radius:4px;background:#edf0f2;overflow:hidden}.bar i{display:block;height:100%;border-radius:4px;background:#1769e0}.task-panel{margin-top:14px;padding:19px}.task-panel header{display:flex;justify-content:space-between;align-items:flex-start}.task-panel h2{margin:0;font-size:18px}.task-row{display:flex;align-items:center;gap:10px;padding:14px 0;border-bottom:1px solid var(--border)}.task-row:last-child{border-bottom:0}.task-row div{flex:1}.task-row b,.task-row small{display:block}.task-row b{font-size:12px}.task-row small{margin-top:4px;color:var(--text-muted);font-size:10px}.task-row strong{color:#20a76a;font-size:11px}.task-row strong:has(+*){}.muted{color:var(--text-muted);font-size:10px}@media(max-width:900px){.monitor-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.monitor-grid{grid-template-columns:1fr}.updated{display:none}}
</style>
