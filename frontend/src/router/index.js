import { createRouter, createWebHashHistory } from "vue-router"
import Analysis from "../views/Analysis.vue"
import Heatmap from "../views/Heatmap.vue"
import Home from "../views/Home.vue"
import Monitor from "../views/Monitor.vue"
import OrderDetail from "../views/OrderDetail.vue"
import Orders from "../views/Orders.vue"
import Ranking from "../views/Ranking.vue"
import Results from "../views/Results.vue"
import UserCenter from "../views/UserCenter.vue"
import UserDetail from "../views/UserDetail.vue"
import Preview from "../views/Preview.vue"

const ScpaiMatches = () => import("../views/ScpaiMatches.vue")
const ScpaiNews = () => import("../views/ScpaiNews.vue")

const routes = [
  { path: "/", component: Preview },
  { path: "/legacy-dashboard", component: Home },
  { path: "/preview", component: Preview },
  { path: "/orders", component: Orders },
  { path: "/analysis", component: Analysis },
  { path: "/match-data", component: ScpaiMatches },
  { path: "/match-data/:externalId", redirect: (route) => ({ path: "/match-data", query: { match: route.params.externalId } }) },
  { path: "/match-news", component: ScpaiNews },
  { path: "/heatmap", component: Heatmap },
  { path: "/results", component: Results },
  { path: "/users", component: UserCenter },
  { path: "/user/detail/:platform/:id", component: UserDetail },
  { path: "/order/detail/:id", component: OrderDetail },
  { path: "/monitor", component: Monitor },
  { path: "/ranking", component: Ranking },
  { path: "/experts", redirect: "/users" },
  { path: "/platform/:platformId/heatmap", redirect: "/heatmap" },
  { path: "/platform/:platformId/results", redirect: "/results" },
  { path: "/platform/:platformId/dashboard", redirect: "/" },
  { path: "/platform/:platformId/schemes", redirect: "/orders" },
]

export default createRouter({ history: createWebHashHistory(), routes })
