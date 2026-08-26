<template>
  <section class="page-shell results-page">
    <header class="page-title">
      <div>
        <p>RESULT ARCHIVE</p>
        <h1>赛果统计</h1>
        <span>统一展示标准化球队名称、全场比分与半场比分</span>
      </div>
      <button class="secondary-button" type="button" @click="load">刷新赛果</button>
    </header>

    <section class="results-panel panel">
      <header class="results-head">
        <span>场次</span><span>对阵</span><span>全场</span><span>半场</span><span>结束时间</span>
      </header>

      <article v-for="item in rows" :key="item.id" class="result-row">
        <span class="match-code">{{ item.match_code || "-" }}</span>
        <b>{{ item.home }} <i>VS</i> {{ item.away }}</b>
        <strong class="score">{{ item.home_score }} : {{ item.away_score }}</strong>
        <span>{{ halfScore(item) }}</span>
        <small>{{ time(item.finished_time) }}</small>
      </article>

      <div v-if="error" class="error-state">
        <div class="state-stack"><span class="state-symbol">!</span><b>{{ error }}</b></div>
      </div>

      <div v-else-if="!rows.length" class="empty-state">
        <div class="state-stack">
          <img class="empty-logo" src="/football-ai-logo.png" alt="">
          <b>暂无已同步赛果</b>
        </div>
      </div>
    </section>

    <div class="pager">
      <button class="secondary-button" type="button" :disabled="page <= 1" @click="changePage(page - 1)">← 上一页</button>
      <span>第 <b>{{ page }}</b> / {{ pages }} 页</span>
      <button class="secondary-button" type="button" :disabled="page >= pages" @click="changePage(page + 1)">下一页 →</button>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue"
import axios from "axios"

const rows = ref([])
const page = ref(1)
const pages = ref(1)
const error = ref("")

async function load() {
  error.value = ""
  try {
    const response = await axios.get("/api/portal/results", { params: { page: page.value, page_size: 50 } })
    if (!response.data || response.data.code !== 200) {
      throw new Error("results unavailable")
    }
    rows.value = response.data.data || []
    pages.value = response.data.pages || 1
  } catch {
    rows.value = []
    error.value = "赛果数据暂时无法读取，请稍后重试。"
  }
}

function changePage(value) {
  page.value = value
  load()
}

function halfScore(item) {
  if (item.half_home_score === null || item.half_home_score === undefined) {
    return "-"
  }
  return item.half_home_score + " : " + item.half_away_score
}

function time(value) {
  return value ? String(value).replace("T", " ").replace("Z", "") : "-"
}

onMounted(load)
</script>

<style scoped>
.results-panel { overflow: hidden; }
.results-head,
.result-row { display: grid; grid-template-columns: minmax(90px,.55fr) minmax(260px,1.5fr) minmax(100px,.65fr) minmax(90px,.55fr) minmax(160px,.9fr); gap: 13px; align-items: center; }
.results-head { min-height: 42px; padding: 0 16px; color: var(--muted-2); background: #0e130f; font-size: 8px; font-weight: 900; }
.result-row { min-height: 66px; padding: 12px 16px; border-top: 1px solid var(--line); color: #a9b4aa; font-size: 10px; }
.result-row:hover { background: rgba(184,255,56,.025); }
.result-row > b { color: var(--text-soft); font-size: 11px; }
.result-row > b i { margin: 0 6px; color: var(--lime); font-size: 8px; font-style: normal; }
.match-code { width: fit-content; padding: 5px 8px; border-radius: 999px; color: var(--mint); background: var(--mint-soft); font-size: 8px; font-weight: 900; }
.score { color: var(--lime); font-size: 18px; }
.result-row small { color: var(--muted); }
.empty-logo { width: 82px; opacity: .72; }
.pager { margin-top: 16px; display: flex; justify-content: center; align-items: center; gap: 11px; color: var(--muted); font-size: 9px; }
.pager b { color: var(--lime); }

@media (max-width: 760px) {
  .results-panel { overflow-x: auto; }
  .results-head,
  .result-row { min-width: 760px; }
}
</style>
