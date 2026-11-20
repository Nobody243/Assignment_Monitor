"""summary.json: everything a phone screen needs, in one small, versioned file.

The phone app reads this file from the student's own private repository (the cloud check, or the desktop app with
"share with my phone", commits it after each check). It is built from the engine's state, so the numbers on the phone
are the numbers on the PC. No passwords, no tokens, no portal links: the phone opens the portal itself when asked.

Times are absolute (ISO 8601, local time of the PC that made the file, no offset): the phone works out the countdown.
"""
from datetime import datetime

SCHEMA_VERSION = 1
MAX_ANNOUNCEMENTS = 10


def _clip(text, n: int) -> str:
    return (text or "").strip()[:n]


def build(state: dict, now: datetime = None) -> dict:
    """The summary for a phone, from the dict `engine.build_state()` returns."""
    now = now or datetime.now()
    meta = state.get("meta") or {}
    att = state.get("attendance") or {}

    assignments = []
    for a in state.get("assignments", []):
        assignments.append({
            "id": a.get("id"), "course": a.get("course"), "title": a.get("title"), "number": a.get("assign_no"),
            "due_at": a.get("due_at"), "extended": bool(a.get("is_extended")), "was_due": a.get("original_due_date") or None,
            "submitted": bool(a.get("is_submitted")), "open": bool(a.get("open")), "urgency": a.get("urgency"),
            "marks": a.get("marks") or None, "can_submit": bool(a.get("can_upload") or a.get("can_replace")),
            "has_brief": bool((a.get("files") or {}).get("brief")),
        })

    attendance = []
    for c in att.get("courses", []):
        attendance.append({
            "code": c.get("code"), "title": c.get("title"), "credit_hours": c.get("credit_hours") or None,
            "teacher": c.get("teacher") or None, "present": c.get("present"), "absent": c.get("absent"),
            "percent": c.get("percent"), "ok": bool(c.get("ok")), "can_miss": c.get("can_miss"), "need": c.get("need"),
            "classes": [{"date": s.get("date"), "hours": s.get("hours"), "present": s.get("present"), "absent": s.get("absent")}
                        for s in (c.get("sessions") or [])][-12:],
        })

    exams = []
    for e in state.get("exams_all") or state.get("exams") or []:
        exams.append({
            "title": e.get("title"), "type": e.get("exam_type") or None, "date": e.get("date") or None,
            "time": e.get("start_time") or None, "room": e.get("room") or None, "row": e.get("row") or None,
            "seat": e.get("column") or None, "scheduled": bool(e.get("scheduled")),
        })

    timetable = [{"day": s.get("day"), "start": s.get("start"), "end": s.get("end"), "course": s.get("course"),
                  "teacher": s.get("teacher") or None}
                 for s in (state.get("timetable") or {}).get("sessions") or []]

    results = None
    if state.get("results"):
        results = {"cgpa": (state.get("standing") or {}).get("cgpa"), "semesters": [
            {"name": s.get("name"), "gpa": s.get("gpa"), "cgpa": s.get("cgpa"), "complete": bool(s.get("complete")),
             "courses": [{"code": c.get("code"), "title": c.get("title"), "credits": c.get("credits"), "grade": c.get("grade") or None}
                         for c in s.get("courses", [])]}
            for s in state["results"].get("semesters", [])]}

    announcements = [{"id": a.get("id"), "course": a.get("course"), "title": _clip(a.get("title"), 120), "text": _clip(a.get("text"), 600),
                      "posted_at": a.get("posted_at") or a.get("first_seen")}
                     for a in (state.get("announcements") or [])[:MAX_ANNOUNCEMENTS]]

    return {
        "schema": SCHEMA_VERSION,
        "generated_at": now.isoformat(timespec="seconds"),
        "app_version": state.get("version"),
        "student": {"name": meta.get("student_name"), "semester": meta.get("semester"), "campus": meta.get("campus")},
        "last_check": meta.get("last_sync"),
        "minimum_attendance": att.get("minimum", 75),
        "assignments": assignments,
        "attendance": attendance,
        "exams": exams,
        "timetable": timetable,
        "results": results,
        "announcements": announcements,
    }
