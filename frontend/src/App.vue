<template>

<div class="app-shell">

    <header class="top-shell">

        <router-link
            class="brand"
            to="/"
        >

            <span class="brand-ball">
                ⚽
            </span>


            <div>

                <b>
                    足球数据中心
                </b>

                <small>
                    FOOTBALL DATA HUB
                </small>

            </div>

        </router-link>


        <nav class="top-nav">

            <router-link
                v-for="item in navigation"
                :key="item.key"
                :to="item.to"
                :class="{
                    active:
                        activeNav
                        ===
                        item.key
                }"
            >
                {{ item.name }}
            </router-link>

        </nav>


        <div class="top-tools">

            <div class="clock">

                <b>
                    {{ dateText }}
                </b>

                <span>
                    {{ timeText }}
                </span>

            </div>


            <button
                class="round-tool"
                @click="reload"
                title="刷新"
            >
                ↻
            </button>

        </div>

    </header>


    <main class="page-container">

        <router-view />

    </main>

</div>

</template>


<script setup>

import {
    computed,
    onMounted,
    onUnmounted,
    ref
}
from "vue"


import {
    useRoute
}
from "vue-router"


const route = useRoute()
const now = ref(new Date())
let timer = null


const navigation = [
    {
        key: "dashboard",
        name: "实时看板",
        to: "/"
    },
    {
        key: "schemes",
        name: "方案大厅",
        to: "/orders"
    },
    {
        key: "analysis",
        name: "赛事分析",
        to: "/analysis"
    },
    {
        key: "heatmap",
        name: "投注热力图",
        to: "/heatmap"
    },
    {
        key: "results",
        name: "赛果统计",
        to: "/results"
    },
    {
        key: "users",
        name: "用户中心",
        to: "/users"
    }
]


const activeNav = computed(() => {

    const path = route.path

    if (path === "/") {
        return "dashboard"
    }

    if (
        path === "/orders"
        ||
        path.includes("/order/detail/")
    ) {
        return "schemes"
    }

    if (path === "/analysis") {
        return "analysis"
    }

    if (path === "/heatmap") {
        return "heatmap"
    }

    if (path === "/results") {
        return "results"
    }

    if (
        path === "/users"
        ||
        path.includes("/user/detail/")
    ) {
        return "users"
    }

    return ""
})


const dateText = computed(() => {

    return now.value.toLocaleDateString(
        "zh-CN",
        {
            year: "numeric",
            month: "2-digit",
            day: "2-digit"
        }
    )
})


const timeText = computed(() => {

    return now.value.toLocaleTimeString(
        "zh-CN",
        {
            hour12: false
        }
    )
})


function reload() {
    window.location.reload()
}


onMounted(() => {

    timer = setInterval(
        () => {
            now.value = new Date()
        },
        1000
    )
})


onUnmounted(() => {

    if (timer) {
        clearInterval(timer)
    }
})

</script>


<style src="./assets/hub.css"></style>
