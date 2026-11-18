import type { Assignment } from '@/api'

// A course keeps one colour everywhere it appears. The colour identifies the course only: status never uses it.
export const COURSE_COLORS = [
  'oklch(0.62 0.17 262)', 'oklch(0.68 0.17 45)', 'oklch(0.64 0.13 178)', 'oklch(0.62 0.18 305)', 'oklch(0.74 0.15 90)',
  'oklch(0.64 0.14 232)', 'oklch(0.62 0.18 8)', 'oklch(0.66 0.14 140)', 'oklch(0.58 0.04 262)',
]

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
