<template><div class="state-box"><div class="state-content"><span class="state-icon">○</span><h3>{{ title }}</h3><p>{{ description }}</p></div></div></template>
<script setup>defineProps({ title: { type:String, default:"暂无数据" }, description: { type:String, default:"当前条件下没有可展示的数据" } })</script>
