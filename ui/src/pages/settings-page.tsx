import { FolderOpen, Moon, Sun } from 'lucide-react'
import { Alert } from '@/components/inline-alert'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'

export const PALETTE_INFO = [
  { key: 'royal', label: 'Royal', note: 'Royal blue with an aqua action colour', swatch: ['oklch(0.5 0.19 262)', 'oklch(0.85 0.13 205)'] },
  { key: 'ink', label: 'Ink', note: 'Monochrome: warm paper and near-black', swatch: ['oklch(0.22 0.012 270)', 'oklch(0.985 0.005 90)'] },
  { key: 'forest', label: 'Forest', note: 'Deep green with a lime action colour', swatch: ['oklch(0.4 0.09 160)', 'oklch(0.9 0.2 122)'] },
  { key: 'ember', label: 'Ember', note: 'Warm orange, like the website', swatch: ['oklch(0.47 0.15 38)', 'oklch(0.7 0.19 38)'] },
] as const

function Section({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <section className="bg-card panel-lift rounded-2xl border p-5" aria-label={title}>
      <h2 className="font-semibold">{title}</h2>
      {description && <p className="text-muted-foreground mt-0.5 text-sm">{description}</p>}
      <div className="mt-4">{children}</div>
    </section>
  )
}

export function SettingsPage({ dark, onToggleTheme, palette, onPalette, paths, version, demo, onOpenFolder }: {
  dark: boolean; onToggleTheme: () => void; palette: string; onPalette: (p: string) => void
  paths: { lectures: string; data: string }; version: string; demo: boolean; onOpenFolder: (k: 'lectures' | 'data') => void
}) {
  return (
    <div className="flex max-w-3xl flex-col gap-5">
      <PageHeader title="Settings" description="How the app looks and where it keeps things." />

      <Section title="Appearance" description="Colours are remembered on this computer.">
        <div className="flex items-center justify-between gap-4 rounded-xl border p-3">
          <div className="flex items-center gap-3 text-sm">{dark ? <Moon className="size-4" /> : <Sun className="size-4" />}<div><div className="font-medium">Dark theme</div><div className="text-muted-foreground text-xs">Easier on the eyes at night</div></div></div>
          <Switch checked={dark} onCheckedChange={onToggleTheme} aria-label="Dark theme" />
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {PALETTE_INFO.map(p => (
            <button key={p.key} type="button" onClick={() => onPalette(p.key)} aria-pressed={palette === p.key}
              className={cn('flex items-center gap-3 rounded-xl border p-3 text-left transition-colors hover:bg-muted/50', palette === p.key && 'border-foreground/60 bg-muted/60')}>
              <span className="flex shrink-0 overflow-hidden rounded-lg border" aria-hidden>
                <span className="block size-10" style={{ background: p.swatch[0] }} /><span className="block size-10" style={{ background: p.swatch[1] }} />
              </span>
              <span><span className="block text-sm font-medium">{p.label}</span><span className="text-muted-foreground block text-xs">{p.note}</span></span>
            </button>
          ))}
        </div>
      </Section>

      <Section title="Files and data">
        <dl className="flex flex-col gap-3 text-sm">
          {([['lectures', 'Downloads (lectures, assignment files)', paths.lectures], ['data', 'App data', paths.data]] as const).map(([k, label, path]) => (
            <div key={k} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3">
              <div className="min-w-0"><dt className="font-medium">{label}</dt><dd className="num text-muted-foreground truncate text-xs">{path}</dd></div>
              <Button variant="outline" size="sm" disabled={demo} onClick={() => onOpenFolder(k)}><FolderOpen />Open</Button>
            </div>
          ))}
        </dl>
      </Section>

      <Section title="About">
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt className="text-muted-foreground">Interface</dt><dd className="num text-right">prototype</dd>
          <dt className="text-muted-foreground">App version</dt><dd className="num text-right">{version}</dd>
          <dt className="text-muted-foreground">Data</dt><dd className="text-right">{demo ? 'sample data (engine not running)' : 'live, from the app engine'}</dd>
        </dl>
      </Section>

      <Alert tone="info">Your sign-in, alerts, automatic checks and cloud checks are still managed in the desktop app's own settings. They move here once this interface replaces it.</Alert>
    </div>
  )
}
