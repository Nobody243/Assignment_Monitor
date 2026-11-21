import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CircleHelp, RefreshCw, Search } from 'lucide-react'
import { patchSettings, deleteSubmission, downloadAssignmentFiles, downloadLectures, getSettings, getUpdate, installUpdate, openFolder, startSync, uploadFile, type Assignment, type FileKind } from '@/api'
import { AppSidebar, NAV_ORDER } from '@/components/app-sidebar'
import { AssignmentSheet } from '@/components/assignment-sheet'
import { CommandMenu } from '@/components/command-menu'
import { ConfirmDialog, EngineOffline, HelpDialog, NotFoundPage, PageSkeleton, RunningPill, TopProgress } from '@/components/feedback'
import { Home, type Go } from '@/components/home'
import { Alert } from '@/components/inline-alert'
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { Toaster } from '@/components/ui/sonner'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { ago, dueParts, sizeLabel } from '@/format'
import { useActivity } from '@/lib/activity'
import { courseColors } from '@/lib/courses'
import { toast } from '@/lib/notify'
import { PAGES, PAGE_TITLES, SETTINGS_TABS, usePage, type Page } from '@/lib/router'
import { directionBetween } from '@/lib/slide'
import { SetupWizard } from '@/components/setup-wizard'
import { AnnouncementsPage } from '@/pages/announcements-page'
import { AssignmentsPage, type Filter } from '@/pages/assignments-page'
import { AttendancePage } from '@/pages/attendance-page'
import { ExamsPage } from '@/pages/exams-page'
import { TimetablePage } from '@/pages/timetable-page'
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
  return [dark, () => setDark(d => !d), setDark] as const
}

function usePalette() {
  const [palette, setPalette] = useState(() => { try { return localStorage.getItem('am-palette') || 'royal' } catch { return 'royal' } })
  useEffect(() => {
    document.documentElement.dataset.palette = palette
    try { localStorage.setItem('am-palette', palette) } catch { /* private mode */ }
  }, [palette])
  return [palette, setPalette] as const
}

function useMotion() {
  const [on, setOn] = useState(() => { try { return localStorage.getItem('am-motion') !== 'off' } catch { return true } })
  useEffect(() => {
    document.documentElement.dataset.motion = on ? 'on' : 'off'
    try { localStorage.setItem('am-motion', on ? 'on' : 'off') } catch { /* private mode */ }
  }, [on])
  return [on, setOn] as const
}

type PendingUpload = { a: Assignment; file: File; replace: boolean }

