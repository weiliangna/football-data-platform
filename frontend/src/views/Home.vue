<template>
<section class="page-shell home-page">

  <header class="page-title">
    <div>
      <p>LIVE DASHBOARD</p>
      <h1>Dashboard</h1>
      <span>
        当前赛事日 {{ data.day || '-' }} · 排行仅统计当日未截止订单
      </span>
    </div>

    <button class="secondary-button" @click="load">
      刷新数据
    </button>
  </header>


  <section class="hero-grid">

    <article class="hero-card">
      <div class="hero-copy">
        <span>FOOTBALL DATA</span>
        <h2>四平台实时方案聚合</h2>
        <p>当日方案、资金、用户与赛果集中展示</p>

        <button
          class="hero-action"
          @click="router.push('/orders')"
        >
          进入方案大厅
        </button>
      </div>

      <div class="hero-kpis">
        <div>
          <span>今日方案</span>
          <b>{{ number(metrics.today_plans) }}</b>
        </div>

        <div>
          <span>未截止</span>
          <b>{{ number(metrics.unexpired_plans) }}</b>
        </div>

        <div>
          <span>今日金额</span>
          <b>¥{{ compactMoney(metrics.today_amount) }}</b>
        </div>
      </div>
    </article>


    <article class="platform-card panel">
      <header>
        <div>
          <span>PLATFORM ACTIVITY</span>
          <h3>平台投注柱形图</h3>
        </div>

        <b>¥{{ compactMoney(metrics.today_amount) }}</b>
      </header>

      <div class="platform-bars">
        <div
          v-for="bar in platformBars"
          :key="bar.platform_id"
          class="bar-item"
        >
          <span class="bar-amount">
            ¥{{ compactMoney(bar.amount) }}
          </span>

          <div class="bar-track">
            <i :style="{height: bar.height + '%'}"></i>
          </div>

          <b>{{ bar.platform_name }}</b>
          <small>{{ bar.order_count }}单</small>
        </div>
      </div>
    </article>

  </section>


  <section class="metric-row">

    <article class="metric-card panel">
      <span class="metric-icon">↗</span>
      <div>
        <small>昨日方案</small>
        <strong>{{ number(metrics.yesterday_plans) }}</strong>
        <span>昨日全部发单</span>
      </div>
    </article>

    <article class="metric-card panel">
      <span class="metric-icon metric-win">✓</span>
      <div>
        <small>已中奖</small>
        <strong>{{ number(metrics.yesterday_wins) }}</strong>
        <span>昨日中奖方案</span>
      </div>
    </article>

    <article class="metric-card panel">
      <span class="metric-icon metric-today">◇</span>
      <div>
        <small>今日跟单人数</small>
        <strong>{{ number(metrics.today_followers) }}</strong>
        <span>当前赛事日</span>
      </div>
    </article>

  </section>


  <section class="favorite-title">
    <div>
      <p>TODAY RANKING</p>
      <h2>当日未截止发单排行</h2>
    </div>

    <span>按自购金额降序 · Hover 查看右侧方案</span>
  </section>


  <section class="ranking-layout">

    <aside class="ranking-list panel">

      <button
        v-for="person in ranking"
        :key="person.platform_id + '-' + person.user_id"
        :class="{active: selectedKey === personKey(person)}"
        @mouseenter="selectPerson(person)"
        @focus="selectPerson(person)"
        @click="selectPerson(person)"
      >
        <span class="rank-index">{{ person.rank }}</span>

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
          <small>
            {{ person.platform_name }} · {{ person.order_count }}单
          </small>
        </span>

        <span class="rank-money">
          <b>¥{{ compactMoney(person.amount) }}</b>
          <small>{{ number(person.followers) }}人</small>
        </span>
      </button>

      <div v-if="!ranking.length" class="empty-state">
        今日暂无未截止订单排行
      </div>

    </aside>


    <article v-if="selected" class="user-showcase">

      <div class="showcase-head">
        <div>
          <span class="showcase-label">发单人</span>

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
              <h2>{{ selected.nickname }}</h2>
              <small>
                {{ selected.platform_name }} · ID {{ selected.user_id }}
              </small>
            </div>
          </div>
        </div>

        <span class="no-pill">NO.{{ selected.rank }}</span>
      </div>


      <div class="user-kpis">

        <article>
          <span>历史战绩</span>
          <strong>{{ selected.history_record }}</strong>
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
          <small>人次</small>
        </article>

        <article>
          <span>中奖金额</span>
          <strong>¥{{ money(selected.bonus) }}</strong>
          <small>平台实际派奖</small>
        </article>

      </div>


      <div class="scheme-heading">
        <div>
          <span>注数串关 · 方案详情</span>
          <b>最近 {{ selected.orders.length }} 个未截止方案</b>
        </div>

        <router-link to="/orders">
          进入方案大厅 →
        </router-link>
      </div>


      <div class="scheme-list">

        <article
          v-for="order in selected.orders"
          :key="order.id"
          class="scheme-card"
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
              <b>
                {{ match.match_code || '-' }}
                · {{ match.home }} VS {{ match.away }}
              </b>

              <span>
                [{{ match.play_type }}：{{ match.selection }}]
              </span>
            </div>
          </div>

          <footer>
            <span>SP {{ order.odds_text || '-' }}</span>
            <span>跟单 {{ number(order.follow_num) }}</span>
          </footer>
        </article>

      </div>

    </article>


    <article v-else class="user-showcase empty-state">
      将鼠标移动到左侧发单人查看详情
    </article>

  </section>

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


