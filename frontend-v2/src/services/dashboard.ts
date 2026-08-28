import type { DashboardMetrics, Match } from '../types/index.js';
export const dashboardMetrics:DashboardMetrics={matches:28,live:6,plans:1364,users:219,anomalies:7,hot:12,completed:15};
export const matches:Match[]=[
{id:'m1',time:'19:30',league:'英超',home:'阿森纳',away:'切尔西',score:'1 - 0',status:'进行中',euro:[{label:'胜',value:'1.86',trend:'down'},{label:'平',value:'3.45',trend:'up'},{label:'负',value:'4.10',trend:'up'}],asian:'主 -0.75 ↑',totals:'2.75 ↓',plans:126,heat:96,anomaly:'主胜过热',category:'竞彩'},
{id:'m2',time:'20:00',league:'西甲',home:'皇家马德里',away:'塞维利亚',score:'- : -',status:'未开赛',euro:[{label:'胜',value:'1.42',trend:'down'},{label:'平',value:'4.80',trend:'flat'},{label:'负',value:'6.90',trend:'up'}],asian:'主 -1.25',totals:'3.0 ↑',plans:188,heat:99,anomaly:'大球升温',category:'竞彩'},
{id:'m3',time:'21:00',league:'德甲',home:'拜仁慕尼黑',away:'多特蒙德',score:'- : -',status:'未开赛',euro:[{label:'胜',value:'1.72',trend:'up'},{label:'平',value:'4.05',trend:'down'},{label:'负',value:'4.35',trend:'down'}],asian:'主 -0.75 ↓',totals:'3.25',plans:154,heat:94,anomaly:'客队受热',category:'竞彩'},
{id:'m4',time:'22:15',league:'意甲',home:'国际米兰',away:'罗马',score:'2 - 1',status:'已结束',euro:[{label:'胜',value:'1.64'},{label:'平',value:'3.70'},{label:'负',value:'5.20'}],asian:'主 -1',totals:'2.5',plans:92,heat:82,category:'其他'},
{id:'m5',time:'23:00',league:'法甲',home:'巴黎圣日耳曼',away:'里昂',score:'0 - 0',status:'进行中',euro:[{label:'胜',value:'1.53',trend:'down'},{label:'平',value:'4.35',trend:'up'},{label:'负',value:'5.75',trend:'up'}],asian:'主 -1.0 ↑',totals:'3.0 ↓',plans:146,heat:91,anomaly:'即时降水',category:'竞彩'},
{id:'m6',time:'23:30',league:'欧冠',home:'曼城',away:'国际米兰',score:'- : -',status:'未开赛',euro:[{label:'胜',value:'1.92',trend:'down'},{label:'平',value:'3.35',trend:'up'},{label:'负',value:'4.05',trend:'flat'}],asian:'主 -0.5',totals:'2.75 ↑',plans:174,heat:97,category:'竞彩'},
{id:'m7',time:'00:30',league:'英超',home:'利物浦',away:'热刺',score:'3 - 2',status:'已结束',euro:[{label:'胜',value:'1.58'},{label:'平',value:'4.40'},{label:'负',value:'5.15'}],asian:'主 -1',totals:'3.25',plans:111,heat:88,category:'竞彩'},
{id:'m8',time:'01:00',league:'西甲',home:'巴塞罗那',away:'比利亚雷亚尔',score:'- : -',status:'未开赛',euro:[{label:'胜',value:'1.48',trend:'down'},{label:'平',value:'4.60',trend:'flat'},{label:'负',value:'6.10',trend:'up'}],asian:'主 -1.25 ↑',totals:'3.25',plans:143,heat:89,anomaly:'主队热度突增',category:'竞彩'}
];
export const marketMoves=[
{time:'00:41',match:'阿森纳 vs 切尔西',company:'Bet365',change:'-0.5 → -0.75',state:'升盘'},
{time:'00:37',match:'拜仁 vs 多特',company:'澳门',change:'-1 → -0.75',state:'降盘'},
{time:'00:31',match:'巴黎 vs 里昂',company:'皇冠',change:'0.82 → 0.74',state:'升盘'},
{time:'00:25',match:'曼城 vs 国际米兰',company:'威廉',change:'2.5 → 2.75',state:'升盘'}
];
export const alerts=[
{type:'赔率偏离',time:'00:42',risk:'高',desc:'主流公司主胜差异超过 8%'},
{type:'资金集中',time:'00:34',risk:'中',desc:'单方向资金占比连续 3 次上升'},
{type:'盘口跳变',time:'00:29',risk:'中',desc:'亚洲盘 10 分钟内跨越两个档位'},
{type:'数据延迟',time:'00:17',risk:'低',desc:'平台 B 同步延迟 24 秒'}
];
export const hotMatches=matches.slice().sort((a,b)=>b.heat-a.heat).slice(0,6);
export const hotUsers=[
{name:'足球老dao',platform:'平台A',winRate:72.8,roi:18.6,plans:8},
{name:'稳坐钓鱼台',platform:'平台B',winRate:69.4,roi:16.2,plans:6},
{name:'沃奇尼亚',platform:'平台A',winRate:67.1,roi:13.8,plans:5},
{name:'红王',platform:'平台C',winRate:65.9,roi:12.5,plans:7}
];
