import { Component, type ComponentProps, type ErrorInfo, type ReactNode } from 'react'
import { CircleHelp, Compass, Copy, Home, Keyboard, Loader2, PlugZap, RefreshCw, Search, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Kbd } from '@/components/ui/kbd'
import { Skeleton } from '@/components/ui/skeleton'
import { record } from '@/lib/activity'
import { cn } from '@/lib/utils'
import type { Running } from '@/useEngine'

// ------------------------------------------------------------------------------------------------ buttons and indicators
export const Spinner = ({ className }: { className?: string }) => <Loader2 aria-hidden className={cn('size-4 animate-spin', className)} />

/** A button that shows work in progress: a spinner, a "busy" state for assistive tech, and no double clicks. */
export function LoadingButton({ loading, children, disabled, ...props }: ComponentProps<typeof Button> & { loading?: boolean }) {
  return <Button {...props} disabled={disabled || loading} aria-busy={loading || undefined}>{loading && <Spinner />}{children}</Button>
}

/** A thin bar across the top of the window while something is running. */
export const TopProgress = ({ active }: { active: boolean }) => active ? <div className="top-progress" role="progressbar" aria-label="Working" /> : null

const KIND_LABEL: Record<string, string> = {
  sync: 'Checking the portal', upload: 'Uploading your file', delete: 'Deleting your submission', download: 'Downloading',
  verify: 'Verifying your sign-in', automation: 'Changing automatic checks', cloud: 'Working on cloud checks', email: 'Sending a test email', push: 'Sending a test notification',
}

/** What is running right now and which step it is on, visible on every page. */
export function RunningPill({ running }: { running: Running | null }) {
  if (!running) return null
  return (
    <div role="status" aria-live="polite" className="bg-popover text-popover-foreground animate-in fade-in slide-in-from-bottom-2 fixed bottom-4 left-1/2 z-40 flex max-w-[calc(100vw-2rem)] -translate-x-1/2 items-center gap-3 rounded-full border px-4 py-2 text-sm shadow-lg">
      <Spinner />
      <span className="font-medium">{KIND_LABEL[running.kind] ?? 'Working'}</span>
      <span className="text-muted-foreground truncate">{running.step.replace(/[….]+$/, '')}</span>
    </div>
  )
}

/** Fades and rises into place; pass an index to cascade a list. */
export function Reveal({ i = 0, className, children }: { i?: number; className?: string; children: ReactNode }) {
  return <div className={cn('animate-in fade-in slide-in-from-bottom-1 duration-300', className)} style={{ animationDelay: `${Math.min(i, 10) * 35}ms`, animationFillMode: 'both' }}>{children}</div>
}

