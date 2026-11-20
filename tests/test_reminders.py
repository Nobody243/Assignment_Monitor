"""Snooze and Done from a notification, the daily digest, the Sunday summary and the support report's redaction."""
from datetime import datetime, timedelta

import pytest

import config
import jobs
import reminders
import support
import toast_actions
import tracker


def _due(now, hours):
    d = now + timedelta(hours=hours)
    return f"{d.day} {d:%B %Y}-{d:%I:%M} {d:%p}".lower()


def _item(now, hours, id_="a#1#T", **kw):
    base = {"id": id_, "title": "Report", "course": "Databases", "due_date": _due(now, hours), "is_submitted": False,
            "action": "Submit", "status": "Pending", "submission_status": "No Submission", "files": {}}
    base.update(kw)
    return base


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(tracker, "REMINDERS_PATH", tmp_path / "rem.json")
    monkeypatch.setattr(tracker, "DB_PATH", tmp_path / "a.json")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return tmp_path


def test_snooze_mutes_until_the_time_is_up_then_wakes_once(store):
    now = datetime(2026, 11, 20, 12, 0)
    item = _item(now, 5)
    until = reminders.snooze(item["id"], 2, now)
    assert until == now + timedelta(hours=2)
    assert reminders.is_muted(item, now + timedelta(hours=1))
    assert not reminders.is_muted(item, now + timedelta(hours=3))
    assert reminders.due_snoozes(now + timedelta(hours=1)) == []
    assert reminders.due_snoozes(now + timedelta(hours=3)) == [item["id"]]
    assert reminders.due_snoozes(now + timedelta(hours=4)) == []               # woke exactly once


def test_snooze_hours_are_bounded(store):
    now = datetime(2026, 11, 20, 12, 0)
    assert reminders.snooze("x", 0, now) == now + timedelta(hours=1)
    assert reminders.snooze("x", 999, now) == now + timedelta(hours=24)


def test_done_silences_this_deadline_but_a_moved_deadline_reminds_again(store):
    now = datetime(2026, 11, 20, 12, 0)
    item = _item(now, 5)
    reminders.acknowledge(item)
    assert reminders.is_muted(item, now)
    moved = dict(item, due_date=_due(now, 30))
    assert not reminders.is_muted(moved, now)


def test_muted_items_get_no_lead_or_due_today_reminders(store):
    now = datetime(2026, 11, 20, 12, 0)
    item = _item(now, 2.5)
    items = {item["id"]: item}
    assert len(jobs.lead_reminders({"REMIND_LEADS": "24,3,1"}, items, now)) == 1
    reminders.acknowledge(item)
    assert jobs.lead_reminders({"REMIND_LEADS": "24,3,1"}, items, now) == []


def test_button_links_are_checked(store):
    now = datetime(2026, 11, 20, 12, 0)
    item = _item(now, 5, "Course#1#Name with space")
    tracker.save_assignments({item["id"]: item})
    link = toast_actions.SCHEME + "://snooze?id=Course%231%23Name%20with%20space&h=2"
    ok, msg = toast_actions.handle(link)
    assert ok and "Snoozed" in msg
    assert reminders.is_muted(item, datetime.now() + timedelta(minutes=30))
    assert toast_actions.handle("assignment-monitor://done?id=Course%231%23Name%20with%20space")[0]
    for bad in ("http://evil.example/snooze?id=x", "assignment-monitor://format?id=x", "assignment-monitor://snooze?id=nope",
                "not a url", ""):
        assert toast_actions.handle(bad)[0] is False


def test_buttons_exist_only_for_an_installed_program(monkeypatch):
    monkeypatch.setattr(config, "FROZEN", False)
    monkeypatch.delenv("AM_SHELL_EXE", raising=False)
    assert toast_actions.actions_for({"id": "a#1"}) == []
    monkeypatch.setenv("AM_SHELL_EXE", r"C:\Apps\AssignmentMonitor.exe")
    labels = [label for label, _ in toast_actions.actions_for({"id": "a#1"})]
    assert labels == ["Snooze 1 h", "Done"]


