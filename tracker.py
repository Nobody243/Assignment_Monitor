import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from campus import attendance_margin, upcoming_exams
from config import (DB_PATH, META_PATH, ATTENDANCE_PATH, EXAMS_PATH, ANNOUNCEMENTS_PATH, REMINDERS_PATH)
from deadlines import is_open_pending

log = logging.getLogger("bahria.tracker")


# ---------------------------------------------------------------------------- generic JSON files
def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("Could not read %s: %s", path.name, e)
        return default


def _save_json(path: Path, data) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        log.error("Could not save %s: %s", path.name, e)


# ---------------------------------------------------------------------------- assignments
def load_stored_assignments() -> Dict[str, dict]:
    """Loads previously saved assignments from the local JSON database."""
    return _load_json(DB_PATH, {})


def save_assignments(assignments: Dict[str, dict]) -> None:
    _save_json(DB_PATH, assignments)


def clear_stored_assignments() -> None:
    for path in (DB_PATH, META_PATH, ATTENDANCE_PATH, EXAMS_PATH, ANNOUNCEMENTS_PATH, REMINDERS_PATH):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def compare_assignments(current_list: List[dict]) -> Tuple[List[dict], List[dict], List[dict]]:
    """
    Merges a fresh scrape into the database.
    Returns (pending, extended, new_items) where:
      pending  - open assignments with no submission yet
      extended - unsubmitted assignments whose deadline moved since the last sync
                 (or that arrived already extended)
      new_items - assignments seen for the first time
    """
    stored = load_stored_assignments()
    now_iso = datetime.now().isoformat(timespec="seconds")
    pending, extended, new_items = [], [], []
    updated_store: Dict[str, dict] = {}

    for item in current_list:
        key = item.get("id") or f"{item.get('course')}_{item.get('title')}"
        item["last_checked"] = now_iso
        old_item = stored.get(key)

        if old_item is None:
            item["first_seen"] = now_iso
            new_items.append(item)
            deadline_changed = bool(item.get("is_extended"))
        else:
            item["first_seen"] = old_item.get("first_seen", now_iso)
            old_due = old_item.get("due_date", "")
            new_due = item.get("due_date", "")
            deadline_changed = (bool(old_due) and bool(new_due) and old_due != new_due) or \
                               (item.get("is_extended") and not old_item.get("is_extended"))
            if deadline_changed:
                item["previous_due_date"] = old_due or item.get("original_due_date", "")
            elif old_item.get("previous_due_date"):
                item["previous_due_date"] = old_item["previous_due_date"]

        if deadline_changed and not item.get("is_submitted"):
            extended.append(item)
        if is_open_pending(item):
            pending.append(item)
        updated_store[key] = item

    # Assignments that vanished from the portal (e.g. semester rolled over) are dropped
    # only when the scrape returned something; an empty scrape keeps the old data.
    if not current_list:
        updated_store = stored
    save_assignments(updated_store)
    return pending, extended, new_items


# ---------------------------------------------------------------------------- attendance
def load_attendance() -> Dict[str, dict]:
    """{course code: course record with 'sessions'}; see compare_attendance for the fields."""
    return _load_json(ATTENDANCE_PATH, {})


def compare_attendance(current: List[dict], minimum: int = 75) -> dict:
    """
    Merges a fresh attendance read. Returns {
      "new_absences": [course records that gained absent hours, with 'new_absent_hours'],
      "below": [courses under the minimum],
      "dropped_below": [courses that crossed under the minimum since last time],
    }. Each stored record also carries 'percent', 'can_miss', 'need', 'ok' for the configured minimum.
    """
    stored = load_attendance()
    now_iso = datetime.now().isoformat(timespec="seconds")
    out = {"new_absences": [], "below": [], "dropped_below": []}
    updated: Dict[str, dict] = {}
    for c in current:
        code = c.get("code") or c.get("title")
        old = stored.get(code)
        margin = attendance_margin(c.get("present", 0), c.get("total", 0), minimum)
        c.update(margin)
        c["last_checked"] = now_iso
        c["first_seen"] = (old or {}).get("first_seen", now_iso)
        c.setdefault("sessions", (old or {}).get("sessions", []))
        if old is not None:
            gained = float(c.get("absent", 0)) - float(old.get("absent", 0))
            if gained > 0:
                c["new_absent_hours"] = round(gained, 1)
                out["new_absences"].append(c)
            if not c["ok"] and old.get("ok", True):
                out["dropped_below"].append(c)
        if not c["ok"]:
            out["below"].append(c)
        updated[code] = c
    if not current:
        updated = stored
    _save_json(ATTENDANCE_PATH, updated)
    return out


# ---------------------------------------------------------------------------- exams
def load_exams() -> List[dict]:
    return _load_json(EXAMS_PATH, [])


def save_exams(current: List[dict]) -> List[dict]:
    """Stores the seating plan (replacing the previous one when the read returned anything) and returns the
    exams that became scheduled since the last read."""
    stored = {e["id"]: e for e in load_exams()}
    newly_scheduled = []
    for e in current:
        old = stored.get(e["id"])
        if e.get("scheduled") and (old is None or not old.get("scheduled") or old.get("date") != e.get("date")
                                   or old.get("room") != e.get("room")):
            newly_scheduled.append(e)
    if current:
        _save_json(EXAMS_PATH, current)
    return newly_scheduled


def exams_within(days: int, exams: List[dict] = None, now: datetime = None) -> List[dict]:
    """Scheduled exams from today up to and including `days` days ahead."""
    exams = load_exams() if exams is None else exams
    return [e for e in upcoming_exams(exams, now) if e["days"] <= days]


# ---------------------------------------------------------------------------- announcements
def load_announcements() -> List[dict]:
    """Newest first."""
    items = _load_json(ANNOUNCEMENTS_PATH, [])
    return sorted(items, key=lambda a: (a.get("posted_at") or "", a.get("first_seen") or ""), reverse=True)


def compare_announcements(current: List[dict]) -> List[dict]:
    """Merges a fresh read and returns the announcements not seen before. On the very first read nothing is
    reported as new (everything would be), but it is all stored."""
    stored = {a["id"]: a for a in _load_json(ANNOUNCEMENTS_PATH, [])}
    first_read = not ANNOUNCEMENTS_PATH.exists()
    now_iso = datetime.now().isoformat(timespec="seconds")
    new = []
    for a in current:
        if a["id"] in stored:
            a["first_seen"] = stored[a["id"]].get("first_seen", now_iso)
        else:
            a["first_seen"] = now_iso
            if not first_read:
                new.append(a)
        stored[a["id"]] = a
    if current or first_read:
        _save_json(ANNOUNCEMENTS_PATH, list(stored.values()))
    return new


# ---------------------------------------------------------------------------- one-shot reminders
def reminder_sent(key: str) -> bool:
    return key in _load_json(REMINDERS_PATH, {})


def mark_reminder(key: str) -> None:
    sent = _load_json(REMINDERS_PATH, {})
    sent[key] = datetime.now().isoformat(timespec="seconds")
    # keep the file small: drop entries older than 60 days
    cutoff = datetime.now().timestamp() - 60 * 86400
    sent = {k: v for k, v in sent.items() if _ts(v) >= cutoff}
    _save_json(REMINDERS_PATH, sent)


def _ts(iso: str) -> float:
    try:
        return datetime.fromisoformat(iso).timestamp()
    except Exception:
        return 0.0
