import { CalendarDays, Clock, DoorOpen, Armchair } from 'lucide-react'
import type { Exam, State } from '@/api'
import { PageHeader, Stat } from '@/components/page-header'
import { Alert } from '@/components/inline-alert'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { parseExamDate } from '@/lib/exams'
import { cn } from '@/lib/utils'

type Row = { e: Exam; date: Date | null; days: number | null }

function ExamCard({ r }: { r: Row }) {
  const { e, date, days } = r
  const done = days != null && days < 0
  return (
    <div className={cn('bg-card panel-lift flex gap-4 rounded-2xl border p-4', done && 'opacity-60')}>
      <div className="bg-muted grid size-16 shrink-0 place-items-center rounded-xl text-center leading-none">
        {date ? (<div><div className="num text-2xl font-medium">{date.getDate()}</div><div className="text-muted-foreground mt-0.5 text-xs uppercase">{new Intl.DateTimeFormat('en-GB', { month: 'short', weekday: 'short' }).format(date)}</div></div>)
          : <div className="text-muted-foreground text-xs">date<br />not posted</div>}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <h2 className="leading-snug font-semibold text-balance">{e.title}</h2>
          {days != null && (
            <span className={cn('num shrink-0 rounded-full border px-2 py-0.5 text-xs', done ? 'text-muted-foreground' : days <= 3 ? 'border-destructive/30 bg-destructive/10 text-destructive' : days <= 7 ? 'border-warning/40 bg-warning/10 text-warning' : 'text-muted-foreground')}>
              {done ? 'Done' : days === 0 ? 'Today' : `in ${days}d`}
            </span>
          )}
        </div>
        {date ? (
          <ul className="text-muted-foreground mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <li className="flex items-center gap-1.5"><Clock className="size-3.5" />{[e.start_time, e.session].filter(Boolean).join(' · ') || 'time not posted'}</li>
            <li className="flex items-center gap-1.5"><DoorOpen className="size-3.5" />{e.room || 'room not posted'}</li>
            <li className="flex items-center gap-1.5"><Armchair className="size-3.5" />{e.row && e.column ? `Row ${e.row}, seat ${e.column}` : 'seat not posted'}</li>
            <li className="flex items-center gap-1.5"><CalendarDays className="size-3.5" />{new Intl.DateTimeFormat('en-GB', { dateStyle: 'full' }).format(date)}</li>
          </ul>
        ) : <p className="text-muted-foreground mt-2 text-xs">The portal has not posted a date, time or seat for this paper yet.</p>}
        {(e.fee_defaulter || (e.surveys && !/completed/i.test(e.surveys))) && (
          <div className="mt-2 flex flex-col gap-1.5">
            {e.fee_defaulter && <Alert tone="danger">Marked as a fee defaulter. You may not be allowed to sit this paper.</Alert>}
            {e.surveys && !/completed/i.test(e.surveys) && <Alert tone="warning">Course survey: {e.surveys}. Complete it so the portal releases your seat.</Alert>}
          </div>
        )}
      </div>
    </div>
  )
}

export function ExamsPage({ state, now }: { state: State; now: number }) {
  const today = new Date(new Date(now).getFullYear(), new Date(now).getMonth(), new Date(now).getDate())
  const rows: Row[] = (state.exams_all ?? []).map(e => {
    const date = parseExamDate(e.date)
    return { e, date, days: date ? Math.round((date.getTime() - today.getTime()) / 864e5) : null }
  })
  const rank = (r: Row) => (r.days == null ? 1 : r.days >= 0 ? 0 : 2)
  rows.sort((a, b) => rank(a) - rank(b) || (a.days ?? 0) - (b.days ?? 0) || a.e.title.localeCompare(b.e.title))
  const types = [...new Set(rows.map(r => r.e.exam_type || 'Exams'))]
  const upcoming = rows.filter(r => r.days != null && r.days >= 0)
  const next = upcoming[0]
  const unposted = rows.filter(r => r.days == null).length
  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Exams" description="Seating plan from the CMS: date, time, room and seat for every paper the portal has posted." />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Upcoming" value={upcoming.length} sub={next ? `next in ${next.days === 0 ? 'today' : `${next.days} days`}` : 'none posted'} />
        <Stat label="Done" value={rows.filter(r => r.days != null && r.days < 0).length} sub="papers already sat" />
        <Stat label="Dates not posted" value={unposted} sub={unposted ? 'waiting for the portal' : 'all scheduled'} tone={unposted ? 'warning' : undefined} />
        <Stat label="Papers" value={rows.length} sub={types.join(' · ') || 'none'} />
      </div>
      {rows.length === 0 ? (
        <Empty className="border border-dashed"><EmptyHeader><EmptyTitle>No exam information yet</EmptyTitle><EmptyDescription>The seating plan appears here once the portal publishes it.</EmptyDescription></EmptyHeader></Empty>
      ) : types.map(t => (
        <section key={t} className="flex flex-col gap-3" aria-label={t}>
          <h2 className="text-muted-foreground text-sm font-semibold">{t}</h2>
          <div className="grid gap-3 lg:grid-cols-2">{rows.filter(r => (r.e.exam_type || 'Exams') === t).map(r => <ExamCard key={r.e.title + r.e.date + t} r={r} />)}</div>
        </section>
      ))}
    </div>
  )
}
