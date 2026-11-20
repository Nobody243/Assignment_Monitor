"""The local JSON service the new interface talks to: who may call it, what it returns, how an upload becomes a job,
and that only one action runs at a time. The portal itself is replaced by stubs; the HTTP layer is real."""
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

import config
import engine
import lms_scraper
import tracker

REC = {"id": "SQA#3#Test", "course": "Software Quality Assurance", "assign_no": "3", "title": "Test Plan",
       "raw_deadline": "21 November 2026-11:55 pm", "due_date": "21 November 2026-11:55 pm", "action": "Submit",
       "status": "Pending", "is_submitted": False, "submission_status": "No Submission", "files": {}}
PAST = dict(REC, id="SQA#1#Old", assign_no="1", title="Old one", action="Deadline Exceeded", status="Missed (Exceeded)",
            raw_deadline="5 October 2026-11:55 pm", due_date="5 October 2026-11:55 pm")


@pytest.fixture()
def api(monkeypatch, tmp_path):
    monkeypatch.setattr(tracker, "DB_PATH", tmp_path / "a.json")
    for name in ("ATTENDANCE_PATH", "EXAMS_PATH", "ANNOUNCEMENTS_PATH", "TIMETABLE_PATH", "RESULTS_PATH", "LECTURES_PATH"):
        monkeypatch.setattr(tracker, name, tmp_path / f"{name}.json")
    tracker.save_assignments({REC["id"]: dict(REC), PAST["id"]: dict(PAST)})
    monkeypatch.setattr(engine, "JOBS", engine.Jobs())
    srv = engine.Engine(0, "secret", ("http://localhost:5173",))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def call(method, path, body=None, headers=None, token="secret"):
        h = {"Authorization": f"Bearer {token}"} if token else {}
        h.update(headers or {})
        req = urllib.request.Request(base + path, data=body, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b"{}"), r.headers
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}"), e.headers

    def wait_job(jid, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            st, job, _ = call("GET", f"/api/jobs/{jid}")
            if job["status"] == "done":
                return job
            time.sleep(0.05)
        raise AssertionError("job did not finish")

    yield call, wait_job, base
    srv.shutdown()


def test_every_route_needs_the_token(api):
    call, _w, _b = api
    assert call("GET", "/api/state", token=None)[0] == 401
    assert call("GET", "/api/state", token="wrong")[0] == 401
    assert call("POST", "/api/sync", token=None)[0] == 401
    assert call("GET", "/api/state")[0] == 200


def test_a_foreign_host_header_is_refused(api):
    call, _w, _b = api
    st, body, _h = call("GET", "/api/state", headers={"Host": "evil.example.com"})
    assert st == 403


def test_cors_only_for_the_known_origin(api):
    call, _w, base = api
    ok = urllib.request.Request(base + "/api/state", method="OPTIONS", headers={"Origin": "http://localhost:5173"})
    with urllib.request.urlopen(ok) as r:
        assert r.status == 204 and r.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    bad = urllib.request.Request(base + "/api/state", method="OPTIONS", headers={"Origin": "https://evil.example"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(bad)
    assert e.value.code == 403
    _st, _b, headers = call("GET", "/api/state", headers={"Origin": "https://evil.example"})
    assert headers.get("Access-Control-Allow-Origin") is None


def test_state_has_urgency_and_allowed_actions(api):
    call, _w, _b = api
    st, body, _h = call("GET", "/api/state")
    assert st == 200 and body["version"]
    by = {a["id"]: a for a in body["assignments"]}
    assert by[REC["id"]]["can_upload"] is True and by[REC["id"]]["can_replace"] is False
    assert by[PAST["id"]]["can_upload"] is False and by[PAST["id"]]["urgency"] == "missed"
    assert by[REC["id"]]["due_at"].startswith("2026-11-21")
    assert body["attendance"]["courses"] == [] and body["attendance"]["overall"] is None and body["standing"] is None


def test_attendance_and_standing_are_derived_from_stored_data(api, monkeypatch):
    call, _w, _b = api
    tracker._save_json(tracker.ATTENDANCE_PATH, {"X 1": {"title": "Course X", "credit_hours": "3", "present": 15.0, "absent": 5.0},
                                                 "Y 2": {"title": "Course Y", "credit_hours": "1", "present": 9.0, "absent": 1.0}})
    tracker._save_json(tracker.RESULTS_PATH, {"semesters": [{"name": "Fall-2025", "gpa": 3.0, "cgpa": 3.0, "complete": True},
                                                          {"name": "Spring-2026", "gpa": 3.5, "cgpa": 3.25, "complete": True},
                                                          {"name": "Fall-2026", "gpa": None, "cgpa": None, "complete": False}]})
    _st, body, _h = call("GET", "/api/state")
    att = body["attendance"]
    assert att["overall"] == 80.0 and att["minimum"] == 75
    by = {c["code"]: c for c in att["courses"]}
    assert by["X 1"]["percent"] == 75.0 and by["X 1"]["ok"] is True and by["Y 2"]["percent"] == 90.0
    assert by["X 1"]["recorded"] is True
    assert body["standing"] == {"semester": "Spring-2026", "gpa": 3.5, "cgpa": 3.25, "semesters": 2,
                                "series": [{"name": "Fall-2025", "gpa": 3.0, "cgpa": 3.0},
                                           {"name": "Spring-2026", "gpa": 3.5, "cgpa": 3.25}]}


def test_upload_is_checked_before_it_becomes_a_job(api):
    call, _w, _b = api
    q = "/api/assignments/upload?id=" + REC["id"].replace("#", "%23")
    assert call("POST", q, b"x", {"X-Filename": "virus.exe"})[0] == 422
    assert call("POST", q, b"", {"X-Filename": "a.pdf"})[0] == 422
    assert call("POST", "/api/assignments/upload?id=nope", b"x", {"X-Filename": "a.pdf"})[0] == 404


def test_upload_runs_as_a_job_and_updates_the_record(api, monkeypatch):
    call, wait_job, _b = api
    seen = {}

    def fake_submit(a, path, replace=False, progress=None):
        progress("Uploading…")
        seen.update(path=path, replace=replace, data=open(path, "rb").read(), title=a["title"])
        return {"ok": True, "message": "Uploaded; the portal lists your submission.", "deleted": replace,
                "row": {"action": "Delete", "is_submitted": True, "status": "Submitted", "submission_status": "Submission"}}
    monkeypatch.setattr(lms_scraper, "submit_assignment", fake_submit)
    q = "/api/assignments/upload?replace=1&id=" + REC["id"].replace("#", "%23")
    st, body, _h = call("POST", q, b"%PDF-1.4 data", {"X-Filename": "My Report.pdf"})
    assert st == 202
    job = wait_job(body["job"])
    assert job["result"]["ok"] and job["result"]["deleted"]
    assert seen["replace"] is True and seen["data"] == b"%PDF-1.4 data" and seen["path"].endswith("My Report.pdf")
    stored = tracker.load_stored_assignments()[REC["id"]]
    assert stored["is_submitted"] is True and stored["action"] == "Delete"


def test_only_one_action_at_a_time(api, monkeypatch):
    call, wait_job, _b = api
    gate = threading.Event()

    def slow_delete(a, progress=None):
        gate.wait(5)
        return {"ok": True, "message": "The submission was deleted.", "deleted": True, "row": None}
    monkeypatch.setattr(lms_scraper, "delete_submission", slow_delete)
    q = "/api/assignments/delete?id=" + REC["id"].replace("#", "%23")
    st, first, _h = call("POST", q)
    assert st == 202
    assert call("POST", q)[0] == 409 and call("POST", "/api/sync")[0] == 409
    gate.set()
    assert wait_job(first["job"])["result"]["ok"]
    assert call("POST", q)[0] == 202                       # free again


def test_a_failing_job_reports_instead_of_crashing(api, monkeypatch):
    call, wait_job, _b = api

    def boom(a, progress=None):
        raise RuntimeError("the portal fell over\nstack...")
    monkeypatch.setattr(lms_scraper, "delete_submission", boom)
    st, body, _h = call("POST", "/api/assignments/delete?id=" + REC["id"].replace("#", "%23"))
    job = wait_job(body["job"])
    assert job["result"] == {"ok": False, "message": "the portal fell over"}


def test_state_carries_everything_the_pages_need(api):
    call, _w, _b = api
    tracker._save_json(tracker.LECTURES_PATH, [{"id": "L1", "course": "C", "week": "1", "title": "Intro", "files": []}])
    _st, body, _h = call("GET", "/api/state")
    assert body["lectures"][0]["id"] == "L1" and "exams_all" in body and "results" in body and "paths" in body
    assert set(body["paths"]) == {"lectures", "data"}


def test_attendance_keeps_class_by_class_detail(api):
    call, _w, _b = api
    sessions = [{"date": "Monday, 31 August 2026", "type": "Class", "hours": 1.5, "present": 1.5, "absent": 0.0}]
    tracker._save_json(tracker.ATTENDANCE_PATH, {"X 1": {"title": "Course X", "present": 1.5, "absent": 0.0, "teacher": "T",
                                                         "class": "BS-7", "sessions": sessions}})
    _st, body, _h = call("GET", "/api/state")
    c = body["attendance"]["courses"][0]
    assert c["sessions"] == sessions and c["teacher"] == "T" and c["class"] == "BS-7"


def test_assignment_files_download_as_a_job(api, monkeypatch):
    call, wait_job, _b = api
    rec = dict(REC, files={"brief": {"href": "Download.php?k=1", "label": "Assignment", "filename": "brief.pdf"}})
    tracker.save_assignments({rec["id"]: rec})
    seen = {}

    def fake(selection, dest, progress=None, should_stop=None):
        seen["kinds"] = [k for _a, k in selection]
        progress("x", 1, 1)
        return {"saved": ["a"], "skipped": 0, "failed": []}
    monkeypatch.setattr(lms_scraper, "download_assignment_files", fake)
    q = "/api/assignments/download?kind=all&id=" + rec["id"].replace("#", "%23")
    st, body, _h = call("POST", q)
    assert st == 202
    job = wait_job(body["job"])
    assert job["result"]["ok"] and "1 file saved" in job["result"]["message"] and seen["kinds"] == ["brief"]
    assert call("POST", "/api/assignments/download?kind=solution&id=" + rec["id"].replace("#", "%23"))[0] == 404


def test_lectures_download_needs_a_selection(api, monkeypatch):
    call, wait_job, _b = api
    tracker._save_json(tracker.LECTURES_PATH, [{"id": "L1", "course": "C", "week": "1", "title": "Intro", "files": []}])
    monkeypatch.setattr(lms_scraper, "download_lectures", lambda sel, dest, progress=None, should_stop=None:
                        {"saved": ["a", "b"], "skipped": 1, "failed": []})
    assert call("POST", "/api/lectures/download", b'{"ids": ["nope"]}')[0] == 404
    assert call("POST", "/api/lectures/download", b"not json")[0] == 400
    st, body, _h = call("POST", "/api/lectures/download", b'{"ids": ["L1"]}')
    assert st == 202
    assert wait_job(body["job"])["result"]["message"] == "2 files saved, 1 already there"


def test_open_folder_only_for_known_folders(api, monkeypatch, tmp_path):
    call, _w, _b = api
    opened = []
    monkeypatch.setattr(engine.os, "startfile", lambda p: opened.append(p), raising=False)
    monkeypatch.setitem(engine.OPENABLE, "data", lambda: tmp_path)
    assert call("POST", "/api/open-folder?kind=../../Windows")[0] == 404
    st, body, _h = call("POST", "/api/open-folder?kind=data")
    assert st == 200 and opened == [str(tmp_path)]


def test_the_log_comes_back_parsed_with_tracebacks_attached(api, monkeypatch, tmp_path):
    call, _w, _b = api
    log = tmp_path / "app.log"
    log.write_text("2026-11-18 09:00:01  INFO    Sync started\n2026-11-18 09:00:05  ERROR   Reading assignments failed: Timeout\n"
                   "Call log:\n  - waiting for locator\n2026-11-18 09:01:00  INFO    Hourly check: nothing due today.\n", encoding="utf-8")
    monkeypatch.setattr(engine, "LOG_PATH", log)
    st, body, _h = call("GET", "/api/log?lines=10")
    entries = body["entries"]
    assert st == 200 and [e["level"] for e in entries] == ["INFO", "ERROR", "INFO"]
    assert "Call log:" in entries[1]["text"] and entries[1]["time"] == "2026-11-18 09:00:05"
    assert call("GET", "/api/log?lines=1")[1]["entries"][0]["text"].startswith("Hourly check")


def test_a_missing_log_is_an_empty_list(api, monkeypatch, tmp_path):
    call, _w, _b = api
    monkeypatch.setattr(engine, "LOG_PATH", tmp_path / "nope.log")
    assert call("GET", "/api/log")[1] == {"entries": []}


def test_the_engine_accepts_only_the_shells_origin_and_exits_with_its_parent():
    """The real thing as a subprocess, the way the desktop shell starts it: a random port and token on the first line,
    CORS for the shell's origin and no other, and the process ends by itself when its stdin is closed."""
    import subprocess
    import sys
    from pathlib import Path
    root = Path(engine.__file__).resolve().parent
    proc = subprocess.Popen([sys.executable, str(root / "engine.py"), "--origin", "app://bundle", "--exit-on-stdin-close"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=root)
    try:
        ready = json.loads(proc.stdout.readline())
        assert ready["port"] > 0 and len(ready["token"]) >= 20
        base = f"http://127.0.0.1:{ready['port']}"
        ok = urllib.request.Request(base + "/api/state", method="OPTIONS", headers={"Origin": "app://bundle"})
        with urllib.request.urlopen(ok, timeout=10) as r:
            assert r.status == 204 and r.headers["Access-Control-Allow-Origin"] == "app://bundle"
        bad = urllib.request.Request(base + "/api/state", method="OPTIONS", headers={"Origin": "http://localhost:5173"})
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(bad, timeout=10)
        assert e.value.code == 403
        proc.stdin.close()                                    # the shell closed (or died)
        assert proc.wait(timeout=15) == 0
    finally:
        if proc.poll() is None:
            proc.kill()


def test_a_malformed_origin_is_refused():
    with pytest.raises(SystemExit):
        engine.parse_args(["--origin", "*"])
    with pytest.raises(SystemExit):
        engine.parse_args(["--origin", "not an origin"])
    assert engine.parse_args(["--origin", "app://bundle"]).origin == ["app://bundle"]


def test_responses_carry_security_headers(api):
    call, _w, _b = api
    _st, _body, h = call("GET", "/api/state")
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in h["Content-Security-Policy"]


def test_oversized_and_malformed_requests_are_refused(api):
    call, _w, _b = api
    assert call("POST", "/api/sync", body=b"x" * (engine.MAX_BODY + 1))[0] == 413
    assert call("POST", "/api/sync", headers={"Content-Length": "abc"})[0] == 400


def test_a_very_long_filename_is_cut_before_use(api, monkeypatch):
    call, wait, _b = api
    seen = {}
    monkeypatch.setattr(lms_scraper, "check_submission_file_bytes", lambda name, size: seen.setdefault("name", name) and "stop")
    url = "/api/assignments/upload?id=" + REC["id"].replace("#", "%23")
    st, _body, _h = call("POST", url, body=b"%PDF", headers={"X-Filename": "a" * 900 + ".pdf"})
    assert st == 422 and len(seen["name"]) <= engine.MAX_FILENAME


def test_wrong_keys_are_throttled(api):
    call, _w, _b = api
    for _ in range(engine.FAIL_LIMIT):
        assert call("GET", "/api/state", token="nope")[0] == 401
    assert call("GET", "/api/state", token="nope")[0] == 429
    assert call("GET", "/api/state")[0] == 200          # the real key is never locked out


def test_headless_flags_do_the_job_and_exit(monkeypatch, capsys):
    import cli
    import jobs
    calls = []
    monkeypatch.setattr(jobs, "run_check", lambda quiet=False, headless=None: calls.append(("check", quiet, headless)) or 0)
    monkeypatch.setattr(jobs, "run_reminder", lambda test=False: calls.append(("remind", test)) or 0)
    assert cli.run(engine.parse_args(["--check", "--quiet", "--visible"])) == 0
    assert cli.run(engine.parse_args(["--remind", "--test"])) == 0
    assert calls == [("check", True, False), ("remind", True)]
    assert cli.run(engine.parse_args([])) is None            # no job asked for: run as the service
    assert not cli.wanted(engine.parse_args(["--dev"]))


def test_tasks_and_shortcuts_start_the_shell_when_one_owns_the_engine(monkeypatch):
    monkeypatch.setenv("AM_SHELL_EXE", r"C:\Apps\AssignmentMonitor.exe")
    assert config.app_command("--check") == [r"C:\Apps\AssignmentMonitor.exe", "--check"]


def test_the_timetable_is_saved_as_a_picture(api, monkeypatch, tmp_path):
    monkeypatch.setattr(engine, "documents_dir", lambda: tmp_path / "docs")
    monkeypatch.setitem(engine.OPENABLE, "timetable", lambda: tmp_path / "docs")
    monkeypatch.setattr(tracker, "load_timetable", lambda: {"semester": "Fall/2026", "sessions": [
        {"day": "Mon", "start": "09:00", "end": "10:30", "course": "Database Systems", "abbr": "DS", "teacher": "Dr. A", "initials": "A"}]})
    call, _w, _b = api
    st, body, _h = call("POST", "/api/timetable/save?format=png&theme=dark")
    assert st == 200 and body["file"] == "Timetable Fall-2026.png"
    assert (tmp_path / "docs" / body["file"]).read_bytes()[:4] == b"\x89PNG"
    assert call("POST", "/api/timetable/save?format=exe")[0] == 400
    monkeypatch.setattr(tracker, "load_timetable", lambda: {})
    assert call("POST", "/api/timetable/save?format=pdf")[0] == 409


# ---------------------------------------------------------------------------- lead-time reminders
def _due(hours_from_now, now):
    from datetime import timedelta
    d = now + timedelta(hours=hours_from_now)
    return f"{d.day} {d:%B %Y}-{d:%I:%M} {d:%p}".lower()


def test_remind_leads_parse_and_default():
    assert config.remind_leads("24,3,1") == [24, 3, 1]
    assert config.remind_leads("1, 24;3") == [24, 3, 1]
    assert config.remind_leads("off") == []
    assert config.remind_leads("nonsense") == [24, 3, 1]
    assert config.remind_leads("500,0") == [24, 3, 1]


def test_a_reminder_is_owed_once_per_lead_and_a_smaller_lead_settles_the_larger(monkeypatch, tmp_path):
    from datetime import datetime

    import jobs
    monkeypatch.setattr(tracker, "REMINDERS_PATH", tmp_path / "rem.json")
    monkeypatch.setattr(jobs, "reminder_sent", lambda k: k in sent)
    sent = set()
    now = datetime(2026, 11, 20, 12, 0)
    due = _due(2.5, now)                                    # inside the 3 h lead, long past the 24 h one
    items = {"a": {"id": "a", "title": "T", "course": "C", "due_date": due, "is_submitted": False, "action": "Submit", "status": "Pending"}}
    owed = jobs.lead_reminders({"REMIND_LEADS": "24,3,1"}, items, now)
    assert len(owed) == 1 and owed[0][1] == 3
    assert [k.rsplit(":", 1)[1] for k in owed[0][3]] == ["24", "3"]        # the 24 h mark is settled with it
    sent.update(owed[0][3])
    assert jobs.lead_reminders({"REMIND_LEADS": "24,3,1"}, items, now) == []
    assert jobs.lead_reminders({"REMIND_LEADS": "off"}, items, now) == []


def test_no_reminder_for_submitted_or_past_or_far_off_deadlines():
    from datetime import datetime

    import jobs
    now = datetime(2026, 11, 20, 12, 0)
    base = {"title": "T", "course": "C", "is_submitted": False, "action": "Submit", "status": "Pending"}
    items = {"far": dict(base, id="far", due_date=_due(100, now)), "past": dict(base, id="past", due_date=_due(-2, now)),
            "done": dict(base, id="done", due_date=_due(2, now), is_submitted=True, action="Delete", status="Submitted")}
    assert jobs.lead_reminders({"REMIND_LEADS": "24,3,1"}, items, now) == []


def test_lead_settings_are_validated(monkeypatch):
    import settings_api
    assert settings_api.coerce("remind_leads", "1, 24 ,3") == "24,3,1"
    assert settings_api.coerce("remind_leads", "") == "off"
    for bad in ("0", "9999", "a,b", "1,2,3,4,5,6,7"):
        with pytest.raises(ValueError):
            settings_api.coerce("remind_leads", bad)
