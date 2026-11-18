import type { Assignment, Urgency } from './api'

export type Tone = 'urgent' | 'soon' | 'week' | 'ok' | 'later'
export const toneOf = (u: Urgency): Tone =>
  ({ today: 'urgent', missed: 'urgent', soon: 'soon', week: 'week', submitted: 'ok', later: 'later', unknown: 'later' } as const)[u]

const dayFmt = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
const timeFmt = new Intl.DateTimeFormat('en-GB', { hour: 'numeric', minute: '2-digit', hour12: true })

export function dueParts(iso: string | null): { day: string; time: string } {
  if (!iso) return { day: 'No deadline', time: '' }
  const d = new Date(iso)
  return { day: dayFmt.format(d).replace(',', ''), time: timeFmt.format(d).replace(' ', '').toLowerCase() }
}

/** "3d 4h", "5h 12m", "42m" until a deadline (or since it passed). */
export function countdown(iso: string | null, now: number): { big: string; unit: string } {
  if (!iso) return { big: '–', unit: 'no deadline' }
  const ms = new Date(iso).getTime() - now
  const abs = Math.abs(ms)
  const d = Math.floor(abs / 864e5), h = Math.floor((abs % 864e5) / 36e5), m = Math.floor((abs % 36e5) / 6e4)
  const big = d > 0 ? `${d}d ${h}h` : h > 0 ? `${h}h ${m}m` : `${m}m`
  return { big, unit: ms >= 0 ? 'until it closes' : 'since it closed' }
}

export function ago(iso: string | null | undefined, now: number): string {
  if (!iso) return 'not checked yet'
  const mins = Math.max(0, Math.round((now - new Date(iso).getTime()) / 6e4))
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const h = Math.round(mins / 60)
  return h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`
}

export const initials = (name?: string) => (name ?? '?').split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?'
export const byDue = (a: Assignment, b: Assignment) =>
  (a.due_at ? new Date(a.due_at).getTime() : Infinity) - (b.due_at ? new Date(b.due_at).getTime() : Infinity)
export const sizeLabel = (n: number) => (n < 1048576 ? `${Math.max(1, Math.round(n / 1024))} KB` : `${(n / 1048576).toFixed(1)} MB`)
