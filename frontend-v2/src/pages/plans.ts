import { plans } from '../services/plans.js';
import type { Plan } from '../types/index.js';
import { avatar, badge, drawer, emptyState, metric, pageHeader, panel } from '../components/ui.js';
import { money } from '../utils/format.js';
import { esc } from '../utils/dom.js';

export interface PlansState {
  query: string;
  platform: string;
  league: string;
  result: string;
  page: number;
  view: 'table' | 'cards';
  selectedPlan: string | null;
}

const pageSize = 8;
const platformOptions = ['全部', '彩站云', '州运宝', '鸿瑞', '云彩'];

export function renderPlans(state: PlansState) {
  const query = state.query.trim().toLowerCase();
  const rows = plans.filter((plan) => {
    const platformMatch = state.platform === '全部' || plan.platform === state.platform;
    const resultMatch = state.result === '全部' || plan.result === state.result;
    const queryMatch = !query || `${plan.user}${plan.userId}${plan.id}${plan.pick}`.toLowerCase().includes(query);
    return platformMatch && resultMatch && queryMatch;
  });

  const total = Math.max(1, Math.ceil(rows.length / pageSize));
  if (state.page > total) state.page = total;
  const pageRows = rows.slice((state.page - 1) * pageSize, state.page * pageSize);
  let html = pageHeader(
    'PLAN MARKET',
    '方案大厅',
    '聚合各平台发单方案，展示金额、SP赔率与结算状态',
    `<div class="view-switch"><button data-action="plans-view-table" class="${state.view === 'table' ? 'active' : ''}">☷</button><button data-action="plans-view-cards" class="${state.view === 'cards' ? 'active' : ''}">▦</button></div>`,
  );

  html += `<div class="filter-toolbar"><div class="search-box wide"><span>⌕</span><input data-input="plans-query" value="${esc(state.query)}" placeholder="搜索方案、用户或订单号"/></div>${select('平台', 'plans-platform', state.platform, platformOptions)}${select('结果', 'plans-result', state.result, ['全部', '已中奖', '未中奖', '待开奖', '走盘'])}<button class="btn ghost" data-action="plans-reset">重置筛选</button></div>`;

  const body = !pageRows.length ? emptyState('暂无方案数据', '当前平台或结果筛选下没有可展示方案') : state.view === 'table' ? table(pageRows) : cards(pageRows);
  html += panel('方案数据列表', body + pagination(state.page, total), `<span class="muted">共 ${rows.length} 条</span>`);

  const selected = plans.find((plan) => plan.id === state.selectedPlan);
  if (selected) html += planDrawer(selected);
  return html;
}

function select(label: string, key: string, value: string, items: string[]) {
  return `<label class="select-field"><span>${label}</span><select data-select="${key}">${items.map((item) => `<option ${item === value ? 'selected' : ''}>${esc(item)}</option>`).join('')}</select></label>`;
}

function resultTone(result: Plan['result']) {
  if (result === '已中奖') return 'danger';
  if (result === '未中奖') return 'dark';
  if (result === '走盘') return 'warning';
  return 'pending';
}

function table(rows: Plan[]) {
  return `<div class="table-wrap"><table class="plans-table"><thead><tr><th>平台</th><th>发单用户</th><th>用户 ID</th><th>投注金额</th><th>SP赔率</th><th>发布时间</th><th>方案状态</th><th>赛果</th><th>预计收益</th></tr></thead><tbody>${rows.map((plan) => `<tr class="clickable" data-open-plan="${esc(plan.id)}"><td><span class="platform-label">${esc(plan.platform)}</span></td><td><button class="user-cell" data-open-plan="${esc(plan.id)}">${avatar(plan.avatar, plan.user)}<span><b>${esc(plan.user)}</b><small>订单 ${esc(plan.id)}</small></span></button></td><td class="muted">${esc(plan.userId)}</td><td>${money(plan.amount)}</td><td class="odds-value">${esc(plan.sp || '--')}</td><td>${esc(plan.publishAt)}</td><td>${badge(plan.status, plan.status === '已结算' ? 'done' : 'live')}</td><td>${badge(plan.result, resultTone(plan.result))}</td><td class="${plan.expectedProfit > 0 ? 'positive' : plan.expectedProfit < 0 ? 'negative' : ''}">${money(plan.expectedProfit)}</td></tr>`).join('')}</tbody></table></div>`;
}

function cards(rows: Plan[]) {
  return `<div class="plan-card-grid">${rows.map((plan) => `<button class="plan-card" data-open-plan="${esc(plan.id)}"><div>${badge(plan.platform)}<span>${esc(plan.publishAt)}</span></div><div class="plan-card-user">${avatar(plan.avatar, plan.user)}<b>${esc(plan.user)}</b></div><div class="plan-card-kpis"><span>投注金额<strong>${money(plan.amount)}</strong></span><span>SP赔率<strong class="odds-value">${esc(plan.sp || '--')}</strong></span></div><div class="plan-card-status">${badge(plan.result, resultTone(plan.result))}<span>${esc(plan.status)}</span></div></button>`).join('')}</div>`;
}

function pagination(page: number, total: number) {
  return `<div class="pagination"><button data-page="${Math.max(1, page - 1)}" ${page <= 1 ? 'disabled' : ''}>‹</button><span>第 ${page} / ${total} 页</span><button data-page="${Math.min(total, page + 1)}" ${page >= total ? 'disabled' : ''}>›</button></div>`;
}

function planDrawer(plan: Plan) {
  return drawer('方案详情', `<div class="detail-stack"><div class="drawer-title-block">${badge(plan.platform)}<h2>${esc(plan.user)}</h2><span>订单 ${esc(plan.id)} · ${esc(plan.publishAt)}</span></div><div class="profile-card">${avatar(plan.avatar, plan.user, 'large')}<div><b>${esc(plan.user)}</b><span>用户 ID ${esc(plan.userId)} · ${esc(plan.platform)}</span></div></div><div class="detail-grid">${metric('投注金额', money(plan.amount))}${metric('SP赔率', plan.sp || '--')}${metric('方案状态', plan.status)}${metric('赛果', plan.result)}${metric('预计收益', money(plan.expectedProfit), '', plan.expectedProfit >= 0 ? 'success' : 'danger')}${metric('发布时间', plan.publishAt)}</div></div>`);
}
