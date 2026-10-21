from datetime import datetime

import pytest

import tracker


@pytest.fixture
def store(tmp_path, monkeypatch):
    for name in ("DB_PATH", "META_PATH", "ATTENDANCE_PATH", "EXAMS_PATH", "ANNOUNCEMENTS_PATH", "REMINDERS_PATH"):
        monkeypatch.setattr(tracker, name, tmp_path / f"{name.lower()}.json")
    return tmp_path


def course(code="ITC 327", present=11.0, absent=7.0, total=18.0, **kw):
    base = {"code": code, "title": "Database Admin", "present": present, "absent": absent, "total": total, "sessions": []}
    base.update(kw)
    return base


def test_attendance_first_read_reports_below_but_no_new_absence(store):
    out = tracker.compare_attendance([course()], minimum=75)
    assert out["new_absences"] == [] and out["dropped_below"] == []
    assert [c["code"] for c in out["below"]] == ["ITC 327"]
    saved = tracker.load_attendance()["ITC 327"]
    assert saved["percent"] == 61.11 and saved["ok"] is False and saved["need"] == 10.0


def test_attendance_new_absence_and_drop_are_detected(store):
    tracker.compare_attendance([course(present=15, absent=3, total=18)], minimum=75)   # 83%, fine
    out = tracker.compare_attendance([course(present=15, absent=6, total=21)], minimum=75)  # 71%: new absence + dropped
    assert len(out["new_absences"]) == 1 and out["new_absences"][0]["new_absent_hours"] == 3.0
    assert len(out["dropped_below"]) == 1
    again = tracker.compare_attendance([course(present=15, absent=6, total=21)], minimum=75)
    assert again["new_absences"] == [] and again["dropped_below"] == [] and len(again["below"]) == 1


def test_attendance_empty_read_keeps_previous(store):
    tracker.compare_attendance([course()], minimum=75)
    tracker.compare_attendance([], minimum=75)
    assert "ITC 327" in tracker.load_attendance()


def exam(title="SQA", date="26/10/2026", room="HL-18", scheduled=True):
    return {"id": f"Mid-Term#{title}", "title": title, "exam_type": "Mid-Term", "date": date, "start_time": "09:00 AM",
            "session": "I", "room": room, "row": "1", "column": "2", "scheduled": scheduled, "fee_defaulter": False}


def test_exams_newly_scheduled_and_window(store):
    newly = tracker.save_exams([exam(scheduled=False, date="")])
    assert newly == []
    newly = tracker.save_exams([exam()])
    assert [e["title"] for e in newly] == ["SQA"]
    assert tracker.save_exams([exam()]) == []                       # unchanged
    assert [e["title"] for e in tracker.save_exams([exam(room="HL-9")])] == ["SQA"]   # room changed
    soon = tracker.exams_within(1, now=datetime(2026, 10, 25, 19, 0))
    assert len(soon) == 1 and soon[0]["days"] == 1
    assert tracker.exams_within(0, now=datetime(2026, 10, 25, 19, 0)) == []


def ann(i="a1", text="Class cancelled", course="Cyber Security"):
    return {"id": i, "course": course, "title": "All", "text": text, "posted": "28-09-2026 11:27:40am", "posted_at": "2026-09-28T11:27:40"}


def test_announcements_first_read_is_silent_then_new_ones_are_reported(store):
    assert tracker.compare_announcements([ann()]) == []
    assert len(tracker.load_announcements()) == 1
    new = tracker.compare_announcements([ann(), ann("a2", "Quiz on Monday")])
    assert [a["id"] for a in new] == ["a2"]
    assert tracker.compare_announcements([ann(), ann("a2")]) == []
    assert len(tracker.load_announcements()) == 2


def test_reminders_fire_once(store):
    assert not tracker.reminder_sent("exam-day:x")
    tracker.mark_reminder("exam-day:x")
    assert tracker.reminder_sent("exam-day:x")