// ------------------------------------------------------------------------------------------------ yes / no
/** The one confirmation used for everything that changes something: a plain question and an explicit Yes and No. */
export function ConfirmDialog({ open, onOpenChange, title, description, details, yes = 'Yes', no = 'No', danger, onYes }: {
  open: boolean; onOpenChange: (o: boolean) => void; title: string; description?: ReactNode; details?: ReactNode; yes?: string; no?: string; danger?: boolean; onYes: () => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>{title}</DialogTitle>{description && <DialogDescription>{description}</DialogDescription>}</DialogHeader>
        {details && <div className="bg-muted/50 rounded-lg border p-3 text-sm">{details}</div>}
        <DialogFooter>
          <Button variant="ghost" autoFocus={danger} onClick={() => onOpenChange(false)}>{no}</Button>
          <Button variant={danger ? 'destructive' : 'default'} onClick={() => { onOpenChange(false); onYes() }}>{yes}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ------------------------------------------------------------------------------------------------ full-page states
function Centered({ icon, title, children, actions }: { icon: ReactNode; title: string; children?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="animate-in fade-in zoom-in-95 mx-auto flex max-w-lg flex-col items-center gap-4 py-16 text-center duration-300" role="alert">
      <div className="bg-muted text-muted-foreground grid size-14 place-items-center rounded-2xl">{icon}</div>
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {children && <div className="text-muted-foreground text-sm">{children}</div>}
      {actions && <div className="mt-2 flex flex-wrap justify-center gap-2">{actions}</div>}
    </div>
  )
}

export function NotFoundPage({ path, onHome, onSearch, onAssignments }: { path: string; onHome: () => void; onSearch: () => void; onAssignments: () => void }) {
  return (
    <Centered icon={<Compass className="size-7" />} title="404: that page does not exist"
      actions={<><Button onClick={onHome}><Home />Go to Home</Button><Button variant="outline" onClick={onAssignments}>Assignments</Button><Button variant="outline" onClick={onSearch}><Search />Search<Kbd>Ctrl K</Kbd></Button></>}>
      <p>Nothing lives at <span className="num text-foreground">#/{path}</span>. The link may be old or mistyped.</p>
    </Centered>
  )
}

export function EngineOffline({ connecting, retryIn, onRetry, onDemo, detail }: { connecting: boolean; retryIn: number | null; onRetry: () => void; onDemo: () => void; detail?: string }) {
  return (
    <Centered icon={<PlugZap className="size-7" />} title="Can't reach the app engine"
      actions={<><LoadingButton loading={connecting} onClick={onRetry}><RefreshCw />{connecting ? 'Trying…' : 'Try again'}</LoadingButton><Button variant="outline" onClick={onDemo}>View sample data</Button></>}>
      <p>The interface shows your data through a small background engine on this PC, and it isn't answering. If you just opened the app, give it a few seconds. Otherwise close and reopen the app.</p>
      <p className="mt-2 text-xs select-text">{retryIn != null ? `Trying again automatically in ${retryIn}s.` : 'Trying again automatically.'}{detail ? ` (${detail})` : ''}</p>
    </Centered>
  )
}

/** Catches a crash inside the interface so the user gets a way out instead of a blank window. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }
  static getDerivedStateFromError(error: Error) { return { error } }
  componentDidCatch(error: Error, info: ErrorInfo) { record({ ok: false, title: 'The interface hit an error', detail: `${error.message}\n${info.componentStack ?? ''}`.slice(0, 600) }) }
  render() {
    const { error } = this.state
    if (!error) return this.props.children
    const details = `${error.name}: ${error.message}\n${error.stack ?? ''}`
    return (
      <div className="bg-background text-foreground grid min-h-dvh place-items-center p-6">
        <Centered icon={<TriangleAlert className="size-7" />} title="Something went wrong"
          actions={<>
            <Button onClick={() => window.location.reload()}><RefreshCw />Reload</Button>
            <Button variant="outline" onClick={() => { window.location.hash = '/home'; this.setState({ error: null }) }}><Home />Back to Home</Button>
            <Button variant="outline" onClick={() => void navigator.clipboard.writeText(details)}><Copy />Copy details</Button>
          </>}>
          <p>The interface stopped on an unexpected error. Your data and settings are safe. Reloading usually fixes it; if it keeps happening, copy the details and send them with a bug report.</p>
          <pre className="bg-muted text-foreground mt-3 max-h-40 overflow-auto rounded-lg p-3 text-left text-xs whitespace-pre-wrap">{error.message}</pre>
        </Centered>
      </div>
    )
  }
}

// ------------------------------------------------------------------------------------------------ loading placeholders
export function PageSkeleton({ kind = 'list' }: { kind?: 'list' | 'home' | 'cards' }) {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Loading">
      {kind === 'home' && <Skeleton className="h-44 w-full rounded-3xl" />}
      <div className="flex flex-col gap-2"><Skeleton className="h-7 w-48" /><Skeleton className="h-4 w-80 max-w-full" /></div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-24 rounded-2xl" />)}</div>
      {kind === 'cards' ? <div className="grid gap-4 lg:grid-cols-2">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-44 rounded-2xl" />)}</div>
        : <div className="flex flex-col gap-2">{[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-12 w-full" />)}</div>}
    </div>
  )
}

// ------------------------------------------------------------------------------------------------ help: what every action does
const SHORTCUTS: [string, string][] = [
  ['Ctrl K  or  /', 'Search assignments, go to any page, run a command'],
  ['F5', 'Check the portal now'],
  ['Ctrl 1 … 9', 'Go to Home, Assignments, Attendance, Exams, Timetable, Lectures, Announcements, Results, Settings'],
  ['Ctrl F', 'Jump to the filter box of the page you are on'],
  ['U', 'Choose a file to upload for the assignment that is open'],
  ['?', 'Show this help'],
  ['Esc', 'Close the open panel or dialog'],
]
const ACTIONS: [string, string][] = [
  ['Check now', 'Signs in to the portal and reads everything again. Takes about a minute.'],
  ['Upload / Replace', 'Sends your file through the portal\'s own Submit form, after you confirm. Replace deletes your current submission first.'],
  ['Delete submission', 'Removes your uploaded file from the portal (allowed until the deadline), after you confirm.'],
  ['Download (file icons)', 'Saves the brief, your submission, returned work or the solution into your Lectures folder.'],
  ['Settings', 'Profile, appearance, alerts, tracking, background and cloud checks, and your data. Changes are saved the moment you make them.'],
  ['Settings › Activity', 'Every action and its result, plus the engine\'s log, so nothing that happened is lost.'],
]

export function HelpDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader><DialogTitle>Shortcuts and what each action does</DialogTitle><DialogDescription>Anything that changes something asks you first and reports the result.</DialogDescription></DialogHeader>
        <div className="grid gap-4 text-sm">
          <section aria-label="Shortcuts"><h3 className="mb-2 flex items-center gap-2 font-medium"><Keyboard className="size-4" />Keyboard</h3>
            <dl className="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-1.5">{SHORTCUTS.map(([k, v]) => <div key={k} className="contents"><dt><Kbd>{k}</Kbd></dt><dd className="text-muted-foreground">{v}</dd></div>)}</dl></section>
          <section aria-label="Actions"><h3 className="mb-2 flex items-center gap-2 font-medium"><CircleHelp className="size-4" />Actions</h3>
            <dl className="flex flex-col gap-2">{ACTIONS.map(([k, v]) => <div key={k}><dt className="font-medium">{k}</dt><dd className="text-muted-foreground">{v}</dd></div>)}</dl></section>
        </div>
        <DialogFooter><Button onClick={() => onOpenChange(false)}>Got it</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
