import { esc } from '../utils/dom.js';

export const badge = (text: string, tone = '') =>
  `<span class="status-badge ${esc(tone)}">${esc(text)}</span>`;

export const metric = (label: string, value: string | number, meta = '', tone = 'default') =>
  `<div class="metric-card tone-${esc(tone)}"><span>${esc(label)}</span><strong>${esc(value)}</strong>${meta ? `<small>${esc(meta)}</small>` : ''}</div>`;

export const avatar = (value: string, label = '', size = '') => {
  const source = String(value || '').trim();
  const fallback = esc((label || source || '用').slice(0, 1));
  const classes = ['avatar', size].filter(Boolean).join(' ');
  if (/^https?:\/\//i.test(source)) {
    return `<span class="${classes}"><img src="${esc(source)}" alt="${esc(label || '用户头像')}" loading="lazy" style="width:100%;height:100%;object-fit:cover;border-radius:inherit" onerror="this.hidden=true;this.nextElementSibling.hidden=false"><span hidden>${fallback}</span></span>`;
  }
  return `<span class="${classes}">${fallback}</span>`;
};

export const emptyState = (title = '暂无数据', desc = '当前筛选条件下没有可展示内容') =>
  `<div class="state-box"><div class="state-icon">•</div><strong>${esc(title)}</strong><span>${esc(desc)}</span></div>`;

export const loadingState = (label = '数据加载中…') =>
  `<div class="state-box"><div class="spinner"></div><strong>${esc(label)}</strong></div>`;

export const errorState = (message = '数据加载失败') =>
  `<div class="state-box error"><div class="state-icon">!</div><strong>${esc(message)}</strong><span>请检查本地数据状态后重试</span><button class="btn" data-action="retry">重试</button></div>`;

export const panel = (title: string, body: string, extra = '') =>
  `<section class="panel"><div class="panel-head"><h2>${esc(title)}</h2>${extra}</div><div class="panel-body">${body}</div></section>`;

export const progress = (value: number) =>
  `<div class="progress"><span style="width:${Math.max(0, Math.min(100, value))}%"></span></div>`;

export const pageHeader = (eyebrow: string, title: string, subtitle: string, actions = '') =>
  `<div class="page-header"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div>${actions ? `<div class="page-actions">${actions}</div>` : ''}</div>`;

export const drawer = (title: string, body: string) =>
  `<div class="drawer-layer"><button class="drawer-mask" data-action="close-drawer" aria-label="关闭详情"></button><aside class="drawer" role="dialog" aria-modal="true"><div class="drawer-head"><strong>${esc(title)}</strong><button class="icon-btn" data-action="close-drawer" aria-label="关闭">×</button></div><div class="drawer-body">${body}</div></aside></div>`;

export const segmented = (items: string[], value: string, key: string) =>
  `<div class="segmented">${items.map((item) => `<button data-segment="${esc(key)}" data-value="${esc(item)}" class="${item === value ? 'active' : ''}">${esc(item)}</button>`).join('')}</div>`;
