import { Fragment, useMemo, useState } from 'react'
import { Copy, Download, FileCheck, FileText, Filter as FilterIcon, Lightbulb, PanelRight, Reply, Search } from 'lucide-react'
import type { Assignment, FileKind } from '@/api'
import { StatusBadge } from '@/components/assignments-table'
import { PageHeader, Stat } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuLabel, ContextMenuSeparator, ContextMenuTrigger } from '@/components/ui/context-menu'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { byDue, dueParts } from '@/format'
import { toast } from '@/lib/notify'
import { cn } from '@/lib/utils'

export type Filter = 'todo' | 'extended' | 'overdue' | 'submitted' | 'all'
export const isTodo = (a: Assignment) => !a.is_submitted && a.urgency !== 'missed'
export const isOverdue = (a: Assignment) => !a.is_submitted && a.urgency === 'missed'

export const FILE_LABELS: Record<string, string> = { brief: 'Assignment brief', submission: 'Your submission', returned: 'Returned work', solution: 'Solution' }
const FILE_ICONS = { brief: FileText, submission: FileCheck, returned: Reply, solution: Lightbulb } as const
export const fileKinds = (a: Assignment) => (['brief', 'submission', 'returned', 'solution'] as const).filter(k => a.files?.[k]?.href)
const hasMarks = (a: Assignment) => !!a.marks && !/not marked/i.test(a.marks)

type Group = { title: string; items: Assignment[] }

function copyText(text: string) {
  navigator.clipboard.writeText(text).then(() => toast.success('Copied'), () => toast.error('Could not copy', { description: 'The clipboard is not available.' }))
}

