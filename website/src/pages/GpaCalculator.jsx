import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { usePageMeta } from "../lib/meta.js";
import { PageHero, Reveal } from "../components/Reveal.jsx";
import { Button } from "../components/Button.jsx";
import { metaFor } from "../data/pages.js";
import { GRADES, GRADE_POINTS, cgpaAfter, creditsOf, gpaOf, lowestGradeFor, neededGpa } from "../lib/gpa.js";

let nextId = 1;
const blank = () => ({ id: nextId++, name: "", credits: "3", grade: "" });
const fmt = (n) => (n == null ? "–" : n.toFixed(2));

/* A calculator that runs entirely in the page: nothing is sent or stored. It reuses the grade scale the CMS prints,
   which the desktop app's Results page also uses, and ends with a quiet pointer to the app. */
export default function GpaCalculator() {
  usePageMeta(...metaFor("/gpa-calculator"));
  const [rows, setRows] = useState(() => [blank(), blank(), blank(), blank(), blank()]);
  const [prevCgpa, setPrevCgpa] = useState("");
  const [prevCredits, setPrevCredits] = useState("");
  const [target, setTarget] = useState("");

  const update = (id, patch) => setRows((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  const remove = (id) => setRows((rs) => (rs.length > 1 ? rs.filter((r) => r.id !== id) : rs));
  const reset = () => { setRows([blank(), blank(), blank(), blank(), blank()]); setPrevCgpa(""); setPrevCredits(""); setTarget(""); };

  const out = useMemo(() => {
    const gpa = gpaOf(rows);
    const credits = creditsOf(rows);
    const allCredits = rows.reduce((n, r) => n + (Number(r.credits) > 0 ? Number(r.credits) : 0), 0);
    const hasPrev = Number(prevCredits) > 0 && prevCgpa !== "" && Number.isFinite(Number(prevCgpa));
    const cgpa = cgpaAfter(rows, prevCgpa, prevCredits);
    const goal = target !== "" ? neededGpa(target, hasPrev ? prevCgpa : "", hasPrev ? prevCredits : "", allCredits) : null;
    return { gpa, credits, allCredits, hasPrev, cgpa, goal };
  }, [rows, prevCgpa, prevCredits, target]);

  const bad = (v, lo, hi) => v !== "" && !(Number(v) >= lo && Number(v) <= hi);

  return (
    <>
      <PageHero kicker="Tool · Results" title="Bahria GPA and CGPA calculator"
        lede="Add your courses, pick the grades, and see your semester GPA and your CGPA. Set a target to see what grades get you there. It runs in your browser: nothing you type is sent or saved." />
      <section className="calc">
        <div className="wrap calc-wrap">
          <Reveal className="calc-card">
            <h2 className="h-md">This semester</h2>
            <div className="calc-rows" role="group" aria-label="Courses">
              <div className="calc-head" aria-hidden="true"><span>Course (optional)</span><span>Credit hours</span><span>Grade</span><span /></div>
              {rows.map((r, i) => (
                <div className="calc-row" key={r.id}>
                  <input type="text" value={r.name} onChange={(e) => update(r.id, { name: e.target.value })} placeholder={`Course ${i + 1}`} aria-label={`Course ${i + 1} name`} maxLength={60} />
                  <select value={r.credits} onChange={(e) => update(r.id, { credits: e.target.value })} aria-label={`Course ${i + 1} credit hours`}>
                    {["0", "1", "2", "3", "4"].map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  <select value={r.grade} onChange={(e) => update(r.id, { grade: e.target.value })} aria-label={`Course ${i + 1} grade`}>
                    <option value="">Grade</option>
                    {GRADES.map((g) => <option key={g} value={g}>{g} ({GRADE_POINTS[g].toFixed(2)})</option>)}
                  </select>
                  <button type="button" className="calc-x" onClick={() => remove(r.id)} aria-label={`Remove course ${i + 1}`} disabled={rows.length === 1}>×</button>
                </div>
              ))}
            </div>
            <div className="calc-actions">
              <button type="button" className="calc-btn" onClick={() => setRows((rs) => [...rs, blank()])}>Add a course</button>
              <button type="button" className="calc-btn calc-btn-quiet" onClick={reset}>Start over</button>
            </div>

            <h2 className="h-md calc-sub">Your record so far <span className="calc-opt">optional, for the CGPA</span></h2>
            <div className="calc-two">
              <label>CGPA before this semester
                <input type="number" inputMode="decimal" step="0.01" min="0" max="4" value={prevCgpa} onChange={(e) => setPrevCgpa(e.target.value)} placeholder="e.g. 3.40" aria-invalid={bad(prevCgpa, 0, 4)} />
              </label>
              <label>Credit hours completed so far
                <input type="number" inputMode="numeric" step="1" min="0" max="300" value={prevCredits} onChange={(e) => setPrevCredits(e.target.value)} placeholder="e.g. 60" aria-invalid={bad(prevCredits, 0, 300)} />
              </label>
            </div>

            <h2 className="h-md calc-sub">A target <span className="calc-opt">optional</span></h2>
            <label className="calc-one">The CGPA you want at the end of this semester
              <input type="number" inputMode="decimal" step="0.01" min="0" max="4" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="e.g. 3.60" aria-invalid={bad(target, 0, 4)} />
            </label>
          </Reveal>

          <Reveal as="aside" className="calc-card calc-result" aria-live="polite">
            <p className="mono">Result</p>
            <dl className="calc-figs">
              <div><dt>Semester GPA</dt><dd>{fmt(out.gpa)}</dd></div>
              <div><dt>{out.hasPrev ? "New CGPA" : "CGPA"}</dt><dd>{fmt(out.cgpa)}</dd></div>
              <div><dt>Credit hours counted</dt><dd>{out.credits}</dd></div>
            </dl>
            {!out.hasPrev && out.gpa != null && <p className="calc-note">Without your earlier record, the CGPA is just this semester's GPA. Add your CGPA and credit hours so far for the real figure.</p>}

            {out.goal && (
              <div className="calc-goal">
                {out.allCredits === 0 ? <p>Add the credit hours of your courses to see what you need.</p>
                  : out.goal.reachable ? (
                    <>
                      <p>To finish on a CGPA of <b>{Number(target).toFixed(2)}</b> you need a semester GPA of <b>{fmt(Math.max(0, out.goal.needed))}</b>.</p>
                      {out.goal.needed <= 0 ? <p>You are already above that target, whatever the grades.</p>
                        : <p>That is {lowestGradeFor(out.goal.needed) ? <>a <b>{lowestGradeFor(out.goal.needed)}</b> or better in every course, or a mix that averages it.</> : "out of reach."}</p>}
                    </>
                  ) : (
                    <p>A CGPA of <b>{Number(target).toFixed(2)}</b> is not reachable this semester: it would need a GPA of {fmt(out.goal.needed)}, and the highest possible is 4.00. Straight As would bring you to <b>{fmt(out.goal.best)}</b>.</p>
                  )}
              </div>
            )}

            <div className="calc-cta">
              <p><b>Do this automatically.</b> Assignment Monitor reads your real transcript from the CMS, keeps every semester, lets you try grades on the running one, and tells you the moment a result is posted. It also watches deadlines, attendance and exams.</p>
              <div className="hero-cta"><Button to="/download">Download the app</Button></div>
            </div>
          </Reveal>

          <Reveal className="calc-card calc-wide">
            <h2 className="h-md">How it is worked out</h2>
            <p>Each course contributes its credit hours times its grade points. The GPA is the total of those divided by the total credit hours. The CGPA is the same sum carried across every graded semester, so it needs your earlier CGPA and credit hours. Zero-credit courses weigh nothing.</p>
            <p>The scale used is the one the CMS result page prints. Confirm it, and any pass marks, with your department; this page is an independent student tool, not an official Bahria University calculator. <Link to="/guide/bahria-cgpa-calculator">Read the guide with worked examples.</Link></p>
          </Reveal>
        </div>
      </section>
    </>
  );
}
