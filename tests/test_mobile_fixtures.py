"""The phone app's contract fixtures must be what `summary.build` produces today, so a change to the summary shape
cannot slip past the app's tests (regenerate with `python tools/make_mobile_fixtures.py`)."""
import json

from tools import make_mobile_fixtures as fx


def test_the_phone_fixtures_match_the_builder():
    import summary
    for name, state in (("empty", {}), ("sparse", fx.SPARSE)):
        on_disk = json.loads((fx.OUT / f"summary_{name}.json").read_text(encoding="utf-8"))
        assert on_disk == json.loads(json.dumps(summary.build(state, fx.NOW))), f"summary_{name}.json is out of date"


def test_the_phone_demo_data_has_the_current_schema():
    data = json.loads((fx.ROOT / "mobile" / "assets" / "summary.json").read_text(encoding="utf-8"))
    assert data["schema"] == 1 and {"assignments", "attendance", "exams", "timetable", "results", "announcements"} <= set(data)
