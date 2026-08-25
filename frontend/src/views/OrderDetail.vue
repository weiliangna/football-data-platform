<template>
<section class="page-shell order-detail-page">

  <header class="page-title">
    <div>
      <p>ORDER DETAIL</p>
      <h1>订单详情</h1>
      <span>
        {{ order.platform_name || '-' }}
        · {{ order.nickname || '-' }}
        · {{ order.platform_order_id || order.id || '-' }}
      </span>
    </div>

    <button
      class="secondary-button"
      @click="router.back()"
    >
      返回
    </button>
  </header>


  <section class="order-summary panel">

    <article>
      <span>发单时间</span>
      <strong>{{ time(order.publish_time) }}</strong>
    </article>

    <article>
      <span>串关</span>
      <strong>
        {{ order.pass_composition || passText(order) }}
      </strong>
    </article>

    <article>
      <span>自购金额</span>
      <strong>¥{{ money(order.stake) }}</strong>
    </article>

    <article>
      <span>跟单</span>
      <strong>{{ number(order.follow_num) }}人</strong>
    </article>

    <article>
      <span>中奖金额</span>
      <strong class="money-positive">
        ¥{{ money(order.bonus) }}
      </strong>
    </article>

  </section>


  <section class="detail-lines panel">

    <div
      v-for="match in order.matches || []"
      :key="match.id"
      class="detail-line"
    >

      <div>
        <b>
          {{ match.match_code || '-' }}
          · {{ match.home }} VS {{ match.away }}
        </b>

        <small>
          {{ match.league || '竞彩足球' }}
        </small>
      </div>


      <div>
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


      <div class="detail-score">
        <b>{{ match.result || '待开奖' }}</b>
        <small>{{ fullScore(match) }}</small>
      </div>

    </div>


    <div
      v-if="!(order.matches || []).length"
      class="empty-state"
    >
      当前订单没有拆场数据
    </div>

  </section>

</section>
</template>


<script setup>
import {
  onMounted,
  ref
} from "vue"

import {
  useRoute,
  useRouter
} from "vue-router"

import axios from "axios"


const route = useRoute()
const router = useRouter()

const order = ref({})


async function load() {

  const response = await axios.get(
    "/api/portal/order/"
    +
    route.params.id
  )

  if (
    response.data
    &&
    response.data.code === 200
  ) {
    order.value = response.data.data || {}
  }
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


function number(value) {

  return Math.round(
    Number(value || 0)
  ).toLocaleString("zh-CN")
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


function fullScore(match) {

  if (
    match.home_score===null
    ||
    match.home_score===undefined
    ||
    match.away_score===null
    ||
    match.away_score===undefined
  ) {
    return "赛果待同步"
  }

  let text = (
    "全场 "
    +
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
      " · 半场 "
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


onMounted(load)
</script>


<style scoped>
.order-detail-page {
  max-width: 1380px;
  margin: 0 auto;
}

.order-summary {
  padding: 14px;
  display: grid;
  grid-template-columns: repeat(5,1fr);
  gap: 10px;
}

.order-summary article {
  padding: 14px;
  border-radius: 15px;
  background: var(--surface-soft);
}

.order-summary span,
.order-summary strong {
  display: block;
}

.order-summary span {
  color: var(--muted);
  font-size: 9px;
}

.order-summary strong {
  margin-top: 5px;
}

.detail-lines {
  margin-top: 16px;
  overflow: hidden;
}

.detail-line {
  min-height: 66px;
  padding: 13px 15px;
  display: grid;
  grid-template-columns: minmax(330px,1.4fr) minmax(260px,1fr) 190px;
  gap: 14px;
  align-items: center;
  border-bottom: 1px solid var(--line);
}

.detail-line:last-child {
  border-bottom: 0;
}

.detail-line > div:first-child b,
.detail-line > div:first-child small,
.detail-score b,
.detail-score small {
  display: block;
}

.detail-line > div:first-child small,
.detail-score small {
  margin-top: 4px;
  color: var(--muted);
  font-size: 9px;
}

.detail-score {
  text-align: right;
}

@media (max-width: 900px) {

  .order-summary {
    grid-template-columns: repeat(2,1fr);
  }

  .detail-line {
    grid-template-columns: 1fr;
  }

  .detail-score {
    text-align: left;
  }
}
</style>
