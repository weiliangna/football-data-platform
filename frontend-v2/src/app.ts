import { shell } from './layouts/shell.js';
import { renderDashboard,type DashboardState } from './pages/dashboard.js';
import { renderPlans,type PlansState } from './pages/plans.js';
import { renderAnalysis,type AnalysisState } from './pages/analysis.js';
import { renderMatches,type MatchesState } from './pages/matches.js';
import { renderHeat,type HeatState } from './pages/heat.js';
import { renderResults,type ResultsState } from './pages/results.js';
import { renderUsers,type UsersState } from './pages/users.js';
import { renderMonitor,type MonitorState } from './pages/monitor.js';
import { renderRanking,type RankingState } from './pages/ranking.js';
import type { BettingPlay } from './types/index.js';
import { qs,toast } from './utils/dom.js';
import { users } from './services/users.js';
import { loadAnalysis,loadDashboard,loadHeatmap,loadMatches,loadNews,loadPlans,loadResults,loadUserDetail,loadUsers } from './services/live.js';

const dashboard:DashboardState={league:'全部',status:'全部',query:'',day:'今日',loading:false,selectedMatch:null};
const plans:PlansState={query:'',platform:'全部',league:'全部',result:'全部',page:1,view:'table',selectedPlan:null};
const analysis:AnalysisState={tab:'盘口总览',query:'阿森纳 vs 切尔西'};
const matches:MatchesState={league:'全部',company:'全部公司',query:'',selectedMatch:null};
const heat:HeatState={play:'胜平负'};
const results:ResultsState={period:'今日',status:'全部'};
const usersState:UsersState={query:'',platform:'全部',minHit:0,selectedUser:null,followed:new Set(users.filter(u=>u.followed).map(u=>u.id))};
const monitor:MonitorState={lastSync:'00:46:18'};
const ranking:RankingState={tab:'用户排行榜',period:'本周',platform:'全部',desc:true,selectedUser:null};

function route(){const key=location.hash.replace(/^#\/?/,'').split('/')[0];return ['dashboard','plans','analysis','matches','heat','results','users','monitor','ranking'].includes(key)?key:'dashboard'}
function page(key:string){switch(key){case'plans':return renderPlans(plans);case'analysis':return renderAnalysis(analysis);case'matches':return renderMatches(matches);case'heat':return renderHeat(heat);case'results':return renderResults(results);case'users':return renderUsers(usersState);case'monitor':return renderMonitor(monitor);case'ranking':return renderRanking(ranking);default:return renderDashboard(dashboard)}}
function render(focusKey?:string){const key=route();const root=qs<HTMLElement>('#root');if(!root)return;root.innerHTML=shell(key,page(key));bindTopbar();updateClock();if(focusKey){const input=qs<HTMLInputElement>(`[data-input="${focusKey}"]`);if(input){input.focus();const n=input.value.length;input.setSelectionRange(n,n)}}}
function closeDrawer(){dashboard.selectedMatch=null;plans.selectedPlan=null;matches.selectedMatch=null;usersState.selectedUser=null;ranking.selectedUser=null;render()}
function bindTopbar(){const menu=qs<HTMLButtonElement>('#menu-btn');menu?.addEventListener('click',()=>qs('#main-nav')?.classList.toggle('mobile-open'));const g=qs<HTMLInputElement>('#global-search');g?.addEventListener('keydown',e=>{if(e.key==='Enter'&&g.value.trim())toast(`全局搜索：${g.value.trim()}`)});}
function updateClock(){const el=qs('#clock');if(el)el.textContent=new Date().toLocaleTimeString('zh-CN',{hour12:false})}
setInterval(updateClock,1000);
window.addEventListener('hashchange',()=>render());
window.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();qs<HTMLInputElement>('#global-search')?.focus()}if(e.key==='Escape')closeDrawer()});

