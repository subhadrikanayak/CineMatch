// Server datetimes are UTC without a timezone suffix; add one so the browser converts correctly.
export const fmtDate = (s) => {
  if (!s) return '-'
  const iso = /Z$|[+-]\d\d:\d\d$/.test(s) ? s : `${s}Z`
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '-' : d.toLocaleString()
}

export const chart = {
  accent: '#f0a6c0',
  violet: '#a78bfa',
  tick: { fill: '#b3a7c7', fontSize: 12 },
  tooltip: {
    contentStyle: {
      background: 'rgba(32,18,48,0.95)',
      border: '1px solid rgba(255,255,255,0.12)',
      borderRadius: 8,
    },
    labelStyle: { color: '#f3eefa' },
    itemStyle: { color: '#f3eefa' },
    cursor: { fill: 'rgba(255,255,255,0.05)' },
  },
}