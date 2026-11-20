"""The support report: what to paste into a bug report, with the personal details taken out.

It carries the app version, Windows version, which features are switched on (yes or no, never a value), counts of
what is stored, and the tail of the app log. Before it leaves the program every line is cleaned: enrollment numbers,
email addresses, the Windows user name in paths, the student's name, tokens and long secret-looking strings."""
import platform
import re
from pathlib import Path

import config
import tracker

_PATTERNS = [
    (re.compile(r"\b\d{2}-\d{6}-\d{3}\b"), "<enrollment>"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<email>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"), "<token>"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "<token>"),
    (re.compile(r"(?i)\b(bearer|token|password|passwd|secret|key)\b(\s*[=:]\s*)\S+"), r"\1\2<hidden>"),
    (re.compile(r"\b[A-Za-z0-9+/_-]{40,}={0,2}"), "<secret>"),
    (re.compile(r"(?i)([A-Z]:\\Users\\)[^\\/]+"), r"\1<user>"),          # a Windows user name may contain a space
    (re.compile(r"(?i)(/Users/|/home/)[^/\s]+"), r"\1<user>"),
]


def redact(text: str, names=()) -> str:
    """The text with personal details replaced by <placeholders>. `names` are extra words to hide (the student's name)."""
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    for name in names:
        for part in {name.strip(), *name.split()}:
            if len(part) >= 3:
                text = re.sub(re.escape(part), "<name>", text, flags=re.IGNORECASE)
    return text


def _tail(path: Path, lines: int) -> list:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()[-lines:]
    except OSError:
        return []


def build_report(log_lines: int = 150) -> str:
    env = config.load_env()
    meta = config.load_meta()
    names = [meta.get("student_name") or ""]
    flags = ["ENABLE_WINDOWS_TOAST", "ENABLE_VOICE", "TRACK_ATTENDANCE", "TRACK_EXAMS", "TRACK_ANNOUNCEMENTS", "TRACK_LECTURES",
             "TRACK_TIMETABLE", "TRACK_RESULTS", "CHECK_UPDATES", "CLOSE_TO_TRAY", "EMAIL_ENABLED", "PUSH_ENABLED", "CALENDAR_ENABLED",
             "CLOUD_ENABLED", "WEEKLY_SUMMARY", "DIGEST_ENABLED"]
    on = ", ".join(f"{k.lower()}={'yes' if env.get(k) else 'no'}" for k in flags)
    counts = {
        "assignments": len(tracker.load_stored_assignments()), "attendance courses": len(tracker.load_attendance()),
        "exams": len(tracker.load_exams()), "announcements": len(tracker.load_announcements()),
        "lecture files": len(tracker.load_lectures()),
    }
    head = [
        f"{config.APP_NAME} {config.APP_VERSION} ({'installed build' if config.FROZEN else 'running from source'})",
        f"Windows: {platform.platform()}",
        f"Python: {platform.python_version()}",
        f"Credentials saved: {'yes' if config.has_credentials(env) else 'no'}; campus id {env.get('INSTITUTE_ID')}",
        f"Last check: {meta.get('last_sync') or 'never'} ({redact(str(meta.get('last_result') or ''), names)})",
        f"Features: {on}",
        "Stored: " + ", ".join(f"{v} {k}" for k, v in counts.items()),
        "",
        f"Last {log_lines} lines of the log:",
    ]
    body = [redact(line, names) for line in _tail(config.LOG_PATH, log_lines)]
    return "\n".join(head + (body or ["(the log is empty)"])) + "\n"
