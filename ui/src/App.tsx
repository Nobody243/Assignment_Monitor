import { useCallback, useEffect, useMemo, useState } from 'react'
import { RefreshCw, Search } from 'lucide-react'
import { toast } from 'sonner'
import { deleteSubmission, downloadAssignmentFiles, downloadLectures, openFolder, startSync, uploadFile, type Assignment, type FileKind } from '@/api'
import { AppSidebar } from '@/components/app-sidebar'
import { AssignmentSheet } from '@/components/assignment-sheet'
import { CommandMenu } from '@/components/command-menu'
import { Home, type Go } from '@/components/home'
import { Alert } from '@/components/inline-alert'
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { Skeleton } from '@/components/ui/skeleton'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ago } from '@/format'
import { courseColors } from '@/lib/courses'
import { PAGE_TITLES, usePage, type Page } from '@/lib/router'
import { AnnouncementsPage } from '@/pages/announcements-page'
import { AssignmentsPage, type Filter } from '@/pages/assignments-page'
import { AttendancePage } from '@/pages/attendance-page'
import { ExamsPage } from '@/pages/exams-page'
import { LecturesPage } from '@/pages/lectures-page'
import { ResultsPage } from '@/pages/results-page'
import { SettingsPage } from '@/pages/settings-page'
import { useEngine } from '@/useEngine'

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

function usePalette() {
  const [palette, setPalette] = useState(() => { try { return localStorage.getItem('am-palette') || 'royal' } catch { return 'royal' } })
  useEffect(() => {
    document.documentElement.dataset.palette = palette
    try { localStorage.setItem('am-palette', palette) } catch { /* private mode */ }
  }, [palette])
  return [palette, setPalette] as const
}

export default function App() {
  const { state, demo, running, run, now, refresh } = useEngine()
  const [dark, toggleTheme] = useTheme()
  const [palette, setPalette] = usePalette()
  const [page, navigate] = usePage()
  const [tab, setTab] = useState<Filter>('todo')
  const [course, setCourse] = useState('all')
  const [selId, setSelId] = useState<string | null>(null)
  const [cmdOpen, setCmdOpen] = useState(false)

  const all = useMemo(() => state?.assignments ?? [], [state])
  const colors = useMemo(() => courseColors(all), [all])
  const sel = all.find(a => a.id === selId) ?? null
  const busy = !!running

  const badges = useMemo<Partial<Record<Page, number>>>(() => {
    if (!state) return {}
    return {
      assignments: all.filter(a => !a.is_submitted && (a.urgency === 'today' || a.urgency === 'soon')).length,
      attendance: state.attendance.courses.filter(c => c.recorded && !c.ok).length,
      lectures: state.lectures.filter(l => l.first_seen && now - new Date(l.first_seen).getTime() < 7 * 864e5).length,
      announcements: state.announcements.filter(a => a.posted_at && now - new Date(a.posted_at).getTime() < 7 * 864e5).length,
    }
  }, [state, all, now])

  const go: Go = useCallback((p, opts) => {
    navigate(p)
    if (p === 'assignments') { if (opts?.tab) setTab(opts.tab); setCourse(opts?.course ?? 'all') }
  }, [navigate])

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

  const folderAction = { label: 'Open folder', onClick: () => void openFolder('lectures').catch(() => toast.error('Could not open the folder.')) }
  const doDownload = async (items: Assignment[], kind: FileKind) => {
    let saved = 0, failed = 0
    const id = toast.loading(items.length > 1 ? `Downloading ${items.length} files…` : 'Downloading…')
    for (const a of items) {
      const r = await run('download', () => downloadAssignmentFiles(a.id, kind), a.id)
      if (r.ok) saved++; else { failed++; if (items.length === 1) { toast.error(`${a.title}: ${r.message}`, { id }); return } }
    }
    if (failed) toast.error(`${saved} downloaded, ${failed} failed`, { id }); else toast.success(items.length > 1 ? `${saved} files downloaded` : 'Downloaded', { id, action: folderAction })
  }
  const doLectureDownload = async (ids: string[]) => {
    const id = toast.loading(`Downloading ${ids.length} item${ids.length > 1 ? 's' : ''}…`)
    const r = await run('download', () => downloadLectures(ids))
    if (r.ok) toast.success(r.message, { id, action: folderAction }); else toast.error(r.message, { id })
  }

  // keyboard: Ctrl/Cmd+K or / for search and commands, u to pick a file for the open assignment
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      const typing = t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || t.isContentEditable
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setCmdOpen(o => !o); return }
      if (typing || cmdOpen || e.ctrlKey || e.metaKey || e.altKey) return
      if (e.key === '/') { e.preventDefault(); setCmdOpen(true) }
      else if (e.key === 'u' && selId) window.dispatchEvent(new Event('am:pick'))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [cmdOpen, selId])

  const meta = state?.meta
  const render = () => {
    if (!state) {
      return (
        <div className="flex flex-col gap-3" aria-busy="true">
          <Skeleton className="h-36 w-full" />
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-24" />)}</div>
          {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      )
    }
    switch (page) {
      case 'home': return <Home state={state} now={now} onOpen={setSelId} onGo={go} />
      case 'assignments':
        return <AssignmentsPage all={all} colors={colors} tab={tab} setTab={setTab} course={course} setCourse={setCourse} selectedId={selId} onSelect={setSelId}
          onDownload={(items, kind) => void doDownload(items, kind)} busy={busy} demo={demo} />
      case 'attendance': return <AttendancePage state={state} />
      case 'exams': return <ExamsPage state={state} now={now} />
      case 'lectures': return <LecturesPage lectures={state.lectures} colors={colors} now={now} busy={busy} demo={demo} folder={state.paths.lectures}
        onDownload={ids => void doLectureDownload(ids)} onOpenFolder={() => void openFolder('lectures')} />
      case 'announcements': return <AnnouncementsPage items={state.announcements} colors={colors} now={now} />
      case 'results': return <ResultsPage results={state.results} />
      case 'settings': return <SettingsPage dark={dark} onToggleTheme={toggleTheme} palette={palette} onPalette={setPalette} paths={state.paths} version={state.version} demo={demo}
        onOpenFolder={k => void openFolder(k)} run={run} running={running} onDataCleared={() => void refresh()} />
    }
  }

  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar name={meta?.student_name} semester={meta?.semester} badges={badges} dark={dark} onToggleTheme={toggleTheme} page={page} onNavigate={navigate} palette={palette} onPalette={setPalette} />
        <SidebarInset>
          <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem className="max-sm:hidden">{meta?.semester ?? 'This semester'}</BreadcrumbItem>
                <BreadcrumbSeparator className="max-sm:hidden" />
                <BreadcrumbItem><BreadcrumbPage>{PAGE_TITLES[page]}</BreadcrumbPage></BreadcrumbItem>
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
            {render()}
          </div>
        </SidebarInset>

        <AssignmentSheet a={sel} now={now} demo={demo} running={running} onClose={() => setSelId(null)}
          onUpload={(f, r) => sel && void doUpload(sel, f, r)} onDelete={() => sel && void doDelete(sel)} onDownload={kind => sel && void doDownload([sel], kind)} />
        <CommandMenu open={cmdOpen} onOpenChange={setCmdOpen} assignments={all} dark={dark} onPick={id => { navigate('assignments'); setSelId(id) }} onSync={() => void doSync()}
          onToggleTheme={toggleTheme} onNavigate={navigate} />
        <Toaster position="bottom-right" theme={dark ? 'dark' : 'light'} />
      </SidebarProvider>
    </TooltipProvider>
  )
}