def test_the_digest_collects_and_sends_one_message(store, monkeypatch):
    now = datetime(2026, 11, 20, 8, 0)
    reminders.queue_digest("New announcement", "Quiz on Monday", now)
    reminders.queue_digest("Attendance", "Databases absent", now)
    sent = []
    import channels
    monkeypatch.setattr(channels, "send_all", lambda title, body, url=None: sent.append((title, body)))
    assert jobs.run_digest({"DIGEST_ENABLED": True}, datetime(2026, 11, 20, 6, 0)) is False          # too early
    assert jobs.run_digest({"DIGEST_ENABLED": True}, now) is True
    assert sent[0][0] == "Daily digest: 2 updates" and "Quiz on Monday" in sent[0][1]
    reminders.queue_digest("Another", "x", now)
    assert jobs.run_digest({"DIGEST_ENABLED": True}, now) is False                                    # once a day
    assert jobs.run_digest({"DIGEST_ENABLED": False}, now) is True                                    # switched off: sent at once


def test_urgent_alerts_skip_the_digest_queue(store, monkeypatch):
    import notifier
    sent = []
    monkeypatch.setattr(notifier, "load_env", lambda: {"DIGEST_ENABLED": True, "ENABLE_WINDOWS_TOAST": False})
    import channels
    monkeypatch.setattr(channels, "send_all", lambda t, b, url=None: sent.append(t))
    notifier._notify("Routine", "x")
    notifier._notify("Urgent", "y", urgent=True)
    assert sent == ["Urgent"]
    assert [i["title"] for i in tracker._load_json(reminders.digest_path(), [])] == ["Routine"]


def test_the_weekly_summary_says_what_is_coming(store):
    now = datetime(2026, 11, 22, 18, 30)                       # a Sunday evening
    assert reminders.weekly_due(now)
    done = _item(now, 40, "c", title="Done", is_submitted=True, action="Delete", status="Submitted")
    assignments = {"a": _item(now, 30, "a"), "b": _item(now, 200, "b", title="Later"), "c": done}
    attendance = {"DB": {"title": "Databases", "present": 14, "absent": 6},
                  "OS": {"title": "Operating Systems", "present": 24, "absent": 1}}
    exams = [{"title": "Mid-term", "when": now + timedelta(days=3)}]
    title, body = reminders.weekly_summary(assignments, attendance, exams, 75, now)
    assert "1 due" in title and "1 exam" in title and "attendance" in title
    assert "Report" in body and "Later" not in body and "Done" not in body
    assert "Databases: 70%, below 75%" in body
    assert reminders.weekly_summary({}, {}, [], 75, now) is None
    assert not reminders.weekly_due(datetime(2026, 11, 21, 19, 0))                       # Saturday


def test_the_weekly_summary_goes_once_a_week(store, monkeypatch):
    import notifier
    sent = []
    monkeypatch.setattr(notifier, "_notify", lambda t, b, **k: sent.append(t))
    now = datetime(2026, 11, 22, 19, 0)
    tracker.save_assignments({"a": _item(now, 30, "a")})
    assert jobs.run_weekly_summary({"WEEKLY_SUMMARY": True}, now) is True
    assert jobs.run_weekly_summary({"WEEKLY_SUMMARY": True}, now) is False
    assert len(sent) == 1
    assert jobs.run_weekly_summary({"WEEKLY_SUMMARY": False}, datetime(2026, 11, 29, 19, 0)) is False


def test_the_support_report_hides_personal_details():
    text = ("Signed in 01-135232-062 as someone@example.com from C:\\Users\\Muhammad Saad\\AppData\\x, "
            "token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345 and Muhammad Saad opened it; "
            "secret ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop12345 end")
    clean = support.redact(text, names=["Muhammad Saad"])
    for leaked in ("01-135232-062", "someone@example.com", "Muhammad", "ghp_ABCDEF", "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"):
        assert leaked not in clean
    assert "<enrollment>" in clean and "<email>" in clean and "<user>" in clean


def test_the_support_report_builds_without_secrets(store, monkeypatch):
    monkeypatch.setattr(config, "LOG_PATH", store / "app.log")
    (store / "app.log").write_text("2026-11-20 10:00:00  INFO  Check for 01-135232-062 done\n", encoding="utf-8")
    report = support.build_report(20)
    assert report.startswith(config.APP_NAME) and "<enrollment>" in report and "01-135232-062" not in report
    assert "PASSWORD" not in report.upper().replace("CREDENTIALS SAVED", "")
