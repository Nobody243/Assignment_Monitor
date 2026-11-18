"""
Writes a complete set of FICTIONAL stored data into a folder, in the exact shapes the app stores, with deadlines relative
to today so every state appears (due today, soon, later, overdue, submitted, extended, under the attendance minimum).

Used by CI and by the local audits, so nothing ever depends on a real student's account:

    python tools/seed_demo_data.py <folder>
    ASSIGNMENT_MONITOR_HOME=<folder> python engine.py --dev
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

COURSES = [
    ("HCI 301", "Human Computer Interaction", 3, "Dr. Rivera", "RV"),
    ("DB 310", "Database Systems", 3, "Dr. Okafor", "OK"),
    ("OS 320", "Operating Systems", 3, "Dr. Lindqvist", "LQ"),
    ("SE 330", "Software Engineering", 3, "Dr. Tanaka", "TK"),
    ("DS 240", "Data Structures Lab", 1, "Ms. Haddad", "HD"),
]
CLASS = "BS (SE)-5 (A) Morning"
STUDENT = "Alex Morgan"


def _fmt(d: datetime) -> str:
    return f"{d.day} {d:%B %Y}-{d:%I:%M} {d:%p}".lower().replace("am", "am").replace("pm", "pm")


def _assignment(course: str, no: int, title: str, due: datetime, submitted: bool, *, extended_from: datetime | None = None,
                files: bool = True, marks: str = "Not marked yet") -> dict:
    now = datetime.now()
    exceeded = due < now
    raw = _fmt(due) + (_fmt(extended_from) if extended_from else "")
    return {
        "id": f"{course}#{no}#{title}".replace(" ", "_"), "course": course, "assign_no": str(no), "title": title,
        "due_date": _fmt(due), "raw_deadline": raw, "is_extended": bool(extended_from), "original_due_date": _fmt(extended_from) if extended_from else "",
        "submission_status": "Submission" if submitted else "No Submission",
        "action": "Delete" if submitted and not exceeded else "Deadline Exceeded" if exceeded else "Submit",
        "marks": marks, "status": "Submitted" if submitted else "Missed (Exceeded)" if exceeded else "Pending", "is_submitted": submitted,
        "files": ({"brief": {"href": f"Download.php?k=demo-{no}", "label": "Assignment", "filename": f"{title}.pdf"}} if files else {}),
    }


def build(today: datetime | None = None) -> dict:
    now = today or datetime.now()
    day = lambda n, h=23, m=55: (now + timedelta(days=n)).replace(hour=h, minute=m, second=0, microsecond=0)  # noqa: E731
    a = [
        _assignment("Human Computer Interaction", 3, "Usability test report", day(0, 23, 59), False),
        _assignment("Database Systems", 4, "Normalisation worksheet", day(2), False),
        _assignment("Operating Systems", 2, "Scheduler simulation", day(5), False, extended_from=day(3)),
        _assignment("Software Engineering", 5, "Sprint retrospective", day(14), False),
        _assignment("Database Systems", 3, "ER diagram draft", day(1), True),
        _assignment("Operating Systems", 1, "Lab journal 1", day(-10), True, marks="8 / 10"),
        _assignment("Human Computer Interaction", 2, "Paper prototype", day(-20), True, marks="9 / 10"),
        _assignment("Software Engineering", 4, "Requirements document", day(-6), False),
        _assignment("Data Structures Lab", 6, "Lab 6: balanced trees", day(-3), False, files=False),
        _assignment("Data Structures Lab", 5, "Lab 5: heaps", day(-17), True, marks="Not marked yet"),
    ]
    att = {}
    spec = {"HCI 301": (22, 3), "DB 310": (14, 6), "OS 320": (20, 5), "SE 330": (24, 1.5), "DS 240": (0, 0)}
    for code, title, credit, teacher, _ in COURSES:
        present, absent = spec[code]
        total = present + absent
        sessions = [{"date": (now - timedelta(days=7 * i + 1)).strftime("%A, %d %B %Y"), "type": "Class", "room": f"R-{10 + i}", "remarks": "",
                     "topics": f"Topic {i + 1}", "hours": 1.5, "present": 1.5 if i % 4 else 0.0, "absent": 0.0 if i % 4 else 1.5} for i in range(min(6, int(total // 1.5)))]
        pct = round(present / total * 100, 2) if total else 0.0
        att[code] = {"code": code, "title": title, "credit_hours": str(credit), "class": CLASS, "teacher": teacher, "fee_status": "Paid",
                     "present": float(present), "absent": float(absent), "total": float(total), "percent": pct, "detail_url": "AttendanceSummary.aspx?v=demo",
                     "sessions": sessions, "can_miss": 0.0, "need": 0.0}
    exams = []
    for i, (code, title, *_rest) in enumerate(COURSES):
        d = now + timedelta(days=10 + i * 2) if i < 3 else None
        exams.append({"title": title, "class": CLASS, "date": d.strftime("%d/%m/%Y") if d else "", "session": "Session - I" if d else "", "start_time": "09:00 AM" if d else "",
                      "room": f"HL-{12 + i}" if d else "", "row": str(i + 1) if d else "", "column": str(i + 2) if d else "", "status": "", "fee_defaulter": False,
                      "surveys": "Completed" if i != 1 else "Pending", "exam_type": "Mid-Term", "id": f"Mid-Term#{title.replace(' ', '_')}", "scheduled": bool(d)})
    lectures = []
    for i, (code, title, *_r) in enumerate(COURSES):
        for wk in range(1, 5):
            lectures.append({"id": f"lec{i}{wk}", "course": title, "week": str(wk), "title": f"Week {wk}: {title.split()[0]} concepts",
                             "files": [{"label": "Download Lecture", "href": f"Download.php?k=lec{i}{wk}", "filename": f"week-{wk}.pdf"}], "videos": [], "remarks": "",
                             "first_seen": (now - timedelta(days=(4 - wk) * 6)).isoformat(timespec="seconds")})
    lectures.append({"id": "misc1", "kind": "misc", "course": COURSES[0][1], "week": 0, "title": "Project guidelines", "files": [{"label": "Download Miscellaneous File", "href": "Download.php?k=m1", "filename": "guidelines.pdf"}],
                     "videos": [], "remarks": "", "first_seen": now.isoformat(timespec="seconds")})
    ann = [{"id": f"an{i}", "course": COURSES[i % 3][1], "title": t, "text": txt, "posted": (now - timedelta(days=d)).strftime("%d-%m-%Y %I:%M:%S%p").lower(),
            "posted_at": (now - timedelta(days=d)).isoformat(timespec="seconds"), "first_seen": now.isoformat(timespec="seconds"), "semester": "Fall-2026"}
           for i, (t, txt, d) in enumerate([("Quiz on Monday", "A short quiz covers weeks 1 to 3.", 1), ("Deadline extended", "The scheduler assignment is extended by two days.", 4),
                                              ("Guest lecture", "A guest lecture on usability testing is on Thursday.", 9)])]

    def grade(code, title, cr, g, pts):
        return {"code": code, "title": title, "credits": float(cr), "grade": g, "points": pts, "product": (cr * pts) if pts is not None else None}
    semesters = [
        {"name": "Fall-2025", "courses": [grade("A1", "Programming", 3, "A", 4.0), grade("A2", "Calculus", 3, "B+", 3.33)], "gpa": 3.67, "cgpa": 3.67, "complete": True},
        {"name": "Spring-2026", "courses": [grade("B1", "Networks", 3, "A-", 3.67), grade("B2", "Statistics", 3, "B", 3.0)], "gpa": 3.34, "cgpa": 3.5, "complete": True},
        {"name": "Fall-2026", "courses": [grade(c, t, cr, "", None) for c, t, cr, *_ in COURSES], "gpa": None, "cgpa": None, "complete": False},
    ]
    sessions = []
    for dayname, (start, end, ci) in {"Mon": ("09:00", "10:30", 1), "Tue": ("11:00", "12:30", 2), "Wed": ("09:00", "10:30", 0), "Thu": ("14:00", "15:30", 3), "Fri": ("10:00", "13:00", 4)}.items():
        c = COURSES[ci]
        sessions.append({"day": dayname, "start": start, "end": end, "course": c[1], "abbr": "".join(w[0] for w in c[1].split()), "teacher": c[3], "initials": c[4], "class": CLASS})
    meta = {"enrollment": "01-000000-000", "institute_id": "1", "campus": "Islamabad E-8 Campus", "student_name": STUDENT, "semester": "Fall-2026",
            "courses": [c[1] for c in COURSES], "last_sync": (now - timedelta(minutes=40)).isoformat(timespec="seconds"), "last_result": "demo data"}
    return {"assignments": {x["id"]: x for x in a}, "attendance": att, "exams": exams, "lectures": lectures, "announcements": ann,
            "results": {"student": {}, "semesters": semesters}, "timetable": {"semester": "Fall-2026", "sessions": sessions, "read_at": now.isoformat(timespec="seconds")}, "meta": meta}


def seed(folder: Path, today: datetime | None = None) -> Path:
    """Writes the data files into <folder>/data (the layout the app uses under ASSIGNMENT_MONITOR_HOME)."""
    data = Path(folder) / "data"
    data.mkdir(parents=True, exist_ok=True)
    for name, payload in build(today).items():
        (data / f"{name}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(seed(Path(sys.argv[1])))
