"""summary.json: the phone's one file. It must carry what the screens need and nothing private."""
import json

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
