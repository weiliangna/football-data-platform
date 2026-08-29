import { dashboardMetrics, hotUsers, matches } from './dashboard.js';
import { plans } from './plans.js';
import { users } from './users.js';
import { results } from './results.js';
import { hot } from '../pages/heat.js';
import { analysisCards, analysisMatch, timeline } from './analysis.js';
import { news } from './news.js';
import type { Plan, Match } from '../types/index.js';

type JsonRow = Record<string, unknown>;

function isRow(value: unknown): value is JsonRow {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function rowsFromPayload(payload: { data?: unknown }): JsonRow[] {
  const body = payload.data;
  if (Array.isArray(body)) return body.filter(isRow);
  if (!isRow(body)) return [];
  const nested = body.items ?? body.data;
  return Array.isArray(nested) ? nested.filter(isRow) : [];
}

function text(value: unknown, fallback = '--') {
  const result = String(value ?? '').trim();
  return result || fallback;
}

function number(value: unknown, fallback = 0) {
  const result = Number(value);
  return Number.isFinite(result) ? result : fallback;
}

/** Loads the existing FastAPI dashboard without changing its response contract. */
export async function loadDashboard(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/dashboard', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: { metrics?: Record<string, unknown>; sender_ranking?: unknown } };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const metrics = payload.data?.metrics;
    if (!metrics) return false;
    const map: Record<string, string> = { matches: 'matches', live: 'live', plans: 'plans', users: 'users', anomalies: 'anomalies', hot: 'hot', completed: 'completed' };
    for (const [target, source] of Object.entries(map)) {
      const value = Number(metrics[source]);
      if (Number.isFinite(value)) (dashboardMetrics as unknown as Record<string, number>)[target] = value;
    }
    if (Array.isArray(payload.data?.sender_ranking)) {
      const ranking = payload.data.sender_ranking.filter(isRow);
      const liveUsers = ranking.slice(0, hotUsers.length).map((row) => ({
        name: text(row.nickname ?? row.username, '未知用户'),
        platform: text(row.platform_name ?? row.platform),
        winRate: number(row.history_hit_rate ?? row.hit_rate),
        roi: number(row.roi ?? row.monthly_roi),
        plans: number(row.order_count ?? row.today_orders),
        avatar: text(row.avatar_url ?? row.avatar, ''),
      }));
      if (liveUsers.length) (hotUsers as unknown as Array<Record<string, unknown>>).splice(0, hotUsers.length, ...liveUsers);
    }
    return true;
  } catch {
    return false;
  }
}

export async function loadPlans(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/schemes?page=1&page_size=50', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const rows = rowsFromPayload(payload);
    if (!rows.length) return false;
    plans.splice(0, plans.length, ...rows.map((row, index) => ({
      id: text(row.id ?? row.order_id, `LIVE-${index}`),
      platform: text(row.platform_name ?? row.platform),
      user: text(row.nickname ?? row.username, '未知用户'),
      userId: text(row.user_id),
      avatar: text(row.avatar_url ?? row.avatar, ''),
      match: text(row.match_name ?? row.match),
      league: text(row.league),
      play: text(row.play_type ?? row.play),
      pick: text(row.selection ?? row.pick),
      amount: number(row.stake ?? row.amount ?? row.self_buy),
      multiple: number(row.multiple ?? row.lot_multi ?? row.bet_count, 1),
      sp: text(row.sp ?? row.odds_text ?? row.odds ?? row.sp_odds ?? row.expected_odds),
      publishAt: text(row.publish_time ?? row.created_time),
      cutoffAt: text(row.deadline_time, ''),
      status: text(row.status, '进行中') as Plan['status'],
      result: text(row.result, '待开奖') as Plan['result'],
      expectedProfit: number(row.expected_bonus ?? row.expected_profit ?? row.profit),
    })));
    return true;
  } catch {
    return false;
  }
}

