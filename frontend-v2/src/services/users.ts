import type { User } from '../types/index.js';
const seed=[
{id:'30481',name:'足球老dao',platform:'平台A',recent:[true,true,false,true,true,true,false,true,true,true],streak:4,record:'182中126',monthlyRoi:18.6,todayPlans:8,followers:1260,followAmount:862000,tags:['稳健','英超','让球'],followed:true,winRate:69.2,selfBuy:184000,profit:52600,roi:28.6,avatar:'足'},
{id:'88217',name:'稳坐钓鱼台',platform:'平台B',recent:[true,false,true,true,true,false,true,true,true,false],streak:3,record:'205中137',monthlyRoi:16.2,todayPlans:6,followers:980,followAmount:641500,tags:['连红','西甲'],followed:false,winRate:66.8,selfBuy:152300,profit:42180,roi:27.7,avatar:'稳'},
{id:'343850',name:'沃奇尼亚',platform:'平台A',recent:[true,true,true,false,true,false,true,true,false,true],streak:1,record:'166中108',monthlyRoi:13.8,todayPlans:5,followers:754,followAmount:433200,tags:['比分','高赔率'],followed:false,winRate:65.1,selfBuy:126800,profit:33880,roi:26.7,avatar:'沃'},
{id:'56803',name:'红王',platform:'平台C',recent:[true,true,false,true,true,false,true,true,true,true],streak:4,record:'143中97',monthlyRoi:12.5,todayPlans:7,followers:690,followAmount:392800,tags:['半全场','欧冠'],followed:true,winRate:67.8,selfBuy:101400,profit:29660,roi:29.2,avatar:'红'}
] as User[];
export const users:User[]=Array.from({length:16},(_,i)=>({...seed[i%seed.length],id:String(Number(seed[i%seed.length].id)+i*13),name:i<4?seed[i].name:`${seed[i%4].name}${i+1}`,followed:i%3===0,monthlyRoi:seed[i%4].monthlyRoi-(i%5)*1.1}));
export const userOrders=[
{match:'阿森纳 vs 切尔西',play:'让球胜平负',pick:'阿森纳 -1 胜',sp:'1.78',result:'待开奖'},
{match:'利物浦 vs 热刺',play:'胜平负',pick:'利物浦 胜',sp:'1.58',result:'已中奖'},
{match:'巴黎 vs 里昂',play:'总进球',pick:'3/4 球',sp:'2.10',result:'未中奖'}
];
