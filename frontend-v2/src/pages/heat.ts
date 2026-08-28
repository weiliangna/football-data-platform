import type { BettingPlay, HotPlayRow } from '../types/index.js';
import { badge, pageHeader, panel, segmented } from '../components/ui.js';
import { esc } from '../utils/dom.js';

export interface HeatState { play: BettingPlay }

const plays: BettingPlay[] = ['胜平负', '让球胜平负', '半全场', '比分'];
const colors: Record<BettingPlay, string> = {
  胜平负: 'accent-blue',
  让球胜平负: 'rose',
  半全场: 'orange',
  比分: 'teal',
};

export const hot: Record<BettingPlay, HotPlayRow[]> = {
  胜平负: [
    { rank: 1, match: '皇家马德里 vs 塞维利亚', time: '20:00', league: '西甲', pick: '主胜', count: 188 },
    { rank: 2, match: '利物浦 vs 热刺', time: '00:30', league: '英超', pick: '主胜', count: 146 },
    { rank: 3, match: '巴黎 vs 里昂', time: '23:00', league: '法甲', pick: '主胜', count: 132 },
  ],
  让球胜平负: [
    { rank: 1, match: '阿森纳 vs 切尔西', time: '19:30', league: '英超', pick: '让胜', count: 126 },
    { rank: 2, match: '拜仁 vs 多特', time: '21:00', league: '德甲', pick: '让平', count: 98 },
    { rank: 3, match: '曼城 vs 国际米兰', time: '23:30', league: '欧冠', pick: '让胜', count: 84 },
  ],
  半全场: [
    { rank: 1, match: '巴黎 vs 里昂', time: '23:00', league: '法甲', pick: '胜/胜', count: 72 },
    { rank: 2, match: '皇马 vs 塞维利亚', time: '20:00', league: '西甲', pick: '胜/胜', count: 66 },
    { rank: 3, match: '拜仁 vs 多特', time: '21:00', league: '德甲', pick: '平/胜', count: 51 },
  ],
  比分: [
    { rank: 1, match: '拜仁 vs 多特', time: '21:00', league: '德甲', pick: '2:1', count: 55 },
    { rank: 2, match: '阿森纳 vs 切尔西', time: '19:30', league: '英超', pick: '2:0', count: 48 },
    { rank: 3, match: '巴萨 vs 比利亚雷亚尔', time: '01:00', league: '西甲', pick: '3:1', count: 44 },
  ],
};

const heatStyles = `<style>
.heat-insight-list{display:grid;gap:8px;padding:12px;width:100%;max-width:none;min-width:0}
.heat-insight-row{display:grid;grid-template-columns:28px minmax(170px,1fr) minmax(78px,auto) 112px 52px;gap:10px;align-items:center;width:100%;min-width:0;padding:11px 10px;border:1px solid var(--border);border-radius:8px;background:#fff;transition:.18s ease}
.heat-insight-row:hover{border-color:#b9cae3;box-shadow:0 5px 14px rgba(35,55,88,.08);transform:translateY(-1px)}
.heat-insight-rank{width:24px;height:24px;border-radius:6px;display:grid;place-items:center;background:#f1f4f8;color:var(--muted);font-size:10px;font-weight:800}
.heat-insight-row:first-child .heat-insight-rank{background:#eef4ff;color:var(--brand-primary)}
.heat-insight-match{min-width:0}
.heat-insight-match b{display:block;font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.heat-insight-match small{display:block;margin-top:4px;color:var(--muted);font-size:9px}
.heat-insight-pick{display:inline-flex;justify-content:center;align-items:center;min-width:58px;padding:5px 8px;border-radius:5px;background:#f4f7fb;color:var(--foreground);font-size:11px;font-weight:750;white-space:nowrap}
.heat-insight-bar{height:6px;background:#eef2f6;border-radius:999px;overflow:hidden}
.heat-insight-bar i{display:block;height:100%;border-radius:999px;background:var(--brand-primary)}
.heat-insight-count{text-align:right;color:var(--brand-primary);font-size:11px;font-weight:750;white-space:nowrap}
.center-analysis{display:block;width:100%;padding:0 12px 10px;min-width:0}
.center-analysis .heat-insight-list{padding:10px 0 0}
.center-analysis .heat-insight-row{max-width:none}
.hot-play-card{display:block;min-width:0}
.hot-play-title{display:flex;align-items:center;justify-content:space-between;min-width:0;white-space:nowrap}
.hot-play-title b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hot-play-grid .heat-insight-list{padding:0}
.hot-play-card .heat-insight-row{grid-template-columns:26px minmax(0,1fr) auto 72px;gap:8px;padding:9px 0;border:0;border-radius:0;border-bottom:1px solid #eef1f5;box-shadow:none;transform:none}
.hot-play-card .heat-insight-row:last-child{border-bottom:0}
.hot-play-card .heat-insight-bar{display:none}
.hot-play-card .heat-insight-pick{min-width:52px;padding:4px 6px;font-size:10px}
.center-analysis.rose .heat-insight-bar i,.hot-play-card.rose .heat-insight-bar i{background:var(--rose)}
.center-analysis.orange .heat-insight-bar i,.hot-play-card.orange .heat-insight-bar i{background:var(--warning)}
.center-analysis.teal .heat-insight-bar i,.hot-play-card.teal .heat-insight-bar i{background:var(--teal)}
@media(max-width:700px){.heat-insight-row{grid-template-columns:25px minmax(0,1fr) auto;gap:8px}.heat-insight-bar{grid-column:2}.heat-insight-count{grid-column:3;grid-row:1}.hot-play-card .heat-insight-row{grid-template-columns:24px minmax(0,1fr) auto}}
</style>`;

