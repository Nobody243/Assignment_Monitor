"""
The app's engine as a small local service: everything the window shows or does, as JSON on 127.0.0.1.

The new interface (ui/) talks to this instead of importing the Python code, so the window can be built with any
toolkit and the portal logic stays in one place, under the same tests. Nothing here is reachable from outside the
PC or from a web page: it binds to the loopback address, answers only to a random token handed to the interface
when it starts, and refuses requests whose Host header is not the loopback address (DNS rebinding).

    python engine.py              # random token and port, printed once as a JSON line on stdout
    python engine.py --dev        # fixed port 8765 and token "dev" for the interface's dev server

Endpoints (all JSON, all need  Authorization: Bearer <token>):
    GET  /api/state                                    stored data, with each assignment's urgency and allowed actions
    GET  /api/jobs/<id>                                progress of a running action
    POST /api/sync                                     one check of everything (a job)
    POST /api/assignments/upload?id=..&replace=0|1     the request body is the file, X-Filename names it (a job)
    POST /api/assignments/delete?id=..                 deletes your submission (a job)
One action runs at a time, as in the window: a second one gets 409.
"""
import argparse
import json
import logging
import os
import secrets
import tempfile
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import lms_scraper as scraper
import tracker
from campus import attendance_margin
from config import APP_NAME, APP_VERSION, load_env, load_meta
from deadlines import classify, deadline_of, is_open_pending
from jobs import collectors_for, process_sync

log = logging.getLogger("engine")

MAX_UPLOAD = 16 * 1024 * 1024          # the portal's limit is 15 MB; a little room for the check to say so itself
DEV_PORT, DEV_TOKEN = 8765, "dev"
DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


# ---------------------------------------------------------------------------- state
def assignment_view(a: dict, now: datetime) -> dict:
    """One assignment as the interface needs it: the stored record plus its urgency and what the portal lets you do."""
    info = classify(a, now)
    due = deadline_of(a)
    can_add, can_replace = scraper.submission_actions(a.get("action"))
    out = dict(a)
    out.update({"urgency": info["key"], "label": info["label"], "days": info["days"],
                "due_at": due.isoformat() if due else None, "open": is_open_pending(a),
                "can_upload": can_add, "can_replace": can_replace})
    return out


def attendance_view(minimum: int) -> dict:
    """Per course: percent, whether it is at or above the minimum, hours that can still be missed or must be attended.
    Plus the overall percent across all courses."""
    courses, present, total = [], 0.0, 0.0
    for code, c in tracker.load_attendance().items():
        p, a = float(c.get("present") or 0), float(c.get("absent") or 0)
        m = attendance_margin(p, p + a, minimum)
        present, total = present + p, total + p + a
        courses.append({"code": code, "title": c.get("title", ""), "credit_hours": c.get("credit_hours", ""),
                        "present": p, "absent": a, "recorded": (p + a) > 0, **m})
    overall = round(100 * present / total, 1) if total else None
    return {"minimum": minimum, "overall": overall, "courses": courses}


def standing(results: dict | None) -> dict | None:
    """The latest finished semester's GPA and the running CGPA, from the Results page data."""
    done = [s for s in (results or {}).get("semesters", []) if s.get("complete") and s.get("cgpa") is not None]
    if not done:
        return None
    last = done[-1]
    return {"semester": last.get("name"), "gpa": last.get("gpa"), "cgpa": last.get("cgpa"), "semesters": len(done)}


def build_state() -> dict:
    now = datetime.now()
    data = tracker.load_stored_assignments()
    minimum = int(load_env().get("ATTENDANCE_MIN", 75))
    return {
        "app": APP_NAME, "version": APP_VERSION, "now": now.isoformat(),
        "meta": load_meta(),
        "assignments": [assignment_view(a, now) for a in data.values()],
        "attendance": attendance_view(minimum),
        "exams": [e for e in tracker.load_exams() if e.get("date")],
        "announcements": tracker.load_announcements(),
        "timetable": tracker.load_timetable(),
        "standing": standing(tracker.load_results()),
    }


# ---------------------------------------------------------------------------- one action at a time
class Jobs:
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs = {}
        self._busy = None

    def start(self, kind: str, fn) -> str | None:
        """Runs fn(progress) in a thread. Returns the job id, or None when another action is running."""
        with self._lock:
            if self._busy:
                return None
            jid = uuid.uuid4().hex[:12]
            self._jobs[jid] = {"id": jid, "kind": kind, "status": "running", "step": "Starting…", "result": None,
                               "started": time.time()}
            self._busy = jid

        def progress(msg):
            self._jobs[jid]["step"] = str(msg)

        def run():
            try:
                result = fn(progress)
            except scraper.LoginError as e:
                result = {"ok": False, "message": str(e)}
            except Exception as e:  # noqa: BLE001 - the interface gets the reason, the log gets the detail
                log.exception("Job %s failed", kind)
                result = {"ok": False, "message": (str(e).splitlines() or ["It did not work."])[0][:200]}
            with self._lock:
                self._jobs[jid].update(status="done", result=result)
                self._busy = None
        threading.Thread(target=run, daemon=True).start()
        return jid

    def get(self, jid: str) -> dict | None:
        return self._jobs.get(jid)


