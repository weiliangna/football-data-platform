<template>
  <section class="page-shell home-page">
    <header class="page-title">
      <div>
        <p>LIVE FOOTBALL INTELLIGENCE</p>
        <h1>足球数据聚合控制台</h1>
        <span>
          赛事日 {{ data.day || "待同步" }} · 汇总多平台方案、用户与赛果状态
        </span>
      </div>

      <div class="title-actions">
        <span v-if="lastUpdated" class="updated-time">
          更新于 {{ lastUpdated }}
        </span>
        <button class="secondary-button" type="button" @click="load">
          刷新数据
        </button>
      </div>
    </header>

    <section v-if="error" class="panel error-state">
      <div class="state-stack">
        <span class="state-symbol">!</span>
        <b>{{ error }}</b>
        <button class="secondary-button" type="button" @click="load">
          重新加载
        </button>
      </div>
    </section>

    <template v-else>
      <section class="hero-grid">
        <article class="hero-card">
          <div class="hero-copy">
            <span class="hero-overline">
              <i></i>
              SIX-PLATFORM LIVE FEED
            </span>

            <h2>六平台发单与赛果<br>一屏掌握</h2>

            <p>
              统一订单结构、比赛身份和用户统计，让实时数据更清晰、更可追溯。
            </p>

            <div class="hero-actions">
              <button
                class="hero-primary"
                type="button"
                @click="router.push('/orders')"
              >
                浏览实时方案
                <span>↗</span>
              </button>

              <button
                class="hero-secondary"
                type="button"
                @click="router.push('/analysis')"
              >
                查看赛事分析
              </button>
            </div>

            <div class="hero-status">
              <span><i></i> 数据链路运行中</span>
              <span>{{ platformBars.length }} 个平台返回当日聚合</span>
            </div>
          </div>

          <div class="hero-visual" aria-hidden="true">
            <div class="orbit orbit-one"></div>
            <div class="orbit orbit-two"></div>
            <div class="orbit-point point-one"></div>
            <div class="orbit-point point-two"></div>
            <img src="/football-ai-logo.png" alt="">
            <span class="visual-card visual-card-top">
              <small>今日方案</small>
              <b>{{ number(metrics.today_plans) }}</b>
            </span>
            <span class="visual-card visual-card-bottom">
              <small>未截止</small>
              <b>{{ number(metrics.unexpired_plans) }}</b>
            </span>
          </div>
        </article>

        <article class="platform-card panel">
          <header>
            <div>
              <span class="eyebrow">PLATFORM FLOW</span>
              <h3>平台投注活跃度</h3>
            </div>
            <div class="total-amount">
              <small>今日总额</small>
              <b>¥{{ compactMoney(metrics.today_amount) }}</b>
            </div>
          </header>

          <div v-if="platformBars.length" class="platform-bars">
            <div
              v-for="bar in platformBars"
              :key="bar.platform_id"
              class="bar-item"
            >
              <span class="bar-amount">¥{{ compactMoney(bar.amount) }}</span>
              <div class="bar-track">
                <i :style="{ height: bar.height + '%' }"></i>
              </div>
              <b>{{ bar.platform_name }}</b>
              <small>{{ number(bar.order_count) }} 单</small>
            </div>
          </div>

          <div v-else class="mini-empty">
            今日平台数据尚未同步
          </div>
        </article>
      </section>

      <section class="metric-row">
        <article class="metric-card panel">
          <span class="metric-icon">↗</span>
          <div>
            <small>今日方案</small>
            <strong>{{ number(metrics.today_plans) }}</strong>
            <span>当前赛事日累计发单</span>
          </div>
        </article>

        <article class="metric-card panel">
          <span class="metric-icon metric-mint">◎</span>
          <div>
            <small>今日跟单</small>
            <strong>{{ number(metrics.today_followers) }}</strong>
            <span>聚合跟单用户人次</span>
          </div>
        </article>

        <article class="metric-card panel">
          <span class="metric-icon metric-amber">✓</span>
          <div>
            <small>昨日中奖</small>
            <strong>{{ number(metrics.yesterday_wins) }}</strong>
            <span>昨日已结算中奖方案</span>
          </div>
        </article>

        <article class="metric-card panel">
          <span class="metric-icon metric-outline">¥</span>
          <div>
            <small>今日金额</small>
            <strong>¥{{ compactMoney(metrics.today_amount) }}</strong>
            <span>多平台自购金额汇总</span>
          </div>
        </article>
      </section>

      <section class="ranking-head">
        <div>
          <p class="eyebrow">TODAY LEADERBOARD</p>
          <h2>当日未截止发单排行</h2>
        </div>

        <router-link to="/users">
          查看全部发单用户 <span>↗</span>
        </router-link>
      </section>

      <section v-if="loading" class="panel loading-state">
        <div class="state-stack">
          <span class="state-symbol loading-symbol">◌</span>
          <span>正在汇总实时数据…</span>
        </div>
      </section>

      <section v-else class="ranking-layout">
        <aside class="ranking-list panel">
          <header>
            <b>发单人</b>
            <span>按自购金额排序</span>
          </header>

          <button
            v-for="person in ranking"
            :key="person.platform_id + '-' + person.user_id"
            type="button"
            :class="{ active: selectedKey === personKey(person) }"
            @mouseenter="selectPerson(person)"
            @focus="selectPerson(person)"
            @click="selectPerson(person)"
          >
            <span class="rank-index">{{ rankLabel(person.rank) }}</span>

            <img
              v-if="person.avatar_url"
              class="avatar"
              :src="person.avatar_url"
              alt=""
            >

            <span v-else class="avatar-fallback">
              {{ avatarText(person.nickname) }}
            </span>

            <span class="rank-main">
              <b>{{ person.nickname }}</b>
              <small>{{ person.platform_name }} · {{ person.order_count }} 单</small>
            </span>

            <span class="rank-money">
              <b>¥{{ compactMoney(person.amount) }}</b>
              <small>{{ number(person.followers) }} 人</small>
            </span>
          </button>

          <div v-if="!ranking.length" class="list-empty">
            今日暂无未截止订单排行
          </div>
        </aside>

        <article v-if="selected" class="user-showcase">
          <header class="showcase-head">
            <div class="showcase-user">
              <img
                v-if="selected.avatar_url"
                class="showcase-avatar"
                :src="selected.avatar_url"
                alt=""
              >

              <span v-else class="showcase-avatar-fallback">
                {{ avatarText(selected.nickname) }}
              </span>

              <div>
                <span>FEATURED SENDER</span>
                <h2>{{ selected.nickname }}</h2>
                <small>{{ selected.platform_name }} · ID {{ selected.user_id }}</small>
              </div>
            </div>

            <span class="rank-pill">NO.{{ selected.rank }}</span>
          </header>

          <div class="user-kpis">
            <article>
              <span>历史战绩</span>
              <strong>{{ selected.history_record || "0胜0负" }}</strong>
              <small>命中率 {{ percent(selected.history_hit_rate) }}</small>
            </article>
            <article>
              <span>自购金额</span>
              <strong>¥{{ money(selected.amount) }}</strong>
              <small>当日未截止</small>
            </article>
            <article>
              <span>跟单人数</span>
              <strong>{{ number(selected.followers) }}</strong>
              <small>聚合人次</small>
            </article>
            <article>
              <span>中奖金额</span>
              <strong>¥{{ money(selected.bonus) }}</strong>
              <small>平台实际派奖</small>
            </article>
          </div>

          <div class="scheme-heading">
            <div>
              <span>ACTIVE SCHEMES</span>
              <b>最近 {{ selected.orders.length }} 个未截止方案</b>
            </div>

            <button
              class="showcase-link"
              type="button"
              @click="openUser(selected)"
            >
              用户详情 ↗
            </button>
          </div>

          <div class="scheme-list">
            <article
              v-for="order in selected.orders"
              :key="order.id"
              class="scheme-card"
              tabindex="0"
              @click="router.push('/order/detail/' + order.id)"
              @keyup.enter="router.push('/order/detail/' + order.id)"
            >
              <header>
                <div>
                  <b>{{ order.pass_composition || passText(order) }}</b>
                  <span>{{ order.result }}</span>
                </div>
                <strong>¥{{ money(order.stake) }}</strong>
              </header>

              <div class="match-lines">
                <div
                  v-for="match in order.matches"
                  :key="match.id"
                  class="match-line"
                >
                  <b>{{ match.match_code || "-" }} · {{ match.home }} VS {{ match.away }}</b>
                  <span>[{{ match.play_type }}：{{ match.selection }}]</span>
                </div>
              </div>

              <footer>
                <span>SP {{ order.odds_text || "-" }}</span>
                <span>跟单 {{ number(order.follow_num) }}</span>
                <span>查看 ↗</span>
              </footer>
            </article>
          </div>
        </article>

        <article v-else class="user-showcase empty-showcase">
          <img src="/football-ai-logo.png" alt="">
          <b>等待今日方案数据</b>
          <span>平台订单写入后，排行与方案详情会在这里自动出现。</span>
        </article>
      </section>
    </template>
  </section>
