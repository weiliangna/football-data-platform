<template>
  <div class="skeleton-state" :class="type" aria-label="数据加载中" aria-busy="true">
    <template v-if="type === 'cards'">
      <div v-for="n in count" :key="n" class="skeleton-card"><i class="skeleton"></i><b class="skeleton"></b><span class="skeleton"></span></div>
    </template>
    <template v-else>
      <div v-for="n in count" :key="n" class="skeleton-row"><i class="skeleton"></i><b class="skeleton"></b><span class="skeleton"></span></div>
    </template>
  </div>
</template>
<script setup>
defineProps({ type: { type: String, default: "rows" }, count: { type: Number, default: 5 } })
</script>
<style scoped>
.skeleton-state.cards { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.skeleton-card { min-height:118px; padding:18px; border:1px solid var(--border); border-radius:var(--radius-lg); background:#fff; }
.skeleton-card i,.skeleton-card b,.skeleton-card span { display:block; }
.skeleton-card i { width:34px; height:9px; }
.skeleton-card b { width:58%; height:30px; margin-top:16px; }
.skeleton-card span { width:76%; height:9px; margin-top:12px; }
.skeleton-row { min-height:62px; padding:14px; display:grid; grid-template-columns:42px minmax(120px,.8fr) 1.5fr; gap:14px; align-items:center; border-bottom:1px solid #eeeeea; background:#fff; }
.skeleton-row i { width:40px; height:40px; border-radius:50%; }
.skeleton-row b,.skeleton-row span { height:11px; }
@media(max-width:767px){.skeleton-state.cards{grid-template-columns:repeat(2,1fr)}}
@media(max-width:479px){.skeleton-state.cards{grid-template-columns:1fr}}
</style>
