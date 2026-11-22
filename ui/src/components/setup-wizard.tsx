import { useState, type ReactNode } from 'react'
import { Bell, Check, CircleCheckBig, FolderOpen, Hand, Palette, ShieldCheck, UserRound, Zap } from 'lucide-react'
import { openFolder, setAutomation, setStartup, testAlert } from '@/api'
import { PALETTES } from '@/components/app-sidebar'
import { ConfirmDialog, LoadingButton } from '@/components/feedback'
import { Alert } from '@/components/inline-alert'
import { Button } from '@/components/ui/button'
import { toast } from '@/lib/notify'
import { cn } from '@/lib/utils'
import type { Outcome } from '@/useEngine'
import { AccountSection } from '@/pages/settings/account'
import { SwitchRow, useSettings } from '@/pages/settings/parts'

type Run = (kind: string, begin: () => Promise<{ job: string }>) => Promise<Outcome>
const LEADS = [24, 12, 6, 3, 1]

type Props = {
  run: Run; busy: boolean; dark: boolean; onTheme: (dark: boolean) => void; palette: string; onPalette: (p: string) => void
  motion: boolean; onMotion: (on: boolean) => void
  /** The student is done (finished or skipped). `checkNow` asks the app to run the first check straight away. */
  onClose: (checkNow: boolean) => void
}

/**
 * The first-run walkthrough: one thing per step, each explained, every optional step skippable, and the whole thing
 * skippable. Nothing here is required to use the app; everything can be changed later in Settings.
 */
