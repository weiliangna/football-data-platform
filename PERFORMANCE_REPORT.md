# football-data-platform 性能诊断报告

诊断日期：2026-08-27
诊断范围：当前 Git `main`、公网只读 HTTP 探测、前后端代码、SQL、systemd 模板、采集与备份任务。
限制：未连接生产 MySQL，未执行 `EXPLAIN`、migration 或生产写操作；数据库耗时不伪造。

## 1. 当前系统架构

- 前端：Vue 3、Vue Router、Axios、Vite；nginx 提供构建后的静态资源。
- 后端：FastAPI + Uvicorn，生产模板为单 Uvicorn 进程、同步 PyMySQL 数据访问。
- 数据库：MySQL，PyMySQL `DictCursor`，每个 API/任务按需创建独立连接；没有连接池。
- 缓存：没有 Redis。公开比赛适配器与首页 Dashboard 使用进程内短缓存和 single-flight。
- 数据采集：Python Spider，由 systemd timer 启动独立进程；主 pipeline、鸿瑞、赛果、结算、统计、头像、日任务和备份均与 API 进程分离。
- 消息队列：无。
- WebSocket/SSE：无。
- ORM：无，使用手写 SQL。
- 部署：nginx + systemd + Uvicorn；前端 `npm run build`。

```text
第三方平台 / 公开比赛数据
          ↓
独立 Spider / Scpai Adapter
          ↓
字段归一、订单腿构建、赛果与统计任务
          ↓
        MySQL
          ↓
FastAPI Portal / Hub / Match APIs
          ↓
      nginx + Vue
```

## 2. 本次生产故障证据

2026-08-27 公网只读基线：

| 接口 | HTTP | TTFB/总耗时 | 结果 |
|---|---:|---:|---|
| `/` | 200 | 15ms | nginx 静态首页正常 |
| `/api/portal/dashboard` | 000 | >15s | 无响应并超时 |
| `/api/platform/list` | 000 | >10s | 线程池饱和时超时 |
| `/api/portal/schemes?page=1&page_size=1` | 000 | >10s | 线程池饱和时超时 |
| `/api/portal/analysis` | 000 | >10s | 线程池饱和时超时 |
| `/api/portal/heatmap` | 000 | >10s | 线程池饱和时超时 |
| `/api/portal/users?page=1&page_size=1` | 200 | 1.562s | 偶尔获得工作线程后返回 |
| `/api/matches` | 200 | 1.812s | 独立 executor，未被 Portal 拖死 |

结论：网站静态入口没有宕机；首页与多个业务页因 FastAPI 默认同步线程池被慢 Dashboard 请求占满而表现为“打不开/一直 Loading”。

## 3. 性能瓶颈 TOP 10

### P0：Dashboard 扫描全部历史待开奖订单并执行不必要的赛果关联

- 文件：`api/portal.py`
- 证据：`build_current_context()` 调用 `load_pending_orders()`，随后原来调用完整 `load_order_matches()`。完整查询为每条订单腿执行带多个 `OR` 的 `match_results` 关联子查询。
- 放大因素：首页每 30 秒刷新；多个用户同时打开后，相同重查询并发执行。
- 本轮处理：Dashboard、分析与热力使用的待开奖订单腿统一改用 `load_hot_play_matches()`，不再关联赛果表，并按 1000 个订单分块。

### P0：Dashboard 与所有同步 API 共享 FastAPI 默认线程池

- 文件：`api/portal.py`、`deploy/systemd/football-api.service`
- 证据：Uvicorn 单进程；Portal 路由为同步函数。慢 Dashboard 请求能够占满同步工作线程，令轻量接口一起超时。
- 本轮处理：Dashboard 改为 async 外壳，数据库构建在独立单线程 executor 中执行，不再占用普通 API 工作线程。

### P0：相同 Dashboard 结果重复计算

- 文件：`frontend/src/views/Home.vue`、`api/portal.py`
- 证据：客户端每 30 秒刷新，服务端此前没有缓存或 single-flight。
- 本轮处理：15 秒新鲜缓存、120 秒 stale-while-revalidate、并发 single-flight。离线测试确认 10 个并发请求只构建一次。

