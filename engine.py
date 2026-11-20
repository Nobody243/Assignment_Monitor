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
import re
import secrets
import socket
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import cli
import config
import lms_scraper as scraper
import settings_api
import tracker
from campus import attendance_margin
from config import APP_NAME, APP_VERSION, DATA_DIR, LOG_PATH, lectures_dir, load_env, load_meta
from deadlines import classify, deadline_of, is_open_pending
from jobs import collectors_for, process_sync

log = logging.getLogger("bahria.engine")          # under "bahria" so it lands in the app log the Activity page reads

MAX_BODY = 1024 * 1024                  # every request except an upload is small JSON
MAX_FILENAME = 200
REQUEST_TIMEOUT = 60                   # seconds a client may stall on the socket before it is dropped
FAIL_LIMIT, FAIL_WINDOW = 20, 60.0     # wrong keys allowed per window before the engine answers 429
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
                        "present": p, "absent": a, "recorded": (p + a) > 0, "teacher": c.get("teacher", ""),
                        "class": c.get("class", ""), "sessions": c.get("sessions") or [], **m})
    overall = round(100 * present / total, 1) if total else None
    return {"minimum": minimum, "overall": overall, "courses": courses}


def standing(results: dict | None) -> dict | None:
    """The latest finished semester's GPA and the running CGPA, from the Results page data."""
    done = [s for s in (results or {}).get("semesters", []) if s.get("complete") and s.get("cgpa") is not None]
    if not done:
        return None
    last = done[-1]
    series = [{"name": x.get("name"), "gpa": x.get("gpa"), "cgpa": x.get("cgpa")} for x in done]
    return {"semester": last.get("name"), "gpa": last.get("gpa"), "cgpa": last.get("cgpa"), "semesters": len(done), "series": series}


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
        "exams_all": tracker.load_exams(),
        "announcements": tracker.load_announcements(),
        "lectures": tracker.load_lectures(),
        "timetable": tracker.load_timetable(),
        "results": tracker.load_results(),
        "standing": standing(tracker.load_results()),
        "paths": {"lectures": str(lectures_dir(load_env())), "data": str(DATA_DIR)},
    }


_LOG_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+([A-Z]+)\s+(.*)$")


def log_tail(lines: int = 300) -> list[dict]:
    """The last lines of the app log as {time, level, text}. A line that does not start with a timestamp (a traceback,
    a multi-line message) is attached to the entry before it."""
    try:
        with open(LOG_PATH, encoding="utf-8", errors="replace") as fh:
            raw = fh.readlines()[-max(1, min(lines, 2000)) * 3:]
    except OSError:
        return []
    out: list[dict] = []
    for line in raw:
        line = line.rstrip("\n")
        m = _LOG_LINE.match(line)
        if m:
            out.append({"time": m.group(1), "level": m.group(2), "text": m.group(3)[:600]})
        elif out and line.strip():
            out[-1]["text"] = (out[-1]["text"] + "\n" + line)[:1200]
    return out[-lines:]


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


def _download_result(res: dict, folder) -> dict:
    saved, skipped, failed = len(res["saved"]), res["skipped"], res["failed"]
    bits = [f"{saved} file{'s' if saved != 1 else ''} saved"]
    if skipped:
        bits.append(f"{skipped} already there")
    if failed:
        bits.append(f"{len(failed)} failed: " + "; ".join(f"{n}: {why}" for n, why in failed[:3]))
    return {"ok": not failed, "message": ", ".join(bits), "folder": str(folder)}


def job_download_assignment_files(items: list):
    def fn(progress):
        dest = lectures_dir(load_env())
        res = scraper.download_assignment_files(items, dest, progress=lambda msg, done, total: progress(f"{done}/{total} · {msg}"))
        return _download_result(res, scraper.assignment_folder(dest, items[0][0]) if len({a["id"] for a, _k in items}) == 1 else dest)
    return fn


def job_download_lectures(selection: list):
    def fn(progress):
        dest = lectures_dir(load_env())
        res = scraper.download_lectures(selection, dest, progress=lambda msg, done, total: progress(f"{done}/{total} · {msg}"))
        return _download_result(res, dest)
    return fn


OPENABLE = {"lectures": lambda: lectures_dir(load_env()), "data": lambda: DATA_DIR, "timetable": lambda: documents_dir()}


def documents_dir():
    """Documents / Assignment Monitor: where the timetable picture and the calendar file are written."""
    from pathlib import Path
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents" / config.APP_NAME


