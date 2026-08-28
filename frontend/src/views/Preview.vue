<template>
  <section class="preview-shell">
    <header class="preview-topbar">
      <div>
        <p class="kicker">FOOTBALL DATA TERMINAL</p>
        <h1>今日总览</h1>
        <p class="subline">多平台赛事、盘口与发单数据实时聚合 · 2026-08-29</p>
      </div>
      <div class="top-actions">
        <label class="search-box"><span>⌕</span><input placeholder="搜索球队、赛事或用户" /></label>
        <button class="icon-btn" aria-label="通知">♧</button>
        <button class="account-btn"><span class="account-avatar">AI</span><span>数据中心</span><b>⌄</b></button>
      </div>
    </header>

    <nav class="preview-tabs" aria-label="数据导航">
      <a class="active">今日总览</a><a>方案大厅</a><a>赛事分析</a><a>赛事数据</a><a>投注热力</a><a>赛果统计</a><a>用户中心</a>
    </nav>

    <section class="kpi-row">
      <article v-for="item in kpis" :key="item.label" class="kpi-card" :class="item.tone">
        <span>{{ item.label }}</span><strong>{{ item.value }}</strong><small>{{ item.note }}</small>
        <i>{{ item.icon }}</i>
      </article>
    </section>

    <section class="content-grid">
      <article class="panel matches-panel">
        <header class="panel-head"><div><p class="kicker">LIVE MATCHES</p><h2>今日赛事</h2></div><button class="plain-btn">全部赛事　›</button></header>
        <div class="filter-row"><button class="filter active">全部</button><button class="filter">进行中</button><button class="filter">未开始</button><button class="filter">已结束</button><span class="filter-spacer"></span><span class="muted">共 128 场</span></div>
        <div class="table-wrap"><table><thead><tr><th>时间</th><th>赛事</th><th>主队</th><th>比分</th><th>客队</th><th>胜平负</th><th>方案</th></tr></thead><tbody><tr v-for="match in matches" :key="match.code"><td class="time">{{ match.time }}</td><td><span class="league-dot"></span>{{ match.league }}</td><td class="team home">{{ match.home }}</td><td><b class="score" :class="match.live ? 'live' : ''">{{ match.score }}</b><small v-if="match.live" class="live-label">进行中</small></td><td class="team">{{ match.away }}</td><td><span class="odds">{{ match.odds }}</span></td><td><b class="scheme-count">{{ match.schemes }}</b><span class="muted"> 方案</span></td></tr></tbody></table></div>
      </article>

      <aside class="side-stack">
        <article class="panel alert-panel"><header class="panel-head"><div><p class="kicker">ODDS WATCH</p><h2>盘口异动</h2></div><span class="status-pill">实时</span></header><div class="alert-list"><div v-for="item in alerts" :key="item.title" class="alert-item"><span class="alert-mark" :class="item.tone">↗</span><div><b>{{ item.title }}</b><small>{{ item.detail }}</small></div><strong>{{ item.delta }}</strong></div></div></article>
        <article class="panel hot-panel"><header class="panel-head"><div><p class="kicker">TOP 10</p><h2>热门赛事</h2></div><button class="plain-btn">查看全部 ›</button></header><ol class="hot-list"><li v-for="(item, index) in hotMatches" :key="item"><span>{{ String(index + 1).padStart(2, '0') }}</span><b>{{ item }}</b><em>{{ 96 - index * 7 }}%</em></li></ol></article>
      </aside>
    </section>

    <section class="lower-grid">
      <article class="panel chart-panel"><header class="panel-head"><div><p class="kicker">PLATFORM ACTIVITY</p><h2>平台发单趋势</h2></div><span class="muted">最近 24 小时</span></header><div class="chart"><div v-for="line in [25, 55, 85, 115]" :key="line" class="grid-line" :style="{ top: line + 'px' }"></div><svg viewBox="0 0 700 150" preserveAspectRatio="none"><path d="M0,124 C55,118 78,108 121,112 S188,88 230,98 S285,58 332,72 S395,93 438,72 S498,54 535,64 S605,24 700,40" /><path class="area" d="M0,124 C55,118 78,108 121,112 S188,88 230,98 S285,58 332,72 S395,93 438,72 S498,54 535,64 S605,24 700,40 L700,150 L0,150Z" /></svg><div class="chart-labels"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span></div></div></article>
      <article class="panel activity-panel"><header class="panel-head"><div><p class="kicker">HOT USERS</p><h2>活跃发单人</h2></div><button class="plain-btn">用户中心 ›</button></header><div class="user-list"><div v-for="user in users" :key="user.name" class="user-row"><span class="user-avatar" :class="user.color">{{ user.name.slice(0, 1) }}</span><div><b>{{ user.name }}</b><small>{{ user.platform }} · 今日 {{ user.count }} 单</small></div><strong>{{ user.amount }}</strong></div></div></article>
    </section>
    <p class="preview-note">预览模式 · 当前展示为结构化 Mock 数据，确认视觉后再接入真实接口</p>
  </section>