</template>

<script setup>
import {
  computed,
  onMounted,
  ref
} from "vue"

import {
  useRouter
} from "vue-router"

import axios from "axios"


const router = useRouter()

const data = ref({})
const selectedKey = ref("")
const loading = ref(true)
const error = ref("")
const lastUpdated = ref("")


const metrics = computed(() => data.value.metrics || {})
const ranking = computed(() => data.value.sender_ranking || [])


const selected = computed(() => ranking.value.find(
  item => personKey(item) === selectedKey.value
) || ranking.value[0] || null)


const platformBars = computed(() => {
  const rows = data.value.platform_bets || []
  const max = Math.max(1, ...rows.map(row => Number(row.amount || 0)))

  return rows.map(row => ({
    ...row,
    height: Math.max(8, Math.round(Number(row.amount || 0) / max * 100))
  }))
})


async function load() {
  loading.value = true
  error.value = ""

  try {
    const response = await axios.get("/api/portal/dashboard")

    if (!response.data || response.data.code !== 200) {
      throw new Error("dashboard unavailable")
    }

    data.value = response.data.data || {}
    const first = (data.value.sender_ranking || [])[0]

    if (first) {
      selectedKey.value = personKey(first)
    }

    lastUpdated.value = new Date().toLocaleTimeString(
      "zh-CN",
      { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }
    )
  } catch {
    error.value = "实时数据暂时无法读取，请确认 API 服务与数据库连接状态。"
  } finally {
    loading.value = false
  }
}


