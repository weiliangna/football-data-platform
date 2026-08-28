# API 待办中心

## 数据监控（MOCK/HYBRID）

- 建议接口：`GET /api/monitor/platforms`、`GET /api/monitor/tasks`、`GET /api/monitor/errors`
- 需要字段：平台状态、最近同步时间、读取行数、写入行数、失败数、耗时、错误摘要。
- 前端页面：数据监控。

## 盘口趋势（HYBRID）

- 当前基础比赛接口可用，盘口历史和公司维度变化字段不完整。
- 建议接口：`GET /api/matches/{id}/odds`。

## 独立排行榜（HYBRID）

- 当前可从用户列表及统计字段聚合。
- 如需稳定分页与排序，建议：`GET /api/ranking/users`、`GET /api/ranking/orders`。
