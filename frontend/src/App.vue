<template>
  <div class="app-shell">
    <header class="top-shell">
      <button
        class="mobile-menu"
        type="button"
        :aria-expanded="sidebarOpen"
        aria-label="打开导航"
        @click="sidebarOpen = !sidebarOpen"
      >
        ☰
      </button>

      <router-link class="brand" to="/" @click="closeSidebar">
        <img
          class="brand-mark"
          src="/football-ai-logo.png"
          alt="绿茵智核足球 AI 标识"
        >

        <span class="brand-copy">
          <strong>绿茵智核</strong>
          <small>FOOTBALL AI INSIGHT</small>
        </span>
      </router-link>

      <nav class="top-nav" aria-label="主导航">
        <router-link
          v-for="item in topNavigation"
          :key="item.key"
          :to="item.to"
          :class="{ active: activeNav === item.key }"
          @click="closeSidebar"
        >
          {{ item.name }}
        </router-link>
      </nav>

      <div class="top-tools">
        <span class="live-chip">
          <i class="live-dot"></i>
          {{ platforms.length || 6 }} 平台聚合中
        </span>

        <div class="clock">
          <b>{{ dateText }}</b>
          <span>{{ timeText }}</span>
        </div>

        <button
          class="round-tool"
          type="button"
          title="刷新当前页面"
          aria-label="刷新当前页面"
          @click="reload"
        >
          ↻
        </button>
      </div>
    </header>

    <div class="app-body">
      <aside class="side-shell" :class="{ open: sidebarOpen }">
        <p class="side-label">DATA WORKSPACE</p>

        <nav class="side-nav" aria-label="数据功能导航">
          <router-link
            v-for="item in sideNavigation"
            :key="item.to"
            class="side-link"
            :class="{ active: isSideActive(item) }"
            :to="item.to"
            @click="closeSidebar"
          >
            <span class="side-icon">{{ item.icon }}</span>
            <span>{{ item.name }}</span>
            <span class="side-arrow">›</span>
          </router-link>
        </nav>

        <section class="platform-monitor" aria-label="平台状态">
          <header>
            <b>平台接入</b>
            <span>{{ enabledPlatformCount }}/{{ platforms.length || 6 }} 已启用</span>
          </header>

          <div class="platform-stack">
            <div
              v-for="item in platforms"
              :key="item.platform_id"
              class="platform-state"
            >
              <i>{{ item.short || shortName(item.name) }}</i>
              <b>{{ item.name }}</b>
              <span :class="{ on: Number(item.enabled) === 1 }"></span>
            </div>
          </div>
        </section>

        <p class="side-note">
          数据来自已授权的平台接口。页面只展示聚合结果，不构成投注或收益建议。
        </p>
      </aside>

      <button
        v-if="sidebarOpen"
        class="side-mask"
        type="button"
        aria-label="关闭导航"
        @click="closeSidebar"
      ></button>

      <section class="page-stage">
        <main class="page-container">
          <router-view />
        </main>

        <footer class="app-footer">
          <div class="footer-brand">
            <img src="/football-ai-logo.png" alt="">
            <div>
              <b>绿茵智核 · 足球数据聚合平台</b>
              <span>让分散的方案、比赛与用户数据形成统一视图。</span>
            </div>
          </div>

          <div class="footer-block">
            <b>数据范围</b>
            <span>平台方案 · 发单用户 · 赛事赛果 · 聚合统计</span>
          </div>

          <div class="footer-block">
            <b>使用说明</b>
            <span>数据存在同步延迟，请以来源平台最终公布结果为准。</span>
          </div>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup>
import {
  computed,
  onMounted,
  onUnmounted,
  ref,
  watch
} from "vue"

import {
  useRoute
} from "vue-router"

import axios from "axios"


const route = useRoute()
const now = ref(new Date())
const sidebarOpen = ref(false)
const platforms = ref([])
let timer = null


const fallbackPlatforms = [
  { platform_id: 1, name: "彩站云", short: "彩", enabled: 1 },
  { platform_id: 2, name: "州运宝", short: "州", enabled: 1 },
  { platform_id: 3, name: "鸿瑞", short: "鸿", enabled: 1 },
  { platform_id: 4, name: "云彩", short: "云", enabled: 0 },
  { platform_id: 5, name: "好店主", short: "店", enabled: 1 },
  { platform_id: 6, name: "启示录", short: "启", enabled: 1 }
]


const topNavigation = [
  { key: "dashboard", name: "数据总览", to: "/" },
  { key: "schemes", name: "方案大厅", to: "/orders" },
  { key: "matches", name: "赛事数据", to: "/analysis" },
  { key: "ranking", name: "英雄榜", to: "/users" }
]


const sideNavigation = [
  { name: "今日总览", to: "/", icon: "⌁", exact: true },
  { name: "方案聚合", to: "/orders", icon: "◎" },
  { name: "赛事分析", to: "/analysis", icon: "◫" },
  { name: "投注热力", to: "/heatmap", icon: "◇" },
  { name: "赛果归档", to: "/results", icon: "✓" },
  { name: "发单用户", to: "/users", icon: "◉" }
]


const activeNav = computed(() => {
  const path = route.path

  if (path === "/") {
    return "dashboard"
  }

  if (path === "/orders" || path.includes("/order/detail/")) {
    return "schemes"
  }

  if (["/analysis", "/heatmap", "/results"].includes(path)) {
    return "matches"
  }

  if (path === "/users" || path.includes("/user/detail/")) {
    return "ranking"
  }

  return ""
})


const dateText = computed(() => now.value.toLocaleDateString(
  "zh-CN",
  {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }
))


const timeText = computed(() => now.value.toLocaleTimeString(
  "zh-CN",
  {
    hour12: false
  }
))


const enabledPlatformCount = computed(() => platforms.value.filter(
  item => Number(item.enabled) === 1
).length)


function isSideActive(item) {
  if (item.exact) {
    return route.path === item.to
  }

  if (item.to === "/orders") {
    return route.path === item.to || route.path.includes("/order/detail/")
  }

  if (item.to === "/users") {
    return route.path === item.to || route.path.includes("/user/detail/")
  }

  return route.path === item.to
}


function shortName(name) {
  return String(name || "平").slice(0, 1)
}


function closeSidebar() {
  sidebarOpen.value = false
}


function reload() {
  window.location.reload()
}


async function loadPlatforms() {
  try {
    const response = await axios.get("/api/platform/list")
    const rows = response.data && response.data.data
    platforms.value = Array.isArray(rows) && rows.length
      ? rows
      : fallbackPlatforms
  } catch {
    platforms.value = fallbackPlatforms
  }
}


watch(
  () => route.fullPath,
  closeSidebar
)


onMounted(() => {
  loadPlatforms()
  timer = setInterval(() => {
    now.value = new Date()
  }, 1000)
})


onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<style src="./assets/hub.css"></style>
