import type { User } from '../types/index.js';

const seed: User[] = [
  { id: '30481', name: '足球老炮', platform: '彩站云', recent: [true, true, false, true, true, true, false, true, true, true], streak: 4, record: '182中26', monthlyRoi: 18.6, todayPlans: 8, followers: 1260, followAmount: 862000, tags: ['稳定', '英超', '让球'], followed: true, winRate: 69.2, selfBuy: 184000, profit: 52600, roi: 28.6, avatar: '' },
  { id: '88217', name: '稳坐钓鱼台', platform: '州运宝', recent: [true, false, true, true, true, false, true, true, true, false], streak: 3, record: '205中37', monthlyRoi: 16.2, todayPlans: 6, followers: 980, followAmount: 641500, tags: ['连红', '西甲'], followed: false, winRate: 66.8, selfBuy: 152300, profit: 42180, roi: 27.7, avatar: '' },
  { id: '343850', name: '沃奇尼亚', platform: '彩站云', recent: [true, true, true, false, true, false, true, true, false, true], streak: 1, record: '166中08', monthlyRoi: 13.8, todayPlans: 5, followers: 754, followAmount: 433200, tags: ['比分', '高回报'], followed: false, winRate: 65.1, selfBuy: 126800, profit: 33880, roi: 26.7, avatar: '' },
  { id: '56803', name: '红王', platform: '鸿瑞', recent: [true, true, false, true, true, false, true, true, true, true], streak: 4, record: '143中17', monthlyRoi: 12.5, todayPlans: 7, followers: 690, followAmount: 392800, tags: ['半全场', '欧冠'], followed: true, winRate: 67.8, selfBuy: 101400, profit: 29660, roi: 29.2, avatar: '' },
];

export const users: User[] = Array.from({ length: 16 }, (_, index) => ({
  ...seed[index % seed.length],
  id: String(Number(seed[index % seed.length].id) + index * 13),
  name: index < seed.length ? seed[index].name : `${seed[index % seed.length].name}${index + 1}`,
  followed: index % 3 === 0,
  monthlyRoi: seed[index % seed.length].monthlyRoi - (index % 5) * 1.1,
}));

export interface UserOrderDetail {
  id?: string | number;
  publish_time?: string;
  match_count?: number;
  match_name?: string;
  play_type?: string;
  selection?: string;
  odds_text?: string;
  odds?: string | number;
  result?: string;
  pass_summary?: string;
  expected_bonus?: number;
  lot_multi?: number;
  stake?: number;
  follow_num?: number;
  bonus?: number;
  profit?: number;
}

export const userOrders: UserOrderDetail[] = [
  { match_name: '阿森纳 vs 切尔西', play_type: '让球胜平负', selection: '阿森纳-1 胜', odds_text: '1.78', result: '待开奖', publish_time: '2026-08-29 15:09', pass_summary: '2串1', expected_bonus: 15.72, lot_multi: 4074, stake: 48888, follow_num: 1377 },
  { match_name: '利物浦 vs 热刺', play_type: '胜平负', selection: '利物浦 胜', odds_text: '1.58', result: '已中奖', publish_time: '2026-08-28 17:08', pass_summary: '2串1', expected_bonus: 28.0, lot_multi: 2934, stake: 48888, follow_num: 2934 },
  { match_name: '巴黎 vs 皇马', play_type: '总进球', selection: '3球', odds_text: '2.10', result: '未中奖', publish_time: '2026-08-27 15:51', pass_summary: '2串1', expected_bonus: 5.76, lot_multi: 12500, stake: 50000, follow_num: 2955 },
];

export interface UserDetailSnapshot {
  user: Record<string, unknown> | null;
  orders: UserOrderDetail[];
}

export const userDetail: UserDetailSnapshot = { user: null, orders: [] };
