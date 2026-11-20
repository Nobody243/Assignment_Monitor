"""Writes the awkward summary.json files the phone app's contract tests read, built by the real `summary.build` so they
follow the real shape: an empty student, and a sparse one with nulls, missing keys and a damaged row here and there.

    python tools/make_mobile_fixtures.py        writes mobile/test/fixtures/summary_empty.json and summary_sparse.json
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import summary  # noqa: E402

OUT = ROOT / "mobile" / "test" / "fixtures"
NOW = datetime(2026, 11, 20, 15, 54, 12)

SPARSE = {
    "meta": {"student_name": "", "semester": None},
    "attendance": {"minimum": None, "courses": [
        {"code": "X1", "title": "Never attended", "percent": None, "present": None, "absent": None, "sessions": None},
        {"title": None, "percent": 50, "present": 1, "absent": 1, "ok": None, "can_miss": None, "need": None, "sessions": [{"date": None}]},
    ]},
    "assignments": [
        {"id": None, "course": None, "title": None, "due_at": None},
        {"id": "a#1#t", "course": "C", "title": "T", "due_at": "not a date", "is_submitted": None, "open": 1},
        {"id": "a#2#t", "course": "C", "title": "Late", "due_at": "2026-11-18T10:00:00", "urgency": "missed", "marks": 7},
    ],
    "exams": [{"title": None}, {"title": "Odd date", "date": "31/02/2026", "scheduled": True}, {"title": "Half", "date": "5/12", "room": 12}],
    "timetable": {"sessions": [{"day": "Mon"}, {"day": "Fun", "start": "9:00", "end": "10:00", "course": "Bad day"},
                               {"day": "Tue", "start": "09:00", "end": "10:30", "course": "Fine", "teacher": None}]},
    "results": {"semesters": [{"name": None, "courses": None}, {"name": "S2", "gpa": "3.5", "courses": [{"code": None, "credits": "3", "grade": 4}]}]},
    "standing": {"cgpa": "n/a"},
    "announcements": [{"title": None, "text": None, "posted_at": "yesterday"}, {"id": 7, "title": 5, "course": None, "text": ["a"]}],
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, state in (("empty", {}), ("sparse", SPARSE)):
        (OUT / f"summary_{name}.json").write_text(json.dumps(summary.build(state, NOW), indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
