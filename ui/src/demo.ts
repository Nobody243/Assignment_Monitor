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
}