</template>

<script setup>
const kpis = [
  { label: "今日入库方案", value: "440", note: "较昨日 +12.8%", icon: "↗", tone: "featured" },
  { label: "今日跟单", value: "2,090", note: "聚合跟单人次", icon: "◎", tone: "" },
  { label: "今日跟单金额", value: "¥ 288,420", note: "来自 6 个数据平台", icon: "¥", tone: "" },
  { label: "昨日中奖", value: "204", note: "已结算中中奖方案", icon: "✓", tone: "" },
]
const matches = [
  { code: "周五008", time: "19:00", league: "欧冠", home: "拜仁慕尼黑", away: "巴黎圣日耳曼", score: "—", odds: "1.62  3.90  4.80", schemes: 36 },
  { code: "周五009", time: "20:30", league: "英超", home: "阿森纳", away: "利物浦", score: "—", odds: "2.10  3.40  3.05", schemes: 28 },
  { code: "周五010", time: "21:00", league: "西甲", home: "皇家马德里", away: "巴塞罗那", score: "1 : 0", odds: "1.88  3.60  3.80", schemes: 52, live: true },
  { code: "周五011", time: "22:00", league: "意甲", home: "国际米兰", away: "AC米兰", score: "—", odds: "1.75  3.55  4.20", schemes: 19 },
]
const alerts = [
  { title: "皇家马德里 · 主胜", detail: "欧赔 · 3 家公司同步下调", delta: "-0.18", tone: "green" },
  { title: "阿森纳 · 让球", detail: "亚盘 · 盘口升至 -0.75", delta: "+0.12", tone: "orange" },
  { title: "拜仁慕尼黑 · 大球", detail: "大小 · 近 10 分钟热度上升", delta: "+8.4%", tone: "purple" },
]
const hotMatches = ["皇家马德里 vs 巴塞罗那", "阿森纳 vs 利物浦", "拜仁慕尼黑 vs 巴黎圣日耳曼", "国际米兰 vs AC米兰"]
const users = [
  { name: "伯纳乌霸王", platform: "彩站云", count: 8, amount: "¥48,888", color: "blue" },
  { name: "沃奇尼亚", platform: "鸿瑞", count: 6, amount: "¥32,900", color: "violet" },
  { name: "绝命赌师", platform: "彩站云", count: 5, amount: "¥21,600", color: "orange" },
]
</script>