def save_timetable_file(fmt: str, theme: str) -> tuple[int, dict]:
    """Draws the timetable the app's own way and saves it as PNG, JPG or PDF into Documents / Assignment Monitor."""
    from timetable_render import save_timetable
    if fmt not in ("png", "jpg", "pdf") or theme not in ("light", "dark"):
        return 400, {"error": "bad format"}
    data = tracker.load_timetable()
    if not data.get("sessions"):
        return 409, {"error": "The timetable has not been read yet."}
    sem = re.sub(r"[^\w .-]", "-", data.get("semester") or "timetable")
    folder = documents_dir()
    path = save_timetable(data, folder / f"Timetable {sem}.{fmt}", theme, student=config.load_meta().get("student_name", ""))
    return 200, {"ok": True, "file": path.name, "folder": str(folder)}


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
    timeout = REQUEST_TIMEOUT
    wbufsize = 64 * 1024            # headers and body leave in one write (small JSON answers; no Nagle / delayed-ACK stall)

    def setup(self):
        super().setup()
        try:
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass

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
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
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
            if self.server.throttled():                # something is guessing: slow it down; the real key is never locked out
                time.sleep(1.0)
                self._send(429, {"error": "too many wrong keys"})
            else:
                self.server.note_failure()
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
        if url.path == "/api/summary":
            import summary
            return self._send(200, summary.build(build_state()))
        if url.path == "/api/support":
            import support
            return self._send(200, {"text": support.build_report()})
        if url.path == "/api/log":
            n = int((parse_qs(url.query).get("lines") or ["300"])[0] or 300)
            return self._send(200, {"entries": log_tail(n)})
        route = settings_api.GET.get(url.path)
        if route:
            status, obj = route(parse_qs(url.query), b"")
            return self._send(status, obj)
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
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0:
            self.close_connection = True
            return self._send(400, {"error": "bad length"})
        uploading = url.path == "/api/assignments/upload"
        if length > (MAX_UPLOAD if uploading else MAX_BODY):
            self.close_connection = True              # the unread body is never consumed
            return self._send(413, {"error": "That file is over the portal's 15 MB limit." if uploading else "Request too large."})
        body = self.rfile.read(length) if length else b""

        entry = settings_api.POST.get(url.path)
        if entry:
            kind, route = entry
            res = route(qs, body)
            if callable(res):
                jid = JOBS.start(kind, res)
                return self._send(202, {"job": jid}) if jid else self._send(409, {"error": "Another action is still running."})
            return self._send(res[0], res[1])
        if url.path == "/api/sync":
            jid = JOBS.start("sync", job_sync())
        elif url.path == "/api/assignments/delete":
            a = self._record(qs)
            if not a:
                return self._send(404, {"error": "no such assignment"})
            jid = JOBS.start("delete", job_delete(a))
        elif url.path == "/api/assignments/download":
            a = self._record(qs)
            if not a:
                return self._send(404, {"error": "no such assignment"})
            kind = (qs.get("kind") or ["all"])[0]
            kinds = [k for k, v in (a.get("files") or {}).items() if isinstance(v, dict) and v.get("href")]
            wanted = kinds if kind == "all" else [k for k in kinds if k == kind]
            if not wanted:
                return self._send(404, {"error": "That file is not available on the portal."})
            jid = JOBS.start("download", job_download_assignment_files([(a, k) for k in wanted]))
        elif url.path == "/api/lectures/download":
            try:
                ids = set(json.loads(body or b"{}").get("ids") or [])
            except ValueError:
                return self._send(400, {"error": "bad request"})
            chosen = [x for x in tracker.load_lectures() if x.get("id") in ids]
            if not chosen:
                return self._send(404, {"error": "nothing selected"})
            jid = JOBS.start("download", job_download_lectures(chosen))
        elif url.path == "/api/timetable/save":
            return self._send(*save_timetable_file((qs.get("format") or ["png"])[0], (qs.get("theme") or ["light"])[0]))
        elif url.path == "/api/open-folder":
            target = OPENABLE.get((qs.get("kind") or [""])[0])
            if not target:
                return self._send(404, {"error": "unknown folder"})
            folder = target()
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))                         # noqa: S606 - a fixed, known folder only
            return self._send(200, {"ok": True, "folder": str(folder)})
        elif url.path == "/api/assignments/upload":
            a = self._record(qs)
            if not a:
                return self._send(404, {"error": "no such assignment"})
            name = os.path.basename((self.headers.get("X-Filename") or "upload.pdf")[:MAX_FILENAME])
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
        self._failures: list[float] = []
        self._fail_lock = threading.Lock()

    def note_failure(self) -> None:
        with self._fail_lock:
            self._failures.append(time.monotonic())

    def throttled(self) -> bool:
        """True while too many wrong keys arrived in the last minute (something is guessing at the engine)."""
        cutoff = time.monotonic() - FAIL_WINDOW
        with self._fail_lock:
            self._failures = [t for t in self._failures if t > cutoff]
            return len(self._failures) >= FAIL_LIMIT


_ORIGIN = re.compile(r"^[a-z][a-z0-9+.\-]*://[^\s/*]+$")


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true", help="fixed port and token for the interface's dev server")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--origin", action="append", default=[], help="a web origin allowed to call the engine (the desktop shell's)")
    cli.add_arguments(ap)
    ap.add_argument("--exit-on-stdin-close", action="store_true", help="exit when the parent closes our stdin (the shell closed or died)")
    args = ap.parse_args(argv)
    for o in args.origin:
        if not _ORIGIN.match(o):
            ap.error(f"not a valid origin: {o}")
    return args


def _watch_stdin(eng: "Engine") -> None:
    """Blocks until the parent process closes the pipe (it closed, or it died), then stops the engine, so the engine
    never outlives the window that owns it."""
    try:
        sys.stdin.buffer.read()
    except Exception:  # noqa: BLE001
        pass
    eng.shutdown()


def main(argv=None):
    args = parse_args(argv)
    config.setup_logging(to_console=args.dev)
    if cli.wanted(args):                       # a scheduled task or a shortcut: do the job and leave, no service
        code = cli.run(args)
        sys.exit(1 if code is None else code)
    origins = tuple(args.origin)
    if args.dev:
        eng = Engine(DEV_PORT, DEV_TOKEN, DEV_ORIGINS + origins)
    else:
        eng = Engine(args.port, secrets.token_urlsafe(24), origins)
    print(json.dumps({"port": eng.server_address[1], "token": eng.token}), flush=True)
    if args.exit_on_stdin_close:
        threading.Thread(target=_watch_stdin, args=(eng,), daemon=True).start()
    try:
        eng.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
