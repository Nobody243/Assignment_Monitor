"""The bookkeeping behind reminders: snooze and "done" from a notification, the queue behind the daily digest, and the
Sunday-evening summary. Everything here is a plain function over the stored data, so it is tested without a screen."""
import logging
from datetime import datetime, timedelta

import config
import tracker
from campus import attendance_margin
from deadlines import deadline_of, is_open_pending

log = logging.getLogger("bahria.reminders")
SNOOZE, ACK = "snooze:", "ack:"
DIGEST_HOUR = 7              # the digest goes out with the first hourly check at or after this hour
SUMMARY_HOUR = 18            # the weekly summary goes out on Sunday from this hour


def _due_stamp(item: dict) -> str:
    due = deadline_of(item)
    return due.isoformat(timespec="minutes") if due else ""


def _store() -> dict:
    return tracker._load_json(tracker.REMINDERS_PATH, {})


def _put(store: dict) -> None:
    tracker._save_json(tracker.REMINDERS_PATH, store)


# ---------------------------------------------------------------------------- snooze and done
def snooze(item_id: str, hours: int = 1, now: datetime = None) -> datetime:
    """Silences reminders for one assignment for a while; when the time is up the hourly job reminds once more."""
    now = now or datetime.now()
    until = now + timedelta(hours=max(1, min(int(hours), 24)))
    store = _store()
    store[SNOOZE + item_id] = until.isoformat(timespec="seconds")
    _put(store)
    return until


def acknowledge(item: dict) -> None:
    """The student says it is handled: no more reminders for this deadline. The portal stays the judge of whether it is
    submitted; a moved deadline starts reminders again."""
    store = _store()
    store[f"{ACK}{item.get('id')}:{_due_stamp(item)}"] = datetime.now().isoformat(timespec="seconds")
    _put(store)


def is_muted(item: dict, now: datetime = None) -> bool:
    now = now or datetime.now()
    store = _store()
    if f"{ACK}{item.get('id')}:{_due_stamp(item)}" in store:
        return True
    until = store.get(SNOOZE + str(item.get("id")))
    try:
        return bool(until) and datetime.fromisoformat(until) > now
    except ValueError:
        return False


def due_snoozes(now: datetime = None) -> list:
    """Item ids whose snooze has run out; they are removed so each wakes exactly once."""
    now = now or datetime.now()
    store = _store()
    woke = []
    for key, until in list(store.items()):
        if not key.startswith(SNOOZE):
            continue
        try:
            over = datetime.fromisoformat(until) <= now
        except ValueError:
            over = True
        if over:
            woke.append(key[len(SNOOZE):])
            del store[key]
    if woke:
        _put(store)
    return woke


# ---------------------------------------------------------------------------- the daily digest queue
def digest_path():
    return config.DATA_DIR / "digest.json"


def queue_digest(title: str, body: str, now: datetime = None) -> None:
    items = tracker._load_json(digest_path(), [])
    items.append({"t": (now or datetime.now()).isoformat(timespec="minutes"), "title": title, "body": body})
    tracker._save_json(digest_path(), items[-200:])


def take_digest() -> list:
    items = tracker._load_json(digest_path(), [])
    if items:
        tracker._save_json(digest_path(), [])
    return items


def digest_text(items: list) -> tuple:
    """(title, body) for one message that carries everything queued since the last digest."""
    n = len(items)
    title = f"Daily digest: {n} update{'s' if n != 1 else ''}"
    lines = []
    for it in items[:25]:
        first = (it.get("body") or "").splitlines()
        lines.append(f"- {it['title']}" + (f" ({first[0]})" if first else ""))
    if n > 25:
        lines.append(f"... and {n - 25} more")
    return title, "\n".join(lines)


# ---------------------------------------------------------------------------- the Sunday summary
def weekly_key(now: datetime) -> str:
    y, w, _ = now.isocalendar()
    return f"weekly:{y}-W{w:02d}"


def weekly_due(now: datetime) -> bool:
    return now.weekday() == 6 and now.hour >= SUMMARY_HOUR and not tracker.reminder_sent(weekly_key(now))


def weekly_summary(assignments: dict, attendance: dict, exams: list, minimum: int, now: datetime = None):
    """(title, body) for the week ahead, or None when there is nothing to say."""
    now = now or datetime.now()
    horizon = now + timedelta(days=8)
    coming = []
    for item in assignments.values():
        due = deadline_of(item)
        if is_open_pending(item) and due and now < due <= horizon:
            coming.append((due, item))
    coming.sort(key=lambda x: x[0])
    risks = []
    for code, c in attendance.items():
        p, a = float(c.get("present") or 0), float(c.get("absent") or 0)
        if p + a <= 0:
            continue
        m = attendance_margin(p, p + a, minimum)
        if not m["ok"]:
            risks.append(f"{c.get('title', code)}: {m['percent']:.0f}%, below {minimum}%")
        elif m["can_miss"] <= 1.5:
            risks.append(f"{c.get('title', code)}: {m['percent']:.0f}%, can miss only {m['can_miss']:g} h")
    papers = [e for e in exams if e.get("when") and now <= e["when"] <= horizon]
    if not (coming or risks or papers):
        return None
    lines = []
    if coming:
        lines.append(f"Due next week ({len(coming)}):")
        lines += [f"- {i['title'][:38]} ({i.get('course', '')[:24]}), {d:%a %d %b %I:%M %p}".replace(" 0", " ") for d, i in coming[:6]]
        if len(coming) > 6:
            lines.append(f"... and {len(coming) - 6} more")
    if papers:
        lines.append(f"Exams ({len(papers)}): " + ", ".join(f"{e['title'][:28]} {e['when']:%a %d %b}" for e in papers[:3]))
    if risks:
        lines.append("Attendance to watch: " + "; ".join(risks[:3]))
    bits = []
    if coming:
        bits.append(f"{len(coming)} due")
    if papers:
        bits.append(f"{len(papers)} exam{'s' if len(papers) != 1 else ''}")
    if risks:
        bits.append(f"{len(risks)} attendance")
    return "Your week ahead: " + ", ".join(bits), "\n".join(lines)
