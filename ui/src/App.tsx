import { useCallback, useEffect, useMemo, useState } from 'react'
import { CheckCheck, RefreshCw, Search, Upload } from 'lucide-react'
import { toast } from 'sonner'
import { deleteSubmission, startSync, uploadFile, type Assignment } from '@/api'
import { AppSidebar } from '@/components/app-sidebar'
import { AssignmentSheet } from '@/components/assignment-sheet'
import { AssignmentsTable } from '@/components/assignments-table'
import { CommandMenu } from '@/components/command-menu'
import { Alert } from '@/components/inline-alert'
import { Badge } from '@/components/ui/badge'
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Kbd } from '@/components/ui/kbd'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { Skeleton } from '@/components/ui/skeleton'
import { Toaster } from '@/components/ui/sonner'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ago, byDue, countdown, dueParts } from '@/format'
import { useEngine } from '@/useEngine'

type Filter = 'todo' | 'overdue' | 'submitted' | 'all'
const isTodo = (a: Assignment) => !a.is_submitted && a.urgency !== 'missed'
const isOverdue = (a: Assignment) => !a.is_submitted && a.urgency === 'missed'

function useTheme() {
  const [dark, setDark] = useState(() => {
    try { const t = localStorage.getItem('am-theme'); if (t) return t === 'dark' } catch { /* private mode */ }
    return matchMedia('(prefers-color-scheme: dark)').matches
  })
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    try { localStorage.setItem('am-theme', dark ? 'dark' : 'light') } catch { /* private mode */ }
  }, [dark])
  return [dark, () => setDark(d => !d)] as const
}

