<template>
<section class="page-shell users-page">

  <header class="page-title">
    <div>
      <p>USER CENTER</p>
      <h1>用户中心</h1>
      <span>六平台用户统一排行，用户名前显示已抓取头像</span>
    </div>
  </header>


  <section class="user-filters panel">

    <select v-model="platform" @change="resetLoad">
      <option value="">全部平台</option>
      <option value="1">彩站云</option>
      <option value="3">鸿瑞</option>
      <option value="2">州运宝</option>
      <option value="4">云彩</option>
      <option value="5">好店主</option>
      <option value="6">启示录</option>
    </select>

    <input
      v-model="keyword"
      placeholder="用户名 / 用户ID"
      @keyup.enter="resetLoad"
    >

    <select v-model="sort" @change="resetLoad">
      <option value="score">综合分</option>
      <option value="orders">发单数</option>
      <option value="hit">命中率</option>
      <option value="profit">盈利</option>
      <option value="roi">ROI</option>
      <option value="follow">跟单人数</option>
    </select>

    <button class="primary-button" @click="resetLoad">
      查询
    </button>

  </section>


  <section class="users-panel panel">

    <table>

      <thead>
        <tr>
          <th>排名</th>
          <th>用户</th>
          <th>平台</th>
          <th>发单</th>
          <th>命中率</th>
          <th>自购金额</th>
          <th>跟单人数</th>
          <th>盈利</th>
          <th>ROI</th>
          <th>综合分</th>
        </tr>
      </thead>

      <tbody>

        <tr
          v-for="item in users"
          :key="item.platform_id + '-' + item.user_id"
          @click="openUser(item)"
        >
          <td>{{ item.rank }}</td>

          <td>
            <div class="user-name">

              <img
                v-if="item.avatar_url"
                class="avatar"
                :src="item.avatar_url"
                alt=""
              >

              <span v-else class="avatar-fallback">
                {{ avatarText(item.nickname) }}
              </span>

              <div>
                <b>{{ item.nickname }}</b>
                <small>ID {{ item.user_id }}</small>
              </div>

            </div>
          </td>

          <td>{{ item.platform_name }}</td>
          <td>{{ item.total_orders }}</td>
          <td>{{ percent(item.hit_rate) }}</td>
          <td>¥{{ money(item.total_stake) }}</td>
          <td>{{ number(item.follow_num) }}</td>

          <td
            :class="
              Number(item.total_profit) >= 0
              ? 'money-positive'
              : 'money-negative'
            "
          >
            {{ profit(item.total_profit) }}
          </td>

          <td>{{ percent(item.roi) }}</td>

          <td>
            <b class="score">
              {{ Number(item.expert_score || 0).toFixed(2) }}
            </b>
          </td>
        </tr>

      </tbody>

    </table>

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
      第 {{ page }} / {{ pages }} 页
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
const sort = ref("score")

const users = ref([])
const page = ref(1)
const pages = ref(1)


async function load() {

  const params = {
    keyword: keyword.value,
    sort: sort.value,
    page: page.value,
    page_size: 30
  }

  if (platform.value) {
    params.platform_id = Number(platform.value)
  }

  const response = await axios.get(
    "/api/portal/users",
    {
      params
    }
  )

  if (
    response.data
    &&
    response.data.code === 200
  ) {
    users.value = response.data.data || []
    page.value = response.data.page || 1
    pages.value = response.data.pages || 1
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


function openUser(item) {

  router.push(
    "/user/detail/"
    +
    item.platform_id
    +
    "/"
    +
    item.user_id
  )
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


onMounted(load)
</script>


<style scoped>
.users-page {
  max-width: 1450px;
  margin: 0 auto;
}

.user-filters {
  padding: 13px;
  display: grid;
  grid-template-columns: 160px minmax(280px,1fr) 170px auto;
  gap: 8px;
}

.user-filters select,
.user-filters input {
  height: 42px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0 14px;
  background: #fff;
}

.users-panel {
  margin-top: 16px;
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 1120px;
  border-collapse: collapse;
}

th,
td {
  padding: 13px;
  border-bottom: 1px solid var(--line);
  text-align: center;
}

th {
  color: #657187;
  background: #f7f7ff;
}

tbody tr {
  cursor: pointer;
}

tbody tr:hover {
  background: #fafaff;
}

.user-name {
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
}

.user-name b,
.user-name small {
  display: block;
}

.user-name small {
  margin-top: 3px;
  color: var(--muted);
  font-size: 9px;
}

.score {
  color: var(--primary);
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}

@media (max-width: 820px) {

  .user-filters {
    grid-template-columns: 1fr;
  }
}
</style>