document.addEventListener('click',e=>{const t=(e.target as Element).closest<HTMLElement>('[data-action],[data-filter],[data-segment],[data-open-match],[data-open-plan],[data-open-user],[data-follow],[data-page],[data-heat-play],[data-ranking-tab],[data-global-action]');if(!t)return;
 const action=t.dataset.action;if(action==='close-drawer'){closeDrawer();return}if(action==='dashboard-loading'){dashboard.loading=true;render();setTimeout(()=>{dashboard.loading=false;render()},500);return}if(action==='plans-view-table'){plans.view='table';render();return}if(action==='plans-view-cards'){plans.view='cards';render();return}if(action==='plans-reset'){Object.assign(plans,{query:'',platform:'全部',league:'全部',result:'全部',page:1});render();return}if(action==='monitor-sync'){monitor.lastSync=new Date().toLocaleTimeString('zh-CN',{hour12:false});render();toast('平台状态已同步');return}if(action==='ranking-sort'){ranking.desc=!ranking.desc;render();return}if(action==='retry'){dashboard.loading=false;render();toast('已重试');return}
 const globalAction=t.dataset.globalAction;if(globalAction){const map:Record<string,string>={refresh:'数据已刷新',message:'暂无新消息',favorite:'收藏状态已更新',user:'用户菜单'};toast(map[globalAction]||'操作完成');return}
 if(t.dataset.filter==='dashboard-league'){dashboard.league=t.dataset.value||'全部';render();return}if(t.dataset.filter==='dashboard-status'){dashboard.status=t.dataset.value||'全部';render();return}
 if(t.dataset.segment){const k=t.dataset.segment;const v=t.dataset.value||'';if(k==='dashboard-day')dashboard.day=v;else if(k==='analysis-tab')analysis.tab=v;else if(k==='heat-play')heat.play=v as BettingPlay;else if(k==='results-period')results.period=v;else if(k==='results-status')results.status=v;else if(k==='ranking-period')ranking.period=v;render();return}
 if(t.dataset.openMatch){if(route()==='matches')matches.selectedMatch=t.dataset.openMatch;else dashboard.selectedMatch=t.dataset.openMatch;render();return}if(t.dataset.openPlan){plans.selectedPlan=t.dataset.openPlan;render();return}if(t.dataset.openUser){const id=t.dataset.openUser;if(route()==='ranking')ranking.selectedUser=id;else usersState.selectedUser=id;render();const selected=users.find((user)=>user.id===id);if(selected)void loadUserDetail(selected).then(()=>{if(usersState.selectedUser===id)render()});return}if(t.dataset.follow){const id=t.dataset.follow;usersState.followed.has(id)?usersState.followed.delete(id):usersState.followed.add(id);render();toast(usersState.followed.has(id)?'已关注用户':'已取消关注');return}if(t.dataset.page){plans.page=Number(t.dataset.page);render();return}if(t.dataset.heatPlay){heat.play=t.dataset.heatPlay as BettingPlay;render();return}if(t.dataset.rankingTab){ranking.tab=t.dataset.rankingTab;render();return}
});
document.addEventListener('change',e=>{const el=(e.target as Element).closest<HTMLSelectElement>('[data-select]');if(!el)return;const k=el.dataset.select;const v=el.value;switch(k){case'plans-platform':plans.platform=v;plans.page=1;break;case'plans-league':plans.league=v;plans.page=1;break;case'plans-result':plans.result=v;plans.page=1;break;case'matches-league':matches.league=v;break;case'matches-company':matches.company=v;break;case'users-platform':usersState.platform=v;break;case'users-min-hit':usersState.minHit=Number(v);break;case'ranking-platform':ranking.platform=v;break;default:return}render()});
document.addEventListener('input',e=>{const el=(e.target as Element).closest<HTMLInputElement>('[data-input]');if(!el)return;const k=el.dataset.input||'';const v=el.value;switch(k){case'dashboard-query':dashboard.query=v;break;case'plans-query':plans.query=v;plans.page=1;break;case'analysis-query':analysis.query=v;break;case'matches-query':matches.query=v;break;case'users-query':usersState.query=v;break;default:return}render(k)});

render();
void loadDashboard().then((loaded)=>{if(loaded)render();});
void loadPlans().then((loaded)=>{if(loaded)render();});
void loadMatches().then((loaded)=>{if(loaded)render();});
void loadUsers().then((loaded)=>{if(loaded)render();});
void loadResults().then((loaded)=>{if(loaded)render();});
void loadHeatmap().then((loaded)=>{if(loaded)render();});
void loadAnalysis().then((loaded)=>{if(loaded)render();});
void loadNews().then((loaded)=>{if(loaded)render();});
