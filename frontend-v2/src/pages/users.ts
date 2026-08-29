import { users, userDetail, userOrders, type UserOrderDetail } from '../services/users.js';
import { avatar, badge, metric, pageHeader, panel } from '../components/ui.js';
import { money } from '../utils/format.js';
import { esc } from '../utils/dom.js';

export interface UsersState { query: string; platform: string; minHit: number; selectedUser: string | null; followed: Set<string> }
const platforms = ['全部', '彩站云', '州运宝', '鸿瑞', '云彩'];

export function renderUsers(state: UsersState) {
  const rows = users.filter((user) => (state.platform === '全部' || user.platform === state.platform) && user.winRate >= state.minHit && (!state.query || `${user.name}${user.id}`.toLowerCase().includes(state.query.toLowerCase())));
  let html = pageHeader('USER DIRECTORY', '用户中心', '按平台与表现筛选发单用户，查看历史战绩与跟单表现');
  html += '<div class="user-tabs"><button class="active">用户目录</button><button>新用户观察</button></div>';
  html += `<div class="filter-toolbar"><div class="search-box wide"><span>⌕</span><input data-input="users-query" value="${esc(state.query)}" placeholder="搜索用户名 / 用户 ID" /></div>${select('平台', 'users-platform', state.platform, platforms)}${select('最低命中率', 'users-min-hit', String(state.minHit), ['0', '60', '65', '70'], (value) => `${value}%`)}${select('收益范围', 'noop', '全部', ['全部', '正收益', '高收益'])}${select('近期状态', 'noop2', '全部', ['全部', '连红', '回撤'])}${select('主要玩法', 'noop3', '全部', ['全部', '胜平负', '让球胜平负', '比分'])}</div>`;

  const table = `<div class="table-wrap"><table class="user-table"><thead><tr><th>用户</th><th>近10场</th><th>连红</th><th>历史战绩</th><th>月回报</th><th>今日发单</th><th>跟单人数</th><th>跟单总额</th><th>画像标签</th><th>关注</th></tr></thead><tbody>${rows.map((user) => `<tr class="clickable" data-open-user="${esc(user.id)}"><td><span class="user-cell">${avatar(user.avatar, user.name)}<span><b>${esc(user.name)}</b><small>${esc(user.platform)} · ID ${esc(user.id)}</small></span></span></td><td><div class="recent-dots" aria-label="近10场战绩">${user.recent.map((hit) => `<i class="${hit ? 'hit' : 'miss'}" title="${hit ? '命中' : '未命中'}"></i>`).join('')}</div></td><td><b class="${user.streak > 0 ? 'positive' : 'negative'}">${user.streak}</b></td><td>${esc(user.record)}</td><td class="${user.monthlyRoi >= 0 ? 'positive' : 'negative'}">${user.monthlyRoi > 0 ? '+' : ''}${user.monthlyRoi.toFixed(1)}%</td><td>${user.todayPlans}</td><td>${user.followers.toLocaleString()}</td><td>${money(user.followAmount)}</td><td><div class="tag-row">${user.tags.slice(0, 2).map((tag) => `<span>${esc(tag)}</span>`).join('')}</div></td><td><button class="follow-btn ${state.followed.has(user.id) ? 'active' : ''}" data-follow="${esc(user.id)}">${state.followed.has(user.id) ? '★ 已关注' : '☆ 关注'}</button></td></tr>`).join('')}</tbody></table></div>`;
  html += panel('用户列表', table, `<span class="muted">${rows.length} 位用户</span>`);

  const selected = users.find((user) => user.id === state.selectedUser);
  if (selected) html += userDetailModal(selected, state.followed.has(selected.id));
  return html;
}

