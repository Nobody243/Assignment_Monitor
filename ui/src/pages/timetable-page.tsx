import { useState } from 'react'
import { Download, FolderOpen } from 'lucide-react'
import { openFolder, saveTimetable, type State } from '@/api'
import { PageHeader } from '@/components/page-header'
import { Alert } from '@/components/inline-alert'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { courseColorAt } from '@/lib/courses'
import { toast } from '@/lib/notify'
import { cn } from '@/lib/utils'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const FULL: Record<string, string> = { Mon: 'Monday', Tue: 'Tuesday', Wed: 'Wednesday', Thu: 'Thursday', Fri: 'Friday', Sat: 'Saturday', Sun: 'Sunday' }
const minutes = (t: string) => { const [h, m] = t.split(':'); return Number(h) * 60 + Number(m || 0) }
const hhmm = (t: string) => t.slice(0, 5)
const HOUR_PX = 64

export function TimetablePage({ state, now, dark, demo }: { state: State; now: number; dark: boolean; demo: boolean }) {
  const sessions = state.timetable.sessions ?? []
  const [saving, setSaving] = useState<string | null>(null)
  if (!sessions.length) {
    return (
      <div className="flex w-full flex-col gap-5">
        <PageHeader title="Timetable" description="Your week, read from the CMS." />
        <Empty className="bg-card rounded-2xl border"><EmptyHeader><EmptyTitle>The timetable has not been read yet</EmptyTitle>
          <EmptyDescription>Run a check and your classes appear here, one column per day.</EmptyDescription></EmptyHeader></Empty>
      </div>
    )
  }
  const used = new Set(sessions.map(s => s.day))
  const days = DAYS.filter((d, i) => i < 5 || used.has(d))
  const startH = Math.floor(Math.min(...sessions.map(s => minutes(s.start))) / 60)
  const endH = Math.ceil(Math.max(...sessions.map(s => minutes(s.end))) / 60)
  const hours = Array.from({ length: endH - startH }, (_, i) => startH + i)
  const courses = [...new Set(sessions.map(s => s.course))].sort()
  const color = (c: string) => courseColorAt(courses.indexOf(c))
  const today = DAYS[(new Date(now).getDay() + 6) % 7]
  const nowMin = new Date(now).getHours() * 60 + new Date(now).getMinutes()

  const save = async (format: 'png' | 'jpg' | 'pdf') => {
    setSaving(format)
    try {
      const r = await saveTimetable(format, dark ? 'dark' : 'light')
      toast.success(`Saved ${r.file}`, { action: { label: 'Open folder', onClick: () => void openFolder('timetable') } })
    } catch (e) { toast.error('Could not save the timetable', { description: e instanceof Error ? e.message : undefined }) }
    setSaving(null)
  }

  return (
    <div className="flex w-full flex-col gap-5">
      <PageHeader title="Timetable" description={`${state.timetable.semester ?? 'This semester'}: one column per day, a colour per course.`}
        actions={<>
          {(['png', 'jpg', 'pdf'] as const).map(f => (
            <Button key={f} variant="outline" size="sm" disabled={demo || saving !== null} onClick={() => void save(f)}><Download />{saving === f ? 'Saving…' : f.toUpperCase()}</Button>
          ))}
          <Button variant="ghost" size="sm" disabled={demo} onClick={() => void openFolder('timetable').catch(() => toast.error('Could not open the folder'))}><FolderOpen />Open folder</Button>
        </>} />
      {demo && <Alert tone="info">Sample data: start the engine to save your timetable as a picture.</Alert>}

      <div className="bg-card overflow-x-auto rounded-2xl border p-4">
        <div className="grid min-w-[44rem]" style={{ gridTemplateColumns: `3.25rem repeat(${days.length}, minmax(0, 1fr))` }}>
          <div />
          {days.map(d => (
            <div key={d} className={cn('pb-2 text-center text-sm font-medium', d === today ? 'text-primary' : 'text-muted-foreground')}>
              {FULL[d]}{d === today && <span className="bg-primary ml-1.5 inline-block size-1.5 rounded-full align-middle" aria-label="today" />}
            </div>
          ))}
          <div className="relative" style={{ height: hours.length * HOUR_PX }}>
            {hours.map((h, i) => <div key={h} className="num text-muted-foreground absolute -translate-y-1/2 text-xs" style={{ top: i * HOUR_PX }}>{String(h).padStart(2, '0')}:00</div>)}
          </div>
          {days.map(d => (
            <div key={d} className={cn('relative border-l', d === today && 'bg-primary/5')} style={{ height: hours.length * HOUR_PX }}>
              {hours.map((h, i) => <div key={h} className="border-border/60 absolute inset-x-0 border-t" style={{ top: i * HOUR_PX }} />)}
              {sessions.filter(s => s.day === d).map(s => {
                const top = ((minutes(s.start) - startH * 60) / 60) * HOUR_PX
                const height = Math.max(28, ((minutes(s.end) - minutes(s.start)) / 60) * HOUR_PX - 3)
                return (
                  <div key={s.start + s.course} className="absolute inset-x-1 overflow-hidden rounded-xl border-l-[3px] p-2 text-xs leading-snug"
                    style={{ top, height, borderLeftColor: color(s.course), background: `color-mix(in oklch, ${color(s.course)} 18%, var(--card))` }}>
                    <div className="num text-muted-foreground">{hhmm(s.start)}–{hhmm(s.end)}</div>
                    <div className="line-clamp-2 font-medium">{s.course}</div>
                    {height > 70 && s.teacher && <div className="text-muted-foreground mt-0.5 truncate">{s.teacher}</div>}
                  </div>
                )
              })}
              {d === today && nowMin >= startH * 60 && nowMin <= endH * 60 && (
                <div className="bg-primary absolute inset-x-0 z-10 h-px" style={{ top: ((nowMin - startH * 60) / 60) * HOUR_PX }}><span className="bg-primary absolute -left-1 -top-[3px] size-[7px] rounded-full" /></div>
              )}
            </div>
          ))}
        </div>
      </div>

      <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
        {courses.map(c => <li key={c} className="flex items-center gap-2"><span className="size-2.5 rounded-full" style={{ background: color(c) }} />{c}</li>)}
      </ul>
    </div>
  )
}
