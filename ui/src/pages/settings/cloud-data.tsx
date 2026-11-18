import { useCallback, useEffect, useRef, useState } from 'react'
import { ExternalLink, FolderOpen, Trash2 } from 'lucide-react'
import { toast } from '@/lib/notify'
import { cloudDisable, cloudPoll, cloudRun, cloudSetup, cloudStart, clearData, getCloudStatus, type CloudStatus, type SettingsView } from '@/api'
import { Alert } from '@/components/inline-alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import type { Outcome, Running } from '@/useEngine'
import { Row, Section } from './parts'

type Run = (kind: string, begin: () => Promise<{ job: string }>) => Promise<Outcome>
type Stage = 'consent' | 'code' | 'setup' | 'done' | 'error'

function CloudDialog({ open, onClose, run, running, onDone }: { open: boolean; onClose: () => void; run: Run; running: Running | null; onDone: () => void }) {
  const [stage, setStage] = useState<Stage>('consent')
  const [code, setCode] = useState<{ user_code: string; verification_uri: string } | null>(null)
  const [message, setMessage] = useState('')
  const alive = useRef(false)
  useEffect(() => { if (open) { setStage('consent'); setCode(null); setMessage('') } else alive.current = false }, [open])

  const begin = async () => {
    setStage('code')
    alive.current = true
    try {
      const flow = await cloudStart()
      setCode(flow)
      let wait = flow.interval
      while (alive.current) {
        await new Promise(r => setTimeout(r, wait * 1000))
        if (!alive.current) return
        const r = await cloudPoll()
        if (r.status === 'ready') break
        wait = r.interval ?? wait
      }
      if (!alive.current) return
      setStage('setup')
      const res = await run('cloud', cloudSetup)
      setMessage(res.message)
      setStage(res.ok ? 'done' : 'error')
      if (res.ok) onDone()
    } catch (e) { setMessage(e instanceof Error ? e.message : 'GitHub sign-in failed.'); setStage('error') }
  }

  return (
    <Dialog open={open} onOpenChange={o => { if (!o && stage !== 'setup') { alive.current = false; onClose() } }}>
      <DialogContent className="sm:max-w-lg">
        {stage === 'consent' && (
          <>
            <DialogHeader><DialogTitle>Before you continue</DialogTitle><DialogDescription>GitHub will run the check for you. To set that up, this app will do the following in your GitHub account, with your permission:</DialogDescription></DialogHeader>
            <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm">
              <li>Create a private repository named assignment-monitor-cloud.</li>
              <li>Store your enrollment number, portal password and the phone and email keys there as GitHub Actions secrets: encrypted by GitHub, readable only by the check while it runs, never shown in logs.</li>
              <li>Copy what this PC has seen so far (assignments, attendance, exams, announcements, timetable) into it and keep that cache updated there.</li>
            </ul>
            <p className="text-sm">GitHub's machines then sign in to the portal each morning and evening (07:43 and 18:37). Until now your password never left this PC; with cloud checks it also lives in GitHub's encrypted secrets. Turning cloud checks off removes the secrets and the workflow.</p>
            <p className="text-muted-foreground text-xs">You need a free GitHub account. GitHub will ask you to grant the “repo” and “workflow” permissions; they cover every repository in your account, and the app touches only the one above. You can revoke the grant any time at github.com/settings/applications.</p>
            <DialogFooter><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={() => void begin()}>Continue with GitHub</Button></DialogFooter>
          </>
        )}
        {stage === 'code' && (
          <>
            <DialogHeader><DialogTitle>Sign in on GitHub</DialogTitle><DialogDescription>Open GitHub, enter this code and approve the request. This page continues by itself.</DialogDescription></DialogHeader>
            <div className="flex flex-col items-center gap-4 py-4">
              {code ? (
                <>
                  <div className="num rounded-xl border px-6 py-4 text-4xl tracking-widest" aria-label="Your code">{code.user_code}</div>
                  <Button asChild variant="outline"><a href={code.verification_uri} target="_blank" rel="noreferrer"><ExternalLink />Open {code.verification_uri.replace('https://', '')}</a></Button>
                  <p className="text-muted-foreground text-sm" role="status">Waiting for you to approve it…</p>
                </>
              ) : <p className="text-muted-foreground text-sm">Asking GitHub for a code…</p>}
            </div>
            <DialogFooter><Button variant="ghost" onClick={() => { alive.current = false; onClose() }}>Cancel</Button></DialogFooter>
          </>
        )}
        {stage === 'setup' && (
          <>
            <DialogHeader><DialogTitle>Setting things up</DialogTitle><DialogDescription>Keep the app open until this finishes.</DialogDescription></DialogHeader>
            <div className="flex flex-col gap-3 py-4" role="status"><Progress value={55} /><p className="text-muted-foreground text-sm">{running?.step ?? 'Working…'}</p></div>
          </>
        )}
        {stage === 'done' && (
          <>
            <DialogHeader><DialogTitle>Cloud checks are on</DialogTitle><DialogDescription>{message}</DialogDescription></DialogHeader>
            <p className="text-sm">The first cloud check has started. Results arrive on GitHub and on your phone in a few minutes.</p>
            <DialogFooter><Button onClick={onClose}>Done</Button></DialogFooter>
          </>
        )}
        {stage === 'error' && (
          <>
            <DialogHeader><DialogTitle>That did not work</DialogTitle></DialogHeader>
            <Alert tone="danger">{message}</Alert>
            <DialogFooter><Button variant="ghost" onClick={onClose}>Close</Button><Button onClick={() => setStage('consent')}>Try again</Button></DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export function CloudSection({ view, run, running, busy, demo, reload }: { view: SettingsView; run: Run; running: Running | null; busy: boolean; demo: boolean; reload: () => Promise<void> }) {
  const [status, setStatus] = useState<CloudStatus | null>(null)
  const [open, setOpen] = useState(false)
  const [confirmOff, setConfirmOff] = useState(false)
  const cl = view.cloud
  const refresh = useCallback(() => { if (cl.enabled) void getCloudStatus().then(setStatus).catch(() => setStatus({ enabled: true, error: 'GitHub could not be reached.' })); else setStatus({ enabled: false }) }, [cl.enabled])
  useEffect(() => { if (!demo) refresh() }, [refresh, demo])

  const last = status?.last
  const lastText = last ? `Last check ${new Date(last.when).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', hour12: true })}: ${last.status !== 'completed' ? 'running now' : last.conclusion === 'success' ? 'passed' : last.conclusion === 'failure' ? 'failed' : (last.conclusion ?? '')}.` : 'No check has run yet.'
  const turnOff = async () => {
    setConfirmOff(false)
    const r = await run('cloud', cloudDisable)
    if (r.ok) toast.success(r.message, r.url ? { action: { label: 'Open the repository', onClick: () => window.open(r.url, '_blank') } } : undefined); else toast.error(r.message)
    await reload()
  }

  return (
    <Section id="cloud" title="Cloud checks (PC off)"
      description="GitHub runs the same check each morning and evening (07:43 and 18:37) from a private repository in your own GitHub account, so phone and email alerts arrive even when this PC is off. Free. While it is on, this PC keeps its desktop and voice alerts and leaves phone and email to the cloud, so nothing arrives twice.">
      {!cl.available ? <Alert tone="info">Not available in this build.</Alert> : (
        <Row label={cl.enabled ? `On, as ${cl.login} on GitHub` : 'Off. Alerts come from this PC only.'} hint={cl.enabled ? (status?.error ?? lastText) : undefined}>
          {cl.enabled && <Button size="sm" variant="outline" disabled={busy || demo} onClick={() => void cloudRun().then(() => { toast.success('Cloud check started. Results in a few minutes.'); setTimeout(refresh, 15000) }).catch(e => toast.error(String(e.message)))}>Run now</Button>}
          {cl.enabled && <Button size="sm" variant="outline" asChild><a href={`https://github.com/${cl.repo}/actions`} target="_blank" rel="noreferrer"><ExternalLink />Open on GitHub</a></Button>}
          <Button size="sm" variant={cl.enabled ? 'outline' : 'default'} disabled={busy || demo} onClick={() => (cl.enabled ? setConfirmOff(true) : setOpen(true))}>{cl.enabled ? 'Turn off' : 'Set up'}</Button>
        </Row>
      )}
      <CloudDialog open={open} onClose={() => setOpen(false)} run={run} running={running} onDone={() => void reload()} />
      <Dialog open={confirmOff} onOpenChange={setConfirmOff}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle>Turn off cloud checks?</DialogTitle><DialogDescription>The secrets and the workflow are removed from your GitHub repository and this PC forgets the GitHub sign-in. The empty repository stays; you can delete it on GitHub afterwards.</DialogDescription></DialogHeader>
          <DialogFooter><Button variant="ghost" onClick={() => setConfirmOff(false)}>Keep it on</Button><Button variant="destructive" onClick={() => void turnOff()}>Turn off</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </Section>
  )
}

export function DataSection({ view, save, paths, demo, onOpenFolder, onCleared }: {
  view: SettingsView | null; save: (p: Record<string, unknown>) => Promise<boolean>
  paths: { lectures: string; data: string }; demo: boolean; onOpenFolder: (k: 'lectures' | 'data') => void; onCleared: () => void
}) {
  const [confirm, setConfirm] = useState(false)
  const current = view?.background.lectures_dir ?? ''
  const fallback = view?.background.downloads_default ?? paths.lectures
  const [folder, setFolder] = useState(current)
  useEffect(() => { setFolder(current) }, [current])
  const dirty = folder.trim() !== current
  return (
    <>
      <Section id="downloads" title="Downloads folder" description="Where lecture notes and assignment files are saved, one folder per course. Files already there are skipped.">
        <Row label="Folder" hint={current ? 'A folder you chose' : <>Using the default: <span className="num">{fallback}</span></>}>
          <Button variant="outline" size="sm" disabled={demo} onClick={() => onOpenFolder('lectures')}><FolderOpen />Open</Button>
        </Row>
        <div className="flex flex-wrap items-center gap-2 py-3">
          <Input className="min-w-0 flex-1 basis-72" value={folder} onChange={e => setFolder(e.target.value)} placeholder={fallback} aria-label="Downloads folder path" disabled={demo || !view} />
          <Button size="sm" disabled={demo || !view || !dirty} onClick={() => void save({ lectures_dir: folder.trim() }).then(ok => ok && toast.success('Downloads folder saved'))}>Save folder</Button>
          <Button size="sm" variant="ghost" disabled={demo || !view || !current} onClick={() => void save({ lectures_dir: '' }).then(ok => ok && toast.success('Using the default folder'))}>Use the default</Button>
        </div>
        <p className="text-muted-foreground text-xs">Type or paste a full folder path, for example D:\University\Lectures. The folder is created the first time something is saved there.</p>
      </Section>
      <Section id="data" title="Your data" description="Everything the app keeps is on this PC. Nothing leaves it unless you turn on cloud checks.">
        <Row label="App data and activity log" hint={<span className="num">{paths.data}</span>}><Button variant="outline" size="sm" disabled={demo} onClick={() => onOpenFolder('data')}><FolderOpen />Open</Button></Row>
        <Row label="Clear saved data" hint="Deletes the saved assignments, attendance, exams, announcements and lecture list. The next check rebuilds them. Your account and settings stay.">
          <Button variant="outline" size="sm" className="text-destructive" disabled={demo} onClick={() => setConfirm(true)}><Trash2 />Clear</Button>
        </Row>
        <Dialog open={confirm} onOpenChange={setConfirm}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader><DialogTitle>Clear the saved data?</DialogTitle><DialogDescription>The saved assignments, attendance, exam plan, announcements and lecture list are deleted. The next check rebuilds them.</DialogDescription></DialogHeader>
            <DialogFooter><Button variant="ghost" onClick={() => setConfirm(false)}>No, keep it</Button>
              <Button variant="destructive" onClick={() => void clearData().then(() => { setConfirm(false); toast.success('Saved data cleared'); onCleared() })}>Yes, clear it</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </Section>
    </>
  )
}