export function AssignmentsPage({ all, colors, now, tab, setTab, course, setCourse, selectedId, onSelect, onDownload, onDropFile, busy, demo }: {
  onDropFile: (a: Assignment, file: File) => void
  all: Assignment[]; now: number; colors: Record<string, string>; tab: Filter; setTab: (t: Filter) => void; course: string; setCourse: (c: string) => void
  selectedId: string | null; onSelect: (id: string | null) => void; onDownload: (a: Assignment[], kind: FileKind) => void; busy: boolean; demo: boolean
}) {
  const [query, setQuery] = useState('')
  const [dropId, setDropId] = useState<string | null>(null)       // the row a file is being dragged over
  const [sort, setSort] = useState<'due' | 'due-desc' | 'course'>('due')
  const courses = useMemo(() => [...new Set(all.map(a => a.course))].sort(), [all])
  const counts = { todo: all.filter(isTodo).length, extended: all.filter(a => a.is_extended && !a.is_submitted && a.open).length, overdue: all.filter(isOverdue).length, submitted: all.filter(a => a.is_submitted).length, all: all.length }
  const week = all.filter(a => a.open && !a.is_submitted && a.due_at && new Date(a.due_at).getTime() - now < 7 * 864e5).length

  const rows = useMemo(() => {
    const pick = ({ todo: isTodo, extended: (a: Assignment) => a.is_extended && !a.is_submitted && a.open, overdue: isOverdue, submitted: (a: Assignment) => a.is_submitted, all: () => true })[tab]
    const q = query.trim().toLowerCase()
    const list = all.filter(a => pick(a) && (course === 'all' || a.course === course) && (!q || `${a.title} ${a.course}`.toLowerCase().includes(q)))
    if (sort === 'course') return list.sort((a, b) => a.course.localeCompare(b.course) || byDue(a, b))
    list.sort(byDue)
    return sort === 'due-desc' ? list.reverse() : list
  }, [all, tab, course, query, sort])

  const groups: Group[] = useMemo(() => {
    if (sort === 'course') return [...new Set(rows.map(a => a.course))].map(c => ({ title: c, items: rows.filter(a => a.course === c) }))
    const g: Group[] = []
    const add = (title: string, items: Assignment[]) => { if (items.length) g.push({ title, items }) }
    add('Due today', rows.filter(a => !a.is_submitted && a.urgency === 'today'))
    add('Coming up', rows.filter(a => !a.is_submitted && (a.urgency === 'soon' || a.urgency === 'week')))
    add('Later', rows.filter(a => !a.is_submitted && (a.urgency === 'later' || a.urgency === 'unknown')))
    add('Overdue', rows.filter(isOverdue))
    add('Submitted', rows.filter(a => a.is_submitted))
    return g
  }, [rows, sort])

  const withBriefs = rows.filter(a => a.files?.brief?.href)

  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Assignments" description="Everything the portal lists for this semester: deadlines, files, marks and your submissions."
        actions={<Button variant="outline" size="sm" disabled={busy || demo || !withBriefs.length} onClick={() => onDownload(withBriefs, 'brief')}>
          <Download />Download briefs{withBriefs.length ? ` (${withBriefs.length})` : ''}</Button>} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="To do" value={counts.todo} sub={`${week} due in the next 7 days`} />
        <Stat label="Overdue" value={counts.overdue} sub={counts.overdue ? 'not submitted' : 'nothing missed'} tone={counts.overdue ? 'danger' : undefined} />
        <Stat label="Submitted" value={<>{counts.submitted}<span className="text-muted-foreground text-base font-normal">/{counts.all}</span></>} sub={`${all.filter(hasMarks).length} marked`} tone="success" />
        <Stat label="Courses" value={courses.length} sub={course === 'all' ? 'showing all' : 'one selected'} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs value={tab} onValueChange={v => setTab(v as Filter)} className="max-w-full overflow-x-auto">
          <TabsList>
            {([['todo', 'To do'], ['extended', 'Extended'], ['overdue', 'Overdue'], ['submitted', 'Submitted'], ['all', 'All']] as const).map(([k, l]) => (
              <TabsTrigger key={k} value={k}>{l}<span className="num text-muted-foreground ml-1.5 text-xs">{counts[k]}</span></TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="text-muted-foreground absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
            <Input value={query} onChange={e => setQuery(e.target.value)} placeholder="Filter by title or course" aria-label="Filter assignments" className="h-8 w-56 pl-8" />
          </div>
          <Select value={course} onValueChange={setCourse}>
            <SelectTrigger size="sm" className="w-52" aria-label="Course"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="all">All courses</SelectItem>{courses.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={sort} onValueChange={v => setSort(v as typeof sort)}>
            <SelectTrigger size="sm" className="w-40" aria-label="Sort"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="due">Due soonest</SelectItem><SelectItem value="due-desc">Due latest</SelectItem><SelectItem value="course">By course</SelectItem></SelectContent>
          </Select>
        </div>
      </div>

      {rows.length === 0 ? (
        <Empty className="border border-dashed"><EmptyHeader><EmptyTitle>Nothing here</EmptyTitle><EmptyDescription>{query ? `No assignment matches “${query}”.` : 'No assignments match this view.'}</EmptyDescription></EmptyHeader></Empty>
      ) : (
        <div className="bg-card overflow-hidden rounded-2xl border">
          <Table>
            <TableHeader className="bg-muted/40">
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-4">Assignment</TableHead>
                <TableHead className="hidden w-48 md:table-cell">Due</TableHead>
                <TableHead className="hidden w-28 xl:table-cell">Files</TableHead>
                <TableHead className="hidden w-24 xl:table-cell">Marks</TableHead>
                <TableHead className="w-36">Status</TableHead>
                <TableHead className="w-24"><span className="sr-only">Actions</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {groups.map(g => (
                <Fragment key={g.title}>
                  <TableRow className="bg-muted/30 hover:bg-muted/30">
                    <TableCell colSpan={6} className="text-muted-foreground py-1.5 pl-4 text-xs font-semibold">{g.title}<span className="num text-muted-foreground/70 ml-2 font-normal">{g.items.length}</span></TableCell>
                  </TableRow>
                  {g.items.map(a => {
                    const d = dueParts(a.due_at)
                    return (
                      <ContextMenu key={a.id}>
                      <ContextMenuTrigger asChild>
                      <TableRow id={`row-${a.id}`} tabIndex={0} data-state={a.id === selectedId ? 'selected' : undefined} className={cn('group cursor-pointer', dropId === a.id && 'bg-primary/10 outline-primary outline-2 -outline-offset-2')}
                        onDragOver={e => { if (e.dataTransfer.types.includes('Files')) { e.preventDefault(); e.dataTransfer.dropEffect = (a.can_upload || a.can_replace) && !demo && !busy ? 'copy' : 'none'; setDropId(a.id) } }}
                        onDragLeave={() => setDropId(cur => (cur === a.id ? null : cur))}
                        onDrop={e => {
                          e.preventDefault(); setDropId(null)
                          const file = e.dataTransfer.files[0]
                          if (!file) return
                          if (demo || busy) return void toast.info(demo ? 'Sample data: start the engine to upload.' : 'Another action is still running.')
                          if (!a.can_upload && !a.can_replace) return void toast.error(`${a.title} cannot be submitted now`, { description: 'The portal is not accepting a submission for it (deadline passed or already closed).' })
                          onDropFile(a, file)
                        }}
                        onClick={() => onSelect(a.id === selectedId ? null : a.id)} onKeyDown={e => { if (e.key === 'Enter') onSelect(a.id) }}>
                        <TableCell className="max-w-0 pl-4">
                          <div className="flex items-center gap-2.5">
                            <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: colors[a.course] }} aria-hidden />
                            <div className="min-w-0">
                              <div className="truncate font-medium">{a.title}</div>
                              <div className="text-muted-foreground truncate text-xs">{a.course} · #{a.assign_no}</div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          <div className="num text-sm">{d.day}{d.time && <span className="text-muted-foreground ml-2 text-xs">{d.time}</span>}</div>
                          {a.is_extended && a.original_due_date && <div className="text-warning text-xs">extended from {a.original_due_date.split(/[ -]/).slice(0, 3).join(' ')}</div>}
                        </TableCell>
                        <TableCell className="hidden xl:table-cell">
                          <div className="flex items-center gap-0.5" onClick={e => e.stopPropagation()}>
                            {fileKinds(a).length === 0 && <span className="text-muted-foreground text-xs">none</span>}
                            {fileKinds(a).map(k => {
                              const Icon = FILE_ICONS[k]
                              return (
                                <Tooltip key={k}>
                                  <TooltipTrigger asChild>
                                    <Button variant="ghost" size="icon" className="size-7" disabled={busy || demo} aria-label={`Download ${FILE_LABELS[k]}`} onClick={() => onDownload([a], k)}><Icon className="size-4" /></Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Download: {FILE_LABELS[k]}</TooltipContent>
                                </Tooltip>
                              )
                            })}
                          </div>
                        </TableCell>
                        <TableCell className="num hidden text-sm xl:table-cell">{hasMarks(a) ? a.marks : <span className="text-muted-foreground">–</span>}</TableCell>
                        <TableCell><StatusBadge a={a} /></TableCell>
                        <TableCell className="text-right">
                          {(a.can_upload || a.can_replace) && (
                            <Button size="sm" variant="outline" tabIndex={-1} className={cn('h-7 opacity-0 transition-opacity group-hover:opacity-100 group-data-[state=selected]:opacity-100 max-sm:opacity-100')}>
                              {a.can_replace ? 'Replace' : 'Upload'}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                      </ContextMenuTrigger>
                      <ContextMenuContent>
                        <ContextMenuLabel className="max-w-64 truncate">{a.title}</ContextMenuLabel>
                        <ContextMenuItem onSelect={() => onSelect(a.id === selectedId ? null : a.id)}><PanelRight />{a.id === selectedId ? 'Close details' : 'Open details'}</ContextMenuItem>
                        <ContextMenuItem onSelect={() => copyText(`${a.course}: ${a.title}`)}><Copy />Copy course and title</ContextMenuItem>
                        <ContextMenuSeparator />
                        <ContextMenuItem disabled={course === a.course} onSelect={() => setCourse(a.course)}><FilterIcon />Show only {a.course}</ContextMenuItem>
                      </ContextMenuContent>
                      </ContextMenu>
                    )
                  })}
                </Fragment>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