function personKey(person) {
  return person.platform_id + "-" + person.user_id
}


function selectPerson(person) {
  selectedKey.value = personKey(person)
}


function openUser(person) {
  router.push("/user/detail/" + person.platform_id + "/" + person.user_id)
}


function avatarText(name) {
  return String(name || "球").slice(-1)
}


function rankLabel(rank) {
  return String(Number(rank || 0)).padStart(2, "0")
}


function number(value) {
  return Math.round(Number(value || 0)).toLocaleString("zh-CN")
}


function money(value) {
  return Number(value || 0).toLocaleString(
    "zh-CN",
    { minimumFractionDigits: 0, maximumFractionDigits: 2 }
  )
}


function compactMoney(value) {
  const amount = Number(value || 0)

  if (Math.abs(amount) >= 10000) {
    return (amount / 10000).toFixed(1) + "万"
  }

  return money(amount)
}


function percent(value) {
  return Number(value || 0).toFixed(2) + "%"
}


function passText(order) {
  const count = Number(order.bet_count || 0)
  const pass = order.pass_summary || "-"
  return count > 0 ? count + "注" + pass : pass
}


onMounted(load)
</script>

<style scoped>
.title-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.updated-time {
  margin: 0;
  color: var(--muted-2);
  font-size: 9px;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(360px, .85fr);
  gap: 18px;
}

.hero-card {
  position: relative;
  min-height: 360px;
  padding: 42px;
  border: 1px solid rgba(184, 255, 56, .32);
  border-radius: var(--radius-xl);
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(300px, .85fr);
  gap: 26px;
  overflow: hidden;
  background:
    linear-gradient(115deg, rgba(184, 255, 56, .13), transparent 43%),
    radial-gradient(circle at 72% 38%, rgba(66, 245, 197, .18), transparent 25%),
    #0f1510;
  box-shadow: var(--shadow);
}

.hero-card::after {
  content: "";
  position: absolute;
  inset: auto -100px -160px auto;
  width: 360px;
  height: 360px;
  border: 1px solid rgba(184, 255, 56, .14);
  border-radius: 50%;
}

.hero-copy {
  position: relative;
  z-index: 3;
  align-self: center;
}