const metrics = computed(() => data.value.metrics || {})
const ranking = computed(() => data.value.sender_ranking || [])


const selected = computed(() => {

  return (
    ranking.value.find(
      item => personKey(item) === selectedKey.value
    )
    ||
    ranking.value[0]
    ||
    null
  )
})


const platformBars = computed(() => {

  const rows = data.value.platform_bets || []

  const max = Math.max(
    1,
    ...rows.map(
      row => Number(row.amount || 0)
    )
  )

  return rows.map(
    row => ({
      ...row,
      height: Math.max(
        10,
        Math.round(
          Number(row.amount || 0) / max * 100
        )
      )
    })
  )
})


async function load() {

  const response = await axios.get(
    "/api/portal/dashboard"
  )

  if (
    response.data
    &&
    response.data.code === 200
  ) {
    data.value = response.data.data || {}

    const first = (
      data.value.sender_ranking
      ||
      []
    )[0]

    if (first) {
      selectedKey.value = personKey(first)
    }
  }
}


function personKey(person) {
  return person.platform_id + "-" + person.user_id
}


function selectPerson(person) {
  selectedKey.value = personKey(person)
}


function avatarText(name) {
  return String(name || "球").slice(-1)
}


function number(value) {

  return Math.round(
    Number(value || 0)
  ).toLocaleString("zh-CN")
}


function money(value) {

  return Number(
    value || 0
  ).toLocaleString(
    "zh-CN",
    {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    }
  )
}


function compactMoney(value) {

  const n = Number(value || 0)

  if (Math.abs(n) >= 10000) {
    return (n / 10000).toFixed(1) + "万"
  }

  return money(n)
}


function percent(value) {
  return Number(value || 0).toFixed(2) + "%"
}


function passText(order) {

  const count = Number(order.bet_count || 0)
  const pass = order.pass_summary || "-"

  return count > 0
    ? count + "注" + pass
    : pass
}


onMounted(load)
</script>


<style scoped>
.home-page {
  max-width: 1500px;
  margin: 0 auto;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0,1.45fr) minmax(330px,.95fr);
  gap: 20px;
}