function insightRow(row: HotPlayRow, index: number, compact = false): string {
  const bar = Math.max(20, 92 - index * 18);
  return `<div class="heat-insight-row">
    <span class="heat-insight-rank">${row.rank}</span>
    <div class="heat-insight-match"><b>${esc(row.match)}</b><small>${esc(row.league)} · ${esc(row.time)}</small></div>
    <span class="heat-insight-pick">${esc(row.pick)}</span>
    ${compact ? '' : `<div class="heat-insight-bar" aria-hidden="true"><i style="width:${bar}%"></i></div>`}
    <span class="heat-insight-count">${row.count} 次</span>
  </div>`;
}

export function renderHeat(state: HeatState): string {
  const active = hot[state.play] || [];
  const analysis = `<div class="center-analysis ${colors[state.play]}"><div class="heat-insight-list">${active.length ? active.map((row, index) => insightRow(row, index)).join('') : '<div class="empty-inline">今日暂无该玩法数据</div>'}</div></div>`;
  const fund = `<div class="fund-heat"><div class="fund-head"><b>阿森纳 vs 切尔西</b>${badge('进行中', 'live')}</div>${[['主胜', 68, 128400], ['平局', 19, 35800], ['客胜', 13, 24600]].map(([label, value, amount]) => `<div class="fund-row"><span>${label}</span><div class="horizontal-bar"><i style="width:${value}%"></i></div><b>${value}%</b><small>¥${Number(amount).toLocaleString()}</small></div>`).join('')}</div>`;
  const cards = plays.map((play) => `<section class="hot-play-card ${colors[play]}"><div class="hot-play-title"><b>${esc(play)}</b><span>TOP 3</span></div><div class="heat-insight-list">${hot[play].length ? hot[play].map((row, index) => insightRow(row, index, true)).join('') : '<div class="empty-inline">今日暂无该玩法数据</div>'}</div></section>`).join('');

  return `${heatStyles}${pageHeader('BETTING HEAT', '投注热力', '各玩法重心、单场资金热力与热门玩法聚合')}
    <div class="play-summary-grid">${plays.map((play, index) => `<button data-heat-play="${esc(play)}" class="play-summary ${colors[play]} ${state.play === play ? 'active' : ''}"><span>${esc(play)}</span><strong>${[48, 27, 14, 11][index]}%</strong><small>今日方案占比</small></button>`).join('')}</div>
    <div class="bottom-grid">${panel('各玩法重心分析', analysis, segmented(plays, state.play, 'heat-play'))}${panel('单场资金热力', fund)}</div>
    ${panel('今日热门玩法 · 聚合汇总', `<div class="hot-play-grid">${cards}</div>`)}`;
}
