import { useCallback, useEffect, useState } from 'react'

export const PAGES = ['home', 'assignments', 'attendance', 'exams', 'lectures', 'announcements', 'results', 'settings'] as const
export type Page = (typeof PAGES)[number]

/** The tabs inside Settings, in the order they are listed. */
export const SETTINGS_TABS = [
  { key: 'profile', label: 'Profile' },
  { key: 'appearance', label: 'Appearance' },
  { key: 'notifications', label: 'Notifications' },
  { key: 'tracking', label: 'Tracking' },
  { key: 'background', label: 'Background and cloud' },
  { key: 'data', label: 'Data and files' },
  { key: 'activity', label: 'Activity' },
  { key: 'about', label: 'About' },
] as const
export type SettingsTab = (typeof SETTINGS_TABS)[number]['key']

export const PAGE_TITLES: Record<Page | 'notfound', string> = {
  home: 'Home', assignments: 'Assignments', attendance: 'Attendance', exams: 'Exams', lectures: 'Lectures',
  announcements: 'Announcements', results: 'Results', settings: 'Settings', notfound: 'Not found',
}

export type Route = { page: Page | 'notfound'; sub: SettingsTab | null; missing: string }

const tabKeys = SETTINGS_TABS.map(t => t.key) as readonly string[]

/** An empty hash is Home; a known page is that page; settings/<tab> is a tab; an old #/activity link lands on the
 *  Activity tab; anything else is a 404 (and says what it was). */
export function parseRoute(hash: string): Route {
  const h = hash.replace(/^#\/?/, '').replace(/\/+$/, '')
  if (!h) return { page: 'home', sub: null, missing: '' }
  if (h === 'activity') return { page: 'settings', sub: 'activity', missing: '' }
  const [page, sub, ...rest] = h.split('/')
  if (page === 'settings' && !rest.length && (sub === undefined || tabKeys.includes(sub))) return { page: 'settings', sub: (sub as SettingsTab) ?? null, missing: '' }
  if (!sub && (PAGES as readonly string[]).includes(page)) return { page: page as Page, sub: null, missing: '' }
  return { page: 'notfound', sub: null, missing: h.slice(0, 80) }
}

/** A page held in the URL hash, so back and forward work and a page can be linked to. */
export function usePage() {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash))
  useEffect(() => {
    const on = () => setRoute(parseRoute(window.location.hash))
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const go = useCallback((p: Page, sub?: SettingsTab) => { window.location.hash = sub ? `/${p}/${sub}` : `/${p}` }, [])
  return { page: route.page, sub: route.sub, missing: route.missing, go }
}
