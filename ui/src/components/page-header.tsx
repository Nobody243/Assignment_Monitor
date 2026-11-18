import type { ReactNode } from 'react'

/** The title block every page starts with: what this page is, one line of context, and its actions on the right. */
export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-muted-foreground mt-1 text-sm">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

/** A figure with a label, for the summary rows at the top of a page. */
export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: 'danger' | 'warning' | 'success' }) {
  return (
    <div className="bg-card panel-lift min-w-0 rounded-2xl border p-4">
      <div className="text-muted-foreground text-xs">{label}</div>
      <div className={`num mt-1 text-2xl font-medium ${tone === 'danger' ? 'text-destructive' : tone === 'warning' ? 'text-warning' : tone === 'success' ? 'text-success' : ''}`}>{value}</div>
      {sub && <div className="text-muted-foreground mt-0.5 text-xs">{sub}</div>}
    </div>
  )
}
