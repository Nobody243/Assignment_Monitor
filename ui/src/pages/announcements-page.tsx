import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import type { Announcement } from '@/api'
import { PageHeader, Stat } from '@/components/page-header'
import { Badge } from '@/components/ui/badge'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const when = (a: Announcement) => (a.posted_at ? new Date(a.posted_at) : null)
const fmt = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', hour12: true })

export function AnnouncementsPage({ items, colors, now }: { items: Announcement[]; colors: Record<string, string>; now: number }) {
  const [query, setQuery] = useState('')
  const [course, setCourse] = useState('all')
  const courses = useMemo(() => [...new Set(items.map(a => a.course))].sort(), [items])
  const q = query.trim().toLowerCase()
  const list = useMemo(() => items
    .filter(a => (course === 'all' || a.course === course) && (!q || `${a.title} ${a.text} ${a.course}`.toLowerCase().includes(q)))
    .sort((a, b) => (b.posted_at ?? '').localeCompare(a.posted_at ?? '')), [items, course, q])
  const recent = items.filter(a => { const d = when(a); return d && now - d.getTime() < 7 * 864e5 }).length
  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Announcements" description="What your teachers posted on the LMS, newest first." />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Stat label="Announcements" value={items.length} sub={`from ${courses.length} course${courses.length === 1 ? '' : 's'}`} />
        <Stat label="Last 7 days" value={recent} sub={recent ? 'recent' : 'nothing new'} tone={recent ? 'success' : undefined} />
        <Stat label="Latest" value={items.length ? (when(list[0] ?? items[0])?.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) ?? '–') : '–'} sub="date posted" />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="text-muted-foreground absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
          <Input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search announcements" aria-label="Search announcements" className="h-8 w-64 pl-8" />
        </div>
        {courses.length > 1 && (
          <Select value={course} onValueChange={setCourse}>
            <SelectTrigger size="sm" className="w-52" aria-label="Course"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="all">All courses</SelectItem>{courses.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        )}
      </div>
      {list.length === 0 ? (
        <Empty className="border border-dashed"><EmptyHeader><EmptyTitle>No announcements</EmptyTitle><EmptyDescription>{query ? `Nothing matches “${query}”.` : 'Teachers have not posted anything yet.'}</EmptyDescription></EmptyHeader></Empty>
      ) : (
        <ul className="flex flex-col gap-3">
          {list.map(a => {
            const d = when(a)
            const fresh = d && now - d.getTime() < 7 * 864e5
            return (
              <li key={a.id} className="bg-card panel-lift rounded-2xl border p-5">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="size-2.5 rounded-full" style={{ backgroundColor: colors[a.course] }} aria-hidden />
                  <span className="text-sm font-medium">{a.course}</span>
                  {fresh && <Badge className="h-5 px-1.5 text-[10px]">New</Badge>}
                  <span className="num text-muted-foreground ml-auto text-xs">{d ? fmt.format(d) : a.posted}</span>
                </div>
                <h2 className="mt-2 font-semibold select-text">{a.title}</h2>
                <p className="text-muted-foreground mt-1 text-sm whitespace-pre-line select-text">{a.text}</p>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
