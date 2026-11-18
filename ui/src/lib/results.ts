import type { ResultSemester } from '@/api'

// The portal's own grade scale, and the same arithmetic as results.py (checked there against a real transcript).
export const GRADE_POINTS: Record<string, number> = {
  A: 4.0, 'A-': 3.67, 'B+': 3.33, B: 3.0, 'B-': 2.67, 'C+': 2.33, C: 2.0, 'C-': 1.67, 'D+': 1.33, D: 1.0, F: 0.0,
}
export const GRADES = Object.keys(GRADE_POINTS)

const graded = (c: { grade: string; points: number | null }) => !!c.grade && c.points != null

export function gpaOf(courses: { credits: number; grade: string; points: number | null }[]): number | null {
  const g = courses.filter(graded)
  const credits = g.reduce((n, c) => n + c.credits, 0)
  if (!credits) return null
  return Math.round((100 * g.reduce((n, c) => n + c.credits * (c.points as number), 0)) / credits) / 100
}

export function totals(semesters: ResultSemester[]) {
  let credits = 0, earned = 0, points = 0
  for (const s of semesters) for (const c of s.courses) {
    if (graded(c)) {
      credits += c.credits
      points += c.credits * (c.points as number)
      if (c.grade !== 'F') earned += c.credits
    }
  }
  return { credits, earned, points, cgpa: credits ? Math.round((100 * points) / credits) / 100 : null }
}

/** What-if for the running semester: picks maps a course code to a letter grade. Only picked courses count. */
export function project(semesters: ResultSemester[], picks: Record<string, string>) {
  const done = totals(semesters.filter(s => s.complete))
  const cur = [...semesters].reverse().find(s => !s.complete)
  if (!cur) return { gpa: null as number | null, cgpa: done.cgpa, picked: 0, of: 0 }
  const chosen = cur.courses.filter(c => picks[c.code] in GRADE_POINTS).map(c => ({ ...c, grade: picks[c.code], points: GRADE_POINTS[picks[c.code]] }))
  const gpa = gpaOf(chosen)
  const credits = done.credits + chosen.reduce((n, c) => n + c.credits, 0)
  const points = done.points + chosen.reduce((n, c) => n + c.credits * c.points, 0)
  return { gpa, cgpa: credits ? Math.round((100 * points) / credits) / 100 : null, picked: chosen.length, of: cur.courses.length }
}
