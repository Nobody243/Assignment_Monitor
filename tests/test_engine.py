"""The local JSON service the new interface talks to: who may call it, what it returns, how an upload becomes a job,
and that only one action runs at a time. The portal itself is replaced by stubs; the HTTP layer is real."""
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

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
    for name in ("ATTENDANCE_PATH", "EXAMS_PATH", "ANNOUNCEMENTS_PATH"):
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
