import { dashboardMetrics, matches } from './dashboard.js';
import { plans } from './plans.js';
import { users } from './users.js';
import { results } from './results.js';
import { hot } from '../pages/heat.js';
import { analysisCards, analysisMatch, timeline } from './analysis.js';
import { news } from './news.js';
import type { Plan } from '../types/index.js';
import type { Match } from '../types/index.js';

/** Loads the existing FastAPI dashboard without changing its response contract. */
export async function loadDashboard(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/dashboard', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: { metrics?: Record<string, unknown> } };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const metrics = payload.data?.metrics;
    if (!metrics) return false;
    const map:Record<string,string>={matches:'matches',live:'live',plans:'plans',users:'users',anomalies:'anomalies',hot:'hot',completed:'completed'};
    for (const [target, source] of Object.entries(map)) {
      const value = Number(metrics[source]);
      if (Number.isFinite(value)) (dashboardMetrics as unknown as Record<string, number>)[target] = value;
    }
    return true;
  } catch { return false; }
}

export async function loadPlans(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/schemes?page=1&page_size=50', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const body = payload.data as { items?: Record<string, unknown>[]; data?: Record<string, unknown>[] } | Record<string, unknown>[] | undefined;
    const rows = Array.isArray(body) ? body : body?.items || body?.data || [];
    if (!rows.length) return false;
    plans.splice(0, plans.length, ...rows.map((row, index) => ({
      id: String(row.id ?? row.order_id ?? `LIVE-${index}`),
      platform: String(row.platform_name ?? row.platform ?? '--'),
      user: String(row.nickname ?? row.username ?? '--'),
      userId: String(row.user_id ?? '--'),
      match: String(row.match_name ?? row.match ?? '--'),
      league: String(row.league ?? '--'),
      play: String(row.play_type ?? row.play ?? '--'),
      pick: String(row.selection ?? row.pick ?? '--'),
      amount: Number(row.stake ?? row.amount ?? 0) || 0,
      multiple: Number(row.multiple ?? row.bet_count ?? 1) || 1,
      publishAt: String(row.publish_time ?? row.created_time ?? '--'),
      cutoffAt: String(row.deadline_time ?? '--'),
      status: String(row.status ?? '进行中'),
      result: String(row.result ?? '待开奖'),
      expectedProfit: Number(row.profit ?? 0) || 0,
    } as Plan)));
    return true;
  } catch { return false; }
}

export async function loadMatches(): Promise<boolean> {
  try {
    const response = await fetch('/api/matches?page=1&page_size=50', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const body = payload.data as { items?: Record<string, unknown>[]; data?: Record<string, unknown>[] } | Record<string, unknown>[] | undefined;
    const rows = Array.isArray(body) ? body : body?.items || body?.data || [];
    if (!rows.length) return false;
    matches.splice(0, matches.length, ...rows.map((row, index) => ({
      id: String(row.id ?? row.match_id ?? `LIVE-MATCH-${index}`),
      time: String(row.match_time ?? row.kickoff ?? row.start_time ?? '--'),
      league: String(row.league ?? row.league_name ?? '--'),
      home: String(row.home_team ?? row.home ?? '--'),
      away: String(row.away_team ?? row.away ?? '--'),
      score: String(row.score ?? '- : -'),
      status: String(row.status ?? '未开始') as Match['status'],
      euro: [], asian: String(row.asian ?? '--'), totals: String(row.totals ?? '--'),
      plans: Number(row.plan_count ?? row.schemes ?? 0) || 0,
      heat: Number(row.heat ?? row.heat_score ?? 0) || 0,
      category: '其他',
    } as Match)));
    return true;
  } catch { return false; }
}

export async function loadUsers(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/users?page=1&page_size=50', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const body = payload.data as { items?: Record<string, unknown>[]; data?: Record<string, unknown>[] } | Record<string, unknown>[] | undefined;
    const rows = Array.isArray(body) ? body : body?.items || body?.data || [];
    if (!rows.length) return false;
    users.splice(0, users.length, ...rows.map((row, index) => ({
      id: String(row.user_id ?? row.id ?? `LIVE-USER-${index}`),
      name: String(row.nickname ?? row.username ?? '--'), platform: String(row.platform_name ?? row.platform ?? '--'),
      recent: [], streak: Number(row.streak ?? row.current_streak ?? 0) || 0,
      record: String(row.history_record ?? row.record ?? '--'), monthlyRoi: Number(row.monthly_roi ?? row.roi ?? 0) || 0,
      todayPlans: Number(row.today_orders ?? row.order_count ?? 0) || 0, followers: Number(row.followers ?? row.follow_num ?? 0) || 0,
      followAmount: Number(row.follow_amount ?? row.total_follow_amount ?? 0) || 0,
      tags: Array.isArray(row.tags) ? row.tags.map(String) : [], followed: Boolean(row.followed),
      winRate: Number(row.history_hit_rate ?? row.hit_rate ?? 0) || 0, selfBuy: Number(row.self_buy ?? 0) || 0,
      profit: Number(row.profit ?? 0) || 0, roi: Number(row.roi ?? 0) || 0, avatar: String(row.avatar_url ?? ''),
    })));
    return true;
  } catch { return false; }
}

