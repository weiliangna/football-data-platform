import type { Plan } from '../types/index.js';
const base:Plan[]=[
{id:'P20260829001',platform:'平台A',user:'足球老dao',userId:'30481',match:'阿森纳 vs 切尔西',league:'英超',play:'让球胜平负',pick:'阿森纳 -1 胜',amount:1200,multiple:2,publishAt:'08-29 00:12',cutoffAt:'08-29 19:25',status:'进行中',result:'待开奖',expectedProfit:936},
{id:'P20260829002',platform:'平台B',user:'稳坐钓鱼台',userId:'88217',match:'皇马 vs 塞维利亚',league:'西甲',play:'胜平负',pick:'皇家马德里 胜',amount:800,multiple:3,publishAt:'08-29 00:18',cutoffAt:'08-29 19:55',status:'进行中',result:'待开奖',expectedProfit:336},
{id:'P20260829003',platform:'平台A',user:'沃奇尼亚',userId:'343850',match:'拜仁 vs 多特',league:'德甲',play:'比分',pick:'2-1 / 3-1',amount:500,multiple:1,publishAt:'08-28 23:56',cutoffAt:'08-29 20:55',status:'进行中',result:'待开奖',expectedProfit:3100},
{id:'P20260829004',platform:'平台C',user:'红王',userId:'56803',match:'国际米兰 vs 罗马',league:'意甲',play:'半全场',pick:'胜/胜',amount:1000,multiple:1,publishAt:'08-28 21:10',cutoffAt:'08-28 22:10',status:'已结算',result:'已中奖',expectedProfit:1460},
{id:'P20260829005',platform:'平台B',user:'蓝海',userId:'10422',match:'巴黎 vs 里昂',league:'法甲',play:'进球数',pick:'3/4 球',amount:600,multiple:2,publishAt:'08-28 22:30',cutoffAt:'08-28 22:55',status:'进行中',result:'待开奖',expectedProfit:920},
{id:'P20260829006',platform:'平台A',user:'老炮',userId:'77121',match:'利物浦 vs 热刺',league:'英超',play:'胜平负',pick:'利物浦 胜',amount:1500,multiple:2,publishAt:'08-28 18:30',cutoffAt:'08-28 23:20',status:'已结算',result:'已中奖',expectedProfit:870},
{id:'P20260829007',platform:'平台D',user:'观潮',userId:'40019',match:'曼城 vs 国际米兰',league:'欧冠',play:'亚洲让球',pick:'曼城 -0.5',amount:980,multiple:1,publishAt:'08-29 00:03',cutoffAt:'08-29 23:25',status:'进行中',result:'待开奖',expectedProfit:804},
{id:'P20260829008',platform:'平台C',user:'精选哥',userId:'90445',match:'巴塞罗那 vs 比利亚雷亚尔',league:'西甲',play:'大小球',pick:'大 3.25',amount:760,multiple:2,publishAt:'08-29 00:21',cutoffAt:'08-30 00:55',status:'进行中',result:'待开奖',expectedProfit:608},
{id:'P20260828009',platform:'平台D',user:'北斗',userId:'22201',match:'AC米兰 vs 拉齐奥',league:'意甲',play:'胜平负',pick:'AC米兰 胜',amount:900,multiple:1,publishAt:'08-28 14:30',cutoffAt:'08-28 18:55',status:'已结算',result:'未中奖',expectedProfit:-900},
{id:'P20260828010',platform:'平台B',user:'稳坐钓鱼台',userId:'88217',match:'摩纳哥 vs 马赛',league:'法甲',play:'让球胜平负',pick:'摩纳哥 -1 平',amount:500,multiple:3,publishAt:'08-28 16:02',cutoffAt:'08-28 21:25',status:'已结算',result:'走盘',expectedProfit:0}
];
export const plans:Plan[]=Array.from({length:34},(_,i)=>({...base[i%base.length],id:`P20260829${String(i+1).padStart(3,'0')}`,amount:base[i%base.length].amount+(i%4)*100}));
