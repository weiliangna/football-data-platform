<template>
<section class="page-shell heatmap-page">

  <header class="page-title">
    <div>
      <p>FOOTBALL BETTING HEATMAP</p>
      <h1>投注热力图</h1>
      <span>
        仅统计今日未截止方案 · 四类玩法 · 独立投注项占比
      </span>
    </div>

    <button class="secondary-button" @click="load">
      刷新热力图
    </button>
  </header>


  <section class="play-tabs panel">

    <button
      v-for="play in plays"
      :key="play"
      :class="{active: playType===play}"
      @click="changePlay(play)"
    >
      {{ play }}
    </button>

    <span>
      占比 = 单场同一玩法下该投注项数量 ÷ 该玩法全部投注项数量
    </span>

  </section>


  <section class="focus-panel panel">

    <header>
      <div>
        <p>CENTER PICKS · {{ playType }}</p>
        <h2>各玩法重心分析</h2>
      </div>

      <span>
        按投注数量最多项自动提取前 4 场比赛
      </span>
    </header>


    <div class="focus-grid">

      <article
        v-for="item in focus"
        :key="item.match_code + item.match_name"
      >
        <span>
          {{ item.match_code || '-' }} · {{ item.match_name }}
        </span>

        <strong>{{ item.option }}</strong>
        <b>{{ item.count }} 次投注</b>
        <small>占该场该玩法 {{ item.share }}%</small>
      </article>

      <article
        v-for="n in Math.max(0,4-focus.length)"
        :key="'empty-'+n"
        class="focus-empty"
      >
        暂无更多比赛
      </article>

    </div>

  </section>


  <section class="platform-summary panel">

    <header>
      <div>
        <p>PLATFORM SUMMARY</p>
        <h2>平台汇总赛事投注项次数</h2>
      </div>
    </header>


    <div class="platform-grid">

      <article
        v-for="item in platformSummary"
        :key="item.platform_id"
      >
        <span>{{ item.platform_name }}</span>
        <strong>{{ item.total_items }}</strong>

        <div>
          <b
            v-for="option in item.options.slice(0,5)"
            :key="option.option"
          >
            {{ option.option }} {{ option.count }}
          </b>
        </div>
      </article>

    </div>

  </section>


  <section class="matrix-panel panel">

    <header>
      <div>
        <p>{{ playType }}</p>
        <h2>赛事投注冷热矩阵</h2>
      </div>

      <span>{{ data.matches?.length || 0 }} 场</span>
    </header>


    <div class="matrix-list">

      <article
        v-for="match in data.matches || []"
        :key="match.match_code + match.match_name"
        class="matrix-row"
      >

        <div class="matrix-match">
          <b>
            {{ match.match_code || '-' }}
            · {{ match.home }} VS {{ match.away }}
          </b>

          <small>
            {{ match.league || '竞彩足球' }}
            · 共 {{ match.total_items }} 个投注项
          </small>
        </div>


        <div class="matrix-options">

          <div
            v-for="option in match.options"
            :key="option.option"
            class="matrix-option"
          >
            <span>{{ option.option }}</span>
            <strong>{{ option.share }}%</strong>

            <div class="share-track">
              <i :style="{width: option.share + '%'}"></i>
            </div>

            <small>
              {{ option.count }} 次
              · 彩{{ option.platforms['1'] || 0 }}
              鸿{{ option.platforms['3'] || 0 }}
              州{{ option.platforms['2'] || 0 }}
              云{{ option.platforms['4'] || 0 }}
              店{{ option.platforms['5'] || 0 }}
              启{{ option.platforms['6'] || 0 }}
            </small>
          </div>

        </div>

      </article>


      <div
        v-if="!(data.matches || []).length"
        class="empty-state"
      >
        今日未截止订单暂无该玩法数据
      </div>

    </div>

  </section>

</section>
</template>


