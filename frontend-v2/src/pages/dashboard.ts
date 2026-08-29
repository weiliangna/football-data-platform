import { alerts, dashboardMetrics, hotMatches, hotUsers, marketMoves, matches } from '../services/dashboard.js';
import type { Match } from '../types/index.js';
import { avatar, badge, drawer, emptyState, loadingState, metric, pageHeader, panel, progress, segmented } from '../components/ui.js';
import { esc } from '../utils/dom.js';

export interface DashboardState { league: string; status: string; query: string; day: string; loading: boolean; selectedMatch: string | null }
const tone = (status: string) => status === '进行中' ? 'live' : status === '已结束' ? 'done' : 'pending';

export function renderDashboard(state: DashboardState) {
  const filtered = matches.filter((match) =>
    (state.league === '全部' || state.league === match.league || (state.league === '竞彩' && match.category === '竞彩') || (state.league === '其他' && match.category === '其他'))
    && (state.status === '全部' || state.status === match.status)
    && (!state.query || `${match.home}${match.away}${match.league}`.toLowerCase().includes(state.query.toLowerCase())),
  );
  const leagueBtns = ['全部', '竞彩', '英超', '西甲', '德甲', '意甲', '法甲', '欧冠', '其他'].map((item) => `<button data-filter="dashboard-league" data-value="${esc(item)}" class="${state.league === item ? 'active' : ''}">${esc(item)}</button>`).join('');
  const statusBtns = ['全部', '未开赛', '进行中', '已结束'].map((item) => `<button data-filter="dashboard-status" data-value="${esc(item)}" class="${state.status === item ? 'active' : ''}">${esc(item)}</button>`).join('');
  const tableBody = filtered.map((match) => `<tr><td>${esc(match.time)}</td><td><span class="league-tag">${esc(match.league)}</span></td><td><button class="link-btn" data-open-match="${esc(match.id)}">${esc(match.home)}</button></td><td class="score">${esc(match.score)}</td><td><button class="link-btn" data-open-match="${esc(match.id)}">${esc(match.away)}</button></td><td>${badge(match.status, tone(match.status))}</td><td><div class="odds-row">${match.euro.map((odd) => `<span>${esc(odd.label)} ${esc(odd.value)} ${odd.trend === 'up' ? '↑' : odd.trend === 'down' ? '↓' : ''}</span>`).join('')}</div></td><td>${esc(match.asian)}</td><td>${esc(match.totals)}</td><td>${match.plans}</td><td><span class="heat">◉ ${match.heat}</span></td><td>${match.anomaly ? badge(match.anomaly, 'danger') : '<span class="muted">—</span>'}</td></tr>`).join('');

  let html = pageHeader('DATA WORKSPACE', '今日总览', '赛事、方案、用户与盘口数据实时聚合', `${segmented(['昨日', '今日', '明日'], state.day, 'dashboard-day')}<button class="btn">▣ 2026-08-29</button>`);
  html += `<div class="filter-toolbar"><div class="filter-group"><span>联赛</span><div class="chips">${leagueBtns}</div></div><div class="filter-group"><span>状态</span><div class="chips">${statusBtns}</div></div><div class="toolbar-spacer"></div><div class="search-box"><span>⌕</span><input data-input="dashboard-query" value="${esc(state.query)}" placeholder="搜索球队 / 联赛" /></div></div>`;
  html += `<div class="metric-grid seven">${metric('今日赛事', dashboardMetrics.matches)}${metric('进行中', dashboardMetrics.live, '', 'success')}${metric('今日方案', dashboardMetrics.plans.toLocaleString())}${metric('发单用户', dashboardMetrics.users)}${metric('异常盘口', dashboardMetrics.anomalies, '', 'danger')}${metric('热门比赛', dashboardMetrics.hot)}${metric('已完成', dashboardMetrics.completed)}</div>`;
  const eventTable = state.loading ? loadingState() : filtered.length ? `<div class="table-wrap"><table><thead><tr><th>时间</th><th>赛事</th><th>主队</th><th>比分</th><th>客队</th><th>状态</th><th>欧赔</th><th>亚洲让球</th><th>大小球</th><th>方案数</th><th>热度</th><th>异常</th></tr></thead><tbody>${tableBody}</tbody></table></div>` : emptyState('没有匹配赛事');
  const moves = marketMoves.map((row) => `<div class="compact-row"><span class="time">${esc(row.time)}</span><div><b>${esc(row.match)}</b><small>${esc(row.company)} · ${esc(row.change)}</small></div>${badge(row.state, row.state === '升盘' ? 'danger' : 'success')}</div>`).join('');
  const warningRows = alerts.map((row) => `<div class="alert-row"><div><b>${esc(row.type)}</b><small>${esc(row.time)} · ${esc(row.desc)}</small></div>${badge(`${row.risk}风险`, row.risk === '高' ? 'danger' : row.risk === '中' ? 'warning' : 'pending')}</div>`).join('');
  html += `<div class="dashboard-grid">${panel('今日赛事', eventTable, `<span class="muted">共 ${filtered.length} 场</span>`)}<div class="side-stack">${panel('盘口异动', `<div class="compact-list">${moves}</div>`)}${panel('异常提醒', `<div class="compact-list">${warningRows}</div>`)}</div></div>`;
  const ranks = hotMatches.map((match, index) => `<button class="rank-row" data-open-match="${esc(match.id)}"><b>#${index + 1}</b><span>${esc(match.home)} <em>vs</em> ${esc(match.away)}</span><small>${esc(match.league)} · ${esc(match.time)}</small><div>${progress(match.heat)}<strong>${match.heat}</strong></div></button>`).join('');
  const userRows = hotUsers.map((user) => `<div class="mini-user">${avatar((user as { avatar?: string }).avatar || '', user.name)}<div><b>${esc(user.name)}</b><small>${esc(user.platform)} · ${user.plans} 个方案</small></div><div class="mini-user-kpi"><strong>${user.winRate}%</strong><span>命中率</span></div><div class="mini-user-kpi positive"><strong>+${user.roi}%</strong><span>ROI</span></div></div>`).join('');
  html += `<div class="bottom-grid">${panel('热门赛事 TOP10', `<div class="rank-list">${ranks}</div>`)}${panel('今日热门用户', `<div class="user-cards">${userRows}</div>`)}</div>`;
  const selected = matches.find((match) => match.id === state.selectedMatch);
  if (selected) html += matchDrawer(selected);
  return html;
}

function matchDrawer(match: Match) {
  return drawer('赛事详情', `<div class="detail-stack"><div class="match-hero"><div><span>${esc(match.league)}</span><h3>${esc(match.home)}</h3></div><strong>${esc(match.score)}</strong><div class="right"><span>${esc(match.time)}</span><h3>${esc(match.away)}</h3></div></div><div class="detail-grid">${metric('状态', match.status)}${metric('方案数', match.plans)}${metric('热度', match.heat)}${metric('异常', match.anomaly || '无')}</div>${panel('即时盘口', `<div class="key-values"><div><span>亚洲让球</span><b>${esc(match.asian)}</b></div><div><span>大小球</span><b>${esc(match.totals)}</b></div>${match.euro.map((odd) => `<div><span>欧赔 · ${esc(odd.label)}</span><b>${esc(odd.value)}</b></div>`).join('')}</div>`)}</div>`);
}
