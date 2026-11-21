import { useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { Bell, Cloud, HardDrive, History, Info, ListChecks, Palette, User } from 'lucide-react'
import { setAutomation, type State } from '@/api'
import { ConfirmDialog } from '@/components/feedback'
import { Alert } from '@/components/inline-alert'
import { Masonry } from '@/components/masonry'
import { PageHeader } from '@/components/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from '@/lib/notify'
import { SETTINGS_TABS, type SettingsTab } from '@/lib/router'
import { SlideMarker } from '@/lib/slide'
import { cn } from '@/lib/utils'
import type { Outcome, Running } from '@/useEngine'
import { ActivityPanel } from './activity-page'
import { AboutSection } from './settings/about'
import { AccountSection } from './settings/account'
import { AppearanceSection } from './settings/appearance'
import { AlertsSection, BackgroundSection, TrackingSection } from './settings/basics'
import { ChannelsSection } from './settings/channels'
import { CloudSection, DataSection } from './settings/cloud-data'
import { PhoneShareSection } from './settings/phone-share'
import { useSettings } from './settings/parts'
import { ProfileCard } from './settings/profile'

const ICONS: Record<SettingsTab, typeof User> = {
  profile: User, appearance: Palette, notifications: Bell, tracking: ListChecks, background: Cloud, data: HardDrive, activity: History, about: Info,
}
const BLURB: Record<SettingsTab, string> = {
  profile: 'Who the app signs in as, and the portal account behind it.',
  appearance: 'Theme, colours and animations.',
  notifications: 'How alerts reach you: on this PC, by email and on your phone.',
  tracking: 'What each check reads from the portal.',
  background: 'Automatic checks, the tray, and checks that run in the cloud while your PC is off.',
  data: 'Where files are saved and what the app keeps on this PC.',
  activity: 'A record of every action and how it ended.',
  about: 'Version, updates, licence and links.',
}

type Props = {
  tab: SettingsTab; onTab: (t: SettingsTab) => void; state: State; now: number; demo: boolean
  dark: boolean; onTheme: (dark: boolean) => void; palette: string; onPalette: (p: string) => void; motion: boolean; onMotion: (on: boolean) => void
  onOpenFolder: (k: 'lectures' | 'data') => void; onDataCleared: () => void
  run: (kind: string, begin: () => Promise<{ job: string }>) => Promise<Outcome>; running: Running | null
}

export function SettingsPage(p: Props) {
  const navRef = useRef<HTMLElement>(null)
  // arrow keys move between the sections (Up and Down in the column, Left and Right when it is a row), Home and End jump
  const walkTabs = (e: KeyboardEvent<HTMLElement>) => {
    if (!['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return
    const items = Array.from(e.currentTarget.querySelectorAll<HTMLButtonElement>('button'))
    const at = items.indexOf(document.activeElement as HTMLButtonElement)
    if (at < 0) return
    const fwd = e.key === 'ArrowDown' || e.key === 'ArrowRight'
    const next = e.key === 'Home' ? 0 : e.key === 'End' ? items.length - 1 : fwd ? (at + 1) % items.length : (at - 1 + items.length) % items.length
    e.preventDefault()
    items[next].focus()
  }
  const { view, error, load, save } = useSettings(p.demo)
  const busy = !!p.running
  const [offerAuto, setOfferAuto] = useState(false)
  const turnOnAuto = async () => {
    const r = await p.run('automation', () => setAutomation(true))
    if (r.ok) toast.success(r.message); else toast.error(r.message)
    await load()
  }
  const loading = !view && !p.demo
  const wait = <Skeleton className="h-64 w-full rounded-2xl" />
  const two = (children: ReactNode) => <Masonry minWidth={1536} className="gap-5 [&>div]:gap-5">{children}</Masonry>

  const content: Record<SettingsTab, ReactNode> = {
    profile: view ? (
      <>
        <ProfileCard view={view} state={p.state} now={p.now} />
        <AccountSection key={view.account.enrollment + view.account.institute_id + String(view.account.password_set)} view={view} save={save} run={p.run} busy={busy}
          onSignedIn={() => { if (!view.background.automatic_checks && !view.background.owned_by_installed_app) setOfferAuto(true) }} />
      </>
    ) : loading ? wait : null,
    appearance: <AppearanceSection dark={p.dark} onTheme={p.onTheme} palette={p.palette} onPalette={p.onPalette} motion={p.motion}
      onMotion={on => { p.onMotion(on); if (view) void save({ animations: on }) }} />,
    notifications: view ? two(<><AlertsSection view={view} save={save} demo={p.demo} /><ChannelsSection view={view} save={save} run={p.run} busy={busy} demo={p.demo} reload={load} /></>) : loading ? wait : null,
    tracking: view ? <TrackingSection view={view} save={save} /> : loading ? wait : null,
    background: view ? two(<><BackgroundSection view={view} save={save} run={p.run} busy={busy} demo={p.demo} reload={load} />
      <CloudSection view={view} run={p.run} running={p.running} busy={busy} demo={p.demo} reload={load} />
      <PhoneShareSection view={view} run={p.run} running={p.running} busy={busy} demo={p.demo} reload={load} /></>) : loading ? wait : null,
    data: <DataSection view={view} save={save} paths={p.state.paths} demo={p.demo} onOpenFolder={p.onOpenFolder} onCleared={p.onDataCleared} />,
    activity: <ActivityPanel now={p.now} demo={p.demo} />,
    about: <AboutSection view={view} version={p.state.version} demo={p.demo} run={p.run} busy={busy} />,
  }

  return (
    <div className="flex w-full flex-col gap-5">
      <ConfirmDialog open={offerAuto} onOpenChange={setOfferAuto} title="Turn on automatic checks?"
        description="Signed in. Windows can now check for you every evening and shortly after you sign in, and remind you hourly while something is due, even when the app is closed."
        yes="Yes, turn on" no="Not now" onYes={() => void turnOnAuto()} />
      <PageHeader title="Settings" description={BLURB[p.tab]} />
      {p.demo && <Alert tone="info">Sample data: start the engine to see and change your real settings.</Alert>}
      {error && !p.demo && <Alert tone="danger">{error}</Alert>}

      <div className="grid gap-6 lg:grid-cols-[13.5rem_minmax(0,1fr)]">
        <nav ref={navRef} aria-label="Settings sections" onKeyDown={walkTabs} className="slide-host relative -mx-1 flex gap-1 overflow-x-auto px-1 pb-1 lg:sticky lg:top-4 lg:mx-0 lg:flex-col lg:self-start lg:overflow-visible lg:px-0 lg:pb-0">
          <SlideMarker host={navRef} selector="[aria-current='page']" watch={p.tab} className="bg-muted rounded-lg" />
          {SETTINGS_TABS.map(t => {
            const Icon = ICONS[t.key]
            const active = p.tab === t.key
            return (
              <button key={t.key} type="button" onClick={() => p.onTab(t.key)} aria-current={active ? 'page' : undefined}
                className={cn('relative z-10 flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm whitespace-nowrap transition-colors active:scale-[0.98]', active ? 'font-medium' : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground')}>
                <Icon className={cn('size-4', active && 'text-foreground')} />{t.label}
              </button>
            )
          })}
        </nav>
        <div key={p.tab} className="animate-in fade-in slide-in-from-bottom-1 flex min-w-0 flex-col gap-5 duration-300">{content[p.tab]}</div>
      </div>
    </div>
  )
}
