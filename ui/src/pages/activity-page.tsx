import { useCallback, useEffect, useMemo, useState } from 'react'
import { CircleCheck, CircleX, RefreshCw, Trash2 } from 'lucide-react'
import { getLog, type LogEntry } from '@/api'
import { ConfirmDialog, LoadingButton, Reveal } from '@/components/feedback'
import { Alert } from '@/components/inline-alert'
import { Stat } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { clearActivity, useActivity } from '@/lib/activity'
import { cn } from '@/lib/utils'

const when = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', hour12: true })
const LEVEL: Record<string, string> = { ERROR: 'text-destructive', CRITICAL: 'text-destructive', WARNING: 'text-warning', INFO: 'text-muted-foreground', DEBUG: 'text-muted-foreground' }

function Actions({ now }: { now: number }) {
  const entries = useActivity()
  const [only, setOnly] = useState<'all' | 'failed'>('all')
  const [confirm, setConfirm] = useState(false)
  const shown = only === 'failed' ? entries.filter(e => !e.ok) : entries
  const failed = entries.filter(e => !e.ok).length
  const today = entries.filter(e => now - e.at < 864e5).length
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Recorded" value={entries.length} sub="most recent 200" />
        <Stat label="Today" value={today} sub="actions in the last 24 hours" />
        <Stat label="Failed" value={failed} sub={failed ? 'worth a look' : 'none'} tone={failed ? 'danger' : 'success'} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs value={only} onValueChange={v => setOnly(v as typeof only)}>
          <TabsList><TabsTrigger value="all">All<span className="num text-muted-foreground ml-1.5 text-xs">{entries.length}</span></TabsTrigger><TabsTrigger value="failed">Failed<span className="num text-muted-foreground ml-1.5 text-xs">{failed}</span></TabsTrigger></TabsList>
        </Tabs>
        <Button variant="ghost" size="sm" className="text-muted-foreground" disabled={!entries.length} onClick={() => setConfirm(true)}><Trash2 />Clear history</Button>
      </div>
      {shown.length === 0 ? (
        <Empty className="border border-dashed"><EmptyHeader><EmptyTitle>{only === 'failed' ? 'Nothing has failed' : 'Nothing yet'}</EmptyTitle><EmptyDescription>Every upload, check, download and setting change is recorded here with its result.</EmptyDescription></EmptyHeader></Empty>
      ) : (
        <ul className="bg-card panel-lift divide-y overflow-hidden rounded-2xl border">
          {shown.slice(0, 120).map((e, i) => (
            <li key={e.id}><Reveal i={i} className="flex items-start gap-3 px-4 py-3">
              {e.ok ? <CircleCheck className="text-success mt-0.5 size-4 shrink-0" /> : <CircleX className="text-destructive mt-0.5 size-4 shrink-0" />}
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium">{e.title}</div>
                {e.detail && <div className="text-muted-foreground mt-0.5 text-xs whitespace-pre-line">{e.detail}</div>}
              </div>
              <time className="num text-muted-foreground shrink-0 text-xs" dateTime={new Date(e.at).toISOString()}>{when.format(e.at)}</time>
            </Reveal></li>
          ))}
        </ul>
      )}
      <ConfirmDialog open={confirm} onOpenChange={setConfirm} title="Clear the history?" description="This removes the list above from this computer. It does not undo anything that was done." yes="Yes, clear it" no="No, keep it" danger onYes={clearActivity} />
    </div>
  )
}

function EngineLog({ demo }: { demo: boolean }) {
  const [entries, setEntries] = useState<LogEntry[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [level, setLevel] = useState<'all' | 'problems'>('problems')
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { setEntries((await getLog(400)).entries) } catch (e) { setError(e instanceof Error ? e.message : 'Could not read the log.') }
    setLoading(false)
  }, [])
  useEffect(() => { if (!demo) void load() }, [demo, load])
  const shown = useMemo(() => (entries ?? []).filter(e => level === 'all' || ['WARNING', 'ERROR', 'CRITICAL'].includes(e.level)).slice().reverse(), [entries, level])
  if (demo) return <Alert tone="info">Sample data: the engine log is available when the engine is running.</Alert>
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs value={level} onValueChange={v => setLevel(v as typeof level)}>
          <TabsList><TabsTrigger value="problems">Warnings and errors</TabsTrigger><TabsTrigger value="all">Everything</TabsTrigger></TabsList>
        </Tabs>
        <LoadingButton variant="outline" size="sm" loading={loading} onClick={() => void load()}><RefreshCw />Refresh</LoadingButton>
      </div>
      {error && <Alert tone="danger">{error}</Alert>}
      {entries && shown.length === 0 ? (
        <Empty className="border border-dashed"><EmptyHeader><EmptyTitle>{level === 'problems' ? 'No warnings or errors' : 'The log is empty'}</EmptyTitle><EmptyDescription>{level === 'problems' ? 'Everything the engine did recently went fine.' : 'Nothing has been logged yet.'}</EmptyDescription></EmptyHeader></Empty>
      ) : (
        <ul className="bg-card panel-lift divide-y overflow-hidden rounded-2xl border font-mono text-xs">
          {shown.slice(0, 200).map((e, i) => (
            <li key={e.time + i} className="flex gap-3 px-4 py-2">
              <span className="text-muted-foreground shrink-0">{e.time.slice(5, 16)}</span>
              <span className={cn('w-14 shrink-0 font-medium', LEVEL[e.level] ?? 'text-muted-foreground')}>{e.level}</span>
              <span className="min-w-0 flex-1 break-words whitespace-pre-wrap">{e.text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** The history of actions and the engine log, shown inside Settings. */
export function ActivityPanel({ now, demo }: { now: number; demo: boolean }) {
  const [tab, setTab] = useState<'mine' | 'engine'>('mine')
  return (
    <section className="flex flex-col gap-4" id="activity" aria-label="Activity">
      <div>
        <h2 className="font-semibold">Activity</h2>
        <p className="text-muted-foreground mt-1 text-sm">Every action you took in this app and how it ended, and what the engine behind it logged. Nothing here is sent anywhere.</p>
      </div>
      <Tabs value={tab} onValueChange={v => setTab(v as typeof tab)}>
        <TabsList><TabsTrigger value="mine">My actions</TabsTrigger><TabsTrigger value="engine">Engine log</TabsTrigger></TabsList>
      </Tabs>
      {tab === 'mine' ? <Actions now={now} /> : <EngineLog demo={demo} />}
    </section>
  )
}
