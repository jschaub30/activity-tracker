export function formatMi(n: number | null | undefined): string {
  if (n == null) return '—'
  return `${n.toFixed(2)} mi`
}

export function formatFt(n: number | null | undefined): string {
  if (n == null) return '—'
  return `${Math.round(n).toLocaleString()} ft`
}

export function formatCal(n: number | null | undefined): string {
  if (n == null) return '—'
  return `${Math.round(n).toLocaleString()} cal`
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m ${s}s`
}

export function weekdayLabel(isoDate: string): string {
  const d = new Date(isoDate + 'T12:00:00')
  return d.toLocaleDateString('en-US', { weekday: 'short' })
}

export function shiftWeek(weekStartIso: string, deltaWeeks: number): string {
  const d = new Date(weekStartIso + 'T12:00:00')
  d.setDate(d.getDate() + deltaWeeks * 7)
  return d.toISOString().slice(0, 10)
}
