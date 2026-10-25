"""Results: the CMS Provisional Result page (every semester on one page, one table per semester) and the GPA
arithmetic around it.

What the portal shows, verified against a real transcript: each course row carries credit hours, the letter
grade, its grade points and the product (credits x points). A semester's GPA is the sum of products over the
sum of credits; the CGPA is the same sum carried over every graded semester so far. Zero-credit courses (Quran,
Tajweed) carry a grade but weigh nothing. A repeated course is simply another row in a later semester; the
portal does not replace the earlier grade in the cumulative figures. Courses of the running semester are
listed with N/A until the result is posted.

Everything here is pure: parsing and arithmetic, no I/O."""
import re
from typing import Dict, List, Optional

from lxml import html as lxml_html

# the letter scale as the portal prints it (grade points per credit hour); read from the page when present
GRADE_POINTS: Dict[str, float] = {
    "A": 4.0, "A-": 3.67, "B+": 3.33, "B": 3.0, "B-": 2.67, "C+": 2.33, "C": 2.0, "C-": 1.67,
    "D+": 1.33, "D": 1.0, "F": 0.0,
}
GRADES = list(GRADE_POINTS.keys())          # best first, for pickers


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _num(text: str) -> Optional[float]:
    try:
        return float(_clean(text))
    except ValueError:
        return None


def parse_results(page_html: str) -> dict:
    """{"student": {...}, "semesters": [{"name", "courses": [...], "gpa", "cgpa", "complete"}]} from the
    Provisional Result page. Semesters come in the portal's order (oldest first). gpa/cgpa are the portal's own
    printed figures (None while the semester is running); each course has credits, grade, points, product."""
    doc = lxml_html.fromstring(page_html)
    student: Dict[str, str] = {}
    for table in doc.xpath("//table[not(caption)]"):
        for row in table.xpath(".//tr"):
            cells = [_clean(c.text_content()) for c in row.xpath("./td|./th")]
            for i in range(0, len(cells) - 1, 2):
                key = cells[i].lower().rstrip(":")
                if key in ("program", "intake semester", "name", "enrollment", "status"):
                    student[key.replace(" ", "_")] = cells[i + 1]
    semesters: List[dict] = []
    for table in doc.xpath("//table[caption]"):
        name = _clean(table.findtext("caption"))
        rows = table.xpath(".//tr")
        courses = []
        gpa = cgpa = None
        for row in rows:
            tds = row.xpath("./td")
            if len(tds) == 1 and "GPA" in tds[0].text_content():
                m = re.search(r"GPA:\s*([\d.]+|N/A)\s*,\s*CGPA:\s*([\d.]+|N/A)", _clean(tds[0].text_content()))
                if m:
                    gpa = _num(m.group(1))
                    cgpa = _num(m.group(2))
                continue
            if len(tds) < 8:
                continue
            cells = [_clean(c.text_content()) for c in tds]
            credits = _num(cells[4])
            if credits is None:
                continue
            grade = cells[5] if cells[5] and cells[5] != "N/A" else ""
            points = _num(cells[6]) if grade else None
            if grade and points is None:
                points = GRADE_POINTS.get(grade)
            courses.append({"code": cells[1], "title": cells[2], "credits": credits, "grade": grade,
                            "points": points, "product": _num(cells[7]) if grade else None})
        if not courses:
            continue
        semesters.append({"name": name, "courses": courses, "gpa": gpa, "cgpa": cgpa,
                          "complete": all(c["grade"] for c in courses)})
    return {"student": student, "semesters": semesters}


# ---------------------------------------------------------------------------- arithmetic
def gpa_of(courses: List[dict]) -> Optional[float]:
    """Credit-weighted average of the graded courses, None when nothing is graded."""
    credits = sum(c["credits"] for c in courses if c.get("grade") and c.get("points") is not None)
    if not credits:
        return None
    points = sum(c["credits"] * c["points"] for c in courses if c.get("grade") and c.get("points") is not None)
    return round(points / credits, 2)


def totals(semesters: List[dict]) -> dict:
    """Cumulative figures over every graded course: credits attempted, credits earned (grade above F), points."""
    credits = earned = points = 0.0
    for s in semesters:
        for c in s["courses"]:
            if c.get("grade") and c.get("points") is not None:
                credits += c["credits"]
                points += c["credits"] * c["points"]
                if c["grade"] != "F":
                    earned += c["credits"]
    return {"credits": credits, "earned": earned, "points": points,
            "cgpa": round(points / credits, 2) if credits else None}


def current_semester(semesters: List[dict]) -> Optional[dict]:
    """The semester still waiting for grades (the last incomplete one), or None."""
    for s in reversed(semesters):
        if not s.get("complete"):
            return s
    return None


