# 新版前端迁移状态

当前分支：`feature/football-data-center-migration`

## 已完成

- 新版首页预览：`/#/preview`
- 统一 API Client（同源 `/api`、超时、Cookie、错误映射）
- API endpoint 常量与 Domain Adapter
- Dashboard、Plans、Users、Matches、Analysis、Heatmap、Results Service
- Monitor Mock Service、Ranking Hybrid Service
- 数据监控与排行榜路由及侧边栏入口
- `live / mock / hybrid` 数据模式配置
- API 映射与待办文档

## 接口覆盖

| 模块 | 当前模式 | 说明 |
| --- | --- | --- |
| Dashboard | hybrid | 现有首页接口可用，异常时可降级 |
| Plans | live | 使用方案分页接口 |
| Analysis | hybrid | 基础分析真实，部分趋势字段待补 |
| Matches | live | 使用比赛列表与上下文接口 |
| News | hybrid | 无新闻时保留空状态 |
| Heatmap | live | 使用后端聚合结果 |
| Results | live | 使用赛果分页接口 |
| Users | live | 使用用户分页接口和 Adapter |
| Monitor | mock | 等待统一监控 API |
| Ranking | hybrid | 暂时复用用户统计排序 |

## 下一阶段

将 `football-data-center` 的页面组件逐页移植为 Vue 组件，先切换 Dashboard，再切换方案大厅和赛事数据。每页保留 loading、error、empty、partial 状态，并通过 Service 层接入，不在组件内直接请求 API。