### P1：Dashboard 用户统计 N+1

- 文件：`api/portal.py`
- 证据：原实现对 `user_groups` 中每位用户单独查询 `user_statistics`。
- 本轮处理：复用 `load_user_statistics()` 一次读取并以内存键查找替代 N+1。

### P1：日期条件中的 `COALESCE` 影响索引利用

- 文件：`api/portal.py`
- 查询：`COALESCE(publish_time,created_time) >= ? AND ... < ?`
- 风险：函数包裹列可能令 MySQL 无法直接使用 `publish_time` 或 `created_time` 的范围索引。
- 建议：取得生产 `EXPLAIN ANALYZE` 后改写为可索引的两支条件，或在确认 MySQL 版本后评估生成列。未在本轮猜测修改。

### P1：完整订单腿查询的关联子查询仍用于需要赛果的页面

- 文件：`api/portal.py::load_order_matches`
- 风险：多列 `OR`、逐腿相关子查询以及 legacy `match_name` fallback 会随历史数据增长变慢。
- 建议：先用生产 `EXPLAIN ANALYZE` 验证 identity v2 命中率，再将 v2 和 legacy fallback 拆成批量查询；不能直接删除 legacy 兼容。

### P1：无 MySQL 连接池

- 文件：`database/mysql.py`
- 现状：每次 API/任务调用 `pymysql.connect()`。
- 影响：连接建立开销、并发连接峰值及 MySQL 线程切换增加。
- 建议：先统计 `Threads_connected`、`Connections`、并发量，再选受控连接池；Spider 独立进程不能盲目共享 API 池。

### P2：部分请求加载整张资料/统计表

- 文件：`api/portal.py::load_profiles`、`load_user_statistics`
- 影响：用户规模继续增长时，单次请求内存与传输量线性增加。
- 建议：下一阶段根据当前订单用户键批量 `IN` 查询，仅加载需要的用户。

### P2：前端仍采用整页轮询而非增量更新

- 文件：`Home.vue`、`Heatmap.vue`、`ScpaiMatches.vue`、`ScpaiNews.vue`
- 现状：30 秒路由内轮询，Home/Heatmap 已有 in-flight 防重入。
- 建议：订单列表优先增加 `updated_after` 增量接口；当前规模下暂不为架构美观强制引入 WebSocket。

### P2：备份、日志和运行数据可能持续占用系统盘

- 文件：`scripts/backup_db.py`、`spider/run_job.py`、`spider/pipeline.py`
- 现状：每天生成全库 gzip 备份并保留 14 天；`spider_logs`、`sync_log` 没有仓库内自动保留策略；journald、nginx、MySQL binlog 也可能增长。
- 影响：系统盘接近满时 MySQL 临时文件、日志写入和服务重启都会异常。
- 要求：先只读盘点，再决定清理策略；不得直接删除数据库目录或未知备份。

## 4. 已修改代码

### `api/portal.py`

- 修改前：每次 Dashboard 都扫描全部历史待开奖订单腿，并进行不需要的赛果匹配；并发请求各自重复执行；用户统计逐用户查询。
- 修改后：热门玩法使用无赛果关联的轻量查询；订单 ID 每 1000 个分块；Dashboard 独立 executor、缓存与 single-flight；统计一次加载。
- 预期收益：解除默认 API 线程池饱和，大幅减少首页 SQL 工作量和重复计算。
- 风险：缓存最多短暂返回 120 秒内旧 Dashboard；订单、比赛、赛果和统计规则未改变。

### `tests/test_portal_performance.py`

- 验证轻量查询不引用 `match_results`。
- 验证大订单集合按 1000 分块。
- 验证 10 个并发请求只构建一次 Dashboard。
- 验证新鲜缓存不访问数据库、过期缓存后台刷新。

## 5. 数据库索引与慢查询

本轮没有创建索引或 migration，因为没有生产 `SHOW INDEX` 与 `EXPLAIN ANALYZE` 证据。当前 schema 已知索引包括：

