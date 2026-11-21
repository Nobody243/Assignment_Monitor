import { useMemo, useState } from 'react'
import { Download, FolderOpen, Paperclip, Search } from 'lucide-react'
import type { Lecture } from '@/api'
import { PageHeader, Stat } from '@/components/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'

const isNew = (l: Lecture, now: number) => !!l.first_seen && now - new Date(l.first_seen).getTime() < 7 * 864e5
const weekNo = (l: Lecture) => (Number(l.week) || 0)

export function LecturesPage({ lectures, colors, now, busy, demo, folder, onDownload, onOpenFolder }: {
  lectures: Lecture[]; colors: Record<string, string>; now: number; busy: boolean; demo: boolean; folder: string
  onDownload: (ids: string[]) => void; onOpenFolder: () => void
}) {
  const [kind, setKind] = useState<'notes' | 'misc'>('notes')
  const [course, setCourse] = useState('all')
  const [query, setQuery] = useState('')
  const [picked, setPicked] = useState<Set<string>>(new Set())

  const notes = lectures.filter(l => l.kind !== 'misc')
  const misc = lectures.filter(l => l.kind === 'misc')
  const pool = kind === 'notes' ? notes : misc
  const courses = useMemo(() => [...new Set(lectures.map(l => l.course))].sort(), [lectures])
  const q = query.trim().toLowerCase()
  const shown = pool.filter(l => (course === 'all' || l.course === course) && (!q || `${l.title} ${l.course}`.toLowerCase().includes(q)))
  const grouped = [...new Set(shown.map(l => l.course))].sort().map(c => ({ course: c, items: shown.filter(l => l.course === c).sort((a, b) => weekNo(b) - weekNo(a)) }))
  const fresh = lectures.filter(l => isNew(l, now)).length
  const fileCount = (l: Lecture) => l.files.length

  const toggle = (id: string) => setPicked(p => { const n = new Set(p); if (n.has(id)) n.delete(id); else n.add(id); return n })
  const toggleCourse = (items: Lecture[]) => setPicked(p => {
    const n = new Set(p)
    const all = items.every(i => n.has(i.id))
    items.forEach(i => (all ? n.delete(i.id) : n.add(i.id)))
    return n
  })
  const chosen = [...picked].filter(id => lectures.some(l => l.id === id))
  // the pill keeps showing the last count while it slides away, instead of flashing "0"
  const [shownCount, setShownCount] = useState(0)
  if (chosen.length > 0 && chosen.length !== shownCount) setShownCount(chosen.length)

  return (
    <div className="flex flex-col gap-5 pb-20">
      <PageHeader title="Lectures" description="Lecture notes and miscellaneous files for every course. Tick what you want and download it in one go."
        actions={<Button variant="outline" size="sm" onClick={onOpenFolder} disabled={demo}><FolderOpen />Open folder</Button>} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Lecture weeks" value={notes.length} sub={`${notes.reduce((n, l) => n + fileCount(l), 0)} files`} />
        <Stat label="Miscellaneous" value={misc.length} sub={`${misc.reduce((n, l) => n + fileCount(l), 0)} files`} />
        <Stat label="New this week" value={fresh} sub="first seen in the last 7 days" tone={fresh ? 'success' : undefined} />
        <Stat label="Courses" value={courses.length} sub="with material" />
      </div>
      <p className="text-muted-foreground -mt-2 text-xs">Downloads go to <span className="num">{folder}</span>, one folder per course. Files already there are skipped.</p>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs value={kind} onValueChange={v => setKind(v as typeof kind)}>
          <TabsList>
            <TabsTrigger value="notes">Lecture notes<span className="num text-muted-foreground ml-1.5 text-xs">{notes.length}</span></TabsTrigger>
            <TabsTrigger value="misc">Miscellaneous<span className="num text-muted-foreground ml-1.5 text-xs">{misc.length}</span></TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="text-muted-foreground absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
            <Input value={query} onChange={e => setQuery(e.target.value)} placeholder="Filter by title" aria-label="Filter lectures" className="h-8 w-52 pl-8" />
          </div>
          <Select value={course} onValueChange={setCourse}>
            <SelectTrigger size="sm" className="w-52" aria-label="Course"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="all">All courses</SelectItem>{courses.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>

      {grouped.length === 0 ? (
        <Empty className="border border-dashed"><EmptyHeader><EmptyTitle>Nothing here</EmptyTitle><EmptyDescription>{query ? `No file matches “${query}”.` : 'No files for this view yet.'}</EmptyDescription></EmptyHeader></Empty>
      ) : grouped.map(g => {
        const all = g.items.every(i => picked.has(i.id))
        return (
          <section key={g.course} className="bg-card panel-lift overflow-hidden rounded-2xl border" aria-label={g.course}>
            <div className="bg-muted/40 flex items-center gap-3 border-b px-4 py-2.5">
              <Checkbox checked={all} onCheckedChange={() => toggleCourse(g.items)} aria-label={`Select all in ${g.course}`} />
              <span className="size-2.5 rounded-full" style={{ backgroundColor: colors[g.course] }} aria-hidden />
              <h2 className="min-w-0 flex-1 truncate text-sm font-semibold">{g.course}</h2>
              <span className="num text-muted-foreground text-xs">{g.items.length}</span>
            </div>
            <ul className="divide-y">
              {g.items.map(l => (
                <li key={l.id}>
                  <label className={cn('hover:bg-muted/40 flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors', picked.has(l.id) && 'bg-muted/50')}>
                    <Checkbox checked={picked.has(l.id)} onCheckedChange={() => toggle(l.id)} className="mt-0.5" aria-label={`Select ${l.title}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {weekNo(l) > 0 && <span className="num text-muted-foreground text-xs">Week {weekNo(l)}</span>}
                        <span className="font-medium">{l.title}</span>
                        {isNew(l, now) && <Badge className="h-5 px-1.5 text-[10px]">New</Badge>}
                      </div>
                      <div className="text-muted-foreground mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs">
                        {l.files.map((f, i) => <span key={i} className="flex items-center gap-1"><Paperclip className="size-3" />{f.filename || f.label}</span>)}
                        {(l.videos?.length ?? 0) > 0 && <span>{l.videos!.length} video{l.videos!.length > 1 ? 's' : ''} (open on the portal)</span>}
                      </div>
                      {l.remarks && <div className="text-muted-foreground mt-1 text-xs">{l.remarks}</div>}
                    </div>
                  </label>
                </li>
              ))}
            </ul>
          </section>
        )
      })}

      {/* the selection pill: centred on the window and fixed, so scrolling and the sidebar do not move it; it slides in and out */}
      <div
        role="region" aria-label="Selected lectures" aria-hidden={chosen.length === 0} inert={chosen.length === 0}
        className={cn(
          'bg-popover/90 text-popover-foreground fixed left-1/2 z-40 flex -translate-x-1/2 items-center gap-1.5 rounded-full border py-1.5 pr-1.5 pl-4 shadow-xl backdrop-blur-md transition-[transform,opacity,bottom] duration-300 ease-[var(--ease-out)]',
          busy ? 'bottom-20' : 'bottom-6',
          chosen.length > 0 ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-6 opacity-0',
        )}>
        <span className="num bg-primary text-primary-foreground grid h-6 min-w-6 place-items-center rounded-full px-1.5 text-xs font-semibold">{shownCount}</span>
        <span className="mr-1 text-sm">selected</span>
        <Button variant="ghost" size="sm" className="rounded-full" onClick={() => setPicked(new Set())}>Clear</Button>
        <Button size="sm" className="rounded-full pr-3.5" disabled={busy || demo} onClick={() => { onDownload(chosen); setPicked(new Set()) }}><Download />Download</Button>
      </div>
    </div>
  )
}
