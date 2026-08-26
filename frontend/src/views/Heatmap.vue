<template>
  <section class="page-shell heatmap-page">
    <header class="page-title">
      <div>
        <p>FOOTBALL BETTING HEATMAP</p>
        <h1>投注热力图</h1>
        <span>仅统计今日未截止方案 · 四类玩法 · 独立投注项占比</span>
      </div>
      <button class="secondary-button" type="button" @click="load">刷新热力图</button>
    </header>

    <section class="play-tabs panel">
      <button
        v-for="play in plays"
        :key="play"
        type="button"
        :class="{ active: playType === play }"
        @click="changePlay(play)"
      >{{ play }}</button>
      <span>占比 = 单场同一玩法下该投注项数量 ÷ 该玩法全部投注项数量</span>
    </section>

    <section v-if="error" class="panel error-state section-gap">
      <div class="state-stack"><span class="state-symbol">!</span><b>{{ error }}</b></div>
    </section>

    <template v-else>
      <section class="focus-panel panel">
        <header>
          <div><p>CENTER PICKS · {{ playType }}</p><h2>各玩法重心分析</h2></div>
          <span>按投注数量最多项自动提取前 4 场比赛</span>
        </header>

        <div class="focus-grid">
          <article v-for="item in focus" :key="item.match_code + item.match_name">
            <span>{{ item.match_code || "-" }} · {{ item.match_name }}</span>
            <strong>{{ item.option }}</strong>
            <b>{{ item.count }} 次投注</b>
            <small>占该场该玩法 {{ item.share }}%</small>
          </article>
          <article v-for="n in Math.max(0, 4 - focus.length)" :key="'empty-' + n" class="focus-empty">
            暂无更多比赛
          </article>
        </div>
      </section>

      <section class="platform-summary panel">
        <header><div><p>PLATFORM SUMMARY</p><h2>平台汇总赛事投注项次数</h2></div></header>
        <div class="platform-grid">
          <article v-for="item in platformSummary" :key="item.platform_id">
            <span>{{ item.platform_name }}</span>
            <strong>{{ item.total_items }}</strong>
            <div>
              <b v-for="option in item.options.slice(0, 5)" :key="option.option">
                {{ option.option }} {{ option.count }}
              </b>
            </div>
          </article>
        </div>
      </section>

      <section class="matrix-panel panel">
        <header>
          <div><p>{{ playType }}</p><h2>赛事投注冷热矩阵</h2></div>
          <span>{{ (data.matches || []).length }} 场</span>
        </header>

        <div class="matrix-list">
          <article
            v-for="match in data.matches || []"
            :key="match.match_code + match.match_name"
            class="matrix-row"
          >
            <div class="matrix-match">
              <b>{{ match.match_code || "-" }} · {{ match.home }} <i>VS</i> {{ match.away }}</b>
              <small>{{ match.league || "竞彩足球" }} · 共 {{ match.total_items }} 个投注项</small>
            </div>

            <div class="matrix-options">
              <div v-for="option in match.options" :key="option.option" class="matrix-option">
                <span>{{ option.option }}</span>
                <strong>{{ option.share }}%</strong>
                <div class="share-track"><i :style="{ width: option.share + '%' }"></i></div>
                <small>
                  {{ option.count }} 次 · 彩{{ option.platforms["1"] || 0 }}
                  鸿{{ option.platforms["3"] || 0 }} 州{{ option.platforms["2"] || 0 }}
                  云{{ option.platforms["4"] || 0 }} 店{{ option.platforms["5"] || 0 }}
                  启{{ option.platforms["6"] || 0 }}
                </small>
              </div>
            </div>
          </article>

          <div v-if="!(data.matches || []).length" class="empty-state">
            今日未截止订单暂无该玩法数据
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import axios from "axios"

const plays = ["胜平负", "让球胜平负", "半全场", "比分"]
const playType = ref("胜平负")
const data = ref({})
const error = ref("")
const focus = computed(() => data.value.focus || [])
const platformSummary = computed(() => data.value.platform_summary || [])

async function load() {
  error.value = ""
  try {
    const response = await axios.get("/api/portal/heatmap", { params: { play_type: playType.value } })
    if (!response.data || response.data.code !== 200) {
      throw new Error("heatmap unavailable")
    }
    data.value = response.data.data || {}
  } catch {
    error.value = "热力数据暂时无法读取，请稍后重试。"
  }
}

