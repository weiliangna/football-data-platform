import { createRouter, createWebHashHistory } from "vue-router"

import Analysis from "../views/Analysis.vue"
import Heatmap from "../views/Heatmap.vue"
import Home from "../views/Home.vue"
import OrderDetail from "../views/OrderDetail.vue"
import Orders from "../views/Orders.vue"
import Results from "../views/Results.vue"
import UserCenter from "../views/UserCenter.vue"
import UserDetail from "../views/UserDetail.vue"


const ScpaiMatches = () => import("../views/ScpaiMatches.vue")
const ScpaiNews = () => import("../views/ScpaiNews.vue")


const routes = [
  { path: "/", component: Home },
  { path: "/orders", component: Orders },
  { path: "/analysis", component: Analysis },
  { path: "/match-data", component: ScpaiMatches },
  {
    path: "/match-data/:externalId",
    redirect: route => ({ path: "/match-data", query: { match: route.params.externalId } }),
  },
  { path: "/match-news", component: ScpaiNews },
  { path: "/heatmap", component: Heatmap },
  { path: "/results", component: Results },
  { path: "/users", component: UserCenter },
  { path: "/user/detail/:platform/:id", component: UserDetail },
  { path: "/order/detail/:id", component: OrderDetail },
  { path: "/experts", redirect: "/users" },
  { path: "/ranking", redirect: "/users" },
  { path: "/platform/:platformId/heatmap", redirect: "/heatmap" },
  { path: "/platform/:platformId/results", redirect: "/results" },
  { path: "/platform/:platformId/dashboard", redirect: "/" },
  { path: "/platform/:platformId/schemes", redirect: "/orders" },
]


export default createRouter({ history: createWebHashHistory(), routes })
