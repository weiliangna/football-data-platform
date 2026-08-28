export const money=(v:number)=>new Intl.NumberFormat('zh-CN',{style:'currency',currency:'CNY',maximumFractionDigits:0}).format(v);
export const num=(v:number)=>new Intl.NumberFormat('zh-CN').format(v);
export const pct=(v:number)=>`${v.toFixed(1)}%`;
export const clamp=(v:number,min=0,max=100)=>Math.min(max,Math.max(min,v));
