# 足球数据聚合分析平台

零第三方运行依赖的 TypeScript 单页应用（SPA），使用本地模拟数据，桌面优先并适配平板/手机。

## 启动

```bash
npm install
npm run dev
```

默认访问：`http://localhost:3000/`

## 校验

```bash
npm run build
npm run lint
npm run test
```

## 页面

- 今日总览
- 方案大厅
- 赛事分析
- 赛事数据
- 投注热力
- 赛果统计
- 用户中心
- 数据监控
- 排行榜

## 数据与类型

`src/services/` 提供本地数据适配；`src/types/index.ts` 定义 Match、Plan、User、Result、BettingPlay、HotPlayRow、PlatformStatus、DashboardMetrics 等类型。

## 主题

全局主题变量位于 `src/styles.css` 的 `:root`，包括 `--brand-primary`、`--background`、`--foreground`、`--muted`、`--border` 等。