def project(semesters: List[dict], picks: Dict[str, str]) -> dict:
    """What-if: `picks` maps a course code of the running semester to a chosen letter grade. Returns the
    projected semester GPA and CGPA counting only the courses that were given a grade, plus how many were."""
    done = totals([s for s in semesters if s.get("complete")])
    cur = current_semester(semesters)
    if not cur:
        return {"gpa": None, "cgpa": done["cgpa"], "picked": 0, "of": 0}
    chosen = []
    for c in cur["courses"]:
        g = picks.get(c["code"])
        if g in GRADE_POINTS:
            chosen.append({**c, "grade": g, "points": GRADE_POINTS[g]})
    gpa = gpa_of(chosen)
    extra_credits = sum(c["credits"] for c in chosen)
    extra_points = sum(c["credits"] * c["points"] for c in chosen)
    cgpa = round((done["points"] + extra_points) / (done["credits"] + extra_credits), 2) if (done["credits"] + extra_credits) else None
    return {"gpa": gpa, "cgpa": cgpa, "picked": len(chosen), "of": len(cur["courses"])}


def required_gpa(semesters: List[dict], target_cgpa: float) -> Optional[float]:
    """The semester GPA the running semester needs for the CGPA to reach `target_cgpa`. None without a running
    semester or credits; the figure can exceed 4 (unreachable) or fall below 0 (already there)."""
    done = totals([s for s in semesters if s.get("complete")])
    cur = current_semester(semesters)
    if not cur:
        return None
    credits = sum(c["credits"] for c in cur["courses"])
    if not credits:
        return None
    needed_points = target_cgpa * (done["credits"] + credits) - done["points"]
    return round(needed_points / credits, 2)


def graded_count(semester: dict) -> int:
    return sum(1 for c in semester.get("courses", []) if c.get("grade"))


def newly_graded(old: Optional[dict], new: dict) -> List[dict]:
    """Semesters that gained grades since `old` was stored (a whole result posted, or a few courses of it when
    teachers post at different times). A first read (old is None) reports nothing, so a fresh install stays
    quiet instead of announcing six old semesters."""
    if old is None:
        return []
    before = {s["name"]: s for s in old.get("semesters", [])}
    out = []
    for s in new.get("semesters", []):
        prev = before.get(s["name"])
        had = graded_count(prev) if prev else 0
        if graded_count(s) > had:
            out.append(s)
    return out


# ---------------------------------------------------------------------------- what-if on past semesters
def apply_overrides(semesters: List[dict], overrides: Dict[tuple, str]) -> List[dict]:
    """A copy of `semesters` with hypothetical grades swapped in: `overrides` maps (semester name, course code)
    to a letter grade. Only graded courses can be overridden; the running semester is left to `project`."""
    out = []
    for s in semesters:
        courses = []
        for c in s["courses"]:
            g = overrides.get((s["name"], c["code"]))
            if g in GRADE_POINTS and c.get("grade"):
                courses.append({**c, "grade": g, "points": GRADE_POINTS[g], "product": round(c["credits"] * GRADE_POINTS[g], 2)})
            else:
                courses.append(c)
        out.append({**s, "courses": courses})
    return out


def uniform_scenarios(semesters: List[dict], picks: Optional[Dict[str, str]] = None) -> List[dict]:
    """For each letter grade: the semester GPA and CGPA if every course of the running semester that has no pick
    yet ends with that grade (picked courses keep their pick). Empty without a running semester."""
    cur = current_semester(semesters)
    if not cur:
        return []
    picks = picks or {}
    out = []
    for g in GRADES:
        full = {c["code"]: picks.get(c["code"], g) for c in cur["courses"]}
        p = project(semesters, full)
        out.append({"grade": g, "gpa": p["gpa"], "cgpa": p["cgpa"]})
    return out


def grade_needed(semesters: List[dict], picks: Dict[str, str], target_cgpa: float) -> dict:
    """The lowest uniform grade in the courses not picked yet that still reaches `target_cgpa`.
    Returns {"grade": "B+" | None, "best": <CGPA with straight A's>, "remaining": n, "reached": bool}."""
    cur = current_semester(semesters)
    if not cur:
        return {"grade": None, "best": None, "remaining": 0, "reached": False}
    remaining = [c for c in cur["courses"] if picks.get(c["code"]) not in GRADE_POINTS]
    scen = {x["grade"]: x for x in uniform_scenarios(semesters, picks)}
    best = scen["A"]["cgpa"]
    if not remaining:
        p = project(semesters, picks)
        return {"grade": None, "best": p["cgpa"], "remaining": 0, "reached": (p["cgpa"] or 0) >= target_cgpa}
    for g in reversed(GRADES):          # F upwards: the first that reaches the target is the lowest that does
        if scen[g]["cgpa"] is not None and scen[g]["cgpa"] >= target_cgpa:
            return {"grade": g, "best": best, "remaining": len(remaining), "reached": True}
    return {"grade": None, "best": best, "remaining": len(remaining), "reached": False}
