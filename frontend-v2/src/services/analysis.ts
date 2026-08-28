import type { TimelineRow } from '../types/index.js';
export const analysisMatch={home:'阿森纳',away:'切尔西',league:'英超',kickoff:'2026-08-29 19:30',status:'进行中',score:'1 - 0'};
export const timeline:TimelineRow[]=[
{time:'08-28 09:00',company:'Bet365',initial:'主 -0.50 / 0.92',current:'主 -0.50 / 0.88',direction:'升盘',note:'主队水位缓慢下修'},
{time:'08-28 14:30',company:'澳门',initial:'主 -0.50 / 0.90',current:'主 -0.75 / 1.02',direction:'升盘',note:'升至半一盘，形成阻力'},
{time:'08-28 19:10',company:'皇冠',initial:'主 -0.50 / 0.94',current:'主 -0.75 / 0.96',direction:'升盘',note:'跟随主流公司调整'},
{time:'08-29 00:20',company:'威廉',initial:'1.95 / 3.50 / 3.90',current:'1.86 / 3.45 / 4.10',direction:'升盘',note:'主胜持续压低，客胜抬升'}
];
export const analysisCards=[
{label:'欧赔走势',value:'主胜 1.86',meta:'较初盘 -4.1%'},{label:'亚洲让球',value:'主 -0.75',meta:'主队 0.96 水位'},{label:'大小球',value:'2.75',meta:'大球 0.91'},{label:'盘口变动',value:'7 次',meta:'近 6 小时 3 次'},{label:'投注热度',value:'96',meta:'主队 68%'},{label:'方案数量',value:'126',meta:'近1小时 +21'},{label:'资金变化',value:'+18.4%',meta:'主队净流入'},{label:'市场异常',value:'2 条',meta:'主胜过热 / 价差'}
];
