import { Children, Fragment, isValidElement, useEffect, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

/** True while the window is at least `px` wide. */
export function useMinWidth(px: number) {
  const [ok, setOk] = useState(() => typeof matchMedia === 'function' && matchMedia(`(min-width: ${px}px)`).matches)
  useEffect(() => {
    const m = matchMedia(`(min-width: ${px}px)`)
    const on = () => setOk(m.matches)
    m.addEventListener('change', on)
    on()
    return () => m.removeEventListener('change', on)
  }, [px])
  return ok
}

/** The children of a fragment (so `two(<><A/><B/></>)` still lays out A and B separately). */
function flatten(children: ReactNode): ReactNode[] {
  return Children.toArray(children).flatMap(c => (isValidElement<{ children?: ReactNode }>(c) && c.type === Fragment ? flatten(c.props.children) : [c]))
}

/**
 * Cards in two independent columns (one column on a narrow window). Each column is its own stack, so a card that grows
 * (a drop-down opening) only pushes down the cards below it in its own column, and the other column is not stretched or
 * left with a gap beside it. Cards are dealt out left, right, left, right, so the order still reads naturally.
 */
export function Masonry({ children, minWidth = 1024, className }: { children: ReactNode; minWidth?: number; className?: string }) {
  const wide = useMinWidth(minWidth)
  const items = flatten(children)
  if (!wide || items.length < 2) return <div className={cn('flex flex-col gap-4', className)}>{items}</div>
  const cols: ReactNode[][] = [[], []]
  items.forEach((c, i) => cols[i % 2].push(c))
  return (
    <div className={cn('grid grid-cols-2 items-start gap-4', className)}>
      {cols.map((c, i) => <div key={i} className="flex min-w-0 flex-col gap-4">{c}</div>)}
    </div>
  )
}
