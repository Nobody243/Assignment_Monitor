import { useCallback, useEffect, useState } from 'react'

export const PAGES = ['home', 'assignments', 'attendance', 'exams', 'lectures', 'announcements', 'results', 'settings'] as const
export type Page = (typeof PAGES)[number]

export const PAGE_TITLES: Record<Page, string> = {
  home: 'Home', assignments: 'Assignments', attendance: 'Attendance', exams: 'Exams', lectures: 'Lectures',
  announcements: 'Announcements', results: 'Results', settings: 'Settings',
}

const read = (): Page => {
  const h = window.location.hash.replace(/^#\/?/, '') as Page
  return (PAGES as readonly string[]).includes(h) ? h : 'home'
}

/** A page held in the URL hash, so back and forward work and a page can be linked to. */
export function usePage() {
  const [page, setPage] = useState<Page>(read)
  useEffect(() => {
    const on = () => setPage(read())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const go = useCallback((p: Page) => { window.location.hash = `/${p}` }, [])
  return [page, go] as const
}
