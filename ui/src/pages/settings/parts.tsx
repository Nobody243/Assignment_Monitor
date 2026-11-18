import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { toast } from '@/lib/notify'
import { getSettings, patchSettings, type SettingsView } from '@/api'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'

export function Section({ title, description, children, id }: { title: string; description?: ReactNode; children: ReactNode; id?: string }) {
  return (
    <section id={id} className="bg-card panel-lift scroll-mt-20 rounded-2xl border p-5" aria-label={title}>
      <h2 className="font-semibold">{title}</h2>
      {description && <p className="text-muted-foreground mt-1 text-sm">{description}</p>}
      <div className="mt-3">{children}</div>
    </section>
  )
}

/** A label with its explanation on the left and the control on the right; rows divide themselves. */
export function Row({ label, hint, children, className }: { label: ReactNode; hint?: ReactNode; children?: ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b py-3 last:border-b-0', className)}>
      <div className="min-w-0 flex-1 basis-60">
        <div className="text-sm font-medium">{label}</div>
        {hint && <div className="text-muted-foreground mt-0.5 text-xs">{hint}</div>}
      </div>
      {children && <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">{children}</div>}
    </div>
  )
}

export function SwitchRow({ label, name, hint, checked, onChange, disabled }: { label: ReactNode; name?: string; hint?: ReactNode; checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <Row label={label} hint={hint}>
      <Switch checked={checked} onCheckedChange={onChange} disabled={disabled} aria-label={name ?? (typeof label === 'string' ? label : undefined)} />
    </Row>
  )
}

const SECTIONS = ['account', 'appearance', 'alerts', 'tracking', 'background', 'channels'] as const
function merge(v: SettingsView, patch: Record<string, unknown>): SettingsView {
  const next = { ...v } as SettingsView
  for (const s of SECTIONS) {
    const part = { ...(v[s] as Record<string, unknown>) }
    let touched = false
    for (const k of Object.keys(patch)) if (k in part) { part[k] = patch[k]; touched = true }
    if (touched) (next as unknown as Record<string, unknown>)[s] = part
  }
  return next
}

/** The engine's settings. A change is shown at once and saved; if the engine refuses it, the page goes back to what is stored. */
export function useSettings(demo: boolean) {
  const [view, setView] = useState<SettingsView | null>(null)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    try { setView(await getSettings()); setError('') } catch (e) { setError(e instanceof Error ? e.message : 'Could not load the settings.') }
  }, [])
  useEffect(() => { if (!demo) void load() }, [demo, load])
  const save = useCallback(async (patch: Record<string, unknown>): Promise<boolean> => {
    setView(v => (v ? merge(v, patch) : v))
    try {
      const r = await patchSettings(patch)
      setView(r.settings)
      const names = Object.keys(patch).map(k => k.replace(/_/g, ' ')).join(', ')
      toast.success(`Saved: ${names}`, { id: 'settings-saved', duration: 2000 })
      return true
    } catch (e) {
      toast.error('That setting was not saved', { description: e instanceof Error ? e.message : undefined })
      await load()
      return false
    }
  }, [load])
  return { view, error, load, save }
}