export async function loadResults(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/results?page=1&page_size=50', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const body = payload.data as { items?: Record<string, unknown>[]; data?: Record<string, unknown>[] } | Record<string, unknown>[] | undefined;
    const rows = Array.isArray(body) ? body : body?.items || body?.data || [];
    if (!rows.length) return false;
    results.splice(0, results.length, ...rows.map((row, index) => ({
      id: String(row.id ?? row.order_id ?? `LIVE-RESULT-${index}`), user: String(row.nickname ?? row.username ?? '--'),
      record: String(row.history_record ?? row.record ?? '--'), selfBuy: Number(row.self_buy ?? row.stake ?? 0) || 0,
      followers: Number(row.follow_num ?? row.followers ?? 0) || 0, payout: Number(row.bonus ?? row.payout ?? 0) || 0,
      bets: Number(row.bet_count ?? row.bets ?? 0) || 0, detail: String(row.detail ?? row.selection ?? '--'),
      result: String(row.result ?? '待开奖') as never, date: String(row.date ?? row.publish_time ?? '--'), odds: Number(row.odds ?? row.odds_text ?? 0) || 0,
    })));
    return true;
  } catch { return false; }
}

export async function loadHeatmap(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/heatmap?page=1&page_size=100', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const body = payload.data as { items?: Record<string, unknown>[]; data?: Record<string, unknown>[] } | Record<string, unknown>[] | undefined;
    const rows = Array.isArray(body) ? body : body?.items || body?.data || [];
    if (!rows.length) return false;
    const groups:Record<string,Array<{rank:number;match:string;time:string;league:string;pick:string;count:number}>> = {};
    Object.keys(hot).forEach((key) => { groups[key] = []; });
    rows.forEach((row, index) => {
      const play = String(row.play_type ?? row.play ?? '');
      if (!(play in groups)) return;
      groups[play].push({ rank: index + 1, match: String(row.match_name ?? row.match ?? '--'), time: String(row.match_time ?? row.time ?? '--'), league: String(row.league ?? '--'), pick: String(row.selection ?? row.option ?? '--'), count: Number(row.count ?? 0) || 0 });
    });
    for (const key of Object.keys(hot) as Array<keyof typeof hot>) if (groups[key].length) hot[key].splice(0, hot[key].length, ...groups[key]);
    return true;
  } catch { return false; }
}

export async function loadAnalysis(): Promise<boolean> {
  try {
    const response = await fetch('/api/portal/analysis', { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: Record<string, unknown> };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const data = payload.data || {};
    const match = (data.match || data) as Record<string, unknown>;
    if (match.home || match.home_team) { analysisMatch.home = String(match.home ?? match.home_team); analysisMatch.away = String(match.away ?? match.away_team ?? '--'); analysisMatch.league = String(match.league ?? match.league_name ?? '--'); analysisMatch.kickoff = String(match.kickoff ?? match.match_time ?? '--'); analysisMatch.score = String(match.score ?? '—'); }
    const cardRows = Array.isArray(data.cards) ? data.cards : [];
    if (cardRows.length) { analysisCards.splice(0, analysisCards.length, ...cardRows.map((row) => ({ label: String((row as Record<string, unknown>).label ?? '--'), value: String((row as Record<string, unknown>).value ?? '--'), meta: String((row as Record<string, unknown>).meta ?? '') }))); }
    const timelineRows = Array.isArray(data.timeline) ? data.timeline : [];
    if (timelineRows.length) timeline.splice(0, timeline.length, ...(timelineRows as typeof timeline));
    return true;
  } catch { return false; }
}

export async function loadNews(matchId?: string): Promise<boolean> {
  try {
    const query = matchId ? `?match_id=${encodeURIComponent(matchId)}` : '';
    const response = await fetch(`/api/news${query}`, { headers: { Accept: 'application/json' }, credentials: 'include' });
    if (!response.ok) return false;
    const payload = await response.json() as { code?: number; data?: unknown };
    if (payload.code !== undefined && payload.code !== 200) return false;
    const body = payload.data as { items?: Record<string, unknown>[]; data?: Record<string, unknown>[] } | Record<string, unknown>[] | undefined;
    const rows = Array.isArray(body) ? body : body?.items || body?.data || [];
    if (!rows.length) return false;
    news.splice(0, news.length, ...rows.map((row, index) => ({ id: String(row.id ?? `LIVE-NEWS-${index}`), title: String(row.title ?? row.content ?? '--'), time: String(row.time ?? row.publish_time ?? '--'), category: String(row.category ?? '赛事资讯'), matchId: row.match_id ? String(row.match_id) : undefined })));
    return true;
  } catch { return false; }
}
