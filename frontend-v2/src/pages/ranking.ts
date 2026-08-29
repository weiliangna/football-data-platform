import { users } from '../services/users.js';
import { avatar, badge, drawer, metric, pageHeader, panel, segmented } from '../components/ui.js';
import { esc } from '../utils/dom.js';

export interface RankingState {
  tab: string;
  period: string;
  platform: string;
  desc: boolean;
  selectedUser: string | null;
}

const tabs = ['用户排行榜', '发单排行榜', '跟单排行榜', '金额排行榜', '命中率排行', 'ROI 排行'];
const platforms = ['全部', '彩站云', '州运宝', '鸿瑞', '云彩'];

export function renderRanking(state: RankingState) {
  const rows = users.filter((user) => state.platform === '全部' || user.platform === state.platform).slice().sort((a, b) => state.desc ? b.roi - a.roi : a.roi - b.roi);
  let html = pageHeader('RANKING', '排行榜', '用户、发单、跟单、金额、命中率与 ROI 多维排名', segmented(['今日', '本周', '本月'], state.period, 'ranking-period'));
  html += `<div class="ranking-tabs">${tabs.map((tab) => `<button class="${state.tab === tab ? 'active' : ''}" data-ranking-tab="${esc(tab)}">${esc(tab)}</button>`).join('')}</div><div class="filter-toolbar">${select('平台', 'ranking-platform', state.platform, platforms)}<button class="btn" data-action="ranking-sort">排序：${state.desc ? '高 → 低' : '低 → 高'}</button></div>`;
  const list = `<div class="ranking-list">${rows.slice(0, 12).map((user, index) => `<button class="ranking-row" data-open-user="${esc(user.id)}"><span class="rank-badge r${index + 1}">${index < 3 ? '●' : index + 1}</span>${avatar(user.avatar, user.name)}<span class="ranking-user"><b>${esc(user.name)}</b><small>${esc(user.platform)} · ID ${esc(user.id)}</small></span><span><small>命中率</small><b>${user.winRate}%</b></span><span><small>月回报</small><b class="positive">+${user.monthlyRoi.toFixed(1)}%</b></span><span><small>跟单人数</small><b>${user.followers.toLocaleString()}</b></span><span><small>ROI</small><strong class="positive">+${user.roi}%</strong></span></button>`).join('')}</div>`;
  html += panel(`${state.tab} · ${state.period}`, list);
  const selected = users.find((user) => user.id === state.selectedUser);
  if (selected) html += drawer('排行榜用户详情', `<div class="detail-stack"><div class="user-detail-head">${avatar(selected.avatar, selected.name, 'large')}<div><h2>${esc(selected.name)}</h2><span>${esc(selected.platform)} · ${esc(selected.id)}</span></div>${badge('TOP 用户', 'success')}</div><div class="detail-grid">${metric('历史战绩', selected.record)}${metric('命中率', `${selected.winRate}%`)}${metric('月回报', `+${selected.monthlyRoi.toFixed(1)}%`, '', 'success')}${metric('ROI', `+${selected.roi}%`, '', 'success')}</div></div>`);
  return html;
}

function select(label: string, key: string, value: string, items: string[]) {
  return `<label class="select-field"><span>${label}</span><select data-select="${key}">${items.map((item) => `<option value="${esc(item)}" ${item === value ? 'selected' : ''}>${esc(item)}</option>`).join('')}</select></label>`;
}
