import type { PhoneShareStatus } from '@/api'

/** "just now", "12 min ago", "3 h ago", "2 days ago" for the time the summary was last sent. */
export function agoText(iso: string, now: number): string {
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return ''
  const mins = Math.max(0, Math.round((now - t) / 60000))
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  if (hours < 48) return `${hours} h ago`
  return `${Math.round(hours / 24)} days ago`
}

/** The line under "Share with my phone": what is happening, in the words a student would use. */
export function phoneShareLine(ps: PhoneShareStatus, now: number): { label: string; hint: string } {
  if (!ps.enabled) return { label: 'Off. The phone app has nothing to read from this PC.', hint: 'Turn it on and the phone app shows your deadlines, attendance, exams and more, even without Cloud checks.' }
  if (ps.covered_by_cloud) return { label: `On, through Cloud checks (${ps.login})`, hint: 'Cloud checks already writes the phone’s summary after each cloud check, so this PC does not send it as well.' }
  const label = `On, as ${ps.login} (${ps.repo})`
  if (ps.error) return { label, hint: `Last attempt failed: ${ps.error}` }
  return { label, hint: ps.last ? `Sent ${agoText(ps.last, now)}. It is sent again after each check that finds something new.` : 'Nothing sent yet. It is sent after the next check.' }
}
