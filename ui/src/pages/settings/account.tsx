import { useState } from 'react'
import { CircleCheck, ShieldCheck } from 'lucide-react'
import { toast } from '@/lib/notify'
import { verifyAccount, type SettingsView } from '@/api'
import { Alert } from '@/components/inline-alert'
import { LoadingButton } from '@/components/feedback'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { Outcome } from '@/useEngine'
import { Section } from './parts'

export function AccountSection({ view, save, run, busy }: {
  view: SettingsView; save: (p: Record<string, unknown>) => Promise<boolean>
  run: (kind: string, begin: () => Promise<{ job: string }>) => Promise<Outcome>; busy: boolean
}) {
  const a = view.account
  const [enrollment, setEnrollment] = useState(a.enrollment)
  const [campus, setCampus] = useState(a.institute_id)
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null)
  const dirty = enrollment !== a.enrollment || campus !== a.institute_id || password !== ''

  const submit = async () => {
    if (!enrollment.trim()) return setStatus({ ok: false, text: 'Enter your enrollment number.' })
    if (!password && !a.password_set) return setStatus({ ok: false, text: 'Enter your password.' })
    setStatus({ ok: true, text: 'Saving…' })
    const patch: Record<string, unknown> = { enrollment: enrollment.trim(), institute_id: campus }
    if (password) patch.password = password
    if (!(await save(patch))) return setStatus({ ok: false, text: 'Not saved. Check the details.' })
    setPassword('')
    setStatus({ ok: true, text: 'Saved. Checking the sign-in with the portal…' })
    const r = await run('verify', verifyAccount)
    setStatus({ ok: r.ok, text: r.ok ? 'Signed in successfully.' : r.message })
    if (r.ok) toast.success('Sign-in verified.'); else toast.error(r.message)
  }

  return (
    <Section id="account" title="Portal account" description="The account the app signs in with. Changing these checks the sign-in when you save.">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="enrollment">Enrollment number</Label>
          <Input id="enrollment" value={enrollment} onChange={e => setEnrollment(e.target.value)} placeholder="01-123456-789" autoComplete="off" />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="campus">Campus</Label>
          <Select value={campus} onValueChange={setCampus}>
            <SelectTrigger id="campus" className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>{view.campuses.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="new-password"
            placeholder={a.password_set ? 'Saved. Type a new one only to change it' : 'Your portal password'} />
          <p className="text-muted-foreground flex items-center gap-1.5 text-xs"><ShieldCheck className="size-3.5" />Stored encrypted for this Windows user only. It is never shown again.</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <LoadingButton onClick={() => void submit()} loading={busy} disabled={!dirty && a.password_set}>Save and verify</LoadingButton>
        {!dirty && a.password_set && !status && <span className="text-muted-foreground flex items-center gap-1.5 text-xs"><CircleCheck className="text-success size-4" />Signed in as {a.enrollment}</span>}
        {status && <span className={status.ok ? 'text-muted-foreground text-sm' : 'text-destructive text-sm'} role="status">{status.text}</span>}
      </div>
      {!a.password_set && <div className="mt-4"><Alert tone="warning">No account is set up yet. Nothing can be checked until you save one.</Alert></div>}
    </Section>
  )
}
