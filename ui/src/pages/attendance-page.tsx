import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { AttendanceCourse, State } from '@/api'
import { PageHeader, Stat } from '@/components/page-header'
import { Masonry } from '@/components/masonry'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { semesterAllowance } from '@/lib/attendance'
import { cn } from '@/lib/utils'

type Level = 'bad' | 'risk' | 'ok' | 'none'
const level = (c: AttendanceCourse): Level => (!c.recorded ? 'none' : !c.ok ? 'bad' : c.can_miss < 2 ? 'risk' : 'ok')
const TONE: Record<Level, string> = { bad: 'text-destructive', risk: 'text-warning', ok: 'text-success', none: 'text-muted-foreground' }
const BAR: Record<Level, string> = { bad: 'bg-destructive', risk: 'bg-warning', ok: 'bg-success', none: 'bg-muted-foreground' }
const hours = (n: number) => `${Number.isInteger(n) ? n : n.toFixed(1)} h`

function Ring({ pct, level: lv }: { pct: number; level: Level }) {
  const r = 22, c = 2 * Math.PI * r
  return (
    <div className="relative size-16 shrink-0" role="img" aria-label={`${Math.round(pct)}% attendance`}>
      <svg viewBox="0 0 56 56" className="size-full -rotate-90">
        <circle cx="28" cy="28" r={r} fill="none" strokeWidth="5" className="stroke-muted" />
        <circle cx="28" cy="28" r={r} fill="none" strokeWidth="5" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - Math.min(100, pct) / 100)}
          className={cn('transition-[stroke-dashoffset] duration-700', lv === 'bad' ? 'stroke-destructive' : lv === 'risk' ? 'stroke-warning' : lv === 'ok' ? 'stroke-success' : 'stroke-muted-foreground')} />
      </svg>
      <div className="absolute inset-0 grid place-items-center"><span className="num text-sm font-medium">{Math.round(pct)}%</span></div>
    </div>
  )
}

