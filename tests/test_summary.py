"""summary.json: the phone's one file. It must carry what the screens need and nothing private."""
import json

import pytest

import config
import engine
import summary
import tracker
from tools import seed_demo_data


def _state(monkeypatch, tmp_path):
    seed_demo_data.seed(tmp_path)
    for attr, name in [("DB_PATH", "assignments"), ("ATTENDANCE_PATH", "attendance"), ("EXAMS_PATH", "exams"), ("RESULTS_PATH", "results"),
                       ("ANNOUNCEMENTS_PATH", "announcements"), ("LECTURES_PATH", "lectures"), ("TIMETABLE_PATH", "timetable")]:
        monkeypatch.setattr(tracker, attr, tmp_path / "data" / f"{name}.json")
    monkeypatch.setattr(config, "META_PATH", tmp_path / "data" / "meta.json")
    return engine.build_state()


def test_the_summary_has_what_the_phone_screens_need(monkeypatch, tmp_path):
    s = summary.build(_state(monkeypatch, tmp_path))
    assert s["schema"] == summary.SCHEMA_VERSION == 1
    assert len(s["assignments"]) == 10 and len(s["attendance"]) >= 4 and s["timetable"] and s["exams"] and s["results"]["semesters"]
    first = s["assignments"][0]
    assert {"id", "course", "title", "due_at", "urgency", "submitted", "extended", "can_submit"} <= set(first)
    assert s["minimum_attendance"] == 75 and s["student"]["semester"] == "Fall-2026"
    assert any(a["extended"] and a["was_due"] for a in s["assignments"])


def test_the_summary_carries_nothing_private(monkeypatch, tmp_path):
    text = json.dumps(summary.build(_state(monkeypatch, tmp_path)))
    for private in ("password", "PASSWORD", "token", "href", "Download.php", "01-000000-000", "settings.env"):
        assert private not in text


ODD_STATES = [
    {}, None, "text", {"assignments": None}, {"announcements": None}, {"timetable": None}, {"results": {"semesters": None}},
    {"results": {"semesters": [{"courses": None}]}}, {"announcements": [{"title": 123, "text": 456}]},
    {"assignments": [{"files": "x"}]}, {"assignments": [None, 5, {"id": "a"}]},
    {"attendance": {"courses": [{"percent": None, "sessions": None}]}}, {"exams": [{"title": None}], "exams_all": None},
]


@pytest.mark.parametrize("state", ODD_STATES)
def test_the_summary_survives_a_damaged_state(state):
    s = summary.build(state)                      # never raises, and always yields the whole shape
    assert s["schema"] == 1 and isinstance(s["assignments"], list) and isinstance(s["announcements"], list)
    json.dumps(s)                                 # and is serialisable


def test_announcements_are_clipped_and_capped():
    many = [{"id": f"a{i}", "title": "t" * 500, "text": "x" * 5000, "course": "c"} for i in range(50)]
    s = summary.build({"announcements": many})
    assert len(s["announcements"]) == summary.MAX_ANNOUNCEMENTS
    assert len(s["announcements"][0]["title"]) <= 120 and len(s["announcements"][0]["text"]) <= 600


def test_write_summary_is_atomic_and_never_raises(monkeypatch, tmp_path):
    import cloud_check
    import config
    import engine
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(engine, "build_state", lambda: {"assignments": [], "meta": {"student_name": "Alex Morgan"}})
    cloud_check.write_summary()
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["student"]["name"] == "Alex Morgan"
    assert not (tmp_path / "summary.json.tmp").exists()                   # swapped in, nothing left behind
    monkeypatch.setattr(engine, "build_state", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    cloud_check.write_summary()                                           # a failure here is swallowed
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["student"]["name"] == "Alex Morgan"   # old file intact


def test_a_failed_check_does_not_rewrite_the_summary(monkeypatch):
    import cloud_check
    import jobs
    calls = []
    monkeypatch.setattr(jobs, "run_check", lambda headless=True: 3)
    monkeypatch.setattr(cloud_check, "write_summary", lambda: calls.append(1))
    assert cloud_check.main(["cloud_check.py", "check"]) == 3 and not calls
    monkeypatch.setattr(jobs, "run_check", lambda headless=True: 0)
    assert cloud_check.main(["cloud_check.py", "check"]) == 0 and calls == [1]
