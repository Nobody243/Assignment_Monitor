import { useRef } from 'react'
import { Moon, Sparkles, Sun } from 'lucide-react'
import { SlideMarker } from '@/lib/slide'
import { cn } from '@/lib/utils'
import { Row, Section, SwitchRow } from './parts'

export const PALETTE_INFO = [
  { key: 'royal', label: 'Royal', note: 'Royal blue with an aqua action colour', swatch: ['oklch(0.5 0.19 262)', 'oklch(0.85 0.13 205)'] },
  { key: 'ink', label: 'Ink', note: 'Monochrome: warm paper and near-black', swatch: ['oklch(0.22 0.012 270)', 'oklch(0.985 0.005 90)'] },
  { key: 'forest', label: 'Forest', note: 'Deep green with a lime action colour', swatch: ['oklch(0.4 0.09 160)', 'oklch(0.9 0.2 122)'] },
  { key: 'ember', label: 'Ember', note: 'Warm orange, like the website', swatch: ['oklch(0.47 0.15 38)', 'oklch(0.7 0.19 38)'] },
] as const

/** Look and feel. These are remembered on this computer and apply at once. */
export function AppearanceSection({ dark, onTheme, palette, onPalette, motion, onMotion }: {
  dark: boolean; onTheme: (dark: boolean) => void; palette: string; onPalette: (p: string) => void; motion: boolean; onMotion: (on: boolean) => void
}) {
  const themeRef = useRef<HTMLDivElement>(null)
  return (
    <Section id="appearance" title="Appearance" description="How the app looks. Changes apply immediately and are remembered on this computer.">
      <Row label="Theme" hint="Dark is easier on the eyes at night">
        <div ref={themeRef} className="bg-muted slide-host relative inline-flex rounded-lg p-0.5" role="group" aria-label="Theme">
          <SlideMarker host={themeRef} selector="[aria-pressed='true']" watch={dark} className="bg-background rounded-md shadow-sm" />
          {([[false, 'Light', Sun], [true, 'Dark', Moon]] as const).map(([v, label, Icon]) => (
            <button key={label} type="button" aria-pressed={dark === v} onClick={() => onTheme(v)}
              className={cn('flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors', 'relative z-10', dark === v ? '' : 'text-muted-foreground hover:text-foreground')}>
              <Icon className="size-4" />{label}
            </button>
          ))}
        </div>
      </Row>
      <div className="border-b py-3">
        <div className="text-sm font-medium">Colour palette</div>
        <div className="text-muted-foreground mt-0.5 mb-3 text-xs">Each palette has its own accent for buttons and highlights.</div>
        <div className="grid gap-3 sm:grid-cols-2">
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
      </div>
      <SwitchRow name="Animations" label={<span className="flex items-center gap-2"><Sparkles className="size-4" />Animations</span>} hint="Page transitions, fades and progress movement. Turn off if you prefer a still screen." checked={motion} onChange={onMotion} />
    </Section>
  )
}