export default function App() {
  const eng = useEngine()
  const { state, demo, running, run, now, refresh } = eng
  const [dark, toggleTheme, setDark] = useTheme()
  const [motion, setMotion] = useMotion()
  const [palette, setPalette] = usePalette()
  const { page, sub, missing, go: navigate } = usePage()
  // which way the page entrance moves is fixed when the page changes (it must not change again on a later re-render, which would replay it)
  const [travel, setTravel] = useState<{ page: string | null; dir: 1 | -1 | 0 }>({ page: null, dir: 0 })
  if (travel.page !== page) setTravel({ page, dir: directionBetween(NAV_ORDER, travel.page, page) })
  const pageDir = travel.dir
  const [tab, setTab] = useState<Filter>('todo')
  const [course, setCourse] = useState('all')
  const [selId, setSelId] = useState<string | null>(null)
  const [cmdOpen, setCmdOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const [pendingUpload, setPendingUpload] = useState<PendingUpload | null>(null)
  const [pendingDelete, setPendingDelete] = useState<Assignment | null>(null)
  const activity = useActivity()

  const all = useMemo(() => state?.assignments ?? [], [state])
  const colors = useMemo(() => courseColors(all), [all])
  const sel = all.find(a => a.id === selId) ?? null
  const busy = !!running

  const badges = useMemo<Partial<Record<Page, number>>>(() => {
    const failed = activity.filter(e => !e.ok && now - e.at < 864e5).length
    if (!state) return { settings: failed }
    return {
      assignments: all.filter(a => !a.is_submitted && (a.urgency === 'today' || a.urgency === 'soon')).length,
      attendance: state.attendance.courses.filter(c => c.recorded && !c.ok).length,
      lectures: state.lectures.filter(l => l.first_seen && now - new Date(l.first_seen).getTime() < 7 * 864e5).length,
      announcements: state.announcements.filter(a => a.posted_at && now - new Date(a.posted_at).getTime() < 7 * 864e5).length,
      settings: failed,
    }
  }, [state, all, now, activity])

  const go: Go = useCallback((p, opts) => {
    navigate(p)
    if (p === 'assignments') { if (opts?.tab) setTab(opts.tab); setCourse(opts?.course ?? 'all') }
  }, [navigate])

  // ---- actions. Each one names what it is doing, shows progress, and reports how it ended (and the report is kept in Activity)
  const doSync = useCallback(async () => {
    if (demo) return void toast.info('Sample data: start the engine to check the portal.')
    // progress is shown once, by the pill at the bottom (RunningPill); the toast only reports how it ended
    const r = await run('sync', startSync)
    if (r.ok) toast.success(r.message || 'Checked the portal.'); else toast.error('The check did not finish', { description: r.message })
  }, [demo, run])
  const loaded = !!state && !demo
  // text cut short with an ellipsis gets its full text as a tooltip the moment the pointer is over it
  useEffect(() => {
    const over = (e: MouseEvent) => {
      const t = (e.target as HTMLElement | null)?.closest?.('.truncate') as HTMLElement | null
      if (t && !t.title && t.scrollWidth > t.clientWidth + 1) t.title = (t.textContent ?? '').trim()
    }
    document.addEventListener('mouseover', over)
    return () => document.removeEventListener('mouseover', over)
  }, [])
  // a file dropped anywhere but on a row must not make the window open it
  useEffect(() => {
    const stop = (e: DragEvent) => { if (e.dataTransfer?.types.includes('Files')) e.preventDefault() }
    window.addEventListener('dragover', stop); window.addEventListener('drop', stop)
    return () => { window.removeEventListener('dragover', stop); window.removeEventListener('drop', stop) }
  }, [])
  // first run: the setup walkthrough, only for a fresh install (an existing sign-in means it was set up before)
  const [setup, setSetup] = useState(false)
  useEffect(() => {
    if (!loaded) return
    void getSettings().then(s => {
      if (s.setup_done) return
      if (s.account.password_set) void patchSettings({ setup_done: true }).catch(() => {})
      else setSetup(true)
    }).catch(() => {})
  }, [loaded])
  useEffect(() => {
    const open = () => setSetup(true)
    window.addEventListener('am:setup', open)
    return () => window.removeEventListener('am:setup', open)
  }, [])
  // every time the app opens, shortly after the engine answers: look for a newer version (installed build, and only if update checks are on).
  // A newer one is announced with an Update now button; nothing is installed until the student says yes.
  const [newVersion, setNewVersion] = useState<string | null>(null)
  const checkedForUpdate = useRef(false)
  useEffect(() => {
    if (demo || checkedForUpdate.current) return
    checkedForUpdate.current = true
    const t = setTimeout(() => {
      void (async () => {
        try {
          const s = await getSettings()
          if (!s.about.installed || !s.background.check_updates) return
          const u = await getUpdate()
          if (!u.newer || !u.version) return
          const v = u.version
          toast.info(`Version ${v} is available`, {
            description: 'Your data and settings are kept.', duration: 30000,
            action: { label: 'Update now', onClick: () => setNewVersion(v) }, cancel: { label: 'Later', onClick: () => {} },
          })
        } catch { /* offline or GitHub unreachable: say nothing */ }
      })()
    }, 3000)
    return () => clearTimeout(t)
  }, [demo])
  const installNow = async () => {
    const r = await run('update', installUpdate)
    if (r.ok) toast.success(r.message); else toast.error('The update did not install', { description: r.message })
  }

  const doUpload = async ({ a, file, replace }: PendingUpload) => {
    const r = await run('upload', () => uploadFile(a.id, file, replace), a.id)
    if (r.ok) toast.success(`${a.title}: ${replace ? 'submission replaced' : 'uploaded'}`, { description: r.message })
    else toast.error(`${a.title} was not uploaded`, { description: r.message + (r.deleted ? ' Your previous submission was already deleted, so upload again before the deadline.' : '') })
  }
  const doDelete = async (a: Assignment) => {
    const r = await run('delete', () => deleteSubmission(a.id), a.id)
    if (r.ok) toast.success(`${a.title}: submission deleted`, { description: r.message }); else toast.error(`${a.title}: could not delete the submission`, { description: r.message })
  }

  const openFolderSafe = (k: 'lectures' | 'data' | 'timetable') => void openFolder(k).catch(e => toast.error('Could not open the folder', { description: e instanceof Error ? e.message : undefined }))
  const folderAction = { label: 'Open folder', onClick: () => openFolderSafe('lectures') }
  const doDownload = async (items: Assignment[], kind: FileKind) => {
    let saved = 0, failed = 0
    for (const a of items) {
      const r = await run('download', () => downloadAssignmentFiles(a.id, kind), a.id)
      if (r.ok) saved++
      else { failed++; if (items.length === 1) { toast.error(`${a.title}: download failed`, { description: r.message }); return } }
    }
    if (failed) toast.error(`${saved} downloaded, ${failed} failed`); else toast.success(items.length > 1 ? `${saved} files downloaded` : 'File downloaded', { action: folderAction })
  }
  const doLectureDownload = async (ids: string[]) => {
    const r = await run('download', () => downloadLectures(ids))
    if (r.ok) toast.success(r.message, { action: folderAction }); else toast.error('Lecture download failed', { description: r.message })
  }

  // keyboard: Ctrl/Cmd+K or / search, ? help, u pick a file for the open assignment
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      const typing = t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || t.isContentEditable
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setCmdOpen(o => !o); return }
      if (cmdOpen) return
      if (e.key === 'F5') { e.preventDefault(); void doSync(); return }                                       // check now, as in the old app
      if ((e.ctrlKey || e.metaKey) && /^[1-9]$/.test(e.key) && PAGES[Number(e.key) - 1]) { e.preventDefault(); navigate(PAGES[Number(e.key) - 1]); return }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {                                          // jump to the page's own filter box
        const box = document.querySelector<HTMLInputElement>('input[aria-label^="Filter"], input[aria-label^="Search"]')
        if (box) { e.preventDefault(); box.focus(); box.select() }
        return
      }
      if (typing || cmdOpen || e.ctrlKey || e.metaKey || e.altKey) return
      if (e.key === '/') { e.preventDefault(); setCmdOpen(true) }
      else if (e.key === '?') { e.preventDefault(); setHelpOpen(true) }
      else if (e.key === 'u' && selId) window.dispatchEvent(new Event('am:pick'))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [cmdOpen, selId, doSync, navigate])

  const meta = state?.meta
  const render = () => {
    if (import.meta.env.DEV && page === 'notfound' && missing === '__crash') throw new Error('Test crash: this route exists only in development to check the crash screen.')
    if (page === 'notfound') return <NotFoundPage path={missing} onHome={() => navigate('home')} onAssignments={() => navigate('assignments')} onSearch={() => setCmdOpen(true)} />
    if (!state) {
      return eng.connection === 'connecting'
        ? <PageSkeleton kind={page === 'home' ? 'home' : page === 'attendance' || page === 'exams' ? 'cards' : 'list'} />
        : <EngineOffline connecting={false} retryIn={eng.retryIn} detail={eng.lastError} onRetry={eng.retry} onDemo={eng.showDemo} />
    }
    switch (page) {
      case 'home': return <Home state={state} now={now} onOpen={setSelId} onGo={go} />
      case 'assignments':
        return <AssignmentsPage all={all} colors={colors} now={now} tab={tab} setTab={setTab} course={course} setCourse={setCourse} selectedId={selId} onSelect={setSelId}
          onDownload={(items, kind) => void doDownload(items, kind)} onDropFile={(a, file) => setPendingUpload({ a, file, replace: a.can_replace })} busy={busy} demo={demo} />
      case 'attendance': return <AttendancePage state={state} />
      case 'exams': return <ExamsPage state={state} now={now} />
      case 'timetable': return <TimetablePage state={state} now={now} dark={dark} demo={demo} />
      case 'lectures': return <LecturesPage lectures={state.lectures} colors={colors} now={now} busy={busy} demo={demo} folder={state.paths.lectures}
        onDownload={ids => void doLectureDownload(ids)} onOpenFolder={() => openFolderSafe('lectures')} />
      case 'announcements': return <AnnouncementsPage items={state.announcements} colors={colors} now={now} />
      case 'results': return <ResultsPage results={state.results} />
      case 'settings': return <SettingsPage tab={sub ?? 'profile'} onTab={t => navigate('settings', t)} state={state} now={now} demo={demo}
        dark={dark} onTheme={setDark} palette={palette} onPalette={setPalette} motion={motion} onMotion={setMotion}
        onOpenFolder={openFolderSafe} onDataCleared={() => void refresh()} run={run} running={running} />
    }
  }

  return (
    <TooltipProvider>
      <TopProgress active={busy} />
      {setup && <SetupWizard run={run} busy={busy} dark={dark} onTheme={setDark} palette={palette} onPalette={setPalette} motion={motion} onMotion={setMotion}
        onClose={checkNow => { setSetup(false); void refresh(); if (checkNow) void doSync() }} />}
      <SidebarProvider>
        <AppSidebar name={meta?.student_name} semester={meta?.semester} badges={badges} dark={dark} onToggleTheme={toggleTheme} page={page === 'notfound' ? 'home' : page} onNavigate={navigate} palette={palette} onPalette={setPalette} />
        <SidebarInset>
          <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem className="max-sm:hidden">{meta?.semester ?? 'This semester'}</BreadcrumbItem>
                <BreadcrumbSeparator className="max-sm:hidden" />
                {page === 'settings' ? (<><BreadcrumbItem className="max-sm:hidden">{PAGE_TITLES.settings}</BreadcrumbItem><BreadcrumbSeparator className="max-sm:hidden" /><BreadcrumbItem><BreadcrumbPage>{SETTINGS_TABS.find(t => t.key === (sub ?? 'profile'))?.label}</BreadcrumbPage></BreadcrumbItem></>) : <BreadcrumbItem><BreadcrumbPage>{PAGE_TITLES[page]}</BreadcrumbPage></BreadcrumbItem>}
              </BreadcrumbList>
            </Breadcrumb>
            <div className="ml-auto flex items-center gap-2">
              <span className="text-muted-foreground mr-1 text-xs max-md:hidden">{eng.stale ? 'Offline · showing the last data' : meta?.last_sync ? `Checked ${ago(meta.last_sync, now)}` : 'Not checked yet'}</span>
              <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className="size-8" aria-label="Shortcuts and what each action does" onClick={() => setHelpOpen(true)}><CircleHelp /></Button></TooltipTrigger><TooltipContent>Shortcuts and actions <Kbd>?</Kbd></TooltipContent></Tooltip>
              <Button variant="outline" size="sm" onClick={() => setCmdOpen(true)} className="text-muted-foreground max-sm:px-2" aria-label="Search and commands">
                <Search /><span className="max-sm:hidden">Search</span><Kbd className="max-sm:hidden">Ctrl K</Kbd>
              </Button>
              <Button size="sm" onClick={() => void doSync()} disabled={busy || (!state && !demo)} aria-busy={running?.kind === 'sync' || undefined}>
                <RefreshCw className={running?.kind === 'sync' ? 'animate-spin' : ''} />
                <span className="max-sm:hidden">{running?.kind === 'sync' ? 'Checking…' : 'Check now'}</span>
              </Button>
            </div>
          </header>

          <div className="flex flex-1 flex-col gap-6 p-4 md:p-6">
            {demo && <Alert tone="info"><span className="flex flex-wrap items-center gap-x-3 gap-y-1">Showing sample data. The engine is not running, so nothing here is yours.<Button size="sm" variant="outline" className="h-7" onClick={eng.leaveDemo}>Try the engine again</Button></span></Alert>}
            {eng.stale && <Alert tone="warning"><span className="flex flex-wrap items-center gap-x-3 gap-y-1">Lost the connection to the engine. You are seeing the last data it sent{eng.lastGood ? ` (${dueParts(new Date(eng.lastGood).toISOString()).time})` : ''}. {eng.retryIn != null ? `Trying again in ${eng.retryIn}s.` : ''}<Button size="sm" variant="outline" className="h-7" onClick={eng.retry}>Try now</Button></span></Alert>}
            <div key={page} data-dir={pageDir} className="page-enter min-w-0">{render()}</div>
          </div>
        </SidebarInset>

        <AssignmentSheet a={sel} now={now} demo={demo} running={running} onClose={() => setSelId(null)}
          onUpload={(file, replace) => sel && setPendingUpload({ a: sel, file, replace })} onDelete={() => sel && setPendingDelete(sel)} onDownload={kind => sel && void doDownload([sel], kind)} />

        <ConfirmDialog open={!!newVersion} onOpenChange={o => { if (!o) setNewVersion(null) }} title={`Install version ${newVersion ?? ''}?`}
          description="The app downloads the update, checks it against the checksum published with the release, then closes and reopens by itself. Your data and settings are kept."
          yes="Yes, update now" no="Not now" onYes={() => void installNow()} />
        <ConfirmDialog open={!!pendingUpload} onOpenChange={o => { if (!o) setPendingUpload(null) }}
          title={pendingUpload?.replace ? 'Replace your submission?' : 'Upload this file?'}
          description="You are graded on exactly what you upload. Check the file and the assignment."
          details={pendingUpload && (
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
              <dt className="text-muted-foreground">File</dt><dd className="break-all">{pendingUpload.file.name} <span className="text-muted-foreground">({sizeLabel(pendingUpload.file.size)})</span></dd>
              <dt className="text-muted-foreground">Assignment</dt><dd>{pendingUpload.a.title}</dd>
              <dt className="text-muted-foreground">Course</dt><dd>{pendingUpload.a.course}</dd>
              <dt className="text-muted-foreground">Due</dt><dd className="num">{dueParts(pendingUpload.a.due_at).day} {dueParts(pendingUpload.a.due_at).time}</dd>
              {pendingUpload.replace && <><dt className="text-muted-foreground">Note</dt><dd>Your current submission is deleted first. You can do this again until the deadline.</dd></>}
            </dl>)}
          yes={pendingUpload?.replace ? 'Yes, replace and upload' : 'Yes, upload'} no="No, go back" onYes={() => pendingUpload && void doUpload(pendingUpload)} />
        <ConfirmDialog open={!!pendingDelete} onOpenChange={o => { if (!o) setPendingDelete(null) }} danger
          title="Delete your submission?" description={pendingDelete ? `${pendingDelete.title} · ${pendingDelete.course}` : undefined}
          details="Your uploaded file is removed from the portal. You can upload again until the deadline."
          yes="Yes, delete it" no="No, keep it" onYes={() => pendingDelete && void doDelete(pendingDelete)} />

        <CommandMenu open={cmdOpen} onOpenChange={setCmdOpen} assignments={all} dark={dark} onPick={id => { navigate('assignments'); setSelId(id) }} onSync={() => void doSync()}
          onToggleTheme={toggleTheme} onNavigate={navigate} onHelp={() => setHelpOpen(true)} />
        <HelpDialog open={helpOpen} onOpenChange={setHelpOpen} />
        <RunningPill running={running} />
        <Toaster position="bottom-right" theme={dark ? 'dark' : 'light'} />
      </SidebarProvider>
    </TooltipProvider>
  )
}

