import { useCallback, useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react'
import { cn } from '@/lib/utils'

export type Box = { x: number; y: number; w: number; h: number }

/** Where `active` sits inside `host`, in the host's own scrolled coordinates (so the marker scrolls with the content). */
export function boxWithin(host: Pick<HTMLElement, 'getBoundingClientRect' | 'scrollLeft' | 'scrollTop'>, active: Pick<HTMLElement, 'getBoundingClientRect'>): Box {
  const h = host.getBoundingClientRect(), a = active.getBoundingClientRect()
  return { x: a.left - h.left + host.scrollLeft, y: a.top - h.top + host.scrollTop, w: a.width, h: a.height }
}

/** Direction of travel between two positions in a list: 1 forward (down), -1 back (up), 0 for the same or unknown. */
export function directionBetween(order: readonly string[], from: string | null | undefined, to: string): 1 | -1 | 0 {
  const a = from ? order.indexOf(from) : -1, b = order.indexOf(to)
  if (a < 0 || b < 0 || a === b) return 0
  return b > a ? 1 : -1
}

/**
 * Follows the element matching `selector` inside `host` with a box that can be animated (transform and size only).
 * It re-measures whenever the choice (`watch`) changes and whenever the host or the chosen element changes size, so it also
 * stays right while a sidebar collapses or a window is resized. Nothing is shown until there is something to follow, and
 * the first placement does not animate (the box must not fly in from the corner when the page opens).
 */
export function useSlidingBox(host: RefObject<HTMLElement | null>, selector: string, watch: unknown) {
  const [box, setBox] = useState<Box | null>(null)
  const [armed, setArmed] = useState(false)
  const frame = useRef(0)

  const measure = useCallback(() => {
    const h = host.current
    const a = h?.querySelector<HTMLElement>(selector)
    if (!h || !a) { setBox(null); return }
    const b = boxWithin(h, a)
    setBox(prev => (prev && prev.x === b.x && prev.y === b.y && prev.w === b.w && prev.h === b.h ? prev : b))
  }, [host, selector])

  const schedule = useCallback(() => {
    cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(measure)
  }, [measure])

  useLayoutEffect(() => { measure() }, [measure, watch])

  useEffect(() => {
    const h = host.current
    if (!h) return
    const ro = new ResizeObserver(schedule)
    ro.observe(h)
    h.querySelectorAll<HTMLElement>(selector).forEach(el => ro.observe(el))
    window.addEventListener('resize', schedule)
    // the chosen item can change without this component re-rendering (a tab strip owns its own state)
    const mo = new MutationObserver(schedule)
    mo.observe(h, { attributes: true, subtree: true, attributeFilter: ['data-state', 'data-active', 'aria-current', 'aria-selected', 'aria-pressed'] })
    const arm = requestAnimationFrame(() => setArmed(true))
    return () => { ro.disconnect(); mo.disconnect(); window.removeEventListener('resize', schedule); cancelAnimationFrame(frame.current); cancelAnimationFrame(arm) }
  }, [host, selector, schedule, watch])

  return { box, armed }
}

/** The moving background (or bar) behind the chosen item of a list, a tab strip or a menu. Put it first inside a
 *  `position: relative` host and give the items `relative z-10` so they sit above it. */
export function SlideMarker({ host, selector, watch, className }: { host: RefObject<HTMLElement | null>; selector: string; watch: unknown; className?: string }) {
  const { box, armed } = useSlidingBox(host, selector, watch)
  return (
    <span
      aria-hidden="true"
      data-slot="slide-marker"
      className={cn('pointer-events-none absolute top-0 left-0 z-0 origin-top-left will-change-transform', armed && 'transition-[transform,width,height,opacity] duration-300 ease-[var(--ease-out)]', className)}
      style={box
        ? { width: box.w, height: box.h, opacity: 1, transform: `translate3d(${box.x}px, ${box.y}px, 0)` }
        : { width: 0, height: 0, opacity: 0 }}
    />
  )
}
