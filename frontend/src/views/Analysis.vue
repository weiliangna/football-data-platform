<template>
<section class="page-shell analysis-page">

  <header class="page-title">
    <div>
      <p>MATCH EVIDENCE</p>
      <h1>赛事分析</h1>
      <span>
        当前赛事日 {{ data.day || '-' }} · 仅使用未截止方案证据
      </span>
    </div>

    <button class="secondary-button" @click="load">
      刷新
    </button>
  </header>


  <section class="analysis-summary panel">

    <div>
      <span>未截止方案</span>
      <strong>{{ data.unexpired_orders || 0 }}</strong>
    </div>

    <div>
      <span>分析场次</span>
      <strong>{{ data.matches?.length || 0 }}</strong>
    </div>

    <div>
      <span>固定玩法</span>
      <strong>4</strong>
    </div>

  </section>


  <section class="match-analysis-list">

    <article
      v-for="match in data.matches || []"
      :key="match.match_code + match.match_name"
      class="match-analysis panel"
    >

      <header>
        <div>
          <b>
            {{ match.match_code || '-' }}
            · {{ match.match_name }}
          </b>

          <small>{{ match.league || '竞彩足球' }}</small>
        </div>
      </header>


      <div class="play-evidence">

        <article
          v-for="play in plays"
          :key="play"
        >
          <h3>{{ play }}</h3>

          <div
            v-if="
              match.plays
              &&
              match.plays[play]
              &&
              match.plays[play].length
            "
            class="evidence-options"
          >
            <div
              v-for="option in match.plays[play]"
              :key="option.option"
            >
              <span>{{ option.option }}</span>
              <strong>{{ option.share }}%</strong>
              <small>{{ option.count }}次</small>
            </div>
          </div>

          <div v-else class="no-evidence">
            暂无采集数据
          </div>
        </article>

      </div>

    </article>


    <div
      v-if="!(data.matches || []).length"
      class="panel empty-state"
    >
      今日暂无可分析的未截止方案
    </div>

  </section>

</section>
</template>


<script setup>
import {
  onMounted,
  ref
} from "vue"

import axios from "axios"


const plays = [
  "胜平负",
  "让球胜平负",
  "半全场",
  "比分"
]

const data = ref({})


async function load() {

  const response = await axios.get(
    "/api/portal/analysis"
  )

  if (
    response.data
    &&
    response.data.code === 200
  ) {
    data.value = response.data.data || {}
  }
}


onMounted(load)
</script>


<style scoped>
.analysis-page {
  max-width: 1480px;
  margin: 0 auto;
}

.analysis-summary {
  padding: 15px;
  display: grid;
  grid-template-columns: repeat(3,1fr);
  gap: 10px;
}

.analysis-summary > div {
  padding: 14px;
  border-radius: 16px;
  background: var(--surface-soft);
}

.analysis-summary span,
.analysis-summary strong {
  display: block;
}

.analysis-summary span {
  color: var(--muted);
  font-size: 9px;
}

.analysis-summary strong {
  margin-top: 5px;
  color: var(--primary);
  font-size: 21px;
}

.match-analysis-list {
  margin-top: 16px;
  display: grid;
  gap: 13px;
}

.match-analysis {
  padding: 17px;
}

.match-analysis header b,
.match-analysis header small {
  display: block;
}

.match-analysis header small {
  margin-top: 4px;
  color: var(--muted);
  font-size: 9px;
}

.play-evidence {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(4,1fr);
  gap: 10px;
}

.play-evidence > article {
  min-height: 150px;
  padding: 13px;
  border-radius: 16px;
  background: #fafaff;
  border: 1px solid var(--line);
}

.play-evidence h3 {
  margin: 0;
  color: #343b51;
  font-size: 12px;
}

.evidence-options {
  margin-top: 9px;
  display: grid;
  gap: 6px;
}

.evidence-options > div {
  padding: 7px;
  border-radius: 10px;
  background: var(--primary-soft);
}

.evidence-options span,
.evidence-options strong,
.evidence-options small {
  display: block;
}

.evidence-options span {
  color: #5f6178;
  font-size: 9px;
}

.evidence-options strong {
  margin-top: 2px;
  color: var(--primary);
}

.evidence-options small {
  color: var(--muted);
  font-size: 8px;
}

.no-evidence {
  min-height: 100px;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 9px;
}

@media (max-width: 1000px) {

  .play-evidence {
    grid-template-columns: repeat(2,1fr);
  }
}

@media (max-width: 600px) {

  .analysis-summary,
  .play-evidence {
    grid-template-columns: 1fr;
  }
}
</style>
