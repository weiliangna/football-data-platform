<template>
<section class="page-shell orders-page">

  <header class="page-title">
    <div>
      <p>SCHEME HALL</p>
      <h1>方案大厅</h1>
      <span>
        发单时间、赛事编号、球队、玩法与投注项统一展示
      </span>
    </div>
  </header>


  <section class="filters panel">

    <select v-model="platform" @change="resetLoad">
      <option value="">全部平台</option>
      <option value="1">彩站云</option>
      <option value="3">鸿瑞</option>
      <option value="2">州运宝</option>
      <option value="4">云彩</option>
    </select>

    <input
      v-model="keyword"
      placeholder="发单人 / 用户ID / 订单号 / 比赛"
      @keyup.enter="resetLoad"
    >

    <select v-model="result" @change="resetLoad">
      <option value="">全部结果</option>
      <option value="待开奖">待开奖</option>
      <option value="赢">赢</option>
      <option value="输">输</option>
    </select>

    <button class="primary-button" @click="resetLoad">
      查找方案
    </button>

  </section>


  <section class="orders-list">

    <article
      v-for="order in orders"
      :key="order.id"
      class="order-card panel"
    >

      <header>

        <div class="sender">

          <img
            v-if="order.avatar_url"
            class="avatar"
            :src="order.avatar_url"
            alt=""
          >

          <span v-else class="avatar-fallback">
            {{ avatarText(order.nickname) }}
          </span>

          <div>
            <button
              class="sender-link"
              @click="openUser(order)"
            >
              {{ order.nickname }}
            </button>

            <small>
              {{ order.platform_name }}
              · ID {{ order.user_id }}
            </small>
          </div>

        </div>


        <div class="order-meta">
          <b>
            {{ order.pass_composition || passText(order) }}
          </b>

          <span>
            {{ time(order.publish_time) }}
          </span>
        </div>


        <div class="order-money">
          <b>¥{{ money(order.stake) }}</b>
          <small>自购金额</small>
        </div>

      </header>


      <div class="scheme-lines">

        <div
          v-for="match in order.matches"
          :key="match.id"
          class="scheme-line"
        >

          <div class="match-main">
            <b>
              {{ match.match_code || '-' }}
              · {{ match.home }} VS {{ match.away }}
            </b>

            <small>
              {{ match.league || '竞彩足球' }}
            </small>
          </div>


          <div class="bet-main">
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


          <div class="score-main">
            <span>{{ match.result }}</span>
            <small>{{ scoreText(match) }}</small>
          </div>

        </div>

      </div>


      <footer>

        <div>
          <span>SP {{ order.odds_text || '-' }}</span>
          <span>跟单 {{ number(order.follow_num) }}人</span>
          <span>中奖金额 ¥{{ money(order.bonus) }}</span>
        </div>

        <button
          class="secondary-button"
          @click="openOrder(order.id)"
        >
          订单详情
        </button>

      </footer>

    </article>


    <div v-if="!orders.length" class="panel empty-state">
      暂无方案
    </div>

  </section>


  <div class="pager">

    <button
      class="secondary-button"
      :disabled="page<=1"
      @click="changePage(page-1)"
    >
      上一页
    </button>

    <span>
      第 {{ page }} / {{ pages }} 页 · {{ total }} 条
    </span>

    <button
      class="secondary-button"
      :disabled="page>=pages"
      @click="changePage(page+1)"
    >
      下一页
    </button>

  </div>

</section>
</template>


<script setup>
import {
  onMounted,
  ref
} from "vue"

import {
  useRouter
} from "vue-router"

import axios from "axios"


const router = useRouter()

const platform = ref("")
const keyword = ref("")
const result = ref("")

const orders = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)


async function load() {

  const params = {
    page: page.value,
    page_size: 30,
    keyword: keyword.value,
    result: result.value
  }

  if (platform.value) {
    params.platform_id = Number(platform.value)
  }

  const response = await axios.get(
    "/api/portal/schemes",
    {
      params
    }
  )

  if (
    response.data
    &&
    response.data.code === 200
  ) {
    orders.value = response.data.data || []
    page.value = response.data.page || 1
    pages.value = response.data.pages || 1
    total.value = response.data.total || 0
  }
}


function resetLoad() {
  page.value = 1
  load()
}


function changePage(value) {
  page.value = value
  load()
}


function openUser(order) {

  router.push(
    "/user/detail/"
    +
    order.platform_id
    +
    "/"
    +
    order.user_id
  )
}


function openOrder(id) {
  router.push("/order/detail/" + id)
}


function avatarText(name) {
  return String(name || "球").slice(-1)
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
.orders-page {
  max-width: 1420px;
  margin: 0 auto;
}

.filters {
  padding: 13px;
  display: grid;
  grid-template-columns:
    150px
    minmax(280px,1fr)
    150px
    auto;
  gap: 8px;
}

.filters select,
.filters input {
  height: 42px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0 14px;
  background: #fff;
}

.orders-list {
  margin-top: 16px;
  display: grid;
  gap: 14px;
}

.order-card {
  padding: 17px;
}

.order-card > header {
  display: grid;
  grid-template-columns:
    minmax(240px,1fr)
    auto
    auto;
  gap: 16px;
  align-items: center;
}

.sender {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sender-link {
  border: 0;
  padding: 0;
  color: var(--text);
  background: transparent;
  font-weight: 900;
}

.sender small {
  display: block;
  margin-top: 3px;
  color: var(--muted);
  font-size: 9px;
}

.order-meta,
.order-money {
  text-align: right;
}

.order-meta b,
.order-meta span,
.order-money b,
.order-money small {
  display: block;
}

.order-meta b {
  color: var(--primary);
}

.order-meta span,
.order-money small {
  margin-top: 3px;
  color: var(--muted);
  font-size: 9px;
}

.scheme-lines {
  margin-top: 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
}

.scheme-line {
  min-height: 58px;
  padding: 12px 14px;
  display: grid;
  grid-template-columns:
    minmax(320px,1.4fr)
    minmax(240px,1fr)
    minmax(140px,.6fr);
  gap: 15px;
  align-items: center;
  border-bottom: 1px solid var(--line);
}

.scheme-line:last-child {
  border-bottom: 0;
}

.match-main b,
.match-main small,
.score-main span,
.score-main small {
  display: block;
}

.match-main b {
  font-size: 13px;
}

.match-main small,
.score-main small {
  margin-top: 3px;
  color: var(--muted);
  font-size: 9px;
}

.bet-main {
  color: #4e5971;
  font-size: 12px;
}

.score-main {
  text-align: right;
}

.score-main > span {
  color: var(--primary);
  font-weight: 800;
}

.order-card > footer {
  margin-top: 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.order-card > footer > div {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  color: var(--muted);
  font-size: 10px;
}

.pager {
  margin-top: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

@media (max-width: 850px) {

  .filters {
    grid-template-columns: 1fr;
  }

  .order-card > header {
    grid-template-columns: 1fr;
  }

  .order-meta,
  .order-money {
    text-align: left;
  }

  .scheme-line {
    grid-template-columns: 1fr;
  }

  .score-main {
    text-align: left;
  }
}
</style>
