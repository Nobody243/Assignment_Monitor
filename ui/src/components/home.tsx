import type { ReactNode } from 'react'
import { ArrowRight, CalendarClock, CheckCheck, CircleAlert, Flag, GraduationCap, TriangleAlert, Upload } from 'lucide-react'
import type { Assignment, State } from '@/api'
import { Alert } from '@/components/inline-alert'
import { Button } from '@/components/ui/button'
import { byDue, countdown, dueParts } from '@/format'
import { attendanceFor, courseColors, courseRows } from '@/lib/courses'
import { parseExamDate } from '@/lib/exams'
import type { Page } from '@/lib/router'
import { cn } from '@/lib/utils'

export type Go = (page: Page, opts?: { tab?: 'todo' | 'overdue' | 'submitted' | 'all'; course?: string }) => void

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate())
const sameDay = (a: Date, b: Date) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
const hhmm = (t: string) => t.slice(0, 5)

function Panel({ title, action, children, className }: { title: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn('bg-card panel-lift rounded-3xl border p-5', className)} aria-label={title}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

const MoreLink = ({ onClick, children }: { onClick: () => void; children: ReactNode }) => (
  <button type="button" onClick={onClick} className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs transition-colors">
    {children}<ArrowRight className="size-3" />
  </button>
)

// ------------------------------------------------------------------------------------------------ banner
function Banner({ state, now, next }: { state: State; now: number; next?: Assignment }) {
  const all = state.assignments
  const hour = new Date(now).getHours()
  const hello = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  const first = (state.meta.student_name ?? '').split(/\s+/)[0]
  const submitted = all.filter(a => a.is_submitted).length
  const pct = all.length ? Math.round((100 * submitted) / all.length) : 0
  const week = all.filter(a => a.open && !a.is_submitted && a.due_at && new Date(a.due_at).getTime() - now < 7 * 864e5).length
  const overdue = all.filter(a => !a.is_submitted && a.urgency === 'missed').length
  const r = 34, c = 2 * Math.PI * r
  const recorded = state.attendance.courses.filter(c => c.recorded)
  const lowest = recorded.length ? Math.min(...recorded.map(c => c.percent)) : null
  const st = state.standing
  const kpis: { label: string; value: string; sub: string }[] = [
    { label: 'Attendance', value: state.attendance.overall != null ? `${Math.round(state.attendance.overall)}%` : '–',
      sub: lowest != null ? `lowest ${Math.round(lowest)}% · minimum ${state.attendance.minimum}%` : `minimum ${state.attendance.minimum}%` },
    { label: 'CGPA', value: st ? st.cgpa.toFixed(2) : '–', sub: st ? `GPA ${st.gpa?.toFixed(2) ?? '–'} in ${st.semester}` : 'no results yet' },
    { label: 'Due this week', value: String(week), sub: week === 1 ? 'assignment still open' : 'assignments still open' },
    { label: 'Overdue', value: String(overdue), sub: overdue ? 'not submitted' : 'nothing missed' },
  ]
  return (
    <section className="flex flex-col gap-5 rounded-3xl bg-[radial-gradient(120%_140%_at_100%_0%,color-mix(in_oklch,var(--glow)_24%,transparent),transparent_55%),linear-gradient(120deg,var(--banner),var(--banner-2))] p-6 text-white shadow-[0_18px_40px_-24px_var(--banner)]" aria-label="Summary">
      <div className="flex flex-wrap items-center justify-between gap-x-8 gap-y-4">
        <div className="min-w-0 flex-1 basis-72">
          <p className="text-xs tracking-wide text-white/80 uppercase">{new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long' }).format(now)}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{hello}{first ? `, ${first}` : ''}.</h1>
          <p className="mt-1.5 max-w-xl text-sm text-white/90">
            {next
              ? <>Next up: <span className="font-medium text-white">{next.title}</span> in <span className="num text-white">{countdown(next.due_at, now).big}</span>.</>
              : 'You are all caught up. Nothing is waiting for you.'}
          </p>
        </div>
        <div className="relative size-20 shrink-0" role="img" aria-label={`${pct}% of this semester's assignments submitted`}>
          <svg viewBox="0 0 80 80" className="size-full -rotate-90">
            <circle cx="40" cy="40" r={r} fill="none" strokeWidth="7" stroke="rgba(255,255,255,0.18)" />
            <circle cx="40" cy="40" r={r} fill="none" strokeWidth="7" strokeLinecap="round" stroke="var(--glow)" strokeDasharray={c} strokeDashoffset={c * (1 - pct / 100)} />
          </svg>
          <div className="absolute inset-0 grid place-items-center text-center leading-none"><div><div className="num text-lg font-medium">{pct}%</div><div className="mt-0.5 text-[10px] text-white/80">submitted</div></div></div>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 border-t border-white/15 pt-4 sm:grid-cols-4">
        {kpis.map(k => (
          <div key={k.label} className="min-w-0">
            <dt className="text-xs text-white/80">{k.label}</dt>
            <dd className="num text-2xl font-medium">{k.value}</dd>
            <dd className="text-[11px] leading-snug text-white/75">{k.sub}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

// ------------------------------------------------------------------------------------------------ up next (the lime tile)
function UpNext({ a, now, onOpen }: { a?: Assignment; now: number; onOpen: (id: string) => void }) {
  if (!a) {
    return (
      <div className="bg-primary text-primary-foreground flex min-h-48 flex-col justify-between rounded-3xl p-6">
        <span className="w-fit rounded-full bg-black/10 px-2.5 py-1 text-xs font-medium">Up next</span>
        <div><CheckCheck className="mb-3 size-7" /><h2 className="text-xl font-semibold tracking-tight">You are all caught up</h2>
          <p className="mt-1 text-sm opacity-75">New work shows up here as soon as the portal lists it.</p></div>
      </div>
    )
  }
  const d = dueParts(a.due_at)
  const left = countdown(a.due_at, now)
  return (
    <div className="text-primary-foreground flex min-h-48 flex-col justify-between gap-5 rounded-3xl bg-[linear-gradient(160deg,color-mix(in_oklch,var(--primary),white_14%),var(--primary))] p-6 shadow-[0_18px_36px_-24px_var(--primary)]">
      <div className="flex items-start justify-between gap-3">
        <span className="rounded-full bg-black/10 px-2.5 py-1 text-xs font-medium">{a.urgency === 'today' ? 'Due today' : 'Up next'}</span>
        <div className="text-right" aria-label={`${left.big} left`}>
          <div className="num text-3xl leading-none font-medium">{left.big}</div>
          <div className="mt-1 text-xs opacity-70">{left.unit}</div>
        </div>
      </div>
      <div>
        <h2 className="text-xl leading-snug font-semibold tracking-tight text-balance">{a.title}</h2>
        <p className="mt-1 text-sm opacity-75">{a.course} · {d.day}{d.time && ` at ${d.time}`}</p>
      </div>
      <Button size="lg" className="w-full bg-[var(--tile-btn)] text-[var(--tile-btn-fg)] hover:bg-[var(--tile-btn)]/85" onClick={() => onOpen(a.id)}>
        <Upload />{a.can_upload ? 'Upload your work' : 'Open'}
      </Button>
    </div>
  )
}

// ------------------------------------------------------------------------------------------------ needs attention (from the Helio reference)
function NeedsAttention({ state, now, onOpen, onGo }: { state: State; now: number; onOpen: (id: string) => void; onGo: Go }) {
  const items: { key: string; tone: 'danger' | 'warning'; title: string; detail: string; run: () => void }[] = []
  const today = startOfDay(new Date(now))
  for (const a of state.assignments.filter(x => !x.is_submitted && x.open && x.due_at && sameDay(new Date(x.due_at), today))) {
    items.push({ key: `t-${a.id}`, tone: 'danger', title: a.title, detail: `Due today at ${dueParts(a.due_at).time} · ${a.course}`, run: () => onOpen(a.id) })
  }
  const overdue = state.assignments.filter(a => !a.is_submitted && a.urgency === 'missed').length
  if (overdue) items.push({ key: 'overdue', tone: 'danger', title: `${overdue} overdue assignment${overdue > 1 ? 's' : ''}`, detail: 'Not submitted. Review them.', run: () => onGo('assignments', { tab: 'overdue' }) })
  for (const c of state.attendance.courses.filter(x => x.recorded)) {
    if (!c.ok) {
      items.push({ key: `a-${c.code}`, tone: 'danger', title: `${c.title}: ${Math.round(c.percent)}% attendance`, detail: `Below the ${state.attendance.minimum}% minimum. Attend the next ${Math.ceil(c.need)} hours.`, run: () => {} })
    } else if (c.can_miss < 2) {
      items.push({ key: `a-${c.code}`, tone: 'warning', title: `${c.title}: ${Math.round(c.percent)}% attendance`, detail: `You can miss only ${c.can_miss} more hours.`, run: () => {} })
    }
  }
  const shown = items.slice(0, 5)
  return (
    <Panel title="Needs attention" action={items.length > 5 ? <span className="text-muted-foreground text-xs">+{items.length - 5} more</span> : undefined}>
      {shown.length === 0 ? (
        <div className="text-muted-foreground flex items-center gap-3 text-sm"><CheckCheck className="text-success size-5" />Nothing needs attention right now.</div>
      ) : (
        <ul className="flex flex-col gap-1">
          {shown.map(i => (
            <li key={i.key}>
              <button type="button" onClick={i.run} className="hover:bg-muted/60 flex w-full items-start gap-3 rounded-xl p-2 text-left transition-colors">
                {i.tone === 'danger' ? <CircleAlert className="text-destructive mt-0.5 size-4 shrink-0" /> : <TriangleAlert className="text-warning mt-0.5 size-4 shrink-0" />}
                <span className="min-w-0"><span className="line-clamp-2 block text-sm leading-snug font-medium">{i.title}</span><span className="text-muted-foreground block text-xs">{i.detail}</span></span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}

// ------------------------------------------------------------------------------------------------ deadlines
function Deadlines({ all, colors, onOpen, onGo }: { all: Assignment[]; colors: Record<string, string>; onOpen: (id: string) => void; onGo: Go }) {
  const list = all.filter(a => a.open && !a.is_submitted).sort(byDue).slice(0, 6)
  return (
    <Panel title="Deadlines" action={<MoreLink onClick={() => onGo('assignments')}>View all</MoreLink>}>
      {list.length === 0 ? <p className="text-muted-foreground text-sm">No open deadlines.</p> : (
        <ul className="flex flex-col">
          {list.map(a => {
            const d = a.days ?? 0
            const chip = a.urgency === 'today' ? 'Today' : `${d}d`
            return (
              <li key={a.id}>
                <button type="button" onClick={() => onOpen(a.id)} className="hover:bg-muted/60 flex w-full items-center gap-3 rounded-xl p-2 text-left transition-colors">
                  <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: colors[a.course] }} aria-hidden />
                  <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{a.title}</span><span className="text-muted-foreground block truncate text-xs">{a.course}</span><span className="num text-muted-foreground block text-[11px]">{dueParts(a.due_at).day} · {dueParts(a.due_at).time}</span></span>
                  <span className={cn('num shrink-0 rounded-full border px-2 py-0.5 text-xs', a.urgency === 'today' ? 'border-destructive/30 bg-destructive/10 text-destructive' : a.urgency === 'soon' ? 'border-warning/40 bg-warning/10 text-warning' : 'text-muted-foreground')}>{chip}</span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}

function CoursesPanel({ state, onGo }: { state: State; onGo: Go }) {
  const rows = courseRows(state.assignments)
  return (
    <Panel title="Courses" action={<span className="text-muted-foreground text-xs">submitted · next due · attendance</span>}>
      <ul className="flex flex-col gap-1">
        {rows.map(c => {
          const pct = c.total ? Math.round((100 * c.submitted) / c.total) : 0
          const done = c.total > 0 && c.submitted === c.total
          const att = attendanceFor(c.name, state.attendance.courses)
          const d = c.next ? dueParts(c.next.due_at) : null
          return (
            <li key={c.name}>
              <button type="button" onClick={() => onGo('assignments', { tab: 'all', course: c.name })} className="hover:bg-muted/60 block w-full rounded-xl p-2.5 text-left transition-colors">
                <div className="flex items-center gap-2.5">
                  <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: c.color }} aria-hidden />
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">{c.name}</span>
                  <span className="num text-sm">{c.submitted}<span className="text-muted-foreground">/{c.total}</span></span>
                  <span className={cn('num w-10 text-right text-xs', done ? 'text-success' : 'text-muted-foreground')}>{pct}%</span>
                </div>
                <div className="bg-muted mt-2 h-1.5 overflow-hidden rounded-full" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`${c.name}: ${c.submitted} of ${c.total} submitted`}>
                  <div className={cn('h-full rounded-full transition-[width] duration-500', done ? 'bg-success' : 'bg-banner dark:bg-foreground/70')} style={{ width: `${pct}%` }} />
                </div>
                <div className="text-muted-foreground mt-1.5 flex items-center justify-between gap-3 text-xs">
                  <span className="min-w-0 truncate">{c.next && d ? <>Next: <span className="text-foreground">{c.next.title}</span> · <span className="num">{d.day}</span></> : done ? 'Everything submitted' : c.overdue ? <span className="text-destructive">{c.overdue} overdue, not submitted</span> : 'Nothing due'}</span>
                  {att
                    ? <span className={cn('num shrink-0', att.ok ? (att.can_miss < 2 ? 'text-warning' : 'text-muted-foreground') : 'text-destructive')}>{Math.round(att.percent)}% attendance</span>
                    : <span className="shrink-0">no attendance yet</span>}
                </div>
              </button>
            </li>
          )
        })}
      </ul>
    </Panel>
  )
}

function ExamsPanel({ state, now }: { state: State; now: number }) {
  const today = startOfDay(new Date(now))
  const upcoming = (state.exams ?? [])
    .map(e => ({ e, d: parseExamDate(e.date) }))
    .filter((x): x is { e: State['exams'][number]; d: Date } => !!x.d && x.d >= today)
    .sort((a, b) => a.d.getTime() - b.d.getTime())
    .slice(0, 4)
  return (
    <Panel title="Exams" action={<GraduationCap className="text-muted-foreground size-4" />}>
      {upcoming.length === 0 ? (
        <p className="text-muted-foreground text-sm">No upcoming exams. Dates appear here as soon as the portal posts them.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {upcoming.map(({ e, d }) => {
            const days = Math.round((d.getTime() - today.getTime()) / 864e5)
            return (
              <li key={e.title + e.date} className="flex items-start gap-3 text-sm">
                <div className="bg-muted grid size-11 shrink-0 place-items-center rounded-xl text-center leading-none"><div><div className="num text-base font-medium">{d.getDate()}</div><div className="text-muted-foreground text-[10px] uppercase">{new Intl.DateTimeFormat('en-GB', { month: 'short' }).format(d)}</div></div></div>
                <div className="min-w-0 flex-1"><div className="truncate font-medium">{e.title}</div>
                  <div className="text-muted-foreground text-xs">{[e.exam_type, e.start_time, e.room].filter(Boolean).join(' · ')}</div></div>
                <span className={cn('num shrink-0 rounded-full border px-2 py-0.5 text-xs', days <= 3 ? 'border-destructive/30 bg-destructive/10 text-destructive' : 'text-muted-foreground')}>{days === 0 ? 'Today' : `${days}d`}</span>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}

function ResultsPanel({ state }: { state: State }) {
  const st = state.standing
  if (!st) return <Panel title="Results"><p className="text-muted-foreground text-sm">No results read yet.</p></Panel>
  const series = st.series.filter(x => x.gpa != null)
  return (
    <Panel title="Results" action={<span className="text-muted-foreground text-xs">GPA per semester</span>}>
      <div className="mb-4 flex items-baseline gap-3">
        <div className="num text-3xl font-medium">{st.cgpa.toFixed(2)}</div>
        <div className="text-muted-foreground text-xs">CGPA after {st.semester}<br />semester GPA {st.gpa?.toFixed(2) ?? '–'}</div>
      </div>
      <div className="flex h-20 items-end gap-2" role="img" aria-label={`GPA by semester, latest ${st.gpa?.toFixed(2) ?? ''}`}>
        {series.map((x, i) => (
          <div key={x.name} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1" title={`${x.name}: GPA ${x.gpa?.toFixed(2)}, CGPA ${x.cgpa?.toFixed(2)}`}>
            <span className="num text-muted-foreground text-[10px]">{x.gpa?.toFixed(1)}</span>
            <div className={cn('w-full rounded-md', i === series.length - 1 ? 'bg-primary' : 'bg-banner/70 dark:bg-foreground/50')} style={{ height: `${Math.max(8, ((x.gpa ?? 0) / 4) * 100)}%` }} />
            <span className="text-muted-foreground text-[10px]">{x.name.replace(/^(Fall|Spring|Summer)-(\d{2})(\d{2})$/, (_m, t: string, _c: string, y: string) => `${t[0]}${y}`)}</span>
          </div>
        ))}
      </div>
    </Panel>
  )
}

// ------------------------------------------------------------------------------------------------ this week (timetable + deadlines)
function Week({ state, now, colors, onOpen }: { state: State; now: number; colors: Record<string, string>; onOpen: (id: string) => void }) {
  const sessions = state.timetable.sessions ?? []
  const today = startOfDay(new Date(now))
  const monday = new Date(today); monday.setDate(today.getDate() - ((today.getDay() + 6) % 7))
  const used = new Set(sessions.map(s => s.day))
  const days = DAYS.filter((d, i) => i < 5 || used.has(d))
  const open = state.assignments.filter(a => a.open && !a.is_submitted && a.due_at)
  const colorFor = (course: string) => { const k = Object.keys(colors).find(n => n.startsWith(course) || course.startsWith(n)); return k ? colors[k] : undefined }
  return (
    <Panel title="This week" action={<span className="text-muted-foreground flex items-center gap-1.5 text-xs"><CalendarClock className="size-3.5" />{state.timetable.semester ?? ''}</span>}>
      <div className="grid gap-3 md:grid-cols-5" style={days.length > 5 ? { gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))` } : undefined}>
        {days.map(day => {
          const date = new Date(monday); date.setDate(monday.getDate() + DAYS.indexOf(day))
          const isToday = sameDay(date, today)
          const classes = sessions.filter(s => s.day === day).sort((a, b) => a.start.localeCompare(b.start))
          const due = open.filter(a => sameDay(new Date(a.due_at!), date))
          const empty = !classes.length && !due.length
          return (
            <div key={day} className={cn('flex min-w-0 flex-col gap-2', empty && 'max-md:hidden')}>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">{day}</span>
                <span className={cn('num grid size-6 place-items-center rounded-full', isToday ? 'bg-primary text-primary-foreground font-semibold' : 'text-foreground')}>{date.getDate()}</span>
              </div>
              {classes.map(s => (
                <div key={s.start + s.course} className="bg-muted/60 rounded-xl border-l-[3px] p-2 text-xs" style={{ borderLeftColor: colorFor(s.course) ?? 'transparent' }}>
                  <div className="num text-muted-foreground">{hhmm(s.start)}–{hhmm(s.end)}</div>
                  <div className="mt-0.5 line-clamp-2 leading-snug font-medium">{s.course}</div>
                </div>
              ))}
              {due.map(a => (
                <button key={a.id} type="button" onClick={() => onOpen(a.id)} className="bg-primary/25 hover:bg-primary/40 rounded-xl p-2 text-left text-xs transition-colors">
                  <div className="flex items-center gap-1 font-medium"><Flag className="size-3 shrink-0" /><span className="num">{dueParts(a.due_at).time}</span></div>
                  <div className="mt-0.5 line-clamp-2 leading-snug">{a.title}</div>
                </button>
              ))}
              {empty && <div className="text-muted-foreground border-t border-dashed pt-2 text-xs">Free</div>}
            </div>
          )
        })}
      </div>
      {sessions.length === 0 && <div className="mt-4"><Alert tone="info">The timetable has not been read yet. Run a check to see your classes here.</Alert></div>}
    </Panel>
  )
}

// ------------------------------------------------------------------------------------------------ deadline load, next 14 days
function Load({ all, now }: { all: Assignment[]; now: number }) {
  const today = startOfDay(new Date(now))
  const days = Array.from({ length: 14 }, (_, i) => { const d = new Date(today); d.setDate(today.getDate() + i); return d })
  const open = all.filter(a => a.open && !a.is_submitted && a.due_at)
  const counts = days.map(d => open.filter(a => sameDay(new Date(a.due_at!), d)))
  const max = Math.max(1, ...counts.map(c => c.length))
  const total = counts.reduce((n, c) => n + c.length, 0)
  return (
    <Panel title="Deadline load" action={<span className="text-muted-foreground text-xs">next 14 days</span>}>
      {total === 0 ? <p className="text-muted-foreground text-sm">No deadlines in the next 14 days.</p> : (
        <div className="flex h-28 items-end gap-1.5" role="img" aria-label={`${total} deadlines in the next 14 days`}>
          {days.map((d, i) => (
            <div key={i} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1.5" title={counts[i].map(a => a.title).join('\n') || 'Nothing due'}>
              <span className="num text-muted-foreground text-[10px]">{counts[i].length || ''}</span>
              <div className={cn('w-full rounded-md', counts[i].length ? (i === 0 ? 'bg-primary' : 'bg-banner/70 dark:bg-foreground/50') : 'bg-muted')} style={{ height: counts[i].length ? `${Math.max(14, (counts[i].length / max) * 62)}%` : '6%' }} />
              <span className={cn('num text-[10px]', i === 0 ? 'text-foreground font-semibold' : 'text-muted-foreground')}>{d.getDate()}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  )
}

// ------------------------------------------------------------------------------------------------ the page
/** What a brand-new install shows instead of an empty dashboard that claims you are "all caught up". */
function FirstRun({ onGo }: { onGo: Go }) {
  const steps = [
    ['Sign in', 'Enter your enrollment number, campus and portal password. They are stored encrypted for your Windows user only, and checked against the portal when you save.'],
    ['Run the first check', 'Press Check now. The app reads your courses, assignments, attendance, exams, lectures, announcements and timetable. It only reads.'],
    ['Let it run by itself', 'Turn on automatic checks in Settings so Windows checks every evening and reminds you hourly while something is due, even when the app is closed.'],
  ]
  return (
    <section className="bg-card flex flex-col gap-6 rounded-3xl border p-6 md:p-8" aria-label="Getting started">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Welcome to Assignment Monitor</h1>
        <p className="text-muted-foreground mt-1.5 max-w-2xl text-sm">Three steps and it keeps track of your deadlines for you. Nothing is shared with anyone: your data stays on this PC.</p>
      </div>
      <ol className="grid gap-3 md:grid-cols-3">
        {steps.map(([title, text], i) => (
          <li key={title} className="bg-muted/50 rounded-2xl p-4">
            <span className="bg-primary text-primary-foreground num mb-3 grid size-7 place-items-center rounded-full text-sm font-medium">{i + 1}</span>
            <h2 className="font-semibold">{title}</h2>
            <p className="text-muted-foreground mt-1 text-sm">{text}</p>
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap gap-2"><Button onClick={() => onGo('settings')}>Set up your account</Button></div>
    </section>
  )
}

export function Home({ state, now, onOpen, onGo }: { state: State; now: number; onOpen: (id: string) => void; onGo: Go }) {
  const all = state.assignments
  const colors = courseColors(all)
  const next = all.filter(a => a.open && !a.is_submitted).sort(byDue)[0]
  if (!state.meta.last_sync && all.length === 0) return <FirstRun onGo={onGo} />
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="xl:col-span-2"><Banner state={state} now={now} next={next} /></div>
      <div className="order-2 flex min-w-0 flex-col gap-4 xl:order-1">
        <Week state={state} now={now} colors={colors} onOpen={onOpen} />
        <Load all={all} now={now} />
        <CoursesPanel state={state} onGo={onGo} />
      </div>
      <div className="order-1 flex min-w-0 flex-col gap-4 xl:order-2">
        <UpNext a={next} now={now} onOpen={onOpen} />
        <NeedsAttention state={state} now={now} onOpen={onOpen} onGo={onGo} />
        <Deadlines all={all} colors={colors} onOpen={onOpen} onGo={onGo} />
        <ExamsPanel state={state} now={now} />
        <ResultsPanel state={state} />
      </div>
    </div>
  )
}
