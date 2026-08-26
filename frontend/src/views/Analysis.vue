<template>
  <section class="page-shell analysis-page">
    <header class="page-title">
      <div>
        <p>MATCH EVIDENCE</p>
        <h1>赛事分析</h1>
        <span>赛事日 {{ data.day || "待同步" }} · 仅使用未截止方案作为分析证据</span>
      </div>
      <button class="secondary-button" type="button" @click="load">刷新分析</button>
    </header>

    <section class="analysis-summary panel">
      <article>
        <span class="summary-icon">◎</span>
        <div><small>未截止方案</small><strong>{{ number(data.unexpired_orders) }}</strong></div>
      </article>
      <article>
        <span class="summary-icon mint">◫</span>
        <div><small>分析场次</small><strong>{{ number((data.matches || []).length) }}</strong></div>
      </article>
      <article>
        <span class="summary-icon amber">◇</span>
        <div><small>覆盖玩法</small><strong>{{ plays.length }}</strong></div>
      </article>
    </section>

    <section v-if="error" class="panel error-state">
      <div class="state-stack">
        <span class="state-symbol">!</span><b>{{ error }}</b>
        <button class="secondary-button" type="button" @click="load">重新加载</button>
      </div>
    </section>

    <section v-else class="match-analysis-list">
      <article
        v-for="match in data.matches || []"
        :key="match.match_code + match.match_name"
        class="match-analysis panel"
      >
        <header>
          <div>
            <span class="match-code">{{ match.match_code || "-" }}</span>
            <b>{{ match.match_name }}</b>
            <small>{{ match.league || "竞彩足球" }}</small>
          </div>
          <span class="evidence-tag">LIVE EVIDENCE</span>
        </header>

        <div class="play-evidence">
          <article v-for="play in plays" :key="play">
            <h3>{{ play }}</h3>
            <div
              v-if="match.plays && match.plays[play] && match.plays[play].length"
              class="evidence-options"
            >
              <div v-for="option in match.plays[play]" :key="option.option">
                <span>{{ option.option }}</span>
                <strong>{{ option.share }}%</strong>
                <i :style="{ width: Math.min(100, Number(option.share || 0)) + '%' }"></i>
                <small>{{ option.count }} 次</small>
              </div>
            </div>
            <div v-else class="no-evidence">暂无采集数据</div>
          </article>
        </div>
      </article>

      <div v-if="!(data.matches || []).length" class="panel empty-state">
        <div class="state-stack">
          <img class="empty-logo" src="/football-ai-logo.png" alt="">
          <b>今日暂无可分析的未截止方案</b>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue"
import axios from "axios"

const plays = ["胜平负", "让球胜平负", "半全场", "比分"]
const data = ref({})
const error = ref("")

async function load() {
  error.value = ""
  try {
    const response = await axios.get("/api/portal/analysis")
    if (!response.data || response.data.code !== 200) {
      throw new Error("analysis unavailable")
    }
    data.value = response.data.data || {}
  } catch {
    error.value = "赛事分析暂时无法读取，请稍后重试。"
  }
}

function number(value) {
  return Math.round(Number(value || 0)).toLocaleString("zh-CN")
}

onMounted(load)
</script>

<style scoped>
.analysis-summary {
  padding: 13px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.analysis-summary article {
  min-height: 88px;
  padding: 13px;
  border: 1px solid rgba(184, 255, 56, .08);
  border-radius: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface-2);
}

.summary-icon {
  width: 43px;
  height: 43px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #07110b;
  background: var(--lime);
  font-weight: 900;
}

.summary-icon.mint { background: var(--mint); }
.summary-icon.amber { background: var(--amber); }

.analysis-summary small,
.analysis-summary strong { display: block; }
.analysis-summary small { color: var(--muted); font-size: 9px; }
.analysis-summary strong { margin-top: 3px; font-size: 22px; }

.match-analysis-list { margin-top: 15px; display: grid; gap: 12px; }
.match-analysis { padding: 18px; }
.match-analysis > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.match-analysis header b,
.match-analysis header small { display: block; }
.match-analysis header b { margin-top: 7px; font-size: 15px; }
.match-analysis header small { margin-top: 4px; color: var(--muted); font-size: 8px; }
.match-code { padding: 4px 8px; border-radius: 999px; color: var(--lime); background: var(--lime-soft); font-size: 8px; font-weight: 900; }
.evidence-tag { color: var(--mint); font-size: 8px; font-weight: 900; letter-spacing: .14em; }

.play-evidence { margin-top: 15px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 9px; }
.play-evidence > article { min-height: 165px; padding: 13px; border: 1px solid var(--line); border-radius: 15px; background: #0e130f; }
.play-evidence h3 { margin: 0; color: var(--text-soft); font-size: 11px; }
.evidence-options { margin-top: 9px; display: grid; gap: 6px; }
.evidence-options > div { position: relative; padding: 8px; border-radius: 10px; overflow: hidden; background: var(--surface-2); }
.evidence-options span,
.evidence-options strong,
.evidence-options small { position: relative; z-index: 2; display: block; }
.evidence-options span { color: #a6b1a7; font-size: 8px; }
.evidence-options strong { margin-top: 2px; color: var(--lime); }
.evidence-options small { color: var(--muted); font-size: 7px; }
.evidence-options i { position: absolute; inset: auto 0 0; height: 3px; background: linear-gradient(90deg, var(--mint), var(--lime)); }
.no-evidence { min-height: 116px; display: grid; place-items: center; color: var(--muted); font-size: 8px; }
.empty-logo { width: 82px; opacity: .7; }

@media (max-width: 1000px) {
  .play-evidence { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 600px) {
  .analysis-summary,
  .play-evidence { grid-template-columns: 1fr; }
}
</style>
