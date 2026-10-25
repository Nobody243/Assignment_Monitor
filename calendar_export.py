"""Deadlines and exams as a calendar: an .ics file kept up to date in Documents, and, when email is linked,
calendar invites mailed for new or changed events so they land in Google Calendar or Outlook on the phone."""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List

from campus import exam_datetime, seat_text
from config import APP_NAME, load_env
from deadlines import deadline_of, is_open_pending

log = logging.getLogger("bahria.calendar")
PRODID = f"-//{APP_NAME}//EN"


def calendar_path() -> Path:
    docs = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents"
    return docs / APP_NAME / f"{APP_NAME}.ics"


def _stamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def _esc(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _uid(kind: str, *parts: str) -> str:
    h = hashlib.sha1("|".join(parts).encode("utf-8"), usedforsecurity=False).hexdigest()[:20]
    return f"am-{kind}-{h}@assignment-monitor"


def events_from(assignments: Iterable[dict], exams: Iterable[dict], now: datetime | None = None) -> List[dict]:
    """Calendar events for open assignments and scheduled exams: {uid, start, end, summary, description, location}."""
    now = now or datetime.now()
    out = []
    for a in assignments:
        due = deadline_of(a)
        if not due or not is_open_pending(a) or due < now - timedelta(days=1):
            continue
        out.append({
            "uid": _uid("asg", a.get("course", ""), a.get("title", "")),
            "start": due - timedelta(minutes=30), "end": due,
            "summary": f"Due: {a.get('title', 'Assignment')} ({a.get('course', '')})",
            "description": "Assignment deadline on the LMS." + (" The date was extended." if a.get("is_extended") else ""),
            "location": "LMS",
            "alarms": ("-P1D", "-PT2H"),
        })
    for e in exams:
        dt = exam_datetime(e)
        if not dt or not e.get("scheduled") or dt < now - timedelta(days=1):
            continue
        out.append({
            "uid": _uid("exam", e.get("course", ""), e.get("date", ""), e.get("type", "")),
            "start": dt, "end": dt + timedelta(hours=3),
            "summary": f"{e.get('type', 'Exam')}: {e.get('course', '')}",
            "description": seat_text(e),
            "location": e.get("room", ""),
            "alarms": ("-P1D", "-PT2H"),
        })
    out.sort(key=lambda x: x["start"])
    return out


def _vevent(ev: dict, now: datetime, organizer: str = "") -> List[str]:
    lines = ["BEGIN:VEVENT", f"UID:{ev['uid']}", f"DTSTAMP:{_stamp(now)}", f"SEQUENCE:{int(ev['start'].timestamp()) % 100000}",
             f"DTSTART:{_stamp(ev['start'])}", f"DTEND:{_stamp(ev['end'])}", f"SUMMARY:{_esc(ev['summary'])}",
             f"DESCRIPTION:{_esc(ev['description'])}"]
    if ev.get("location"):
        lines.append(f"LOCATION:{_esc(ev['location'])}")
    if organizer:
        lines.append(f"ORGANIZER;CN={APP_NAME}:mailto:{organizer}")
        lines.append(f"ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=FALSE:mailto:{organizer}")
    for trigger in ev.get("alarms", ()):
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(ev['summary'])}", f"TRIGGER:{trigger}", "END:VALARM"]
    lines.append("END:VEVENT")
    return lines


def build_ics(events: List[dict], now: datetime | None = None, method: str | None = None, organizer: str = "") -> str:
    now = now or datetime.now()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN",
             f"X-WR-CALNAME:{APP_NAME}"]
    if method:
        lines.append(f"METHOD:{method}")
    for ev in events:
        lines += _vevent(ev, now, organizer)
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def write_calendar(events: List[dict], path: Path | None = None) -> Path:
    path = path or calendar_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_ics(events), encoding="utf-8")
    return path


def sync_calendar(assignments: Iterable[dict], exams: Iterable[dict], env: dict | None = None, send=None,
                  sent_before=None, mark_sent=None) -> dict:
    """Refreshes the .ics file and mails invites for events not sent before. `send(subject, body, ics)` and the
    reminder hooks are injected so this stays testable. Returns {"events": n, "invited": n, "path": str}."""
    env = env or load_env()
    out = {"events": 0, "invited": 0, "path": ""}
    if not env.get("CALENDAR_ENABLED"):
        return out
    events = events_from(assignments, exams)
    out["events"] = len(events)
    try:
        out["path"] = str(write_calendar(events))
    except OSError as e:
        log.warning("Calendar file could not be written: %s", e)
    if env.get("CALENDAR_INVITES") and send and env.get("EMAIL_ENABLED") and env.get("EMAIL_TO"):
        organizer = (env.get("EMAIL_USER") or env.get("EMAIL_TO")).strip()
        for ev in events:
            key = f"cal:{ev['uid']}:{_stamp(ev['start'])}"
            if sent_before and sent_before(key):
                continue
            try:
                moment = ev["end"] if ev["uid"].startswith("am-asg") else ev["start"]
                when = moment.strftime("%a %d %b, %I:%M %p")
                send(f"{ev['summary']} · {when}", f"{ev['summary']}\n{when}\n{ev['description']}",
                     build_ics([ev], method="REQUEST", organizer=organizer))
                out["invited"] += 1
                if mark_sent:
                    mark_sent(key)
            except Exception as e:
                log.warning("Calendar invite failed: %s", str(e)[:200])
                break
    return out