export async function loadMatches(): Promise<boolean> {
  try {
    const response = await fetch('/api/matches?page=1&page_size=50', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const rows = rowsFromPayload(payload);
    if (!rows.length) return false;
    matches.splice(0, matches.length, ...rows.map((row, index) => ({
      id: text(row.id ?? row.match_id, `LIVE-MATCH-${index}`),
      time: text(row.match_time ?? row.kickoff ?? row.start_time),
      league: text(row.league ?? row.league_name),
      home: text(row.home_team ?? row.home),
      away: text(row.away_team ?? row.away),
      score: text(row.score, '- : -'),
      status: text(row.status, '未开赛') as Match['status'],
      euro: [],
      asian: text(row.asian),
      totals: text(row.totals),
      plans: number(row.plan_count ?? row.schemes),
      heat: number(row.heat ?? row.heat_score),
      category: '其他' as const,
    })));
    return true;
  } catch {
    return false;
  }
}

export async function loadUsers(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/users?page=1&page_size=50', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const rows = rowsFromPayload(payload);
    if (!rows.length) return false;
    users.splice(0, users.length, ...rows.map((row, index) => ({
      id: text(row.user_id ?? row.id, `LIVE-USER-${index}`),
      name: text(row.nickname ?? row.username, '未知用户'),
      platform: text(row.platform_name ?? row.platform),
      recent: Array.isArray(row.recent) ? row.recent.map(Boolean) : [],
      streak: number(row.streak ?? row.current_streak),
      record: text(row.history_record ?? row.record),
      monthlyRoi: number(row.monthly_roi ?? row.roi),
      todayPlans: number(row.today_orders ?? row.order_count),
      followers: number(row.followers ?? row.follow_num),
      followAmount: number(row.follow_amount ?? row.total_follow_amount),
      tags: Array.isArray(row.tags) ? row.tags.map(String) : [],
      followed: Boolean(row.followed),
      winRate: number(row.history_hit_rate ?? row.hit_rate),
      selfBuy: number(row.self_buy),
      profit: number(row.profit),
      roi: number(row.roi),
      avatar: text(row.avatar_url ?? row.avatar, ''),
    })));
    return true;
  } catch {
    return false;
  }
}

export async function loadResults(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/results?page=1&page_size=50', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const rows = rowsFromPayload(payload);
    if (!rows.length) return false;
    results.splice(0, results.length, ...rows.map((row, index) => ({
      id: text(row.id ?? row.order_id, `LIVE-RESULT-${index}`),
      user: text(row.nickname ?? row.username, '未知用户'),
      record: text(row.history_record ?? row.record),
      selfBuy: number(row.self_buy ?? row.stake),
      followers: number(row.follow_num ?? row.followers),
      payout: number(row.bonus ?? row.payout),
      bets: number(row.bet_count ?? row.bets),
      detail: text(row.detail ?? row.selection),
      result: text(row.result, '待开奖') as never,
      date: text(row.date ?? row.publish_time),
      odds: number(row.odds ?? row.odds_text),
    })));
    return true;
  } catch {
    return false;
  }
}

export async function loadHeatmap(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/heatmap?page=1&page_size=100', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const rows = rowsFromPayload(payload);
    if (!rows.length) return false;
    const groups: Record<string, Array<{ rank: number; match: string; time: string; league: string; pick: string; count: number }>> = {};
    Object.keys(hot).forEach((key) => { groups[key] = []; });
    rows.forEach((row, index) => {
      const play = text(row.play_type ?? row.play, '');
      if (!(play in groups)) return;
      groups[play].push({ rank: index + 1, match: text(row.match_name ?? row.match), time: text(row.match_time ?? row.time), league: text(row.league), pick: text(row.selection ?? row.option), count: number(row.count) });
    });
    for (const key of Object.keys(hot) as Array<keyof typeof hot>) if (groups[key].length) hot[key].splice(0, hot[key].length, ...groups[key]);
    return true;
  } catch {
    return false;
  }
}

export async function loadAnalysis(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/analysis', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: Record<string, unknown> };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const data = payload.data || {};
    const match = (data.match || data) as Record<string, unknown>;
    if (match.home || match.home_team) {
      analysisMatch.home = text(match.home ?? match.home_team);
      analysisMatch.away = text(match.away ?? match.away_team);
      analysisMatch.league = text(match.league ?? match.league_name);
      analysisMatch.kickoff = text(match.kickoff ?? match.match_time);
      analysisMatch.score = text(match.score, '—');
    }
    const cardRows = Array.isArray(data.cards) ? data.cards : [];
    if (cardRows.length) analysisCards.splice(0, analysisCards.length, ...cardRows.filter(isRow).map((row) => ({ label: text(row.label), value: text(row.value), meta: text(row.meta, '') })));
    const timelineRows = Array.isArray(data.timeline) ? data.timeline : [];
    if (timelineRows.length) timeline.splice(0, timeline.length, ...(timelineRows as typeof timeline));
    return true;
  } catch {
    return false;
  }
}

export async function loadNews(matchId?: string): Promise<boolean> {
  try {
    const query = matchId ? `?match_id=${encodeURIComponent(matchId)}` : '';
    const response = await fetch(`/api/news${query}`, { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const rows = rowsFromPayload(payload);
    if (!rows.length) return false;
    news.splice(0, news.length, ...rows.map((row, index) => ({ id: text(row.id, `LIVE-NEWS-${index}`), title: text(row.title ?? row.content), time: text(row.time ?? row.publish_time), category: text(row.category, '赛事资讯'), matchId: row.match_id ? String(row.match_id) : undefined })));
    return true;
  } catch {
    return false;
  }
}
