"""What happens when the app itself breaks.

Errors inside the window (a button handler, a view refresh, a worker thread) are logged and shown once in a
dialog: what the browser of errors said, a Copy button, the log file, and a pre-filled GitHub issue. Without this,
an exception inside a Tk callback in the packaged app goes to a stderr that does not exist, and the user sees a
button that does nothing. Background jobs (--check, --remind) only log; nobody is watching them.

The description never carries the user's profile path (it would name the Windows account) and the report carries
only the app version, the Windows version and the error lines; the log file stays on the PC.
"""
import logging
import os
import platform
import sys
import threading
import time
import traceback
from urllib.parse import quote

from config import APP_NAME, APP_VERSION, LOG_PATH, REPO_URL

log = logging.getLogger("bahria.crash")
ISSUES_URL = f"{REPO_URL}/issues/new"
_last = {"sig": None, "at": 0.0}


def describe(exc_type, exc, tb, frames: int = 10) -> str:
    """'Type: message' followed by the innermost frames, file names only, home directory redacted."""
    head = f"{getattr(exc_type, '__name__', 'Error')}: {exc}".strip()
    lines = [head]
    try:
        for fr in traceback.extract_tb(tb)[-frames:]:
            lines.append(f"  at {os.path.basename(fr.filename)}:{fr.lineno} in {fr.name}" + (f"  {fr.line.strip()}" if fr.line else ""))
    except Exception:   # a broken traceback must not break the report
        pass
    text = "\n".join(lines)
    home = os.path.expanduser("~")
    if home and home != "~":
        text = text.replace(home, "~").replace(home.replace("\\", "/"), "~")
    return text


def report_url(details: str, where: str = "") -> str:
    """A GitHub 'new issue' link with the title and body filled in."""
    first = (details.splitlines() or ["error"])[0][:80]
    title = f"Crash: {first}"
    body = (f"**App version:** {APP_VERSION}\n**Windows:** {platform.platform()}\n**Python:** {platform.python_version()}\n"
            + (f"**Where:** {where}\n" if where else "")
            + f"\n```\n{details[:2500]}\n```\n\nWhat I was doing:\n")
    return f"{ISSUES_URL}?title={quote(title)}&body={quote(body)}"


def should_show(details: str, window: float = 60.0) -> bool:
    """One dialog per distinct error per minute; a loop of the same failure must not stack windows."""
    sig = details.splitlines()[0] if details else ""
    now = time.monotonic()
    if sig == _last["sig"] and now - _last["at"] < window:
        return False
    _last.update(sig=sig, at=now)
    return True


def install(app, show) -> None:
    """Routes Tk callback errors, worker-thread errors and anything else uncaught to the log and to `show(details)`
    on the Tk thread."""
    def handle(exc_type, exc, tb, where=""):
        if issubclass(exc_type, KeyboardInterrupt):
            return
        details = describe(exc_type, exc, tb)
        log.error("Unhandled error%s:\n%s", f" in {where}" if where else "", details)
        if not should_show(details):
            return
        try:
            app.after(0, show, details)
        except Exception:
            pass

    app.report_callback_exception = lambda et, e, tb: handle(et, e, tb, "a window callback")
    sys.excepthook = lambda et, e, tb: handle(et, e, tb)
    threading.excepthook = lambda args: handle(args.exc_type, args.exc_value, args.exc_traceback,
                                               f"the {args.thread.name} thread" if args.thread else "a thread")


def last_resort(exc_info) -> None:
    """When the window could not even be built: a plain Windows message box pointing at the log."""
    details = describe(*exc_info)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None, f"{APP_NAME} could not start.\n\n{details[:600]}\n\nThe log is at:\n{LOG_PATH}", APP_NAME, 0x10)
    except Exception:
        pass
