<template>
  <div v-if="rows.length" class="activity-chart">
    <div class="chart-area">
      <div class="grid-lines"><i v-for="n in 5" :key="n"></i></div>
      <svg viewBox="0 0 1000 240" preserveAspectRatio="none" role="img" aria-label="各平台方案数量折线图">
        <defs><linearGradient id="activity-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d9ff35" stop-opacity=".36"/><stop offset="1" stop-color="#d9ff35" stop-opacity="0"/></linearGradient></defs>
        <path :d="areaPath" fill="url(#activity-fill)" />
        <path :d="linePath" fill="none" stroke="#748711" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
        <g v-for="point in points" :key="point.id"><circle :cx="point.x" :cy="point.y" r="7" fill="#fff" stroke="#242426" stroke-width="4" vector-effect="non-scaling-stroke"><title>{{ point.name }}：{{ point.count }} 个方案，自购 ¥{{ money(point.amount) }}，跟单 {{ point.followers }} 人</title></circle></g>
      </svg>
    </div>
    <div class="chart-labels"><div v-for="row in rows" :key="row.platform_id"><b>{{ row.platform_name || ('平台 ' + row.platform_id) }}</b><span>{{ number(row.order_count) }} 个方案</span></div></div>
  </div>
  <EmptyState v-else title="暂无平台活跃数据" description="今日平台统计尚未返回，不展示推测趋势" />
</template>
<script setup>
import { computed } from "vue"
import EmptyState from "../ui/EmptyState.vue"
const props = defineProps({ rows:{type:Array,default:()=>[]} })
const points = computed(() => { const max=Math.max(1,...props.rows.map(r=>Number(r.order_count||0))); const gap=props.rows.length>1?880/(props.rows.length-1):0; return props.rows.map((r,i)=>({id:r.platform_id,name:r.platform_name,count:Number(r.order_count||0),amount:Number(r.amount||0),followers:Number(r.followers||0),x:60+i*gap,y:205-(Number(r.order_count||0)/max)*165})) })
const linePath = computed(() => points.value.map((p,i)=>(i?"L":"M")+p.x+","+p.y).join(" "))
const areaPath = computed(() => points.value.length ? linePath.value+" L "+points.value.at(-1).x+",220 L "+points.value[0].x+",220 Z" : "")
function number(v){return Math.round(Number(v||0)).toLocaleString("zh-CN")}
function money(v){return Number(v||0).toLocaleString("zh-CN",{maximumFractionDigits:2})}
</script>
<style scoped>
.activity-chart{margin-top:18px}.chart-area{position:relative;height:250px}.grid-lines{position:absolute;inset:10px 0 20px;display:flex;flex-direction:column;justify-content:space-between}.grid-lines i{display:block;border-top:1px solid #eeeeea}.chart-area svg{position:relative;width:100%;height:100%;overflow:visible}.chart-labels{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;text-align:center}.chart-labels b,.chart-labels span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.chart-labels b{font-size:11px}.chart-labels span{margin-top:3px;color:var(--text-muted);font-size:10px}@media(max-width:700px){.chart-labels{grid-template-columns:repeat(3,1fr);row-gap:10px}.chart-area{height:215px}}
</style>
