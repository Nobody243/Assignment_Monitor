from datetime import datetime

import pytest

from deadlines import classify, days_until, is_open_pending, parse_deadline, parse_deadline_datetime, sort_key

NOW = datetime(2026, 10, 19, 20, 0)


@pytest.mark.parametrize("raw, expected", [
    ("4 October 2026 - 11:50 am13 September 2026-11:55 am",
     ("4 October 2026 - 11:50 am", True, "13 September 2026-11:55 am")),
    ("28 September 2026 - 12:00 am22 September 2026-12:00 am",
     ("28 September 2026 - 12:00 am", True, "22 September 2026-12:00 am")),
    ("19 October 2026-10:30 pm", ("19 October 2026-10:30 pm", False, "")),
    ("", ("N/A", False, "")),
    ("   ", ("N/A", False, "")),
])
def test_parse_deadline_splits_extended_from_original(raw, expected):
    assert parse_deadline(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("19 October 2026-10:30 pm", datetime(2026, 10, 19, 22, 30)),
    ("19 October 2026 - 10:30 am", datetime(2026, 10, 19, 10, 30)),
    ("28 September 2026 - 12:00 am", datetime(2026, 9, 28, 0, 0)),
    ("13 October 2026 - 12:00 pm", datetime(2026, 10, 13, 12, 0)),
    ("5 Nov 2026-11:55 pm", datetime(2026, 11, 5, 23, 55)),
    ("5 November 2026", datetime(2026, 11, 5, 23, 59)),
    ("N/A", None),
    ("", None),
    ("Deadline Exceeded", None),
])
def test_parse_deadline_datetime(raw, expected):
    assert parse_deadline_datetime(raw) == expected


def test_days_until():
    assert days_until(datetime(2026, 10, 22, 1, 0), NOW) == 3
    assert days_until(datetime(2026, 10, 19, 23, 59), NOW) == 0
    assert days_until(None, NOW) is None


@pytest.mark.parametrize("item, key", [
    ({"due_date": "19 October 2026-10:30 pm"}, "today"),
    ({"due_date": "19 October 2026-10:30 am"}, "missed"),
    ({"due_date": "20 October 2026-11:55 pm"}, "soon"),
    ({"due_date": "22 October 2026-11:55 pm"}, "soon"),
    ({"due_date": "25 October 2026-11:55 pm"}, "week"),
    ({"due_date": "5 November 2026-11:55 pm"}, "later"),
    ({"due_date": "4 October 2026 - 11:50 am", "is_submitted": True}, "submitted"),
    ({"due_date": "4 October 2026-11:55 am", "status": "Missed (Exceeded)"}, "missed"),
    ({"due_date": "30 October 2026-11:55 am", "status": "Missed (Exceeded)"}, "missed"),
    ({"due_date": "N/A"}, "unknown"),
])
def test_classify(item, key):
    assert classify(item, NOW)["key"] == key


def test_classify_labels_mention_time_for_today_and_tomorrow():
    assert classify({"due_date": "19 October 2026-10:30 pm"}, NOW)["label"] == "Due today at 10:30 pm"
    assert classify({"due_date": "20 October 2026-08:00 am"}, NOW)["label"] == "Due tomorrow at 8:00 am"


def test_is_open_pending():
    assert is_open_pending({"is_submitted": False, "status": "Pending"})
    assert not is_open_pending({"is_submitted": True, "status": "Submitted"})
    assert not is_open_pending({"is_submitted": False, "status": "Missed (Exceeded)"})


def test_sort_key_puts_open_work_first_by_nearest_deadline():
    items = [
        {"title": "submitted-late", "due_date": "30 October 2026-11:55 pm", "is_submitted": True, "status": "Submitted"},
        {"title": "open-far", "due_date": "28 October 2026-11:55 pm", "is_submitted": False, "status": "Pending"},
        {"title": "open-near", "due_date": "21 October 2026-11:55 pm", "is_submitted": False, "status": "Pending"},
        {"title": "submitted-early", "due_date": "1 October 2026-11:55 pm", "is_submitted": True, "status": "Submitted"},
    ]
    ordered = [i["title"] for i in sorted(items, key=sort_key)]
    assert ordered == ["open-near", "open-far", "submitted-late", "submitted-early"]
