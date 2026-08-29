import type { Plan } from '../types/index.js';

const base: Plan[] = [
  { id: 'P20260829001', platform: '彩站云', user: '足球老dao', userId: '30481', avatar: '足', match: '阿森纳 vs 切尔西', league: '英超', play: '让球胜平负', pick: '让胜', amount: 1200, multiple: 2, sp: '1.86', publishAt: '08-29 00:12', cutoffAt: '08-29 19:25', status: '进行中', result: '待开奖', expectedProfit: 936 },
  { id: 'P20260829002', platform: '州运宝', user: '稳坐钓鱼台', userId: '88217', avatar: '稳', match: '皇家马德里 vs 塞维利亚', league: '西甲', play: '胜平负', pick: '主胜', amount: 800, multiple: 3, sp: '1.42', publishAt: '08-29 00:18', cutoffAt: '08-29 19:55', status: '进行中', result: '待开奖', expectedProfit: 336 },
  { id: 'P20260829003', platform: '彩站云', user: '沃奇尼亚', userId: '343850', avatar: '沃', match: '拜仁 vs 多特', league: '德甲', play: '比分', pick: '2:1 / 3:1', amount: 500, multiple: 1, sp: '6.50', publishAt: '08-28 23:56', cutoffAt: '08-29 20:55', status: '进行中', result: '待开奖', expectedProfit: 3100 },
  { id: 'P20260829004', platform: '鸿瑞', user: '红王', userId: '56803', avatar: '红', match: '国际米兰 vs 罗马', league: '意甲', play: '半全场', pick: '胜/胜', amount: 1000, multiple: 1, sp: '4.20', publishAt: '08-28 21:10', cutoffAt: '08-28 22:10', status: '已结算', result: '已中奖', expectedProfit: 1460 },
  { id: 'P20260829005', platform: '州运宝', user: '蓝海', userId: '10422', avatar: '蓝', match: '巴黎 vs 里昂', league: '法甲', play: '进球数', pick: '3球', amount: 600, multiple: 2, sp: '3.10', publishAt: '08-28 22:30', cutoffAt: '08-28 22:55', status: '进行中', result: '待开奖', expectedProfit: 920 },
  { id: 'P20260829006', platform: '彩站云', user: '老炮', userId: '77121', avatar: '老', match: '利物浦 vs 热刺', league: '英超', play: '胜平负', pick: '主胜', amount: 1500, multiple: 2, sp: '1.58', publishAt: '08-28 18:30', cutoffAt: '08-28 23:20', status: '已结算', result: '已中奖', expectedProfit: 870 },
  { id: 'P20260829007', platform: '云彩', user: '观潮', userId: '40019', avatar: '观', match: '曼城 vs 国际米兰', league: '欧冠', play: '让球胜平负', pick: '让胜', amount: 980, multiple: 1, sp: '1.92', publishAt: '08-29 00:03', cutoffAt: '08-29 23:25', status: '进行中', result: '待开奖', expectedProfit: 804 },
  { id: 'P20260829008', platform: '鸿瑞', user: '精选哥', userId: '90445', avatar: '精', match: '巴塞罗那 vs 比利亚雷亚尔', league: '西甲', play: '大小球', pick: '大 3.25', amount: 760, multiple: 2, sp: '1.78', publishAt: '08-29 00:21', cutoffAt: '08-30 00:55', status: '进行中', result: '待开奖', expectedProfit: 608 },
  { id: 'P20260828009', platform: '云彩', user: '北斗', userId: '22201', avatar: '北', match: 'AC米兰 vs 拉齐奥', league: '意甲', play: '胜平负', pick: '主胜', amount: 900, multiple: 1, sp: '1.66', publishAt: '08-28 14:30', cutoffAt: '08-28 18:55', status: '已结算', result: '未中奖', expectedProfit: -900 },
  { id: 'P20260828010', platform: '州运宝', user: '稳坐钓鱼台', userId: '88217', avatar: '稳', match: '摩纳哥 vs 马赛', league: '法甲', play: '让球胜平负', pick: '让平', amount: 500, multiple: 3, sp: '3.60', publishAt: '08-28 16:02', cutoffAt: '08-28 21:25', status: '已结算', result: '走盘', expectedProfit: 0 },
];

export const plans: Plan[] = Array.from({ length: 34 }, (_, index) => ({
  ...base[index % base.length],
  id: `P20260829${String(index + 1).padStart(3, '0')}`,
  amount: base[index % base.length].amount + (index % 4) * 100,
}));
