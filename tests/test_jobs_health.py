"""Failed checks are counted, not announced one by one; an empty semester is quiet after one notice."""
import pytest

import config
import jobs
import tracker
from lms_scraper import LoginError


@pytest.fixture
def quiet_env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "META_PATH", tmp_path / "meta.json")
    monkeypatch.setattr(tracker, "DB_PATH", tmp_path / "assignments.json")
    monkeypatch.setattr(tracker, "REMINDERS_PATH", tmp_path / "reminders.json")
    monkeypatch.setattr(jobs, "load_env", lambda: {"ENROLLMENT": "01-111111-111", "PASSWORD": "x", "HEADLESS": True})
    monkeypatch.setattr(jobs, "has_credentials", lambda env: True)
    toasts = []
    monkeypatch.setattr(jobs, "send_toast", lambda title, body: toasts.append((title, body)))
    return toasts


def _raise(exc):
    def fn(**kwargs):
        raise exc
    return fn


def test_portal_failures_are_reported_on_the_third_in_a_row(quiet_env, monkeypatch):
    monkeypatch.setattr(jobs, "run_sync", _raise(RuntimeError("portal timed out")))
    codes = [jobs.run_check() for _ in range(7)]
    assert codes == [1] * 7
    assert [t[0] for t in quiet_env] == ["Assignment Monitor: Checks are failing"] * 2      # after 3 and 6
    assert "6 checks in a row" in quiet_env[1][1]
    assert config.load_meta()["fail_streak"] == 7
    assert config.load_meta()["last_failure_kind"] == "sync"


def test_rejected_sign_in_is_reported_once_per_streak(quiet_env, monkeypatch):
    monkeypatch.setattr(jobs, "run_sync", _raise(LoginError("Invalid enrollment or password")))
    assert [jobs.run_check() for _ in range(3)] == [3, 3, 3]
    assert len(quiet_env) == 1 and quiet_env[0][0].endswith("Sign-in failed")


def test_a_successful_sync_resets_the_count(quiet_env, monkeypatch):
    monkeypatch.setattr(jobs, "run_sync", _raise(RuntimeError("down")))
    jobs.run_check()
    jobs.run_check()
    assert config.load_meta()["fail_streak"] == 2
    # the scraper rewrites meta.json on success; here that is stood in for by a fresh file
    config.save_meta({"last_sync": "2026-10-23T19:00:00", "courses": ["A"]})
    assert "fail_streak" not in config.load_meta()


def test_an_empty_semester_is_quiet_after_one_notice(quiet_env, monkeypatch):
    alerted = []
    monkeypatch.setattr(jobs, "alert_assignments", lambda p, e: alerted.append((p, e)))
    env = {"TRACK_ATTENDANCE": False}
    result = {"assignments": [], "courses": [], "semester": "Fall 2026", "errors": {}}
    s1 = jobs.process_sync(result, env, notify=True)
    s2 = jobs.process_sync(result, env, notify=True)
    assert s1["courses"] == 0 and s2["courses"] == 0
    assert alerted == []                                   # no "all caught up" every check
    assert [t[0] for t in quiet_env] == ["Assignment Monitor: No courses yet"]


def test_a_normal_sync_still_alerts(quiet_env, monkeypatch):
    alerted = []
    monkeypatch.setattr(jobs, "alert_assignments", lambda p, e: alerted.append((p, e)))
    jobs.process_sync({"assignments": [], "courses": ["Course A"], "semester": "Fall 2026", "errors": {}}, {}, notify=True)
    assert len(alerted) == 1 and quiet_env == []


def test_returned_work_is_announced(quiet_env, monkeypatch):
    announced = []
    monkeypatch.setattr(jobs, "alert_assignments", lambda p, e: None)
    monkeypatch.setattr(jobs, "alert_assignment_files", lambda posted: announced.append(posted))
    a = {"id": "C#1#T", "course": "C", "title": "T", "due_date": "", "files": {"returned": {"href": "r"}}, "newly_posted": ["returned"]}
    s = jobs.process_sync({"assignments": [a], "courses": ["C"], "semester": "Fall 2026", "errors": {}}, {}, notify=True)
    assert s["posted"] == 1 and announced and announced[0][0][1] == ["returned"]
