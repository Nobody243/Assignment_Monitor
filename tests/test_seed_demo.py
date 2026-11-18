"""The fictional data used by CI and audits must load through the real engine and show every state."""
import importlib

from tools import seed_demo_data


def test_seed_loads_through_engine(tmp_path, monkeypatch):
    seed_demo_data.seed(tmp_path)
    for name in ("assignments", "attendance", "exams", "lectures", "announcements", "results", "timetable", "meta"):
        assert (tmp_path / "data" / f"{name}.json").exists()
    import tracker
    for attr, name in [("DB_PATH", "assignments"), ("ATTENDANCE_PATH", "attendance"), ("EXAMS_PATH", "exams"), ("RESULTS_PATH", "results"),
                       ("ANNOUNCEMENTS_PATH", "announcements"), ("LECTURES_PATH", "lectures"), ("TIMETABLE_PATH", "timetable")]:
        monkeypatch.setattr(tracker, attr, tmp_path / "data" / f"{name}.json")
    engine = importlib.import_module("engine")
    state = engine.build_state()
    assert len(state["assignments"]) == 10
    assert {a["urgency"] for a in state["assignments"]} >= {"today", "soon", "week", "later"}
