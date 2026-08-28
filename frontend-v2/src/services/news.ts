export interface NewsItem { id: string; title: string; time: string; category: string; matchId?: string }
export const news: NewsItem[] = [
  { id: 'N1', title: '赛前阵容与盘口动态更新', time: '00:42', category: '赛前快讯' },
  { id: 'N2', title: '主队核心球员恢复合练', time: '00:36', category: '球队动态' },
  { id: 'N3', title: '主流公司盘口出现同步变化', time: '00:29', category: '盘口异动' },
]
