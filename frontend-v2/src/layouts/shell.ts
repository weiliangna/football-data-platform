import { esc } from '../utils/dom.js';
export const navItems=[
  ['dashboard','今日总览','▦'],['plans','方案大厅','▤'],['analysis','赛事分析','⌁'],['matches','赛事数据','▥'],['heat','投注热力','♨'],['results','赛果统计','▧'],['users','用户中心','♟'],['monitor','数据监控','◉'],['ranking','排行榜','★']
] as const;
export function shell(active:string,content:string){
 return `<div class="app-shell"><header class="topbar"><div class="brand"><div class="brand-mark">⚽</div><div><b>足球数据中心</b><span>FOOTBALL DATA CENTER</span></div></div><nav class="nav" id="main-nav">${navItems.map(([key,label,icon])=>`<a href="#/${key}" class="${active===key?'active':''}" data-route="${key}"><span>${icon}</span>${esc(label)}</a>`).join('')}</nav><div class="top-actions"><div class="global-search"><span>⌕</span><input id="global-search" placeholder="搜索比赛、球队、用户"/><kbd>Ctrl K</kbd></div><div class="clock"><span>◷</span><span id="clock">--:--:--</span></div><button class="icon-btn" data-global-action="refresh" aria-label="刷新">↻</button><button class="icon-btn" data-global-action="message" aria-label="消息">◌</button><button class="icon-btn" data-global-action="favorite" aria-label="收藏">☆</button><button class="user-btn" data-global-action="user">♙ 管理员</button><button class="menu-btn" id="menu-btn" aria-label="菜单">☰</button></div></header><main class="content">${content}</main></div>`
}