- `orders(result)`、`orders(created_time)`、`orders(platform_id,publish_time)`
- `order_matches(order_id)`、`order_matches(deadline_time)`、`order_matches(match_code)`、`order_matches(match_key)`
- `user_statistics(platform_id,user_id)` 唯一键

需要生产只读确认后再决定：

1. `orders` 日期筛选是否使用索引；
2. identity v2 的 `match_results(platform_id,match_date,match_code)` 与 `(platform_id,match_date,match_key)` 普通索引是否已应用；
3. `spider_logs`、`sync_log` 的行数和占用；
4. 慢查询日志中真实最慢 SQL。

## 6. 系统盘只读盘点

优先检查：

```bash
df -hT
df -ih
free -h
sudo du -xhd1 / 2>/dev/null | sort -h
sudo du -xhd1 /var /www /tmp 2>/dev/null | sort -h
sudo du -xhd2 /www/backups /var/log /var/lib/mysql 2>/dev/null | sort -h | tail -80
sudo journalctl --disk-usage
sudo find /var/log /www/backups /tmp -xdev -type f -size +100M \
  -printf '%s %TY-%Tm-%Td %p\n' 2>/dev/null | sort -nr | head -80
```

这些命令只读，不删除文件，也不输出 env 或数据库密码。重点判断：

- `/www/backups/football` 是否确实只保留 14 天；
- `/var/log/journal`、nginx 日志、`football-deploy.log` 是否异常增长；
- `/var/lib/mysql` 中数据文件、binlog 或慢查询日志占用；
- `/tmp` 是否有遗留 dump；
- 项目中的 `frontend/node_modules`、`frontend/dist`、`venv`、`.git` 是部署依赖或构建产物，不能看到大就直接删除。

## 7. 优化前后对比

### 可验证的代码级对比

| 项目 | Before | After |
|---|---|---|
| 10 个并发 Dashboard 请求 | 最多重复执行 10 次完整构建 | 离线测试确认只执行 1 次 |
| 热门玩法腿查询 | 关联 `match_results` 相关子查询 | 不读取 `match_results` |
| Dashboard 用户统计 | 1 + N 查询 | 1 次批量查询 |
| Dashboard 对普通 API 线程池影响 | 共享并可占满 | 独立单线程 executor |
| Dashboard 重复刷新 | 无服务端缓存 | 15 秒缓存、120 秒旧值兜底 |

### 生产真实耗时

优化前已取得 `/api/portal/dashboard >15s` 的公网基线。优化后尚未部署，无法获得真实生产 benchmark，不能伪造数字。部署后使用：

```bash
for i in 1 2 3 4 5; do
  curl -sS -o /dev/null \
    -w 'HTTP=%{http_code} TTFB=%{time_starttransfer}s TOTAL=%{time_total}s\n' \
    http://127.0.0.1:8000/api/portal/dashboard
done
```

## 8. 下一阶段路线

1. **低风险高收益**：部署本轮 P0 修复，重启 API，验证 Dashboard 与其他 Portal 接口恢复。
2. **只读取证**：收集磁盘占用、MySQL 表大小、`SHOW INDEX`、慢查询和 `EXPLAIN ANALYZE`。
3. **数据库优化**：仅根据取证生成独立索引 SQL，人工审查和执行。
4. **数据体积优化**：profiles/statistics 按用户键批量加载，订单列表字段裁剪和 cursor pagination。
5. **刷新优化**：增加订单 `updated_after` 增量接口；只有数据量与在线用户证明需要时再评估 Redis/SSE。

# 性能瓶颈总览

① Dashboard 全历史待开奖腿 + 赛果相关子查询
影响：★★★★★　优化收益：★★★★★

② 慢 Dashboard 占满 FastAPI 公共同步线程池
影响：★★★★★　优化收益：★★★★★

③ Dashboard 无缓存、30 秒并发重复计算
影响：★★★★★　优化收益：★★★★★

④ 用户统计 N+1 与全表资料加载
影响：★★★★☆　优化收益：★★★★☆

⑤ 系统盘备份、日志、MySQL 运行文件增长风险
影响：★★★★☆　优化收益：★★★★☆