.hero-card {
  min-height: 260px;
  padding: 28px;
  border-radius: 26px;
  display: grid;
  grid-template-columns: minmax(0,1.3fr) minmax(260px,.8fr);
  gap: 20px;
  color: #fff;
  background:
    radial-gradient(circle at 75% 20%, rgba(255,255,255,.20), transparent 24%),
    linear-gradient(135deg,#706ce6,#9a96f4);
  box-shadow: 0 18px 36px rgba(91,86,211,.18);
  overflow: hidden;
}

.hero-copy > span {
  font-size: 11px;
  letter-spacing: 1.5px;
  opacity: .82;
}

.hero-copy h2 {
  max-width: 470px;
  margin: 11px 0 8px;
  font-size: clamp(30px,3vw,45px);
  line-height: 1.05;
}

.hero-copy p {
  margin: 0;
  color: rgba(255,255,255,.80);
}

.hero-action {
  margin-top: 26px;
  border: 0;
  border-radius: 999px;
  padding: 10px 20px;
  color: #fff;
  background: rgba(38,36,104,.78);
  font-weight: 800;
}

.hero-kpis {
  align-self: center;
  display: grid;
  gap: 10px;
}

.hero-kpis div {
  padding: 13px 16px;
  border: 1px solid rgba(255,255,255,.28);
  border-radius: 16px;
  background: rgba(255,255,255,.12);
}

.hero-kpis span,
.hero-kpis b {
  display: block;
}

.hero-kpis span {
  font-size: 10px;
  opacity: .78;
}

.hero-kpis b {
  margin-top: 4px;
  font-size: 21px;
}

.platform-card {
  padding: 22px;
}

.platform-card header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.platform-card header span {
  color: var(--primary);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 1.4px;
}

.platform-card header h3 {
  margin: 5px 0 0;
  font-size: 18px;
}

.platform-card header > b {
  color: var(--primary);
}

.platform-bars {
  height: 170px;
  margin-top: 17px;
  display: grid;
  grid-template-columns: repeat(4,1fr);
  gap: 12px;
  align-items: end;
}

.bar-item {
  display: grid;
  grid-template-rows: 18px 1fr 18px 13px;
  text-align: center;
}

.bar-amount {
  color: var(--muted);
  font-size: 9px;
}

.bar-track {
  height: 105px;
  display: flex;
  align-items: end;
  justify-content: center;
  border-radius: 18px;
  background: #f2f2fb;
}

.bar-track i {
  width: 65%;
  min-height: 10px;
  border-radius: 14px 14px 5px 5px;
  background:
    repeating-linear-gradient(
      135deg,
      #6e69e4 0,
      #6e69e4 5px,
      #847ff0 5px,
      #847ff0 9px
    );
}

.bar-item b {
  margin-top: 4px;
  font-size: 10px;
}

.bar-item small {
  color: var(--muted);
  font-size: 8px;
}

.metric-row {
  margin-top: 20px;
  display: grid;
  grid-template-columns: repeat(3,1fr);
  gap: 20px;
}

.metric-card {
  min-height: 100px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.metric-icon {
  width: 52px;
  height: 52px;
  flex: 0 0 52px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  font-size: 21px;
  font-weight: 900;
}

.metric-win {
  color: var(--red);
  background: #ffe8ed;
}

.metric-today {
  color: #4e76c9;
  background: #e8f2ff;
}

.metric-card small,
.metric-card strong,
.metric-card div > span {
  display: block;
}

.metric-card small {
  color: var(--muted);
}

.metric-card strong {
  margin-top: 2px;
  font-size: 20px;
}

.metric-card div > span {
  margin-top: 4px;
  color: var(--primary);
  font-size: 9px;
}

.favorite-title {
  margin: 28px 0 13px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.favorite-title p {
  margin: 0;
  color: var(--primary);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 1.5px;
}

.favorite-title h2 {
  margin: 5px 0 0;
  font-size: 23px;
}

.favorite-title > span {
  color: var(--muted);
  font-size: 11px;
}

.ranking-layout {
  display: grid;
  grid-template-columns: minmax(320px,.62fr) minmax(0,1.55fr);
  gap: 18px;
}

.ranking-list {
  max-height: 590px;
  padding: 12px;
  overflow-y: auto;
}

.ranking-list button {
  width: 100%;
  min-height: 68px;
  padding: 10px;
  border: 0;
  border-radius: 18px;
  display: grid;
  grid-template-columns: 28px 42px minmax(0,1fr) auto;
  align-items: center;
  gap: 9px;
  color: var(--text);
  background: transparent;
  text-align: left;
  transition: .17s ease;
}

.ranking-list button:hover,
.ranking-list button.active {
  background: var(--surface-soft);
  transform: translateX(2px);
}

.ranking-list button.active {
  box-shadow: inset 3px 0 var(--primary);
}

.rank-index {
  color: var(--primary);
  font-weight: 900;
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
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-main small,
.rank-money small {
  margin-top: 3px;
  color: var(--muted);
  font-size: 9px;
}

.rank-money {
  text-align: right;
}

.rank-money b {
  color: var(--primary);
  font-size: 11px;
}

.user-showcase {
  min-height: 590px;
  padding: 22px;
  border-radius: 25px;
  color: #153049;
  background: linear-gradient(135deg,#d8edf9,#a9cce0);
  box-shadow: var(--shadow);
}

.showcase-head {
  display: flex;
  justify-content: space-between;
}

.showcase-label {
  color: #54758e;
  font-size: 10px;
}

.showcase-user {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.showcase-avatar,
.showcase-avatar-fallback {
  width: 52px;
  height: 52px;
  border-radius: 50%;
}

.showcase-avatar {
  object-fit: cover;
  border: 2px solid rgba(255,255,255,.7);
}

.showcase-avatar-fallback {
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(135deg,var(--primary),#8e89ee);
  font-weight: 900;
}

.showcase-user h2 {
  margin: 0;
  font-size: 27px;
}

.showcase-user small {
  color: #58758a;
}

.no-pill {
  height: fit-content;
  border: 1px solid rgba(255,255,255,.55);
  border-radius: 999px;
  padding: 7px 12px;
  color: #fff;
  font-size: 10px;
}

.user-kpis {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(4,1fr);
  gap: 8px;
}

.user-kpis article {
  min-height: 96px;
  padding: 14px;
  border: 1px solid rgba(255,255,255,.38);
  border-radius: 16px;
  background: rgba(255,255,255,.18);
}

.user-kpis span,
.user-kpis strong,
.user-kpis small {
  display: block;
}

.user-kpis span,
.user-kpis small {
  color: #58758a;
  font-size: 9px;
}

.user-kpis strong {
  margin: 7px 0 4px;
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
  color: #5b7b91;
  font-size: 9px;
}

.scheme-heading b {
  margin-top: 4px;
}

.scheme-heading a {
  color: #29465c;
  text-decoration: none;
  font-size: 10px;
  font-weight: 900;
}

.scheme-list {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2,minmax(0,1fr));
  gap: 9px;
}

.scheme-card {
  padding: 13px;
  border: 1px solid rgba(255,255,255,.40);
  border-radius: 17px;
  background: rgba(255,255,255,.20);
}

.scheme-card header {
  display: flex;
  justify-content: space-between;
}

.scheme-card header div b,
.scheme-card header div span {
  display: block;
}

.scheme-card header div span {
  margin-top: 3px;
  color: #58758a;
  font-size: 9px;
}

.scheme-card header > strong {
  font-size: 11px;
}

.match-lines {
  margin-top: 10px;
  display: grid;
  gap: 6px;
}

.match-line b {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10px;
}

.match-line span {
  display: block;
  margin-top: 2px;
  color: #395b73;
  font-size: 9px;
  line-height: 1.45;
}

.scheme-card footer {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  color: #58758a;
  font-size: 8px;
}

@media (max-width: 1100px) {

  .hero-grid,
  .ranking-layout {
    grid-template-columns: 1fr;
  }

  .metric-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {

  .hero-card {
    grid-template-columns: 1fr;
  }

  .user-kpis,
  .scheme-list {
    grid-template-columns: 1fr;
  }
}
</style>