export function SetupWizard(p: Props) {
  const { view, load, save } = useSettings(false)
  const [i, setI] = useState(0)
  const [done, setDone] = useState<Record<string, string>>({})        // what was set up, for the last page
  const [confirmSkip, setConfirmSkip] = useState(false)
  const [autoBusy, setAutoBusy] = useState(false)
  const mark = (k: string, text: string) => setDone(d => ({ ...d, [k]: text }))

  const finish = async (checkNow: boolean) => { await save({ setup_done: true }); p.onClose(checkNow) }
  const al = view?.alerts
  const leads = view?.tracking.remind_leads ?? []

  const turnOnAuto = async () => {
    setAutoBusy(true)
    const r = await p.run('automation', () => setAutomation(true))
    setAutoBusy(false)
    if (r.ok) { mark('auto', 'Automatic checks are on'); toast.success(r.message) } else toast.error(r.message)
    await load()
  }

  const steps: { key: string; title: string; icon: typeof Hand; skippable: boolean; body: ReactNode }[] = [
    { key: 'welcome', title: 'Welcome', icon: Hand, skippable: false, body: (
      <>
        <p>Assignment Monitor watches your Bahria portal so you do not have to: deadlines (including ones a teacher extends), attendance, exams, announcements, lecture notes, your timetable and your results.</p>
        <ul className="text-muted-foreground mt-4 grid gap-2 text-sm">
          <li className="flex gap-2"><ShieldCheck className="text-success mt-0.5 size-4 shrink-0" />Your password stays on this PC, encrypted for your Windows account.</li>
          <li className="flex gap-2"><ShieldCheck className="text-success mt-0.5 size-4 shrink-0" />It only reads the portal. It writes only when you press Upload, Replace or Delete and confirm.</li>
          <li className="flex gap-2"><ShieldCheck className="text-success mt-0.5 size-4 shrink-0" />Every step after this one is optional, and everything can be changed later in Settings.</li>
        </ul>
      </>) },
    { key: 'account', title: 'Sign in', icon: UserRound, skippable: true, body: view ? (
      <>
        <p className="text-muted-foreground mb-4 text-sm">Use the same enrollment number and password you use on the student portal. The app checks them with the portal before saving.</p>
        <AccountSection view={view} save={save} run={p.run} busy={p.busy} onSignedIn={() => { mark('account', `Signed in as ${view.account.enrollment || 'your account'}`); void load(); setI(x => x + 1) }} />
      </>) : <p className="text-muted-foreground text-sm">Loading…</p> },
    { key: 'look', title: 'Make it yours', icon: Palette, skippable: true, body: (
      <>
        <p className="text-muted-foreground mb-4 text-sm">Pick a colour and light or dark. Both can be changed any time from the sidebar menu or Settings.</p>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Palette">
          {PALETTES.map(x => <Button key={x.key} variant={p.palette === x.key ? 'default' : 'outline'} aria-pressed={p.palette === x.key} onClick={() => { p.onPalette(x.key); mark('look', `${x.label}, ${p.dark ? 'dark' : 'light'}`) }}>{x.label}</Button>)}
        </div>
        <div className="mt-3 flex gap-2" role="group" aria-label="Theme">
          <Button variant={!p.dark ? 'default' : 'outline'} aria-pressed={!p.dark} onClick={() => p.onTheme(false)}>Light</Button>
          <Button variant={p.dark ? 'default' : 'outline'} aria-pressed={p.dark} onClick={() => p.onTheme(true)}>Dark</Button>
        </div>
        <div className="mt-2"><SwitchRow label="Animations" name="Animations" hint="Page transitions and fades. Turn off for a still screen." checked={p.motion} onChange={on => { p.onMotion(on); void save({ animations: on }) }} /></div>
      </>) },
    { key: 'alerts', title: 'Reminders', icon: Bell, skippable: true, body: al ? (
      <>
        <p className="text-muted-foreground mb-2 text-sm">How the app gets your attention. Phone and email alerts can be added later in Settings.</p>
        <SwitchRow label="Windows notifications" hint="A pop-up from the notification area" checked={al.toast} onChange={v => { void save({ toast: v }); mark('alerts', 'Reminders set') }} />
        <SwitchRow label="Spoken reminders" hint="Reads the reminder aloud" checked={al.voice} onChange={v => void save({ voice: v })} />
        <div className="py-3">
          <div className="text-sm font-medium">Remind me before a deadline</div>
          <div className="mt-2 flex flex-wrap gap-1.5" role="group" aria-label="Reminder lead times">
            {LEADS.map(h => {
              const on = leads.includes(h)
              const next = (on ? leads.filter(x => x !== h) : [...leads, h]).sort((a, b) => b - a)
              return <Button key={h} size="sm" variant={on ? 'default' : 'outline'} aria-pressed={on} onClick={() => { void save({ remind_leads: next.length ? next.join(',') : 'off' }); mark('alerts', 'Reminders set') }}>{h === 24 ? '1 day' : `${h} h`} before</Button>
            })}
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => void testAlert().then(() => toast.info('Test alert sent.')).catch(() => toast.error('Could not send the test alert'))}><Bell />Send a test alert</Button>
      </>) : <p className="text-muted-foreground text-sm">Loading…</p> },
    { key: 'background', title: 'Run by itself', icon: Zap, skippable: true, body: view ? (
      <>
        <p className="text-muted-foreground mb-4 text-sm">Windows can check for you every evening and shortly after you sign in, and remind you hourly while something is due, even when the app is closed.</p>
        {view.background.automatic_checks
          ? <Alert tone="success">Automatic checks are on.</Alert>
          : view.background.owned_by_installed_app
            ? <Alert tone="info">Automatic checks belong to the installed app and are managed there.</Alert>
            : <LoadingButton loading={autoBusy} onClick={() => void turnOnAuto()}>Turn on automatic checks</LoadingButton>}
        <div className="mt-3">
          <SwitchRow label="Start with Windows" hint="Opens minimised to the tray when you sign in" checked={view.background.starts_with_windows}
            onChange={v => void setStartup(v).then(() => { mark('start', v ? 'Starts with Windows' : ''); return load() }).catch(() => toast.error('Could not change that'))} />
          <SwitchRow label="Keep running in the tray when closed" hint="Closing the window leaves the app running" checked={view.background.close_to_tray} onChange={v => void save({ close_to_tray: v })} />
        </div>
      </>) : <p className="text-muted-foreground text-sm">Loading…</p> },
    { key: 'files', title: 'Where files go', icon: FolderOpen, skippable: true, body: (
      <>
        <p className="text-muted-foreground text-sm">Lecture notes and assignment files you download are saved here, in course and week folders:</p>
        <p className="num bg-muted/60 mt-3 rounded-lg border p-3 text-sm break-all select-text">{view?.background.lectures_dir || view?.background.downloads_default || '…'}</p>
        <div className="mt-3 flex flex-wrap gap-2"><Button variant="outline" size="sm" onClick={() => void openFolder('lectures').catch(() => toast.error('Could not open the folder'))}><FolderOpen />Open it</Button></div>
        <p className="text-muted-foreground mt-3 text-xs">To use another folder, change it in Settings, Data and files.</p>
      </>) },
    { key: 'finish', title: 'All set', icon: CircleCheckBig, skippable: false, body: (
      <>
        <p>That is everything. Here is what you set up:</p>
        <ul className="mt-3 grid gap-1.5 text-sm">
          {['account', 'look', 'alerts', 'auto', 'start'].map(k => (
            <li key={k} className="flex items-center gap-2">{done[k] ? <Check className="text-success size-4" /> : <span className="bg-muted-foreground/40 ml-1.5 mr-1 size-1.5 rounded-full" />}<span className={done[k] ? '' : 'text-muted-foreground'}>{done[k] || ({ account: 'Sign-in: skipped for now', look: 'Look: left as it is', alerts: 'Reminders: left as they are', auto: 'Automatic checks: not turned on', start: 'Start with Windows: not turned on' } as Record<string, string>)[k]}</span></li>
          ))}
        </ul>
        {!view?.account.password_set && <div className="mt-4"><Alert tone="warning">You have not signed in yet. Open Settings, Profile whenever you are ready; nothing can be checked until then.</Alert></div>}
      </>) },
  ]

  const step = steps[i]
  const last = i === steps.length - 1
  return (
    <div className="bg-background fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-4" role="dialog" aria-modal="true" aria-label="Setup">
      <div className="bg-card grid w-full max-w-4xl overflow-hidden rounded-3xl border shadow-xl md:grid-cols-[15rem_minmax(0,1fr)]">
        <nav aria-label="Setup steps" className="bg-sidebar hidden border-r p-5 md:block">
          <div className="mb-5 flex items-center gap-2 font-semibold"><div className="bg-primary text-primary-foreground grid size-8 place-items-center rounded-lg"><CircleCheckBig className="size-4" /></div>Setup</div>
          <ol className="grid gap-1">
            {steps.map((s, n) => (
              <li key={s.key}>
                <button type="button" onClick={() => setI(n)} aria-current={n === i ? 'step' : undefined}
                  className={cn('flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-sm transition-colors', n === i ? 'bg-background font-medium shadow-sm' : 'text-muted-foreground hover:text-foreground')}>
                  <span className={cn('num grid size-5 shrink-0 place-items-center rounded-full border text-xs', n < i && 'bg-primary text-primary-foreground border-transparent')}>{n < i ? <Check className="size-3" /> : n + 1}</span>
                  {s.title}
                </button>
              </li>
            ))}
          </ol>
        </nav>
        <div className="flex min-h-[34rem] flex-col p-6 md:p-8">
          <div className="mb-1 flex items-center justify-between gap-3">
            <p className="text-muted-foreground text-xs tracking-wide uppercase">Step {i + 1} of {steps.length}</p>
            {!last && <Button variant="ghost" size="sm" onClick={() => setConfirmSkip(true)}>Skip setup</Button>}
          </div>
          <h1 className="flex items-center gap-2.5 text-2xl font-semibold tracking-tight"><step.icon className="text-primary size-6" aria-hidden />{step.title}</h1>
          <div className="mt-4 flex-1 text-sm leading-relaxed">{step.body}</div>
          <div className="mt-6 flex flex-wrap items-center justify-between gap-2 border-t pt-4">
            <Button variant="ghost" onClick={() => setI(x => Math.max(0, x - 1))} disabled={i === 0}>Back</Button>
            <div className="flex flex-wrap gap-2">
              {last ? (
                <>
                  <Button variant="outline" onClick={() => void finish(false)}>Open the app</Button>
                  <Button onClick={() => void finish(true)} disabled={!view?.account.password_set}>Run the first check</Button>
                </>
              ) : (
                <>
                  {step.skippable && <Button variant="outline" onClick={() => setI(x => x + 1)}>Skip this step</Button>}
                  <Button onClick={() => setI(x => x + 1)}>{i === 0 ? 'Get started' : 'Next'}</Button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
      <ConfirmDialog open={confirmSkip} onOpenChange={setConfirmSkip} title="Skip the setup?" description="Nothing is required. You can sign in and change everything later in Settings."
        yes="Yes, skip it" no="No, continue" onYes={() => void finish(false)} />
    </div>
  )
}
