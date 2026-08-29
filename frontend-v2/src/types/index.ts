export type MatchStatus = '未开赛' | '进行中' | '已结束';
export type Trend = 'up' | 'down' | 'flat';

export interface OddsPoint {
  label: string;
  value: string;
  trend?: Trend;
}

export interface Match {
  id: string;
  time: string;
  league: string;
  home: string;
  away: string;
  score: string;
  status: MatchStatus;
  euro: OddsPoint[];
  asian: string;
  totals: string;
  plans: number;
  heat: number;
  anomaly?: string;
  category?: '竞彩' | '其他';
}

export interface Plan {
  id: string;
  platform: string;
  user: string;
  userId: string;
  avatar: string;
  match: string;
  league: string;
  play: string;
  pick: string;
  amount: number;
  /** Kept for API compatibility; the UI displays sp instead. */
  multiple: number;
  sp: string;
  publishAt: string;
  cutoffAt: string;
  status: '进行中' | '已结算' | '待开奖';
  result: '已中奖' | '未中奖' | '待开奖' | '走盘';
  expectedProfit: number;
}

export interface User {
  id: string;
  platformId?: number;
  name: string;
  platform: string;
  recent: boolean[];
  streak: number;
  record: string;
  monthlyRoi: number;
  todayPlans: number;
  followers: number;
  followAmount: number;
  tags: string[];
  followed: boolean;
  winRate: number;
  selfBuy: number;
  profit: number;
  roi: number;
  avatar: string;
}

export interface Result {
  id: string;
  user: string;
  record: string;
  selfBuy: number;
  followers: number;
  payout: number;
  bets: number;
  detail: string;
  result: '已中奖' | '未中奖' | '待开奖' | '走盘';
  date: string;
  odds: number;
}

export type BettingPlay = '胜平负' | '让球胜平负' | '半全场' | '比分';

export interface HotPlayRow {
  rank: number;
  match: string;
  time: string;
  league: string;
  pick: string;
  count: number;
}

export interface PlatformStatus {
  id: string;
  platform: string;
  collectStatus: '正常' | '部分成功' | '采集失败' | '等待同步' | '缺少配置' | '已停用';
  runStatus: string;
  lastSync: string;
  added: number;
  duplicates: number;
  failed: number;
  latency: number;
  config: string;
  alert?: string;
}

export interface DashboardMetrics {
  matches: number;
  live: number;
  plans: number;
  users: number;
  anomalies: number;
  hot: number;
  completed: number;
}

export interface TimelineRow {
  time: string;
  company: string;
  initial: string;
  current: string;
  direction: '升盘' | '降盘' | '不变';
  note: string;
}