<style scoped>
.preview-shell{max-width:1560px;margin:0 auto;padding:28px 34px 36px;color:#1f2937}.preview-topbar{display:flex;justify-content:space-between;align-items:flex-start;gap:24px}.kicker{margin:0 0 7px;color:#1769e0;font-size:10px;font-weight:800;letter-spacing:.16em}.preview-topbar h1{margin:0;font-size:30px;letter-spacing:-.03em}.subline{margin:7px 0 0;color:#6b7280;font-size:12px}.top-actions{display:flex;align-items:center;gap:10px}.search-box{display:flex;align-items:center;width:275px;height:38px;padding:0 12px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;color:#9ca3af}.search-box span{font-size:23px;line-height:0;margin-right:8px}.search-box input{width:100%;border:0;outline:0;font-size:12px}.icon-btn,.account-btn{height:38px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;color:#374151}.icon-btn{width:38px;font-size:17px}.account-btn{display:flex;align-items:center;gap:8px;padding:0 11px;font-size:12px}.account-btn b{color:#9ca3af}.account-avatar,.user-avatar{display:grid;place-items:center;border-radius:50%;font-weight:800}.account-avatar{width:24px;height:24px;color:#fff;background:#1769e0;font-size:9px}.preview-tabs{display:flex;gap:26px;margin-top:27px;border-bottom:1px solid #e5e7eb}.preview-tabs a{padding:0 2px 13px;color:#6b7280;font-size:13px;cursor:pointer}.preview-tabs a.active{color:#1769e0;border-bottom:2px solid #1769e0;font-weight:700}.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:20px}.kpi-card{position:relative;padding:18px 19px;border:1px solid #e5e7eb;border-radius:9px;background:#fff}.kpi-card.featured{color:#fff;border-color:#102a4c;background:#102a4c}.kpi-card span,.kpi-card small{display:block;font-size:11px;color:#6b7280}.kpi-card.featured span,.kpi-card.featured small{color:#b9c8db}.kpi-card strong{display:block;margin:10px 0 7px;font-size:27px;letter-spacing:-.04em}.kpi-card i{position:absolute;top:16px;right:17px;width:25px;height:25px;display:grid;place-items:center;border-radius:6px;color:#1769e0;background:#eef5ff;font-style:normal;font-weight:800}.kpi-card.featured i{color:#fff;background:#244b7a}.content-grid,.lower-grid{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(310px,.75fr);gap:14px;margin-top:14px}.panel{border:1px solid #e5e7eb;border-radius:9px;background:#fff}.matches-panel{padding:19px 19px 9px}.panel-head{display:flex;justify-content:space-between;align-items:flex-start}.panel-head h2{margin:0;font-size:17px}.plain-btn{padding:3px 0;border:0;background:transparent;color:#1769e0;font-size:11px}.filter-row{display:flex;align-items:center;gap:7px;margin:17px 0 10px}.filter{padding:6px 12px;border:1px solid #e5e7eb;border-radius:5px;background:#fff;color:#6b7280;font-size:11px}.filter.active{color:#fff;border-color:#1769e0;background:#1769e0}.filter-spacer{flex:1}.muted{color:#9ca3af;font-size:11px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:11px}th{padding:10px 8px;color:#9ca3af;border-top:1px solid #eef0f2;border-bottom:1px solid #eef0f2;font-weight:600;text-align:left}td{padding:14px 8px;border-bottom:1px solid #f0f1f3;white-space:nowrap}.time{color:#6b7280;font-variant-numeric:tabular-nums}.league-dot{display:inline-block;width:6px;height:6px;margin-right:6px;border-radius:50%;background:#1769e0}.team{font-weight:600}.home{color:#172b4d}.score{display:inline-block;min-width:32px;text-align:center}.score.live{color:#1769e0}.live-label{display:block;margin-top:3px;color:#22a06b;font-size:9px}.odds{color:#6b7280;font-variant-numeric:tabular-nums}.scheme-count{color:#1769e0}.side-stack{display:grid;gap:14px}.alert-panel,.hot-panel{padding:19px}.status-pill{padding:4px 8px;border-radius:12px;color:#16804d;background:#e9f8f0;font-size:10px}.alert-list{margin-top:13px}.alert-item{display:flex;align-items:center;gap:9px;padding:12px 0;border-bottom:1px solid #f0f1f3}.alert-item:last-child{border-bottom:0}.alert-mark{width:25px;height:25px;display:grid;place-items:center;border-radius:6px;font-size:13px;font-weight:800}.alert-mark.green{color:#16804d;background:#e9f8f0}.alert-mark.orange{color:#bd6b16;background:#fff2df}.alert-mark.purple{color:#7556c7;background:#f1edff}.alert-item div{min-width:0;flex:1}.alert-item b,.alert-item small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.alert-item b{font-size:11px}.alert-item small{margin-top:4px;color:#9ca3af;font-size:9px}.alert-item strong{color:#16804d;font-size:11px}.hot-list{margin:13px 0 0;padding:0;list-style:none}.hot-list li{display:grid;grid-template-columns:24px minmax(0,1fr) auto;gap:8px;align-items:center;padding:11px 0;border-bottom:1px solid #f0f1f3}.hot-list li:last-child{border:0}.hot-list li span{color:#9ca3af;font-size:10px}.hot-list li b{font-size:11px}.hot-list li em{color:#1769e0;font-size:10px;font-style:normal}.chart-panel,.activity-panel{padding:19px}.chart{position:relative;height:175px;margin-top:18px}.grid-line{position:absolute;left:0;right:0;border-top:1px dashed #edf0f2}.chart svg{position:absolute;inset:0;width:100%;height:145px}.chart path{fill:none;stroke:#1769e0;stroke-width:3;stroke-linecap:round}.chart path.area{fill:#1769e0;opacity:.08;stroke:0}.chart-labels{position:absolute;bottom:0;left:0;right:0;display:flex;justify-content:space-between;color:#9ca3af;font-size:9px}.user-list{margin-top:11px}.user-row{display:flex;align-items:center;gap:10px;padding:11px 0;border-bottom:1px solid #f0f1f3}.user-row:last-child{border:0}.user-avatar{width:32px;height:32px;color:#fff;font-size:12px}.user-avatar.blue{background:#1769e0}.user-avatar.violet{background:#7656cf}.user-avatar.orange{background:#e28537}.user-row div{flex:1}.user-row b,.user-row small{display:block}.user-row b{font-size:11px}.user-row small{margin-top:3px;color:#9ca3af;font-size:9px}.user-row strong{font-size:11px}.preview-note{margin:20px 0 0;text-align:center;color:#9ca3af;font-size:10px}@media(max-width:1000px){.preview-shell{padding:20px}.top-actions{display:none}.content-grid,.lower-grid{grid-template-columns:1fr}.kpi-row{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.preview-shell{padding:16px}.preview-tabs{gap:13px;overflow-x:auto}.preview-tabs a{font-size:11px;white-space:nowrap}.kpi-row{grid-template-columns:1fr 1fr}.kpi-card{padding:14px}.kpi-card strong{font-size:21px}th,td{padding-left:5px;padding-right:5px}}
</style>
