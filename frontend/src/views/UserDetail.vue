<template>
<section class="page-shell user-detail-page">

  <header class="profile-hero">

    <div class="profile-main">

      <img
        v-if="user.avatar_url"
        class="profile-avatar"
        :src="user.avatar_url"
        alt=""
      >

      <span v-else class="profile-avatar-fallback">
        {{ avatarText(user.nickname) }}
      </span>

      <div>
        <span>发单人</span>
        <h1>{{ user.nickname || '用户详情' }}</h1>
        <small>
          {{ user.platform_name }} · ID {{ user.user_id }}
        </small>
      </div>

    </div>

    <button
      class="secondary-button"
      @click="router.back()"
    >
      返回
    </button>

  </header>


  <section class="profile-kpis">

    <article>
      <span>历史战绩</span>
      <strong>
        {{ user.win_orders || 0 }}胜{{ user.lose_orders || 0 }}负
      </strong>
      <small>
        命中率 {{ percent(user.hit_rate) }}
      </small>
    </article>

    <article>
      <span>自购金额</span>
      <strong>¥{{ money(user.total_stake) }}</strong>
      <small>累计投注</small>
    </article>

    <article>
      <span>跟单人数</span>
      <strong>{{ number(user.follow_num) }}</strong>
      <small>累计人次</small>
    </article>

    <article>
      <span>累计盈利</span>
      <strong
        :class="
          Number(user.total_profit || 0) >= 0
          ? 'money-positive'
          : 'money-negative'
        "
      >
        {{ profit(user.total_profit) }}
      </strong>
      <small>ROI {{ percent(user.roi) }}</small>
    </article>

  </section>


  <section class="history-head">
    <div>
      <p>HISTORY ORDERS</p>
      <h2>历史发单</h2>
    </div>

    <span>赛果同步后，命中的投注内容自动标红</span>
  </section>


  <section class="history-list">

    <article
      v-for="order in orders"
      :key="order.id"
      class="history-order panel"
    >

      <header>
        <div>
          <b>{{ order.pass_composition || passText(order) }}</b>
          <span>{{ time(order.publish_time) }}</span>
        </div>

        <div class="history-money">
          <strong>¥{{ money(order.stake) }}</strong>
          <small>自购</small>
        </div>

        <div class="history-money bonus">
          <strong>¥{{ money(order.bonus) }}</strong>
          <small>中奖金额</small>
        </div>
      </header>


      <div class="history-lines">

        <div
          v-for="match in order.matches"
          :key="match.id"
          class="history-line"
        >

          <div>
            <b>
              {{ match.match_code || '-' }}
              · {{ match.home }} VS {{ match.away }}
            </b>

            <small>{{ match.league || '竞彩足球' }}</small>
          </div>


          <div class="history-bet">
            <span>{{ match.play_type }}：</span>

            <b
              :class="{
                'option-win': match.result==='赢',
                'option-loss': match.result==='输',
                'option-pending': match.result==='待开奖'
              }"
            >
              {{ match.selection }}
            </b>
          </div>


          <div class="history-score">
            <b>{{ match.result }}</b>
            <small>{{ scoreText(match) }}</small>
          </div>

        </div>

      </div>


      <footer>
        <span>SP {{ order.odds_text || '-' }}</span>
        <span>跟单 {{ number(order.follow_num) }}人</span>

        <button
          class="secondary-button"
          @click="router.push('/order/detail/' + order.id)"
        >
          订单详情
        </button>
      </footer>

    </article>

  </section>

</section>
</template>


<script setup>
import {
  onMounted,
  ref,
  watch
} from "vue"

import {
  useRoute,
  useRouter
} from "vue-router"

import axios from "axios"


const route = useRoute()
const router = useRouter()

const user = ref({})
const orders = ref([])


async function load() {

  const response = await axios.get(
    "/api/portal/user/"
    +
    route.params.platform
    +
    "/"
    +
    route.params.id
  )

  if (
    response.data
    &&
    response.data.code === 200
  ) {
    user.value = response.data.data.user || {}
    orders.value = response.data.data.orders || []
  }
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
      maximumFractionDigits: 2
    }
  )
}


function percent(value) {
  return Number(value || 0).toFixed(2) + "%"
}


function profit(value) {

  const n = Number(value || 0)

  if (n > 0) {
    return "+¥" + money(n)
  }

  if (n < 0) {
    return "-¥" + money(Math.abs(n))
  }

  return "¥0"
}


