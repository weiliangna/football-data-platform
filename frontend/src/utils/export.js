export function downloadBlob(content, type, filename) {
  const blob = content instanceof Blob ? content : new Blob([content], {type})
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}

export function downloadJson(data, filename) {
  downloadBlob(JSON.stringify(data, null, 2), 'application/json;charset=utf-8', filename)
}

export function downloadExcel(title, headers, rows, filename) {
  const esc = (v) => String(v ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>${esc(title)}</title></head><body><table border="1"><caption>${esc(title)}</caption><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></body></html>`
  downloadBlob('\ufeff' + html, 'application/vnd.ms-excel;charset=utf-8', filename.endsWith('.xls') ? filename : filename + '.xls')
}

export function downloadTextPng(title, lines, filename) {
  const safeLines = Array.isArray(lines) ? lines : []
  const width = 1500
  const lineHeight = 30
  const padding = 44
  const height = Math.max(700, padding * 2 + 90 + safeLines.length * lineHeight)
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  const gradient = ctx.createLinearGradient(0, 0, width, 0)
  gradient.addColorStop(0, '#9e74f8')
  gradient.addColorStop(.52, '#8069f8')
  gradient.addColorStop(1, '#6884fc')
  ctx.fillStyle = '#f6f6f8'
  ctx.fillRect(0, 0, width, height)
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, width, 110)
  ctx.fillStyle = '#fff'
  ctx.font = '700 34px Microsoft YaHei, sans-serif'
  ctx.fillText(title, padding, 68)
  ctx.fillStyle = '#242238'
  ctx.font = '18px Microsoft YaHei, sans-serif'
  safeLines.forEach((line, index) => {
    const y = 150 + index * lineHeight
    if (y > height - padding) return
    ctx.fillText(String(line ?? ''), padding, y)
  })
  canvas.toBlob((blob) => {
    if (blob) downloadBlob(blob, 'image/png', filename.endsWith('.png') ? filename : filename + '.png')
  }, 'image/png')
}

export function stamp(prefix) {
  const d = new Date()
  const two = (v) => String(v).padStart(2, '0')
  return `${prefix}-${d.getFullYear()}${two(d.getMonth()+1)}${two(d.getDate())}-${two(d.getHours())}${two(d.getMinutes())}${two(d.getSeconds())}`
}
