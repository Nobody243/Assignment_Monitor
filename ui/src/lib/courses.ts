import type { Assignment, AttendanceCourse } from '@/api'

// Course colours are an analogous family around the active palette's hue (--course-h), with lightness varied so
// neighbours stay distinguishable. They identify a course (a dot, a class edge); they never carry status.
const HUE = [0, 24, -24, 48, -48, 60, -60, 12, -12]
const LIGHT = [0.62, 0.72, 0.66, 0.6, 0.74, 0.68, 0.64, 0.76, 0.58]
const colorAt = (i: number) => `oklch(${LIGHT[i % LIGHT.length]} 0.13 calc(var(--course-h) + ${HUE[i % HUE.length]}))`

export function courseColors(all: Assignment[]): Record<string, string> {
  const names = [...new Set(all.map(a => a.course))].sort()
  return Object.fromEntries(names.map((n, i) => [n, colorAt(i)]))
}

/** Attendance for a course. The portal truncates some attendance titles (a lab shows as "... L"), so: exact first, then
 *  a course whose name begins with the attendance title. A theory course never matches its lab's longer title. */
export function attendanceFor(course: string, list: AttendanceCourse[]): AttendanceCourse | undefined {
  const rec = list.filter(c => c.recorded)
  return rec.find(c => c.title === course) ?? rec.find(c => c.title.length > 6 && course.startsWith(c.title))
}

export type CourseRow = { name: string; total: number; submitted: number; color: string; next?: Assignment; pending: number; overdue: number }
export function courseRows(all: Assignment[]): CourseRow[] {
  const colors = courseColors(all)
  return Object.keys(colors).map(name => {
    const mine = all.filter(a => a.course === name)
    const open = mine.filter(a => a.open && !a.is_submitted).sort((a, b) => (a.due_at ?? '').localeCompare(b.due_at ?? ''))
    return { name, total: mine.length, submitted: mine.filter(a => a.is_submitted).length, color: colors[name], next: open[0], pending: open.length,
      overdue: mine.filter(a => !a.is_submitted && a.urgency === 'missed').length }
  })
}