function userDetailModal(user: (typeof users)[number], followed: boolean) {
  const detail = userDetail.user;
  const orders = userDetail.orders.length ? userDetail.orders : userOrders;
  const value = (key: string, fallback: string | number) => detail && detail[key] !== undefined && detail[key] !== null ? detail[key] as string | number : fallback;
  const recent = Array.isArray(detail?.recent10) ? detail.recent10 : user.recent;
  return `<div class="drawer-layer user-modal-layer"><button class="drawer-mask" data-action="close-drawer" aria-label="关闭用户详情"></button><aside class="drawer user-detail-modal" role="dialog" aria-modal="true" style="width:min(1180px,96vw);height:min(92vh,900px);align-self:center;border-radius:12px;overflow:hidden"><div class="user-modal-banner"><div><strong>${esc(user.name)}</strong><span>${esc(user.platform)} · 用户详情</span></div><button class="icon-btn" data-action="close-drawer" aria-label="关闭">×</button></div><div class="drawer-body"><div class="user-profile-card"><div class="user-profile-main">${avatar(String(value('avatar_url', user.avatar)), user.name, 'large')}<div><span class="eyebrow">SENDER PROFILE</span><h2>${esc(String(value('nickname', user.name)))}</h2><small>${esc(user.platform)} · 用户 ID ${esc(user.id)}</small></div><button class="follow-btn ${followed ? 'active' : ''}" data-follow="${esc(user.id)}">${followed ? '★ 已关注' : '☆ 关注'}</button></div><div class="recent-summary"><span>全部订单 · 近10单</span><div class="recent-dots">${recent.slice(0, 10).map((item) => `<i class="${item === true || item === '赢' || item === '命中' ? 'hit' : 'miss'}"></i>`).join('')}</div><b>${recent.length}中${recent.filter((item) => item === true || item === '赢' || item === '命中').length}</b></div></div><div class="detail-grid user-stat-grid">${metric('连红', value('current_streak', user.streak))}${metric('月回报', `${value('month_roi', user.monthlyRoi)}%`)}${metric('累计方案', value('total_orders', user.todayPlans))}${metric('关注人数', value('follow_num', user.followers))}${metric('跟单金额', money(Number(value('total_stake', user.followAmount))))}${metric('累计奖金', money(Number(value('total_profit', user.profit))))}${metric('7日自购', money(Number(value('self_buy7d', user.selfBuy))))}</div><section class="panel history-panel"><div class="panel-head"><h2>已入库历史 · 玩法明细</h2><span class="muted">${orders.length} 张方案 · 按发单时间倒序</span></div><div class="table-wrap"><table class="user-history-table"><thead><tr><th>发单时间</th><th>场次</th><th>比赛队伍</th><th>玩法</th><th>投注项</th><th>SP赔率</th><th>赛果</th><th>过关玩法</th><th>预计回报</th><th>投注倍数</th><th>自购金额</th><th>跟单人数</th><th>订单结果</th></tr></thead><tbody>${orders.map((order) => historyRow(order)).join('')}</tbody></table></div></section></div></aside></div>`;
}

function historyRow(order: UserOrderDetail) {
  const result = order.result || '待开奖';
  const won = result === '已中奖' || result === '中奖';
  return `<tr><td>${esc(order.publish_time || '--')}</td><td>${order.match_count || 1}</td><td>${esc(order.match_name || '--')}</td><td>${esc(order.play_type || '--')}</td><td class="${won ? 'positive' : ''}">${esc(order.selection || '--')}</td><td>${esc(order.odds_text || (order.odds === undefined ? '--' : String(order.odds)))}</td><td class="${won ? 'positive' : result === '未中奖' ? 'negative' : ''}">${esc(result)}</td><td>${esc(order.pass_summary || '--')}</td><td>${order.expected_bonus === undefined ? '--' : money(order.expected_bonus)}</td><td>${order.lot_multi || '--'}</td><td>${order.stake === undefined ? '--' : money(order.stake)}</td><td>${order.follow_num || 0}</td><td>${badge(won ? `中奖 ${money(order.bonus || order.profit || 0)}` : result === '未中奖' ? '未中奖' : '待结算', won ? 'danger' : result === '未中奖' ? 'dark' : 'pending')}</td></tr>`;
}

function select(label: string, key: string, value: string, items: string[], format: (value: string) => string = (item) => item) {
  return `<label class="select-field"><span>${label}</span><select data-select="${key}">${items.map((item) => `<option value="${esc(item)}" ${item === value ? 'selected' : ''}>${esc(format(item))}</option>`).join('')}</select></label>`;
}
