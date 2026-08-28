<template>
  <div class="app-shell">
    <AppSidebar :open="sidebarOpen" :platforms="platforms" :platform-error="platformError" @close="sidebarOpen = false" />
    <main class="app-main">
      <div class="mobile-toolbar">
        <button type="button" :aria-expanded="sidebarOpen" aria-label="打开菜单" @click="sidebarOpen = true">☰</button>
        <img src="/football-ai-logo.png" alt="绿茵智核足球 AI 标识">
        <span class="mobile-toolbar-spacer" aria-hidden="true"></span>
      </div>
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from "vue"
import { useRoute } from "vue-router"
import axios from "axios"
import AppSidebar from "./components/layout/AppSidebar.vue"

const route = useRoute()
const sidebarOpen = ref(false)
const platforms = ref([])
const platformError = ref(false)

async function loadPlatforms() {
  platformError.value = false
  try {
    const response = await axios.get("/api/platform/list", { timeout: 25000 })
    const rows = response.data && response.data.data
    platforms.value = Array.isArray(rows) ? rows : []
  } catch {
    platforms.value = []
    platformError.value = true
  }
}

function handleEscape(event) { if (event.key === "Escape") sidebarOpen.value = false }

watch(() => route.fullPath, () => { sidebarOpen.value = false })
onMounted(() => { loadPlatforms(); window.addEventListener("keydown", handleEscape) })
onUnmounted(() => window.removeEventListener("keydown", handleEscape))
</script>

<style src="./assets/hub.css"></style>