function time(value) {

  if (!value) {
    return "-"
  }

  return String(value)
    .replace("T"," ")
    .replace("Z","")
}


function passText(order) {

  const count = Number(order.bet_count || 0)
  const pass = order.pass_summary || "-"

  return count > 0
    ? count + "注" + pass
    : pass
}


function scoreText(match) {

  if (
    match.home_score===null
    ||
    match.home_score===undefined
    ||
    match.away_score===null
    ||
    match.away_score===undefined
  ) {
    return "待同步"
  }

  let text = (
    match.home_score
    +
    ":"
    +
    match.away_score
  )

  if (
    match.half_home_score!==null
    &&
    match.half_home_score!==undefined
    &&
    match.half_away_score!==null
    &&
    match.half_away_score!==undefined
  ) {
    text += (
      " / 半 "
      +
      match.half_home_score
      +
      ":"
      +
      match.half_away_score
    )
  }

  return text
}


watch(
  () => route.fullPath,
  load
)

onMounted(load)
</script>


<style scoped>
.user-detail-page {
  max-width: 1420px;
  margin: 0 auto;
}

.profile-hero {
  min-height: 185px;
  padding: 28px;
  border-radius: 26px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  color: #153049;
  background: linear-gradient(135deg,#dceef8,#a8c9dc);
  box-shadow: var(--shadow);
}

.profile-main {
  display: flex;
  align-items: center;
  gap: 14px;
}

.profile-avatar,
.profile-avatar-fallback {
  width: 62px;
  height: 62px;
  border-radius: 50%;
}

.profile-avatar {
  object-fit: cover;
  border: 3px solid rgba(255,255,255,.65);
}

.profile-avatar-fallback {
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--primary);
  font-size: 21px;
  font-weight: 900;
}

.profile-main span,
.profile-main small {
  color: #58758a;
  font-size: 10px;
}

.profile-main h1 {
  margin: 5px 0 4px;
  font-size: 31px;
}

.profile-kpis {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(4,1fr);
  gap: 12px;
}

.profile-kpis article {
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: #fff;
  box-shadow: var(--shadow);
}

.profile-kpis span,
.profile-kpis strong,
.profile-kpis small {
  display: block;
}

.profile-kpis span,
.profile-kpis small {
  color: var(--muted);
  font-size: 9px;
}

.profile-kpis strong {
  margin: 6px 0 4px;
  font-size: 18px;
}

.history-head {
  margin: 26px 0 12px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.history-head p {
  margin: 0;
  color: var(--primary);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 1.5px;
}

.history-head h2 {
  margin: 4px 0 0;
}

.history-head > span {
  color: var(--muted);
  font-size: 10px;
}

.history-list {
  display: grid;
  gap: 13px;
}

.history-order {
  padding: 16px;
}

.history-order > header {
  display: grid;
  grid-template-columns: minmax(0,1fr) 140px 140px;
  gap: 12px;
  align-items: center;
}

.history-order > header div:first-child b,
.history-order > header div:first-child span {
  display: block;
}

.history-order > header div:first-child span {
  margin-top: 4px;
  color: var(--muted);
  font-size: 9px;
}

.history-money {
  text-align: right;
}

.history-money strong,
.history-money small {
  display: block;
}

.history-money small {
  color: var(--muted);
  font-size: 9px;
}

.bonus strong {
  color: var(--red);
}

.history-lines {
  margin-top: 12px;
  border: 1px solid var(--line);
  border-radius: 15px;
  overflow: hidden;
}

.history-line {
  padding: 11px 13px;
  display: grid;
  grid-template-columns: minmax(320px,1.4fr) minmax(240px,1fr) 140px;
  gap: 12px;
  align-items: center;
  border-bottom: 1px solid var(--line);
}

.history-line:last-child {
  border-bottom: 0;
}

.history-line > div:first-child b,
.history-line > div:first-child small,
.history-score b,
.history-score small {
  display: block;
}

.history-line > div:first-child small,
.history-score small {
  margin-top: 3px;
  color: var(--muted);
  font-size: 9px;
}

.history-score {
  text-align: right;
}

.history-order > footer {
  margin-top: 11px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 13px;
  color: var(--muted);
  font-size: 9px;
}

@media (max-width: 850px) {

  .profile-kpis {
    grid-template-columns: repeat(2,1fr);
  }

  .history-order > header,
  .history-line {
    grid-template-columns: 1fr;
  }

  .history-money,
  .history-score {
    text-align: left;
  }
}
</style>