JOBS = Jobs()


def _portal_result(res: dict, record_id: str) -> dict:
    if res.get("row"):
        tracker.update_assignment_row(record_id, res["row"])
    return {"ok": bool(res.get("ok")), "message": res.get("message", ""), "deleted": bool(res.get("deleted"))}


def job_upload(a: dict, path: str, replace: bool):
    def fn(progress):
        try:
            return _portal_result(scraper.submit_assignment(a, path, replace=replace, progress=progress), a["id"])
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    return fn


def job_delete(a: dict):
    return lambda progress: _portal_result(scraper.delete_submission(a, progress=progress), a["id"])


def job_sync():
    def fn(progress):
        env = load_env()
        data = scraper.run_sync(headless=True, collect=collectors_for(env), previous_attendance=tracker.load_attendance(),
                                progress=progress)
        s = process_sync(data, env, notify=True)
        bits = [f"Synced {s['assignments']} assignments · {s['pending']} pending"]
        if data.get("errors"):
            bits.append("some pages could not be read")
        return {"ok": True, "message": " · ".join(bits)}
    return fn


# ---------------------------------------------------------------------------- http
class Handler(BaseHTTPRequestHandler):
    server_version = "AssignmentMonitorEngine"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):          # the app log is enough; no per-request noise on the console
        log.debug("%s " + fmt, self.address_string(), *args)

    # -- plumbing
    def _origin_ok(self) -> str | None:
        origin = self.headers.get("Origin")
        allowed = self.server.allowed_origins
        return origin if origin and origin in allowed else None

    def _send(self, status: int, body: dict | None = None):
        raw = json.dumps(body if body is not None else {}, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        origin = self._origin_ok()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(raw)

    def _guard(self) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        if host not in ("127.0.0.1", "localhost", "::1"):
            self._send(403, {"error": "bad host"})
            return False
        supplied = (self.headers.get("Authorization") or "")
        if not secrets.compare_digest(supplied.encode(), f"Bearer {self.server.token}".encode()):
            self._send(401, {"error": "unauthorized"})
            return False
        return True

    def do_OPTIONS(self):
        origin = self._origin_ok()
        self.send_response(204 if origin else 403)
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Filename")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # -- routes
    def do_GET(self):
        if not self._guard():
            return
        url = urlparse(self.path)
        if url.path == "/api/state":
            return self._send(200, build_state())
        if url.path.startswith("/api/jobs/"):
            job = JOBS.get(url.path.rsplit("/", 1)[-1])
            return self._send(200, job) if job else self._send(404, {"error": "no such job"})
        self._send(404, {"error": "not found"})

    def _record(self, qs: dict) -> dict | None:
        rid = (qs.get("id") or [""])[0]
        return tracker.load_stored_assignments().get(rid)

    def do_POST(self):
        if not self._guard():
            return
        url = urlparse(self.path)
        qs = parse_qs(url.query)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD:
            return self._send(413, {"error": "That file is over the portal's 15 MB limit."})
        body = self.rfile.read(length) if length else b""

        if url.path == "/api/sync":
            jid = JOBS.start("sync", job_sync())
        elif url.path == "/api/assignments/delete":
            a = self._record(qs)
            if not a:
                return self._send(404, {"error": "no such assignment"})
            jid = JOBS.start("delete", job_delete(a))
        elif url.path == "/api/assignments/upload":
            a = self._record(qs)
            if not a:
                return self._send(404, {"error": "no such assignment"})
            name = os.path.basename(self.headers.get("X-Filename") or "upload.pdf")
            reason = scraper.check_submission_file_bytes(name, len(body))
            if reason:
                return self._send(422, {"error": reason})
            fd, path = tempfile.mkstemp(suffix=os.path.splitext(name)[1], prefix=os.path.splitext(name)[0][:40] + "_")
            with os.fdopen(fd, "wb") as fh:
                fh.write(body)
            # the portal sees the name the student chose, not the temp name
            final = os.path.join(os.path.dirname(path), f"{uuid.uuid4().hex[:6]}-{name}")
            os.replace(path, final)
            jid = JOBS.start("upload", job_upload(a, final, (qs.get("replace") or ["0"])[0] == "1"))
            if jid is None:
                os.unlink(final)
        else:
            return self._send(404, {"error": "not found"})
        if jid is None:
            return self._send(409, {"error": "Another action is still running."})
        self._send(202, {"job": jid})


class Engine(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, token: str, allowed_origins=()):
        super().__init__(("127.0.0.1", port), Handler)
        self.token = token
        self.allowed_origins = tuple(allowed_origins)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true", help="fixed port and token for the interface's dev server")
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.dev:
        eng = Engine(DEV_PORT, DEV_TOKEN, DEV_ORIGINS)
    else:
        eng = Engine(args.port, secrets.token_urlsafe(24))
    print(json.dumps({"port": eng.server_address[1], "token": eng.token}), flush=True)
    try:
        eng.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
