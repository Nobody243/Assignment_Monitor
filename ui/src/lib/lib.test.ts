import { describe, expect, it } from 'vitest'
import type { Assignment, AttendanceCourse, ResultSemester } from '@/api'
import { attendanceFor, courseColors, courseRows } from '@/lib/courses'
import { parseExamDate } from '@/lib/exams'
import { gpaOf, project, totals } from '@/lib/results'

// The expected numbers below were produced by results.py on the same data, so the interface and the engine agree.
const course = (code: string, credits: number, grade: string, points: number | null) => ({ code, title: code, credits, grade, points, product: null })
const SEMS: ResultSemester[] = [
  { name: 'S1', complete: true, gpa: null, cgpa: null, courses: [course('A1', 3, 'A', 4.0), course('A2', 3, 'B+', 3.33)] },
  { name: 'S2', complete: true, gpa: null, cgpa: null, courses: [course('B1', 2, 'C', 2.0), course('B2', 1, 'F', 0.0)] },
  { name: 'S3', complete: false, gpa: null, cgpa: null, courses: [course('C1', 3, '', null), course('C2', 1, '', null)] },
]

describe('results maths (parity with results.py)', () => {
  it('totals over the finished semesters', () => {
    const t = totals(SEMS.filter(s => s.complete))
    expect(t.credits).toBe(9)
    expect(t.earned).toBe(8)
    expect(t.cgpa).toBe(2.89)
  })
  it('a semester GPA is credit weighted', () => expect(gpaOf(SEMS[0].courses)).toBe(3.67))
  it('what-if with two grades picked', () => expect(project(SEMS, { C1: 'A', C2: 'B' })).toEqual({ gpa: 3.75, cgpa: 3.15, picked: 2, of: 2 }))
  it('what-if with nothing picked leaves the CGPA alone', () => expect(project(SEMS, {})).toEqual({ gpa: null, cgpa: 2.89, picked: 0, of: 2 }))
  it('only picked courses count', () => expect(project(SEMS, { C1: 'A-' })).toEqual({ gpa: 3.67, cgpa: 3.08, picked: 1, of: 2 }))
  it('with no running semester there is nothing to project', () => expect(project(SEMS.slice(0, 2), { C1: 'A' }).picked).toBe(0))
})

describe('exam dates', () => {
  it('reads the CMS format dd/mm/yyyy', () => {
    const d = parseExamDate('26/10/2026')!
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 9, 26])
  })
  it('rejects anything else', () => {
    expect(parseExamDate('')).toBeNull()
    expect(parseExamDate('2026-10-26')).toBeNull()
  })
})

const att = (title: string, recorded = true): AttendanceCourse => ({ code: title, title, present: 1, absent: 0, recorded, percent: 100, ok: true, can_miss: 5, need: 0 })
describe('attendance matching', () => {
  it('matches a theory course exactly, never its lab', () => {
    const list = [att('Database Administration and Management L'), att('Database Administration and Management')]
    expect(attendanceFor('Database Administration and Management', list)?.title).toBe('Database Administration and Management')
  })
  it('matches a lab whose portal title is truncated', () => {
    expect(attendanceFor('Database Administration and Management Lab', [att('Database Administration and Management L')])?.title).toBe('Database Administration and Management L')
  })
  it('ignores courses with no recorded hours', () => expect(attendanceFor('Final Year Project', [att('Final Year Project', false)])).toBeUndefined())
})

const asg = (id: string, courseName: string, over: Partial<Assignment> = {}): Assignment => ({
  id, course: courseName, assign_no: '1', title: id, due_date: '', due_at: '2026-12-01T10:00:00', urgency: 'later', label: '', days: 10, is_submitted: false,
  action: 'Submit', open: true, can_upload: true, can_replace: false, ...over,
})
describe('course summaries', () => {
  it('counts submitted, open and overdue work per course', () => {
    const rows = courseRows([
      asg('a', 'X', { is_submitted: true, open: false, can_upload: false }),
      asg('b', 'X'),
      asg('c', 'X', { urgency: 'missed', open: false, due_at: '2026-09-01T10:00:00', can_upload: false }),
      asg('d', 'Y'),
    ])
    const x = rows.find(r => r.name === 'X')!
    expect([x.total, x.submitted, x.pending, x.overdue]).toEqual([3, 1, 1, 1])
    expect(x.next?.id).toBe('b')
  })
  it('gives every course its own colour', () => {
    const c = courseColors([asg('a', 'X'), asg('b', 'Y'), asg('c', 'Z')])
    expect(new Set(Object.values(c)).size).toBe(3)
  })
})
