<template><div class="state-box"><div class="state-content"><span class="state-icon">!</span><h3>{{ title }}</h3><p>{{ description }}</p></div></div></template>
<script setup>defineProps({ title:{ type:String, default:"数据加载失败" }, description:{ type:String, default:"数据暂时不可用，系统会在后续访问时再次同步" } })</script>
