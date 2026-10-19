import json

import pytest

import tracker


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "assignments.json"
    monkeypatch.setattr(tracker, "DB_PATH", path)
    monkeypatch.setattr(tracker, "META_PATH", tmp_path / "meta.json")
    return path


def item(**overrides):
    base = {"id": "Course#1#Title", "course": "Course", "assign_no": "1", "title": "Title",
            "due_date": "25 October 2026-11:55 pm", "is_submitted": False, "status": "Pending",
            "is_extended": False, "original_due_date": ""}
    base.update(overrides)
    return base


def test_first_sync_stores_items_and_reports_them_new(db):
    pending, extended, new = tracker.compare_assignments([item()])
    assert len(new) == 1 and len(pending) == 1 and extended == []
    stored = json.loads(db.read_text(encoding="utf-8"))
    assert "Course#1#Title" in stored
    assert stored["Course#1#Title"]["first_seen"]


def test_deadline_change_is_reported_as_extension_with_previous_date(db):
    tracker.compare_assignments([item()])
    pending, extended, new = tracker.compare_assignments(
        [item(due_date="28 October 2026-11:55 pm", is_extended=True, original_due_date="25 October 2026-11:55 pm")])
    assert new == []
    assert len(extended) == 1
    assert extended[0]["previous_due_date"] == "25 October 2026-11:55 pm"


def test_extension_on_submitted_work_is_not_alerted(db):
    tracker.compare_assignments([item()])
    pending, extended, _ = tracker.compare_assignments(
        [item(due_date="28 October 2026-11:55 pm", is_submitted=True, status="Submitted")])
    assert pending == [] and extended == []


def test_submitted_items_are_not_pending(db):
    pending, _, _ = tracker.compare_assignments([item(is_submitted=True, status="Submitted")])
    assert pending == []


def test_exceeded_items_are_not_pending(db):
    pending, _, _ = tracker.compare_assignments([item(status="Missed (Exceeded)")])
    assert pending == []


def test_empty_scrape_keeps_existing_data(db):
    tracker.compare_assignments([item()])
    tracker.compare_assignments([])
    assert len(tracker.load_stored_assignments()) == 1


def test_items_missing_from_portal_are_dropped(db):
    tracker.compare_assignments([item(), item(id="Course#2#Other", title="Other")])
    tracker.compare_assignments([item()])
    assert list(tracker.load_stored_assignments()) == ["Course#1#Title"]


def test_corrupt_database_is_treated_as_empty(db):
    db.write_text("{not json", encoding="utf-8")
    assert tracker.load_stored_assignments() == {}


def test_clear_removes_files(db):
    tracker.compare_assignments([item()])
    tracker.clear_stored_assignments()
    assert not db.exists()
