import { useCallback, useEffect, useState } from 'react'

export const PAGES = ['home', 'assignments', 'attendance', 'exams', 'lectures', 'announcements', 'results', 'activity', 'settings'] as const
export type Page = (typeof PAGES)[number]

export const PAGE_TITLES: Record<Page | 'notfound', string> = {
  home: 'Home', assignments: 'Assignments', attendance: 'Attendance', exams: 'Exams', lectures: 'Lectures',
  announcements: 'Announcements', results: 'Results', activity: 'Activity', settings: 'Settings', notfound: 'Not found',
}

export type Route = { page: Page | 'notfound'; missing: string }

/** An empty hash is Home; a known page is that page; anything else is a 404 (and says what it was). */
export function parseRoute(hash: string): Route {
  const h = hash.replace(/^#\/?/, '').replace(/\/+$/, '')
  if (!h) return { page: 'home', missing: '' }
  return (PAGES as readonly string[]).includes(h) ? { page: h as Page, missing: '' } : { page: 'notfound', missing: h.slice(0, 80) }
}

/** A page held in the URL hash, so back and forward work and a page can be linked to. */
export function usePage() {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash))
  useEffect(() => {
    const on = () => setRoute(parseRoute(window.location.hash))
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const go = useCallback((p: Page) => { window.location.hash = `/${p}` }, [])
  return [route.page, go, route.missing] as const
}
