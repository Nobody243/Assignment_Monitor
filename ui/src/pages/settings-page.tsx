import { Moon, Sun } from 'lucide-react'
import { Alert } from '@/components/inline-alert'
import { PageHeader } from '@/components/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import type { Outcome, Running } from '@/useEngine'
import { AccountSection } from './settings/account'
import { AlertsSection, BackgroundSection, TrackingSection } from './settings/basics'
import { ChannelsSection } from './settings/channels'
import { CloudSection, DataSection } from './settings/cloud-data'
import { Row, Section, useSettings } from './settings/parts'

export const PALETTE_INFO = [
  { key: 'royal', label: 'Royal', note: 'Royal blue with an aqua action colour', swatch: ['oklch(0.5 0.19 262)', 'oklch(0.85 0.13 205)'] },
  { key: 'ink', label: 'Ink', note: 'Monochrome: warm paper and near-black', swatch: ['oklch(0.22 0.012 270)', 'oklch(0.985 0.005 90)'] },
  { key: 'forest', label: 'Forest', note: 'Deep green with a lime action colour', swatch: ['oklch(0.4 0.09 160)', 'oklch(0.9 0.2 122)'] },
  { key: 'ember', label: 'Ember', note: 'Warm orange, like the website', swatch: ['oklch(0.47 0.15 38)', 'oklch(0.7 0.19 38)'] },
] as const

const NAV = [['account', 'Account'], ['appearance', 'Appearance'], ['alerts', 'Notifications'], ['tracking', 'Tracking'], ['background', 'Background'],
  ['channels', 'Phone and email'], ['cloud', 'Cloud checks'], ['data', 'Your data']] as const

export function SettingsPage({ dark, onToggleTheme, palette, onPalette, paths, version, demo, onOpenFolder, run, running, onDataCleared }: {
  dark: boolean; onToggleTheme: () => void; palette: string; onPalette: (p: string) => void
  paths: { lectures: string; data: string }; version: string; demo: boolean; onOpenFolder: (k: 'lectures' | 'data') => void
  run: (kind: string, begin: () => Promise<{ job: string }>) => Promise<Outcome>; running: Running | null; onDataCleared: () => void
}) {
  const { view, error, load, save } = useSettings(demo)
  const busy = !!running

  return (
    <div className="flex w-full flex-col gap-5">
      <PageHeader title="Settings" description="Your account, alerts and how the app runs. Changes are saved as you make them." />

      <nav aria-label="Sections" className="flex flex-wrap gap-1.5">
        {NAV.map(([id, label]) => <a key={id} href={`#/settings`} onClick={e => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }}
          className="text-muted-foreground hover:bg-muted hover:text-foreground rounded-full border px-3 py-1 text-xs transition-colors">{label}</a>)}
      </nav>

      {demo && <Alert tone="info">Sample data: start the engine to see and change your real settings.</Alert>}
      {error && !demo && <Alert tone="danger">{error}</Alert>}

      {/* sections flow into two balanced columns on wide screens and never split across them */}
      <div className="columns-1 gap-5 xl:columns-2 [&>section]:mb-5 [&>section]:break-inside-avoid">
      {view ? <AccountSection key={view.account.enrollment + view.account.institute_id + String(view.account.password_set)} view={view} save={save} run={run} busy={busy} /> : !demo && <Skeleton className="h-64 w-full rounded-2xl" />}

      <Section id="appearance" title="Appearance" description="Colours are remembered on this computer.">
        <Row label="Dark theme" hint="Easier on the eyes at night">
          {dark ? <Moon className="text-muted-foreground size-4" /> : <Sun className="text-muted-foreground size-4" />}
          <Switch checked={dark} onCheckedChange={onToggleTheme} aria-label="Dark theme" />
        </Row>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          {PALETTE_INFO.map(p => (
            <button key={p.key} type="button" onClick={() => onPalette(p.key)} aria-pressed={palette === p.key}
              className={cn('hover:bg-muted/50 flex items-center gap-3 rounded-xl border p-3 text-left transition-colors', palette === p.key && 'border-foreground/60 bg-muted/60')}>
              <span className="flex shrink-0 overflow-hidden rounded-lg border" aria-hidden>
                <span className="block size-10" style={{ background: p.swatch[0] }} /><span className="block size-10" style={{ background: p.swatch[1] }} />
              </span>
              <span><span className="block text-sm font-medium">{p.label}</span><span className="text-muted-foreground block text-xs">{p.note}</span></span>
            </button>
          ))}
        </div>
      </Section>

      {view && (
        <>
          <AlertsSection view={view} save={save} demo={demo} />
          <TrackingSection view={view} save={save} />
          <BackgroundSection view={view} save={save} run={run} busy={busy} demo={demo} reload={load} />
          <ChannelsSection view={view} save={save} run={run} busy={busy} demo={demo} reload={load} />
          <CloudSection view={view} run={run} running={running} busy={busy} demo={demo} reload={load} />
        </>
      )}
      <DataSection paths={paths} demo={demo} onOpenFolder={onOpenFolder} onCleared={onDataCleared} />

      <Section id="about" title="About">
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt className="text-muted-foreground">Interface</dt><dd className="num text-right">prototype</dd>
          <dt className="text-muted-foreground">App version</dt><dd className="num text-right">{version}</dd>
          <dt className="text-muted-foreground">Data</dt><dd className="text-right">{demo ? 'sample data (engine not running)' : 'live, from the app engine'}</dd>
        </dl>
      </Section>
      </div>
    </div>
  )
}
