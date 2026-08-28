import type { PlatformStatus } from '../types/index.js';
export const platforms:PlatformStatus[]=[
{id:'pl1',platform:'平台A',collectStatus:'正常',runStatus:'运行中',lastSync:'00:46:18',added:126,duplicates:19,failed:0,latency:182,config:'已配置'},
{id:'pl2',platform:'平台B',collectStatus:'部分成功',runStatus:'运行中',lastSync:'00:45:54',added:88,duplicates:23,failed:4,latency:620,config:'已配置',alert:'部分详情接口超时'},
{id:'pl3',platform:'平台C',collectStatus:'等待同步',runStatus:'排队中',lastSync:'00:43:10',added:0,duplicates:0,failed:0,latency:0,config:'已配置'},
{id:'pl4',platform:'平台D',collectStatus:'采集失败',runStatus:'重试中',lastSync:'00:40:02',added:11,duplicates:4,failed:18,latency:1410,config:'已配置',alert:'连续 3 次请求失败'},
{id:'pl5',platform:'平台E',collectStatus:'缺少配置',runStatus:'未运行',lastSync:'--',added:0,duplicates:0,failed:0,latency:0,config:'缺少 Token',alert:'请补充访问配置'},
{id:'pl6',platform:'平台F',collectStatus:'已停用',runStatus:'已停止',lastSync:'08-25 14:20',added:0,duplicates:0,failed:0,latency:0,config:'已停用'}
];