.hero-overline {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: var(--lime);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: .17em;
}

.hero-overline i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--mint);
  box-shadow: 0 0 13px rgba(66, 245, 197, .72);
}

.hero-copy h2 {
  margin: 17px 0 13px;
  font-size: clamp(39px, 4vw, 62px);
  line-height: .98;
  letter-spacing: -.065em;
}

.hero-copy p {
  max-width: 560px;
  margin: 0;
  color: #9da89e;
  font-size: 13px;
  line-height: 1.8;
}

.hero-actions {
  margin-top: 27px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-primary,
.hero-secondary {
  min-height: 45px;
  border-radius: 999px;
  padding: 0 20px;
  font-size: 11px;
  font-weight: 900;
}

.hero-primary {
  border: 1px solid var(--lime);
  color: #07110b;
  background: var(--lime);
}

.hero-primary span {
  margin-left: 13px;
}

.hero-secondary {
  border: 1px solid var(--line-strong);
  color: var(--text-soft);
  background: rgba(255, 255, 255, .035);
}

.hero-status {
  margin-top: 31px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: var(--muted);
  font-size: 9px;
}

.hero-status span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.hero-status i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--mint);
}

.hero-visual {
  position: relative;
  min-height: 270px;
  display: grid;
  place-items: center;
}

.hero-visual > img {
  position: relative;
  z-index: 3;
  width: min(235px, 80%);
  filter: drop-shadow(0 24px 28px rgba(0, 0, 0, .32));
}

.orbit {
  position: absolute;
  border: 1px solid rgba(184, 255, 56, .18);
  border-radius: 50%;
}

.orbit-one {
  width: 270px;
  height: 270px;
}

.orbit-two {
  width: 320px;
  height: 155px;
  transform: rotate(-19deg);
}

.orbit-point {
  position: absolute;
  z-index: 4;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 18px rgba(184, 255, 56, .76);
}

.point-one {
  top: 38px;
  right: 47px;
}

.point-two {
  bottom: 47px;
  left: 28px;
  background: var(--mint);
}

.visual-card {
  position: absolute;
  z-index: 5;
  min-width: 105px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, .12);
  border-radius: 13px;
  background: rgba(9, 14, 10, .72);
  backdrop-filter: blur(12px);
  box-shadow: 0 12px 25px rgba(0, 0, 0, .2);
}

.visual-card small,
.visual-card b {
  display: block;
}

.visual-card small {
  color: var(--muted);
  font-size: 8px;
}

.visual-card b {
  margin-top: 3px;
  color: var(--lime);
  font-size: 17px;
}

.visual-card-top {
  top: 34px;
  left: 2px;
}

.visual-card-bottom {
  right: 0;
  bottom: 31px;
}

.platform-card {
  min-height: 360px;
  padding: 23px;
}

.platform-card > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 15px;
}

.platform-card h3 {
  margin: 6px 0 0;
  font-size: 18px;
}

.total-amount {
  text-align: right;
}

.total-amount small,
.total-amount b {
  display: block;
}

.total-amount small {
  color: var(--muted);
  font-size: 8px;
}

.total-amount b {
  margin-top: 3px;
  color: var(--lime);
  font-size: 17px;
}

.platform-bars {
  height: 255px;
  margin-top: 19px;
  display: grid;
  grid-template-columns: repeat(6, minmax(42px, 1fr));
  gap: 8px;
  align-items: end;
}

.bar-item {
  min-width: 0;
  display: grid;
  grid-template-rows: 22px 1fr 18px 14px;
  text-align: center;
}

.bar-amount {
  overflow: hidden;
  color: var(--muted);
  font-size: 7px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  height: 170px;
  display: flex;
  align-items: end;
  justify-content: center;
  border-radius: 11px;
  background:
    linear-gradient(180deg, rgba(184, 255, 56, .02), rgba(184, 255, 56, .065)),
    repeating-linear-gradient(0deg, transparent 0, transparent 30px, rgba(255, 255, 255, .035) 31px);
}

