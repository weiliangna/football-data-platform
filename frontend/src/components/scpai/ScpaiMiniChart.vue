<template>
  <div class="scpai-mini-chart" aria-hidden="true">
    <div class="scpai-chart-stats"><span>初始 <b>{{ firstValue }}</b></span><span>当前 <b>{{ lastValue }}</b></span></div>
    <svg viewBox="0 0 320 112" preserveAspectRatio="none">
      <line v-for="line in 4" :key="line" x1="0" x2="320" :y1="line * 22" :y2="line * 22" class="gridline" />
      <polyline v-if="points" :points="points" fill="none" class="plot-line" />
      <circle v-for="(point,index) in dots" :key="index" :cx="point.x" :cy="point.y" r="3.5" class="plot-dot" />
    </svg>
    <div class="scpai-chart-time"><span>{{ labels[0] || "起始" }}</span><span>{{ labels[labels.length - 1] || "当前" }}</span></div>
  </div>
</template>
<script setup>
import { computed } from "vue"
const props=defineProps({values:{type:Array,default:()=>[]},labels:{type:Array,default:()=>[]}})
const numeric=computed(()=>props.values.map(Number).filter(Number.isFinite))
const dots=computed(()=>{const rows=numeric.value;if(!rows.length)return[];const low=Math.min(...rows),high=Math.max(...rows),range=Math.max(high-low,.01);return rows.map((value,index)=>({x:rows.length===1?160:(index/(rows.length-1))*320,y:98-((value-low)/range)*80}))})
const points=computed(()=>dots.value.map(point=>`${point.x},${point.y}`).join(" "))
const firstValue=computed(()=>numeric.value.length?numeric.value[0].toFixed(2):"--")
const lastValue=computed(()=>numeric.value.length?numeric.value[numeric.value.length-1].toFixed(2):"--")
</script>
