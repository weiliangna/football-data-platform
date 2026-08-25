<template>
<section class="page-shell results-page">

  <header class="page-title">
    <div>
      <p>RESULT ARCHIVE</p>
      <h1>赛果统计</h1>
      <span>统一展示标准化球队名称、全场与半场比分</span>
    </div>

    <button class="secondary-button" @click="load">
      刷新赛果
    </button>
  </header>


  <section class="results-panel panel">

    <table>

      <thead>
        <tr>
          <th>场次</th>
          <th>对阵</th>
          <th>全场</th>
          <th>半场</th>
          <th>结束时间</th>
        </tr>
      </thead>

      <tbody>

        <tr
          v-for="item in rows"
          :key="item.id"
        >
          <td>{{ item.match_code || '-' }}</td>

          <td>
            <b>{{ item.home }} VS {{ item.away }}</b>
          </td>

          <td>
            <strong class="score">
              {{ item.home_score }} : {{ item.away_score }}
            </strong>
          </td>

          <td>
            {{
              item.half_home_score===null
              ||
              item.half_home_score===undefined
              ?
              '-'
              :
              item.half_home_score
              +
              ':'
              +
              item.half_away_score
            }}
          </td>

          <td>{{ time(item.finished_time) }}</td>
        </tr>

      </tbody>

    </table>


    <div v-if="!rows.length" class="empty-state">
      暂无赛果
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

    <span>第 {{ page }} / {{ pages }} 页</span>

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

import axios from "axios"


const rows = ref([])
const page = ref(1)
const pages = ref(1)


async function load() {

  const response = await axios.get(
    "/api/portal/results",
    {
      params: {
        page: page.value,
        page_size: 50
      }
    }
  )

  if (
    response.data
    &&
    response.data.code === 200
  ) {
    rows.value = response.data.data || []
    pages.value = response.data.pages || 1
  }
}


function changePage(value) {
  page.value = value
  load()
}


function time(value) {

  if (!value) {
    return "-"
  }

  return String(value)
    .replace("T"," ")
    .replace("Z","")
}


onMounted(load)
</script>


<style scoped>
.results-page {
  max-width: 1350px;
  margin: 0 auto;
}

.results-panel {
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 850px;
  border-collapse: collapse;
}

th,
td {
  padding: 14px;
  border-bottom: 1px solid var(--line);
  text-align: center;
}

th {
  color: #667188;
  background: #f8f8ff;
}

.score {
  color: var(--primary);
  font-size: 18px;
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}
</style>
