import { useEffect, useRef, useState } from 'react'
import { Copy, Mail, Smartphone } from 'lucide-react'
import { toast } from '@/lib/notify'
import { pairCancel, pairPoll, pairStart, testEmail, testPush, unpair, type SettingsView } from '@/api'
import { ConfirmDialog } from '@/components/feedback'
import { Alert } from '@/components/inline-alert'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { Outcome } from '@/useEngine'
import { Row, Section, SwitchRow } from './parts'

type Save = (p: Record<string, unknown>) => Promise<boolean>
type Run = (kind: string, begin: () => Promise<{ job: string }>) => Promise<Outcome>

function PairDialog({ open, onClose, onPaired }: { open: boolean; onClose: () => void; onPaired: () => void }) {
  const [pairing, setPairing] = useState<{ url: string; code: string; qr: string } | null>(null)
  const [status, setStatus] = useState('Waiting for the phone to open the link…')
  const [error, setError] = useState('')
  const alive = useRef(false)

  useEffect(() => {
    if (!open) return
    alive.current = true
    setPairing(null); setError(''); setStatus('Waiting for the phone to open the link…')
    void (async () => {
      try {
        setPairing(await pairStart())
        while (alive.current) {
          await new Promise(r => setTimeout(r, 2000))
          if (!alive.current) break
          const r = await pairPoll()
          if (r.status === 'paired') { alive.current = false; toast.success(`Phone paired${r.device ? `: ${r.device}` : ''}.`); onPaired(); onClose(); return }
          setStatus(r.status === 'opened' ? 'The phone opened the page. Tap “Allow notifications and pair” there.' : 'Waiting for the phone to open the link…')
        }
      } catch (e) { setError(e instanceof Error ? e.message : 'Pairing failed.') }
    })()
    return () => { alive.current = false; void pairCancel().catch(() => undefined) }
  }, [open, onClose, onPaired])

  return (
    <Dialog open={open} onOpenChange={o => { if (!o) onClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Pair your phone in three taps</DialogTitle>
          <DialogDescription>Alerts then reach your phone even when this PC is off.</DialogDescription>
        </DialogHeader>
        <ol className="text-muted-foreground flex list-decimal flex-col gap-1.5 pl-5 text-sm">
          <li>Open the ordinary Camera app on your phone.</li>
          <li>Point it at the code below and tap the link that pops up.</li>
          <li>On the page that opens, tap “Allow notifications and pair”.</li>
        </ol>
        {error ? <Alert tone="danger">{error}</Alert> : pairing ? (
          <div className="flex flex-col items-center gap-3">
            <img src={pairing.qr} alt="Pairing code" className="size-56 rounded-xl border bg-white p-2" />
            <div className="text-sm font-medium" role="status">{status}</div>
            <div className="text-muted-foreground num text-xs">Code {pairing.code} · the page shows the same code</div>
            <Button variant="outline" size="sm" onClick={() => void navigator.clipboard.writeText(pairing.url).then(() => toast.info('Link copied. Paste it to your phone and open it there.'))}><Copy />Copy link instead</Button>
            <p className="text-muted-foreground text-center text-xs">iPhone: in Safari tap Share, Add to Home Screen, open it from there, then pair.</p>
          </div>
        ) : <div className="text-muted-foreground py-10 text-center text-sm">Preparing a code…</div>}
      </DialogContent>
    </Dialog>
  )
}

export function ChannelsSection({ view, save, run, busy, demo, reload }: { view: SettingsView; save: Save; run: Run; busy: boolean; demo: boolean; reload: () => Promise<void> }) {
  const c = view.channels
  const [email, setEmail] = useState(c.email_to)
  const [pass, setPass] = useState('')
  const [host, setHost] = useState(c.email_host)
  const [port, setPort] = useState(String(c.email_port))
  const [pairOpen, setPairOpen] = useState(false)
  const [confirmUnpair, setConfirmUnpair] = useState(false)
  useEffect(() => { setEmail(c.email_to); setHost(c.email_host); setPort(String(c.email_port)) }, [c.email_to, c.email_host, c.email_port])
  const emailDirty = email !== c.email_to || pass !== ''

  const saveEmail = async () => {
    const patch: Record<string, unknown> = { email_to: email.trim() }
    if (pass) patch.email_pass = pass
    if (await save(patch)) { setPass(''); toast.success('Email settings saved.') }
  }
  const sendTest = async () => {
    if (emailDirty && !(await save({ email_to: email.trim(), ...(pass ? { email_pass: pass } : {}) }))) return
    setPass('')
    const r = await run('email', testEmail)
    if (r.ok) toast.success(r.message); else toast.error(r.message)
  }
  const sendPushTest = async () => {
    const r = await run('push', testPush)
    if (r.ok) toast.success(r.message); else toast.error(r.message)
  }

  return (
    <Section id="channels" title="Phone, email and calendar" description="Extra places alerts can go. Each is optional.">
      <div className="flex items-center gap-2 pb-1 text-sm font-medium"><Mail className="size-4" />Email</div>
      <SwitchRow label="Send alerts by email" hint="Needs an app password from your email provider (not your normal password)" checked={c.email_enabled} onChange={v => void save({ email_enabled: v })} />
      <div className="grid gap-4 py-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5"><Label htmlFor="email-to">Your address</Label><Input id="email-to" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@gmail.com" autoComplete="off" /></div>
        <div className="flex flex-col gap-1.5"><Label htmlFor="email-pass">App password</Label>
          <Input id="email-pass" type="password" value={pass} onChange={e => setPass(e.target.value)} autoComplete="new-password" placeholder={c.email_pass_set ? 'Saved. Type a new one to change it' : 'The 16-letter app password'} /></div>
      </div>
      <Collapsible>
        <CollapsibleTrigger className="text-muted-foreground hover:text-foreground mb-2 text-xs underline-offset-2 hover:underline">Advanced: mail server</CollapsibleTrigger>
        <CollapsibleContent>
          <div className="grid gap-4 pb-3 sm:grid-cols-[1fr_8rem]">
            <div className="flex flex-col gap-1.5"><Label htmlFor="smtp-host">Server (empty picks it from your address)</Label><Input id="smtp-host" value={host} onChange={e => setHost(e.target.value)} placeholder="smtp.gmail.com" /></div>
            <div className="flex flex-col gap-1.5"><Label htmlFor="smtp-port">Port</Label><Input id="smtp-port" inputMode="numeric" value={port} onChange={e => setPort(e.target.value.replace(/\D/g, ''))} /></div>
            <div className="sm:col-span-2"><Button size="sm" variant="outline" onClick={() => void save({ email_host: host.trim(), email_port: Number(port) || 587 }).then(ok => ok && toast.success('Server saved.'))}>Save server</Button></div>
          </div>
        </CollapsibleContent>
      </Collapsible>
      <div className="flex flex-wrap gap-2 pb-4">
        <Button size="sm" onClick={() => void saveEmail()} disabled={!emailDirty}>Save email</Button>
        <Button size="sm" variant="outline" onClick={() => void sendTest()} disabled={busy || demo}>Send a test email</Button>
      </div>

      <div className="flex items-center gap-2 border-t pt-4 pb-1 text-sm font-medium"><Smartphone className="size-4" />Phone</div>
      <Row label={c.push_paired ? `Paired: ${c.push_device || 'your phone'}` : 'No phone paired yet'} hint="Alerts arrive as phone notifications, even when this PC is off">
        <Button size="sm" variant="outline" onClick={() => setPairOpen(true)} disabled={demo}>{c.push_paired ? 'Pair another' : 'Pair a phone'}</Button>
        {c.push_paired && <Button size="sm" variant="outline" onClick={() => void sendPushTest()} disabled={busy}>Test</Button>}
        {c.push_paired && <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setConfirmUnpair(true)}>Unpair</Button>}
      </Row>
      <SwitchRow label="Send alerts to the phone" checked={c.push_enabled} onChange={v => void save({ push_enabled: v })} disabled={!c.push_paired} />

      <div className="border-t pt-4 text-sm font-medium">Calendar</div>
      <SwitchRow label="Keep a calendar file up to date" hint="Deadlines and exams in a file your calendar app can subscribe to" checked={c.calendar_enabled} onChange={v => void save({ calendar_enabled: v })} />
      <SwitchRow label="Email calendar invites" hint="Sends each deadline as an invite so it lands in your calendar" checked={c.calendar_invites} onChange={v => void save({ calendar_invites: v })} disabled={!c.email_enabled} />

      <ConfirmDialog open={confirmUnpair} onOpenChange={setConfirmUnpair} danger title="Unpair this phone?" description="Alerts will stop arriving on it. You can pair it again at any time."
        yes="Yes, unpair" no="No, keep it paired" onYes={() => void unpair().then(() => { toast.success('Phone unpaired'); return reload() })} />
      <PairDialog open={pairOpen} onClose={() => setPairOpen(false)} onPaired={() => void reload()} />
    </Section>
  )
}
