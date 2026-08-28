# 前端 API 映射（迁移基线）

新版数据终端通过 `frontend/src/api/client.js` 访问同源 `/api` 代理，页面不再直接拼接服务器地址。Service 负责请求，Domain adapter 负责把后端 snake_case 转换为 UI 字段。

| 新版模块 | 当前接口 | 状态 | 适配说明 |
| --- | --- | --- | --- |
| 今日总览 | `GET /api/portal/dashboard` | LIVE | dashboard service 保留后端聚合字段 |
| 方案大厅 | `GET /api/portal/schemes` | LIVE | `adaptPlan` 映射用户、金额、时间、赛果 |
| 赛事分析 | `GET /api/portal/analysis` | HYBRID | 基础数据可用，盘口趋势字段按空状态处理 |
| 赛事数据 | `GET /api/matches` | LIVE | 比赛基础信息复用现有接口 |
| 比赛新闻 | `GET /api/news` | HYBRID | 无数据时保留空状态 |
| 投注热力 | `GET /api/portal/heatmap` | LIVE | 由后端聚合，页面不做全量计算 |
| 赛果统计 | `GET /api/portal/results` | LIVE | 使用分页和日期筛选 |
| 用户中心 | `GET /api/portal/users` | LIVE | `adaptUser` 统一字段 |
| 数据监控 | 暂无统一接口 | MOCK/HYBRID | 后续接入 `/api/monitor/*` |
| 排行榜 | `/api/portal/users` 聚合 | HYBRID | 后续可替换独立排行榜接口 |

所有列表统一支持 `page`、`page_size`；缺失字段显示 `--` 或“暂无数据”，不会导致页面白屏。
