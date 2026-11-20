import { useEffect, useRef, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { toast } from '@/lib/notify'
import { phoneDisable, phoneEnable, phonePoll, phonePush, phoneStart, type SettingsView } from '@/api'
import { Alert } from '@/components/inline-alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { phoneShareLine } from '@/lib/phone-share'
import type { Outcome, Running } from '@/useEngine'
import { Row, Section } from './parts'

type Run = (kind: string, begin: () => Promise<{ job: string }>) => Promise<Outcome>
type Stage = 'consent' | 'code' | 'setup' | 'done' | 'error'

function ShareDialog({ open, onClose, run, running, onDone }: { open: boolean; onClose: () => void; run: Run; running: Running | null; onDone: () => void }) {
  const [stage, setStage] = useState<Stage>('consent')
  const [code, setCode] = useState<{ user_code: string; verification_uri: string } | null>(null)
  const [message, setMessage] = useState('')
  const alive = useRef(false)
  useEffect(() => { if (open) { setStage('consent'); setCode(null); setMessage('') } else alive.current = false }, [open])

  const begin = async () => {
    setStage('code')
    alive.current = true
    try {
      const flow = await phoneStart()
      setCode(flow)
      let wait = flow.interval
      while (alive.current) {
        await new Promise(r => setTimeout(r, wait * 1000))
        if (!alive.current) return
        const r = await phonePoll()
        if (r.status === 'ready') break
        wait = r.interval ?? wait
      }
      if (!alive.current) return
      setStage('setup')
      const res = await run('phone', phoneEnable)
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
            <DialogHeader><DialogTitle>Share with my phone</DialogTitle><DialogDescription>The phone app reads a small summary file from a private repository in your own GitHub account. To set that up, this app will, with your permission:</DialogDescription></DialogHeader>
            <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm">
              <li>Create (or reuse) a private repository named assignment-monitor-cloud.</li>
              <li>After each check, write one file there, <span className="num">state/summary.json</span>: your name, courses, deadlines, attendance, exams, timetable, results and announcement text.</li>
            </ul>
            <p className="text-sm">Your portal password is never sent anywhere: it stays on this PC. Nothing else is put in the repository.</p>
            <p className="text-muted-foreground text-xs">You need a free GitHub account. GitHub will ask you to grant the “repo” permission; it covers every repository in your account, and the app touches only the one above. You can revoke it any time at github.com/settings/applications.</p>
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
            <DialogHeader><DialogTitle>Your phone can read it</DialogTitle><DialogDescription>{message}</DialogDescription></DialogHeader>
            <p className="text-sm">Sign in to the phone app with the same GitHub account. The summary is sent again after each check that finds something new.</p>
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

export function PhoneShareSection({ view, run, running, busy, demo, reload }: { view: SettingsView; run: Run; running: Running | null; busy: boolean; demo: boolean; reload: () => Promise<void> }) {
  const [open, setOpen] = useState(false)
  const [confirmOff, setConfirmOff] = useState(false)
  const [sending, setSending] = useState(false)
  const ps = view.phone_share
  if (!ps) return null
  const line = phoneShareLine(ps, Date.now())

  const sendNow = async () => {
    setSending(true)
    try {
      const r = await phonePush()
      toast.success(r.pushed ? 'Sent to your phone’s repository.' : r.message)
    } catch (e) { toast.error('Could not send it', { description: e instanceof Error ? e.message : undefined }) }
    setSending(false)
    await reload()
  }
  const turnOff = async () => {
    setConfirmOff(false)
    try { await phoneDisable(); toast.success('Sharing with your phone is off. The repository and the file in it stay.') } catch (e) { toast.error(e instanceof Error ? e.message : 'Could not turn it off') }
    await reload()
  }

  return (
    <Section id="phone-share" title="Share with my phone"
      description="The phone app reads a small summary file (your deadlines, attendance, exams, timetable and results) from a private repository in your own GitHub account. Free, no server of ours, and your portal password never goes with it. If you use Cloud checks, those already share it.">
      {!ps.available ? <Alert tone="info">Not available in this build.</Alert> : (
        <Row label={line.label} hint={line.hint}>
          {ps.enabled && !ps.covered_by_cloud && <Button size="sm" variant="outline" disabled={busy || demo || sending} aria-busy={sending || undefined} onClick={() => void sendNow()}>{sending ? 'Sending…' : 'Share now'}</Button>}
          {ps.enabled && <Button size="sm" variant="outline" asChild><a href={`https://github.com/${ps.repo}`} target="_blank" rel="noreferrer"><ExternalLink />Open on GitHub</a></Button>}
          <Button size="sm" variant={ps.enabled ? 'outline' : 'default'} disabled={busy || demo} onClick={() => (ps.enabled ? setConfirmOff(true) : setOpen(true))}>{ps.enabled ? 'Turn off' : 'Set up'}</Button>
        </Row>
      )}
      <ShareDialog open={open} onClose={() => setOpen(false)} run={run} running={running} onDone={() => void reload()} />
      <Dialog open={confirmOff} onOpenChange={setConfirmOff}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle>Stop sharing with your phone?</DialogTitle><DialogDescription>This PC forgets the GitHub sign-in and stops sending the summary. The repository and the file already in it stay on GitHub; the phone app keeps showing the last copy until you delete the repository.</DialogDescription></DialogHeader>
          <DialogFooter><Button variant="ghost" onClick={() => setConfirmOff(false)}>Keep sharing</Button><Button variant="destructive" onClick={() => void turnOff()}>Turn off</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </Section>
  )
}
