// Fictional sample data, shown only when the engine cannot be reached (and clearly labelled as such).
import type { Assignment, State, Urgency } from './api'

const H = 3600_000
function make(i: number, course: string, title: string, inHours: number | null, submitted = false, action?: string): Assignment {
  const now = Date.now()
  const due = inHours === null ? null : new Date(now + inHours * H)
  let urgency: Urgency = 'unknown'
  let label = 'No deadline'
  if (submitted) { urgency = 'submitted'; label = 'Submitted' }
  else if (due) {
    const days = Math.floor(inHours! / 24)
    if (inHours! < 0) { urgency = 'missed'; label = 'Overdue' }
    else if (inHours! < 24) { urgency = 'today'; label = 'Due today' }
    else if (days <= 3) { urgency = 'soon'; label = `Due in ${days} days` }
    else if (days <= 7) { urgency = 'week'; label = `Due in ${days} days` }
    else { urgency = 'later'; label = `Due in ${days} days` }
  }
  const open = !submitted && !!due && inHours! >= 0
  return {
    id: `demo-${i}`, course, assign_no: String(i), title, due_date: due ? due.toDateString() : '', due_at: due ? due.toISOString() : null,
    urgency, label, days: due ? Math.floor(inHours! / 24) : null, is_submitted: submitted,
    action: action ?? (submitted ? 'Delete' : open ? 'Submit' : 'Deadline Exceeded'), open,
    can_upload: open && !submitted, can_replace: submitted && !!due && inHours! >= 0,
  }
}

export const DEMO: State = {
  version: 'demo', now: new Date().toISOString(),
  meta: { student_name: 'Alex Morgan', semester: 'Fall-2026', last_sync: new Date(Date.now() - 40 * 60_000).toISOString(), enrollment: '01-000000-000' },
  assignments: [
    make(1, 'Human Computer Interaction', 'Usability test report', 19),
    make(2, 'Database Systems', 'Normalisation worksheet', 52),
    make(3, 'Operating Systems', 'Scheduler simulation', 26 * 5),
    make(4, 'Software Engineering', 'Sprint retrospective', 24 * 12),
    make(5, 'Database Systems', 'ER diagram draft', 30, true),
    make(6, 'Operating Systems', 'Lab journal 4', -48),
    make(7, 'Human Computer Interaction', 'Paper prototype', -24 * 9, true, 'Deadline Exceeded'),
    make(8, 'Software Engineering', 'Requirements document', 24 * 20),
  ],
  attendance: {
    minimum: 75, overall: 82.5,
    courses: [
      { code: 'HCI 301', title: 'Human Computer Interaction', present: 22, absent: 3, recorded: true, percent: 88, ok: true, can_miss: 4, need: 0 },
      { code: 'DB 310', title: 'Database Systems', present: 14, absent: 6, recorded: true, percent: 70, ok: false, can_miss: 0, need: 4 },
      { code: 'OS 320', title: 'Operating Systems', present: 20, absent: 5, recorded: true, percent: 80, ok: true, can_miss: 1, need: 0 },
    ],
  },
  timetable: {
    semester: 'Fall-2026',
    sessions: [
      { day: 'Mon', start: '09:00', end: '10:30', course: 'Database Systems', abbr: 'DB', teacher: 'Sample Teacher', initials: 'ST' },
      { day: 'Tue', start: '11:00', end: '12:30', course: 'Operating Systems', abbr: 'OS', teacher: 'Sample Teacher', initials: 'ST' },
      { day: 'Wed', start: '09:00', end: '10:30', course: 'Human Computer Interaction', abbr: 'HCI', teacher: 'Sample Teacher', initials: 'ST' },
      { day: 'Thu', start: '14:00', end: '15:30', course: 'Software Engineering', abbr: 'SE', teacher: 'Sample Teacher', initials: 'ST' },
    ],
  },
  standing: { semester: 'Spring-2026', gpa: 3.4, cgpa: 3.3, semesters: 4 },
}
