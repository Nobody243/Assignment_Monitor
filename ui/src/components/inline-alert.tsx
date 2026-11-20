import type { ReactNode } from 'react'
import { CircleAlert, Info, TriangleAlert, CircleCheck } from 'lucide-react'
import { cn } from '@/lib/utils'

const TONES = {
  success: { icon: CircleCheck, box: 'bg-success/10 text-foreground', icn: 'text-success' },
  info: { icon: Info, box: 'bg-muted/50 text-foreground', icn: 'text-muted-foreground' },
  warning: { icon: TriangleAlert, box: 'bg-warning/10 text-foreground', icn: 'text-warning' },
  danger: { icon: CircleAlert, box: 'bg-destructive/10 text-foreground', icn: 'text-destructive' },
} as const

/** A compact inline notice (the shadcn Alert is a heavier, card-like block; this is the one-line version). */
export function Alert({ tone, children }: { tone: keyof typeof TONES; children: ReactNode }) {
  const t = TONES[tone]
  return (
    <div role={tone === 'info' ? 'status' : 'alert'} className={cn('flex gap-2.5 rounded-lg px-3 py-2.5 text-sm', t.box)}>
      <t.icon className={cn('mt-0.5 size-4 shrink-0', t.icn)} />
      <div className="min-w-0">{children}</div>
    </div>
  )
}