function changePlay(play) {
  playType.value = play
  load()
}

onMounted(load)
</script>

<style scoped>
.play-tabs { padding: 13px; display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 8px; }
.play-tabs button { min-height: 37px; border: 1px solid var(--line); border-radius: 999px; padding: 0 19px; color: var(--muted); background: var(--surface-2); font-size: 10px; font-weight: 900; }
.play-tabs button.active { color: #07110b; border-color: var(--lime); background: var(--lime); box-shadow: 0 8px 18px rgba(184,255,56,.14); }
.play-tabs > span { flex-basis: 100%; margin-top: 4px; color: var(--muted-2); text-align: center; font-size: 8px; }
.section-gap,
.focus-panel,
.platform-summary,
.matrix-panel { margin-top: 16px; }
.focus-panel,
.platform-summary,
.matrix-panel { padding: 19px; }
.focus-panel > header,
.platform-summary > header,
.matrix-panel > header { display: flex; align-items: flex-end; justify-content: space-between; gap: 14px; }
.focus-panel header p,
.platform-summary header p,
.matrix-panel header p { margin: 0; color: var(--lime); font-size: 8px; font-weight: 900; letter-spacing: .15em; }
.focus-panel header h2,
.platform-summary header h2,
.matrix-panel header h2 { margin: 5px 0 0; font-size: 19px; }
.focus-panel header > span,
.matrix-panel header > span { color: var(--muted); font-size: 9px; }

.focus-grid { margin-top: 14px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.focus-grid article { min-height: 150px; padding: 16px; border: 1px solid var(--line); border-radius: 16px; text-align: center; background: linear-gradient(145deg, rgba(66,245,197,.09), rgba(184,255,56,.025)); }
.focus-grid article > span { display: block; min-height: 34px; color: var(--mint); font-size: 9px; font-weight: 800; }
.focus-grid article > strong { display: block; margin-top: 15px; color: #fff; font-size: 18px; }
.focus-grid article > b { display: block; margin-top: 5px; color: var(--lime); }
.focus-grid article > small { display: block; margin-top: 6px; color: var(--muted); font-size: 8px; }
.focus-empty { display: grid; place-items: center; color: var(--muted); }

.platform-grid { margin-top: 13px; display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
.platform-grid article { padding: 14px; border: 1px solid var(--line); border-radius: 15px; background: var(--surface-2); }
.platform-grid article > span { color: var(--muted); font-size: 9px; }
.platform-grid article > strong { display: block; margin-top: 4px; color: var(--lime); font-size: 24px; }
.platform-grid article > div { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 5px; }
.platform-grid article b { padding: 4px 7px; border-radius: 999px; color: #abc0ae; background: #0e130f; font-size: 7px; }

.matrix-list { margin-top: 13px; display: grid; gap: 9px; }
.matrix-row { padding: 14px; border: 1px solid var(--line); border-radius: 16px; display: grid; grid-template-columns: minmax(260px,.75fr) minmax(0,2fr); gap: 17px; background: #0e130f; }
.matrix-match b,
.matrix-match small { display: block; }
.matrix-match b { font-size: 11px; }
.matrix-match b i { margin: 0 5px; color: var(--lime); font-size: 8px; font-style: normal; }
.matrix-match small { margin-top: 5px; color: var(--muted); font-size: 8px; }
.matrix-options { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px,1fr)); gap: 7px; }
.matrix-option { padding: 10px; border-radius: 12px; background: var(--surface-2); }
.matrix-option span,
.matrix-option strong,
.matrix-option small { display: block; }
.matrix-option span { color: #aab5ab; font-size: 8px; }
.matrix-option strong { margin-top: 3px; color: var(--lime); font-size: 16px; }
.share-track { height: 5px; margin: 7px 0; border-radius: 999px; overflow: hidden; background: #293329; }
.share-track i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--mint), var(--lime)); }
.matrix-option small { color: var(--muted); font-size: 7px; }

@media (max-width: 950px) {
  .focus-grid { grid-template-columns: repeat(2, 1fr); }
  .matrix-row { grid-template-columns: 1fr; }
}

@media (max-width: 580px) {
  .focus-panel > header,
  .matrix-panel > header { align-items: flex-start; flex-direction: column; }
  .focus-grid { grid-template-columns: 1fr; }
}
</style>
