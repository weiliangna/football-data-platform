import { users, userOrders } from '../services/users.js';
import { avatar, badge, drawer, metric, pageHeader, panel } from '../components/ui.js';
import { money } from '../utils/format.js';
import { esc } from '../utils/dom.js';

export interface UsersState {
  query: string;
  platform: string;
  minHit: number;
  selectedUser: string | null;
  followed: Set<string>;
}

const platforms = ['全部', '彩站云', '州运宝', '鸿瑞', '云彩'];

export function renderUsers(state: UsersState) {
  const rows = users.filter((user) =>
    (state.platform === '全部' || user.platform === state.platform)
    && user.winRate >= state.minHit
    && (!state.query || `${user.name}${user.id}`.toLowerCase().includes(state.query.toLowerCase())),
  );

  let html = pageHeader('USER DIRECTORY', '用户中心', '按平台与表现筛选发单用户，查看历史战绩与跟单表现');
  html += '<div class="user-tabs"><button class="active">用户目录</button><button>新用户观察</button></div>';
  html += `<div class="filter-toolbar"><div class="search-box wide"><span>⌕</span><input data-input="users-query" value="${esc(state.query)}" placeholder="搜索用户名 / 用户 ID" /></div>${select('平台', 'users-platform', state.platform, platforms)}${select('最低命中率', 'users-min-hit', String(state.minHit), ['0', '60', '65', '70'], (value) => `${value}%`)}${select('收益范围', 'noop', '全部', ['全部', '正收益', '高收益'])}${select('近期状态', 'noop2', '全部', ['全部', '连红', '回撤'])}${select('主要玩法', 'noop3', '全部', ['全部', '胜平负', '让球胜平负', '比分'])}</div>`;

  const table = `<div class="table-wrap"><table class="user-table"><thead><tr><th>用户</th><th>近10场</th><th>连红</th><th>历史战绩</th><th>月回报</th><th>今日发单</th><th>跟单人数</th><th>跟单总额</th><th>画像标签</th><th>关注</th></tr></thead><tbody>${rows.map((user) => `<tr><td><button class="user-cell" data-open-user="${esc(user.id)}">${avatar(user.avatar, user.name)}<span><b>${esc(user.name)}</b><small>${esc(user.platform)} · ID ${esc(user.id)}</small></span></button></td><td><div class="recent-dots" aria-label="近10场战绩">${user.recent.map((hit) => `<i class="${hit ? 'hit' : 'miss'}" title="${hit ? '命中' : '未命中'}"></i>`).join('')}</div></td><td><b class="${user.streak > 0 ? 'positive' : 'negative'}">${user.streak}</b></td><td>${esc(user.record)}</td><td class="${user.monthlyRoi >= 0 ? 'positive' : 'negative'}">${user.monthlyRoi > 0 ? '+' : ''}${user.monthlyRoi.toFixed(1)}%</td><td>${user.todayPlans}</td><td>${user.followers.toLocaleString()}</td><td>${money(user.followAmount)}</td><td><div class="tag-row">${user.tags.slice(0, 2).map((tag) => `<span>${esc(tag)}</span>`).join('')}</div></td><td><button class="follow-btn ${state.followed.has(user.id) ? 'active' : ''}" data-follow="${esc(user.id)}">${state.followed.has(user.id) ? '★ 已关注' : '☆ 关注'}</button></td></tr>`).join('')}</tbody></table></div>`;
  html += panel('用户列表', table, `<span class="muted">${rows.length} 位用户</span>`);

  const selected = users.find((user) => user.id === state.selectedUser);
  if (selected) {
    const orders = userOrders.slice().reverse();
    html += drawer('用户详情', `<div class="detail-stack"><div class="user-detail-head">${avatar(selected.avatar, selected.name, 'large')}<div><h2>${esc(selected.name)}</h2><span>${esc(selected.platform)} · 用户 ID ${esc(selected.id)}</span></div><button class="follow-btn ${state.followed.has(selected.id) ? 'active' : ''}" data-follow="${esc(selected.id)}">${state.followed.has(selected.id) ? '★ 已关注' : '☆ 关注'}</button></div><div class="detail-grid">${metric('历史战绩', selected.record)}${metric('命中率', `${selected.winRate}%`)}${metric('自购金额', money(selected.selfBuy))}${metric('跟单人数', selected.followers.toLocaleString())}${metric('累计盈利', money(selected.profit), '', 'success')}${metric('ROI', `+${selected.roi}%`, '', 'success')}</div>${panel('历史发单方案', `<div class="table-wrap"><table><thead><tr><th>比赛队伍</th><th>玩法</th><th>投注项</th><th>SP赔率</th><th>赛果</th></tr></thead><tbody>${orders.map((order) => `<tr><td>${esc(order.match)}</td><td>${esc(order.play)}</td><td>${esc(order.pick)}</td><td>${esc(order.sp)}</td><td>${badge(order.result, order.result === '已中奖' ? 'danger' : order.result === '未中奖' ? 'dark' : 'pending')}</td></tr>`).join('')}</tbody></table></div>`)}</div>`);
  }
  return html;
}

function select(label: string, key: string, value: string, items: string[], format: (value: string) => string = (item) => item) {
  return `<label class="select-field"><span>${label}</span><select data-select="${key}">${items.map((item) => `<option value="${esc(item)}" ${item === value ? 'selected' : ''}>${esc(format(item))}</option>`).join('')}</select></label>`;
}
