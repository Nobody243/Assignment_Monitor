/* The grade arithmetic behind the calculator page. Plain functions, no imports, so it loads in Node and is tested there
   (scripts/gpa.test.mjs). The scale is the one the CMS result page prints; the app's Results page uses the same one. */

export const GRADE_POINTS = {
  "A": 4.0, "A-": 3.67, "B+": 3.33, "B": 3.0, "B-": 2.67, "C+": 2.33, "C": 2.0, "C-": 1.67, "D+": 1.33, "D": 1.0, "F": 0.0,
};
export const GRADES = Object.keys(GRADE_POINTS);                       // best first

const round2 = (n) => Math.round(n * 100) / 100;

/** A row counts once it has credit hours above zero and a known grade. */
export function counted(rows) {
  return rows
    .map((r) => ({ credits: Number(r.credits), points: GRADE_POINTS[r.grade] }))
    .filter((r) => Number.isFinite(r.credits) && r.credits > 0 && r.points !== undefined);
}

/** GPA of one semester: sum of (credits x points) over sum of credits. null when nothing is graded yet. */
export function gpaOf(rows) {
  const c = counted(rows);
  const credits = c.reduce((n, r) => n + r.credits, 0);
  if (!credits) return null;
  return round2(c.reduce((n, r) => n + r.credits * r.points, 0) / credits);
}

export function creditsOf(rows) { return counted(rows).reduce((n, r) => n + r.credits, 0); }
export function pointsOf(rows) { return counted(rows).reduce((n, r) => n + r.credits * r.points, 0); }

/** The CGPA after this semester, from the CGPA and credit hours so far. Without earlier credits it is just the GPA. */
export function cgpaAfter(rows, prevCgpa, prevCredits) {
  const credits = creditsOf(rows);
  const pc = Number(prevCredits) > 0 ? Number(prevCredits) : 0;
  const pg = Number(prevCgpa);
  if (!credits) return pc && Number.isFinite(pg) ? round2(pg) : null;
  if (!pc || !Number.isFinite(pg)) return gpaOf(rows);
  return round2((pg * pc + pointsOf(rows)) / (pc + credits));
}

/**
 * What semester GPA ends on the target CGPA, given the credit hours of this semester (all of them, graded or not).
 * Returns { needed, reachable, best } where `best` is the CGPA with straight As, and `needed` is null when there is
 * nothing to work with (no credits).
 */
export function neededGpa(target, prevCgpa, prevCredits, semesterCredits) {
  const t = Number(target);
  const sc = Number(semesterCredits);
  const pc = Number(prevCredits) > 0 ? Number(prevCredits) : 0;
  const pg = pc ? Number(prevCgpa) : 0;
  if (!Number.isFinite(t) || !(sc > 0) || (pc && !Number.isFinite(pg))) return null;
  const needed = (t * (pc + sc) - pg * pc) / sc;
  const best = (pg * pc + 4 * sc) / (pc + sc);
  return { needed: round2(needed), reachable: needed <= 4 + 1e-9, best: round2(best) };
}

/** The lowest letter grade that, for every course, still reaches `gpa`. null if even an A is not enough. */
export function lowestGradeFor(gpa) {
  if (gpa > 4 + 1e-9) return null;
  let found = null;
  for (const g of GRADES) { if (GRADE_POINTS[g] + 1e-9 >= gpa) found = g; }
  return found;
}