export default function App() {
  const { state, demo, running, run, now } = useEngine()
  const [dark, toggleTheme] = useTheme()
  const [tab, setTab] = useState<Filter>('todo')
  const [course, setCourse] = useState('all')
  const [selId, setSelId] = useState<string | null>(null)
  const [cmdOpen, setCmdOpen] = useState(false)

  const all = useMemo(() => state?.assignments ?? [], [state])
  const courses = useMemo(() => [...new Set(all.map(a => a.course))].sort(), [all])
  const counts = useMemo(() => ({
    todo: all.filter(isTodo).length, overdue: all.filter(isOverdue).length, submitted: all.filter(a => a.is_submitted).length, all: all.length,
  }), [all])
  const today = all.filter(a => !a.is_submitted && a.urgency === 'today')
  const coming = all.filter(a => !a.is_submitted && (a.urgency === 'soon' || a.urgency === 'week'))
  const dueSoon = today.length + all.filter(a => !a.is_submitted && a.urgency === 'soon').length

  const rows = useMemo(() => {
    const pick = ({ todo: isTodo, overdue: isOverdue, submitted: (a: Assignment) => a.is_submitted, all: () => true })[tab]
    const list = all.filter(a => pick(a) && (course === 'all' || a.course === course)).sort(byDue)
    return tab === 'overdue' || tab === 'submitted' ? list.reverse() : list
  }, [all, tab, course])

  const next = useMemo(() => all.filter(a => a.open && !a.is_submitted).sort(byDue)[0], [all])
  const sel = all.find(a => a.id === selId) ?? null
  const order = useMemo(() => rows.map(a => a.id), [rows])

  const doSync = useCallback(async () => {
    if (demo) return void toast.info('Sample data: start the engine to check the portal.')
    const id = toast.loading('Checking the portal…')
    const r = await run('sync', startSync)
    if (r.ok) toast.success(r.message || 'Checked.', { id }); else toast.error(r.message || 'The check did not finish.', { id })
  }, [demo, run])

  const doUpload = async (a: Assignment, file: File, replace: boolean) => {
    const r = await run('upload', () => uploadFile(a.id, file, replace), a.id)
    if (r.ok) toast.success(`${a.title}: ${r.message}`)
    else toast.error(`${a.title} was not uploaded`, { description: r.message + (r.deleted ? ' Your previous submission was already deleted, so upload again before the deadline.' : ''), duration: 9000 })
  }
  const doDelete = async (a: Assignment) => {
    const r = await run('delete', () => deleteSubmission(a.id), a.id)
    if (r.ok) toast.success(`${a.title}: ${r.message}`); else toast.error(`${a.title}: ${r.message}`)
  }

  // keyboard: Ctrl/Cmd+K or / search, j/k move, u upload
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      const typing = t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || t.isContentEditable
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setCmdOpen(o => !o); return }
      if (typing || cmdOpen || e.ctrlKey || e.metaKey || e.altKey) return
      if (e.key === '/') { e.preventDefault(); setCmdOpen(true) }
      else if (e.key === 'j' || e.key === 'k') {
        const step = e.key === 'j' ? 1 : -1
        const i = selId ? order.indexOf(selId) : -1
        const to = order[Math.min(order.length - 1, Math.max(0, i + step))]
        if (to) setSelId(to)
      } else if (e.key === 'u' && selId) window.dispatchEvent(new Event('am:pick'))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [cmdOpen, order, selId])

  const meta = state?.meta
  const busy = !!running
  const first = (list: Assignment[]) => [...list].sort(byDue)[0]
  const stats: { label: string; n: number; foot: string; go: Filter }[] = [
    { label: 'Due today', n: today.length, foot: today.length ? first(today).title : 'Nothing due today', go: 'todo' },
    { label: 'Coming up', n: coming.length, foot: coming.length ? `Next: ${first(coming).title}` : 'Nothing in the next 7 days', go: 'todo' },
    { label: 'Overdue', n: counts.overdue, foot: counts.overdue ? 'Not submitted' : 'Nothing missed', go: 'overdue' },
    { label: 'Submitted', n: counts.submitted, foot: `of ${counts.all} this semester`, go: 'submitted' },
  ]

  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar name={meta?.student_name} semester={meta?.semester} dueSoon={dueSoon} dark={dark} onToggleTheme={toggleTheme} />
        <SidebarInset>
          <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem className="max-sm:hidden">{meta?.semester ?? 'This semester'}</BreadcrumbItem>
                <BreadcrumbSeparator className="max-sm:hidden" />
                <BreadcrumbItem><BreadcrumbPage>Assignments</BreadcrumbPage></BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
            <div className="ml-auto flex items-center gap-2">
              <span className="text-muted-foreground mr-1 text-xs max-md:hidden">Checked {ago(meta?.last_sync, now)}</span>
              <Button variant="outline" size="sm" onClick={() => setCmdOpen(true)} className="text-muted-foreground max-sm:px-2">
                <Search /><span className="max-sm:hidden">Search</span><Kbd className="max-sm:hidden">Ctrl K</Kbd>
              </Button>
              <Button size="sm" onClick={() => void doSync()} disabled={busy}>
                <RefreshCw className={running?.kind === 'sync' ? 'animate-spin' : ''} />
                <span className="max-sm:hidden">{running?.kind === 'sync' ? 'Checking…' : 'Check now'}</span>
              </Button>
            </div>
          </header>

          <div className="flex flex-1 flex-col gap-6 p-4 md:p-6">
            {demo && state && <Alert tone="info">Showing sample data. The engine is not running, so nothing here is yours yet.</Alert>}

            {!state ? (
              <div className="flex flex-col gap-3" aria-busy="true">
                <Skeleton className="h-36 w-full" />
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-24" />)}</div>
                {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : (
              <>
                {next ? (
                  <Card className="border-brand/25 bg-gradient-to-br from-brand/[0.06] to-transparent">
                    <CardContent className="flex flex-wrap items-center justify-between gap-6">
                      <div className="min-w-0 flex-1">
                        <Badge variant="outline" className="border-brand/30 text-brand mb-3 gap-1.5"><span className="bg-brand size-1.5 rounded-full" />{next.urgency === 'today' ? 'Due today' : 'Up next'}</Badge>
                        <h2 className="text-xl font-semibold tracking-tight text-balance">{next.title}</h2>
                        <p className="text-muted-foreground mt-1 text-sm">{next.course} · {dueParts(next.due_at).day}{dueParts(next.due_at).time && ` at ${dueParts(next.due_at).time}`}</p>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right" aria-label={`${countdown(next.due_at, now).big} left`}>
                          <div className="num text-4xl font-medium">{countdown(next.due_at, now).big}</div>
                          <div className="text-muted-foreground text-xs">{countdown(next.due_at, now).unit}</div>
                        </div>
                        <Button size="lg" onClick={() => setSelId(next.id)}><Upload />{next.can_upload ? 'Upload your work' : 'Open'}</Button>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <Empty className="border border-dashed">
                    <EmptyHeader>
                      <EmptyMedia variant="icon"><CheckCheck /></EmptyMedia>
                      <EmptyTitle>You are all caught up</EmptyTitle>
                      <EmptyDescription>{all.length ? 'Nothing is waiting for you. New work shows up here as soon as the portal lists it.' : 'No assignments yet. They appear here once the portal lists them.'}</EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                )}

                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  {stats.map(s => (
                    <Card key={s.label} size="sm" className="hover:bg-muted/40 cursor-pointer transition-colors" role="button" tabIndex={0}
                      onClick={() => setTab(s.go)} onKeyDown={e => { if (e.key === 'Enter') setTab(s.go) }}>
                      <CardHeader>
                        <CardDescription>{s.label}</CardDescription>
                        <CardTitle className="num text-3xl font-medium">{s.n}</CardTitle>
                      </CardHeader>
                      <CardFooter className="text-muted-foreground truncate text-xs">{s.foot}</CardFooter>
                    </Card>
                  ))}
                </div>

                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <Tabs value={tab} onValueChange={v => setTab(v as Filter)}>
                      <TabsList>
                        {([['todo', 'To do'], ['overdue', 'Overdue'], ['submitted', 'Submitted'], ['all', 'All']] as const).map(([k, l]) => (
                          <TabsTrigger key={k} value={k}>{l}<span className="num text-muted-foreground ml-1.5 text-xs">{counts[k]}</span></TabsTrigger>
                        ))}
                      </TabsList>
                    </Tabs>
                    {courses.length > 1 && (
                      <Select value={course} onValueChange={setCourse}>
                        <SelectTrigger size="sm" className="w-52" aria-label="Course"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All courses</SelectItem>
                          {courses.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                  {rows.length ? (
                    <AssignmentsTable rows={rows} selectedId={selId} onSelect={id => setSelId(id === selId ? null : id)} />
                  ) : (
                    <Empty className="border border-dashed">
                      <EmptyHeader><EmptyTitle>Nothing here</EmptyTitle><EmptyDescription>No assignments match this view.</EmptyDescription></EmptyHeader>
                    </Empty>
                  )}
                </div>
              </>
            )}
          </div>
        </SidebarInset>

        <AssignmentSheet a={sel} now={now} demo={demo} running={running} onClose={() => setSelId(null)}
          onUpload={(f, r) => sel && void doUpload(sel, f, r)} onDelete={() => sel && void doDelete(sel)} />
        <CommandMenu open={cmdOpen} onOpenChange={setCmdOpen} assignments={all} dark={dark} onPick={setSelId} onSync={() => void doSync()} onToggleTheme={toggleTheme} />
        <Toaster position="bottom-right" theme={dark ? 'dark' : 'light'} />
      </SidebarProvider>
    </TooltipProvider>
  )
}