<script setup>
import {
  computed,
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

const playType = ref("胜平负")
const data = ref({})


const focus = computed(() => data.value.focus || [])
const platformSummary = computed(
  () => data.value.platform_summary || []
)


async function load() {

  const response = await axios.get(
    "/api/portal/heatmap",
    {
      params: {
        play_type: playType.value
      }
    }
  )

  if (
    response.data
    &&
    response.data.code === 200
  ) {
    data.value = response.data.data || {}
  }
}


function changePlay(play) {
  playType.value = play
  load()
}


onMounted(load)
</script>


<style scoped>
.heatmap-page {
  max-width: 1480px;
  margin: 0 auto;
}

.play-tabs {
  padding: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}

.play-tabs button {
  border: 1px solid #dcdff0;
  border-radius: 999px;
  padding: 10px 22px;
  background: #fff;
  color: #625f83;
  font-weight: 800;
}

.play-tabs button.active {
  color: #fff;
  background: var(--primary);
  border-color: var(--primary);
  box-shadow: 0 8px 18px rgba(93,89,217,.20);
}

.play-tabs > span {
  flex-basis: 100%;
  margin-top: 5px;
  color: var(--muted);
  text-align: center;
  font-size: 9px;
}

.focus-panel,
.platform-summary,
.matrix-panel {
  margin-top: 18px;
  padding: 20px;
}

.focus-panel > header,
.platform-summary > header,
.matrix-panel > header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.focus-panel header p,
.platform-summary header p,
.matrix-panel header p {
  margin: 0;
  color: var(--primary);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 1.5px;
}

.focus-panel header h2,
.platform-summary header h2,
.matrix-panel header h2 {
  margin: 5px 0 0;
}

.focus-panel header > span,
.matrix-panel header > span {
  color: var(--muted);
  font-size: 10px;
}

.focus-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(4,1fr);
  gap: 12px;
}

.focus-grid article {
  min-height: 150px;
  padding: 17px;
  border-radius: 18px;
  background:
    linear-gradient(
      180deg,
      #f0efff,
      #fbfbff
    );
  border: 1px solid #dfdff2;
  text-align: center;
}

.focus-grid article > span {
  display: block;
  min-height: 34px;
  color: var(--primary);
  font-size: 10px;
  font-weight: 800;
}

.focus-grid article > strong {
  display: block;
  margin-top: 17px;
  font-size: 17px;
}

.focus-grid article > b {
  display: block;
  margin-top: 6px;
  color: #2a3242;
}

.focus-grid article > small {
  display: block;
  margin-top: 7px;
  color: var(--muted);
}

.focus-empty {
  display: grid;
  place-items: center;
  color: var(--muted);
}

.platform-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(4,1fr);
  gap: 12px;
}

.platform-grid article {
  padding: 15px;
  border-radius: 17px;
  background: var(--surface-soft);
}

.platform-grid article > span {
  color: var(--muted);
  font-size: 10px;
}

.platform-grid article > strong {
  display: block;
  margin-top: 5px;
  color: var(--primary);
  font-size: 24px;
}

.platform-grid article > div {
  margin-top: 9px;
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.platform-grid article b {
  padding: 4px 7px;
  border-radius: 999px;
  color: #5a5f79;
  background: #fff;
  font-size: 8px;
}

.matrix-list {
  margin-top: 14px;
  display: grid;
  gap: 10px;
}

.matrix-row {
  padding: 15px;
  border: 1px solid var(--line);
  border-radius: 17px;
  display: grid;
  grid-template-columns: minmax(260px,.75fr) minmax(0,2fr);
  gap: 18px;
}

.matrix-match b,
.matrix-match small {
  display: block;
}

.matrix-match small {
  margin-top: 5px;
  color: var(--muted);
  font-size: 9px;
}

.matrix-options {
  display: grid;
  grid-template-columns:
    repeat(
      auto-fit,
      minmax(145px,1fr)
    );
  gap: 8px;
}

.matrix-option {
  padding: 10px;
  border-radius: 13px;
  background: #fafaff;
}

.matrix-option span,
.matrix-option strong,
.matrix-option small {
  display: block;
}

.matrix-option span {
  color: #5a6072;
  font-size: 9px;
}

.matrix-option strong {
  margin-top: 4px;
  color: var(--primary);
  font-size: 16px;
}

.share-track {
  height: 6px;
  margin: 7px 0;
  border-radius: 999px;
  background: #ececf8;
  overflow: hidden;
}

.share-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background:
    linear-gradient(
      90deg,
      var(--primary),
      #9894f6
    );
}

.matrix-option small {
  color: var(--muted);
  font-size: 8px;
}

@media (max-width: 950px) {

  .focus-grid,
  .platform-grid {
    grid-template-columns: repeat(2,1fr);
  }

  .matrix-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 580px) {

  .focus-grid,
  .platform-grid {
    grid-template-columns: 1fr;
  }
}
</style>
