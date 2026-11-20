/**
 * How much a student may miss over the WHOLE semester, from the course's credit hours, not from what has been held so far.
 * A semester has 16 teaching weeks. A theory course meets its credit hours a week (2 credit hours: 32 h, 3: 48 h); a
 * one-credit-hour lab meets three hours a week (48 h). The minimum attendance (75%) leaves 25% of those hours missable:
 * 12 h for a lab or a 3-credit-hour course, 8 h for a 2-credit-hour course. If the teacher holds fewer classes than planned,
 * the limit follows the hours actually held (25% of 42 h is 10.5 h).
 */
export const SEMESTER_WEEKS = 16

export type Allowance = {
  planned: number        // contact hours planned for the semester
  max: number            // hours that may be missed in total
  used: number           // hours already missed
  left: number           // hours that may still be missed (never below 0)
  classLen: number       // typical length of one class, hours
  classes: number        // whole classes that fit in `max`
  heldLimit: number | null   // limit if the course ends with only the hours held so far
}

export function plannedHours(credit: number): number {
  if (!Number.isFinite(credit) || credit <= 0) return 0
  return (credit === 1 ? 3 : credit) * SEMESTER_WEEKS
}

export function typicalClassLength(credit: number, sessionHours: number[] = []): number {
  const known = sessionHours.filter(h => h > 0).sort((a, b) => a - b)
  if (known.length) return known[Math.floor(known.length / 2)]
  return credit === 1 ? 3 : credit === 2 ? 2 : 1.5
}

export function semesterAllowance(creditText: string | number | undefined, minimum: number, absent: number, held: number, sessionHours: number[] = []): Allowance | null {
  const credit = Number(creditText)
  const planned = plannedHours(credit)
  if (!planned) return null
  const share = Math.max(0, 100 - minimum) / 100
  const max = planned * share
  const classLen = typicalClassLength(credit, sessionHours)
  return {
    planned, max, used: absent, left: Math.max(0, max - absent), classLen, classes: Math.floor(max / classLen + 1e-9),
    heldLimit: held > 0 && held < planned ? held * share : null,
  }
}