.bar-track i {
  width: 64%;
  min-height: 8px;
  border-radius: 8px 8px 3px 3px;
  background: linear-gradient(180deg, var(--lime), #6fa321);
  box-shadow: 0 0 16px rgba(184, 255, 56, .1);
}

.bar-item:nth-child(even) .bar-track i {
  background: linear-gradient(180deg, var(--mint), #218c6e);
}

.bar-item > b {
  margin-top: 4px;
  overflow: hidden;
  font-size: 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-item > small {
  color: var(--muted-2);
  font-size: 7px;
}

.mini-empty {
  height: 250px;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 10px;
}

.metric-row {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.metric-card {
  min-height: 103px;
  padding: 15px;
  display: flex;
  align-items: center;
  gap: 13px;
}

.metric-icon {
  width: 48px;
  height: 48px;
  flex: 0 0 48px;
  border-radius: 15px;
  display: grid;
  place-items: center;
  color: #07110b;
  background: var(--lime);
  font-size: 19px;
  font-weight: 900;
}

.metric-mint {
  background: var(--mint);
}

.metric-amber {
  background: var(--amber);
}

.metric-outline {
  color: var(--lime);
  border: 1px solid rgba(184, 255, 56, .32);
  background: var(--lime-soft);
}

.metric-card small,
.metric-card strong,
.metric-card div > span {
  display: block;
}

.metric-card small {
  color: var(--muted);
  font-size: 9px;
}

.metric-card strong {
  margin-top: 2px;
  color: #fff;
  font-size: 20px;
}

.metric-card div > span {
  margin-top: 3px;
  color: var(--muted-2);
  font-size: 8px;
}

.ranking-head {
  margin: 31px 0 13px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
}

.ranking-head h2 {
  margin: 6px 0 0;
  font-size: 24px;
}

.ranking-head a {
  color: var(--lime);
  font-size: 10px;
  font-weight: 900;
}

.ranking-head a span {
  margin-left: 7px;
}

.ranking-layout {
  display: grid;
  grid-template-columns: minmax(330px, .62fr) minmax(0, 1.38fr);
  gap: 16px;
}

.ranking-list {
  max-height: 620px;
  padding: 11px;
  overflow-y: auto;
}

.ranking-list > header {
  padding: 7px 9px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ranking-list > header b {
  font-size: 11px;
}

.ranking-list > header span {
  color: var(--muted-2);
  font-size: 8px;
}

.ranking-list > button {
  width: 100%;
  min-height: 69px;
  padding: 9px;
  border: 1px solid transparent;
  border-radius: 15px;
  display: grid;
  grid-template-columns: 28px 42px minmax(0, 1fr) auto;
  gap: 9px;
  align-items: center;
  color: var(--text);
  background: transparent;
  text-align: left;
  transition: border-color .17s ease, background .17s ease, transform .17s ease;
}

.ranking-list > button:hover,
.ranking-list > button.active {
  border-color: rgba(184, 255, 56, .16);
  background: var(--lime-soft);
  transform: translateX(2px);
}

.rank-index {
  color: var(--lime);
  font-size: 10px;
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.rank-main,
.rank-money {
  min-width: 0;
}

.rank-main b,
.rank-main small,
.rank-money b,
.rank-money small {
  display: block;
}

.rank-main b {
  overflow: hidden;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-main small,
.rank-money small {
  margin-top: 3px;
  color: var(--muted);
  font-size: 8px;
}

.rank-money {
  text-align: right;
}

.rank-money b {
  color: var(--lime);
  font-size: 10px;
}

.list-empty {
  min-height: 180px;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 10px;
}

.user-showcase {
  min-height: 620px;
  padding: 24px;
  border: 1px solid rgba(66, 245, 197, .28);
  border-radius: var(--radius-xl);
  color: var(--text);
  background:
    radial-gradient(circle at 92% 8%, rgba(184, 255, 56, .18), transparent 22%),
    linear-gradient(145deg, rgba(36, 72, 53, .74), rgba(14, 26, 18, .95));
  box-shadow: var(--shadow);
}

.showcase-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.showcase-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.showcase-avatar,
.showcase-avatar-fallback {
  width: 58px;
  height: 58px;
  flex: 0 0 58px;
  border-radius: 50%;
}

.showcase-avatar {
  object-fit: cover;
  border: 2px solid rgba(184, 255, 56, .34);
}

.showcase-avatar-fallback {
  display: grid;
  place-items: center;
  color: #07110b;
  background: linear-gradient(145deg, var(--mint), var(--lime));
  font-size: 20px;
  font-weight: 900;
}

.showcase-user span {
  color: var(--mint);
  font-size: 8px;
  font-weight: 900;
  letter-spacing: .15em;
}

.showcase-user h2 {
  margin: 4px 0 2px;
  font-size: 25px;
}

.showcase-user small {
  color: #9eb2a3;
  font-size: 9px;
}

.rank-pill {
  padding: 7px 12px;
  border: 1px solid rgba(184, 255, 56, .35);
  border-radius: 999px;
  color: var(--lime);
  background: rgba(184, 255, 56, .07);
  font-size: 9px;
  font-weight: 900;
}

.user-kpis {
  margin-top: 19px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 9px;
}

.user-kpis article {
  min-height: 93px;
  padding: 13px;
  border: 1px solid rgba(163, 195, 171, .16);
  border-radius: 15px;
  background: rgba(6, 13, 8, .25);
}

.user-kpis span,
.user-kpis strong,
.user-kpis small {
  display: block;
}

.user-kpis span,
.user-kpis small {
  color: #8fa391;
  font-size: 8px;
}

.user-kpis strong {
  margin: 7px 0 3px;
  font-size: 17px;
}

.scheme-heading {
  margin-top: 22px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.scheme-heading span,
.scheme-heading b {
  display: block;
}

.scheme-heading span {
  color: var(--mint);
  font-size: 8px;
  font-weight: 900;
  letter-spacing: .14em;
}

.scheme-heading b {
  margin-top: 4px;
  font-size: 12px;
}

.showcase-link {
  border: 0;
  color: var(--lime);
  background: transparent;
  font-size: 9px;
  font-weight: 900;
}

.scheme-list {
  margin-top: 11px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}

.scheme-card {
  min-width: 0;
  padding: 13px;
  border: 1px solid rgba(163, 195, 171, .16);
  border-radius: 16px;
  background: rgba(6, 13, 8, .25);
  cursor: pointer;
  transition: border-color .17s ease, transform .17s ease, background .17s ease;
}

.scheme-card:hover,
.scheme-card:focus-visible {
  border-color: rgba(184, 255, 56, .38);
  background: rgba(184, 255, 56, .055);
  transform: translateY(-2px);
}

.scheme-card > header,
.scheme-card > footer {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.scheme-card > header div b,
.scheme-card > header div span {
  display: block;
}

.scheme-card > header div span {
  margin-top: 3px;
  color: var(--amber);
  font-size: 8px;
}

.scheme-card > header > strong {
  color: var(--lime);
  font-size: 11px;
}

.match-lines {
  margin-top: 10px;
  display: grid;
  gap: 6px;
}

.match-line b,
.match-line span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.match-line b {
  font-size: 9px;
}

.match-line span {
  margin-top: 2px;
  color: #9db1a0;
  font-size: 8px;
}

.scheme-card > footer {
  margin-top: 11px;
  color: #809483;
  font-size: 8px;
}

.empty-showcase {
  display: grid;
  place-items: center;
  align-content: center;
  text-align: center;
}

.empty-showcase img {
  width: 105px;
  opacity: .78;
}

.empty-showcase b {
  margin-top: 12px;
}

.empty-showcase span {
  max-width: 340px;
  margin-top: 7px;
  color: #91a294;
  font-size: 10px;
  line-height: 1.7;
}

.loading-symbol {
  animation: spin 1.1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1260px) {
  .hero-grid,
  .ranking-layout {
    grid-template-columns: 1fr;
  }

  .metric-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 760px) {
  .title-actions {
    width: 100%;
    justify-content: space-between;
  }

  .hero-card {
    min-height: auto;
    padding: 28px 22px;
    grid-template-columns: 1fr;
  }

  .hero-visual {
    min-height: 250px;
  }

  .hero-copy h2 {
    font-size: 42px;
  }

  .metric-row,
  .user-kpis,
  .scheme-list {
    grid-template-columns: 1fr;
  }

  .ranking-head {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 480px) {
  .platform-card {
    padding: 16px;
  }

  .platform-bars {
    grid-template-columns: repeat(3, 1fr);
    height: auto;
    row-gap: 15px;
  }

  .bar-track {
    height: 110px;
  }

  .ranking-list > button {
    grid-template-columns: 25px 38px minmax(0, 1fr);
  }

  .rank-money {
    display: none;
  }

  .user-showcase {
    padding: 18px;
  }
}
</style>