function CourseCard({ c, minimum }: { c: AttendanceCourse; minimum: number }) {
  const [open, setOpen] = useState(false)
  const lv = level(c)
  const allow = semesterAllowance(c.credit_hours, minimum, c.absent, c.present + c.absent, (c.sessions ?? []).map(x => x.hours ?? 0))
  const total = c.present + c.absent
  const sessions = [...(c.sessions ?? [])].reverse()
  return (
    <div className="bg-card panel-lift flex flex-col gap-4 rounded-2xl border p-5">
      <div className="flex items-start gap-4">
        <Ring pct={c.percent} level={lv} />
        <div className="min-w-0 flex-1">
          <h2 className="leading-snug font-semibold text-balance">{c.title}</h2>
          <p className="text-muted-foreground mt-0.5 text-xs">{[c.teacher, c.class, c.credit_hours ? `${c.credit_hours} credit hours` : ''].filter(Boolean).join(' · ')}</p>
          <p className={cn('mt-2 text-sm', TONE[lv])}>
            {lv === 'none' ? 'No classes recorded yet.'
              : lv === 'bad' ? `Below the ${minimum}% minimum. Attend the next ${Math.ceil(c.need)} hours to get back.`
              : lv === 'risk' ? `Close to the limit: you can miss only ${hours(c.can_miss)} more.`
              : `Safe: you can miss ${hours(c.can_miss)} more and stay above ${minimum}%.`}
          </p>
        </div>
      </div>

      {c.recorded && (
        <div>
          <div className="relative">
            <div className="bg-muted h-2 overflow-hidden rounded-full"><div className={cn('h-full rounded-full transition-[width] duration-500', BAR[lv])} style={{ width: `${Math.min(100, c.percent)}%` }} /></div>
            <div className="bg-foreground/60 absolute -top-1 h-4 w-px" style={{ left: `${minimum}%` }} title={`Minimum ${minimum}%`} aria-hidden />
          </div>
          <div className="text-muted-foreground num mt-2 flex justify-between text-xs"><span>Present {hours(c.present)}</span><span>Absent {hours(c.absent)}</span><span>Total {hours(total)}</span></div>
        </div>
      )}

      {allow && (
        <div className="bg-muted/50 rounded-xl border p-3 text-sm" aria-label="Whole semester">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span className="font-medium">Whole semester: you can miss {hours(allow.max)} in total</span>
            <span className={cn('num text-xs', allow.left === 0 ? 'text-destructive' : 'text-muted-foreground')}>{hours(allow.used)} used · {hours(allow.left)} left</span>
          </div>
          <div className="bg-muted mt-2 h-1.5 overflow-hidden rounded-full"><div className={cn('h-full rounded-full', allow.left === 0 ? 'bg-destructive' : allow.left <= allow.classLen ? 'bg-warning' : 'bg-success')} style={{ width: `${Math.min(100, (allow.used / allow.max) * 100)}%` }} /></div>
          <p className="text-muted-foreground mt-2 text-xs">
            Based on {c.credit_hours} credit hour{Number(c.credit_hours) === 1 ? '' : 's'}: {hours(allow.planned)} planned over the semester, so about {allow.classes} classes of {hours(allow.classLen)}.
            {' '}If the teacher ends up holding fewer classes than planned, the limit is {100 - minimum}% of the hours actually held (for example {hours(42 * (100 - minimum) / 100)} out of 42 h).
          </p>
        </div>
      )}

      {sessions.length > 0 && (
        <Collapsible open={open} onOpenChange={setOpen}>
          <CollapsibleTrigger className="text-muted-foreground hover:text-foreground hover:bg-muted/60 focus-visible:ring-ring/50 flex min-h-11 w-full cursor-pointer items-center justify-between rounded-xl px-3 text-sm font-medium transition-colors outline-none focus-visible:ring-3">
            Class by class ({sessions.length})<ChevronDown className={cn('size-4 transition-transform duration-300 ease-[var(--ease-out)]', open && 'rotate-180')} />
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ul className="mt-3 flex flex-col divide-y rounded-xl border">
              {sessions.map((s, i) => {
                const missed = s.absent > 0
                return (
                  <li key={i} className="flex items-start gap-3 p-2.5 text-xs">
                    <span className={cn('mt-1 size-2 shrink-0 rounded-full', missed ? (s.present > 0 ? 'bg-warning' : 'bg-destructive') : 'bg-success')} aria-hidden />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium">{s.date}</div>
                      {s.topics && <div className="text-muted-foreground line-clamp-2">{s.topics}</div>}
                    </div>
                    <div className="num text-muted-foreground shrink-0 text-right">{missed ? (s.present > 0 ? `${hours(s.present)} of ${hours(s.hours)}` : `Absent ${hours(s.hours)}`) : `Present ${hours(s.hours)}`}{s.room && <div>{s.room}</div>}</div>
                  </li>
                )
              })}
            </ul>
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  )
}

export function AttendancePage({ state }: { state: State }) {
  const [filter, setFilter] = useState<'all' | Level>('all')
  const att = state.attendance
  const order: Level[] = ['bad', 'risk', 'ok', 'none']
  const list = [...att.courses].filter(c => filter === 'all' || level(c) === filter).sort((a, b) => order.indexOf(level(a)) - order.indexOf(level(b)) || a.percent - b.percent)
  const bad = att.courses.filter(c => level(c) === 'bad').length
  const risk = att.courses.filter(c => level(c) === 'risk').length
  const classes = att.courses.reduce((n, c) => n + (c.sessions?.length ?? 0), 0)
  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Attendance" description={`Per course, against your ${att.minimum}% minimum, with how many hours you can still miss or must attend.`} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Overall" value={att.overall != null ? `${att.overall.toFixed(1)}%` : '–'} sub={`minimum ${att.minimum}%`} tone={att.overall == null ? undefined : att.overall >= att.minimum ? 'success' : 'danger'} />
        <Stat label="Below the minimum" value={bad} sub={bad ? 'courses to catch up' : 'none'} tone={bad ? 'danger' : 'success'} />
        <Stat label="Close to the limit" value={risk} sub="can miss under 2 hours" tone={risk ? 'warning' : undefined} />
        <Stat label="Classes recorded" value={classes} sub={`across ${att.courses.filter(c => c.recorded).length} courses`} />
      </div>
      <Tabs value={filter} onValueChange={v => setFilter(v as typeof filter)} className="max-w-full overflow-x-auto">
        <TabsList>
          {([['all', 'All courses'], ['bad', 'Below the minimum'], ['risk', 'Close to the limit'], ['ok', 'On track']] as const).map(([k, l]) => (
            <TabsTrigger key={k} value={k}>{l}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      {list.length === 0 ? (
        <Empty className="border border-dashed"><EmptyHeader><EmptyTitle>No attendance yet</EmptyTitle><EmptyDescription>Run a check to read it from the portal.</EmptyDescription></EmptyHeader></Empty>
      ) : (
        <Masonry>{list.map(c => <CourseCard key={c.code} c={c} minimum={att.minimum} />)}</Masonry>
      )}
    </div>
  )
}
