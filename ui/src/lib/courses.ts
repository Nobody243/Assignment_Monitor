import type { Assignment } from '@/api'

// A course keeps one colour everywhere it appears. The colour identifies the course only: status never uses it.
export const COURSE_COLORS = ['#3b6cf0', '#e2562a', '#0e9f87', '#9b51e0', '#d4a017', '#0f87c9', '#c2417a', '#5f7c3b', '#6b7280']

export function courseColors(all: Assignment[]): Record<string, string> {
  const names = [...new Set(all.map(a => a.course))].sort()
  return Object.fromEntries(names.map((n, i) => [n, COURSE_COLORS[i % COURSE_COLORS.length]]))
}

export type CourseProgress = { name: string; total: number; submitted: number; color: string }
export function courseProgress(all: Assignment[]): CourseProgress[] {
  const colors = courseColors(all)
  return Object.keys(colors).map(name => {
    const mine = all.filter(a => a.course === name)
    return { name, total: mine.length, submitted: mine.filter(a => a.is_submitted).length, color: colors[name] }
  })
}
