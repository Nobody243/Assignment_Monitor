"""Deadline parsing and urgency classification shared by the scraper, reminders and the GUI."""
import re
from datetime import datetime
from typing import Optional, Tuple

_SPLIT_RE = re.compile(r"(?<=[ap]m)(?=[0-9])", re.IGNORECASE)
_DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*([ap]m)", re.IGNORECASE)


def parse_deadline(raw_deadline: str) -> Tuple[str, bool, str]:
    """
    Bahria LMS concatenates an extended deadline with the original one, e.g.
    '28 September 2026 - 12:00 am22 September 2026-12:00 am'.
    Returns (active_deadline, is_extended, original_deadline).
    """
    raw = (raw_deadline or "").strip()
    if not raw:
        return "N/A", False, ""
    parts = _SPLIT_RE.split(raw)
    if len(parts) >= 2:
        return parts[0].strip(), True, parts[1].strip()
    return raw, False, ""


def parse_deadline_datetime(raw_str: str) -> Optional[datetime]:
    """Parses '17 October 2026 - 11:30 pm' or '17 October 2026-11:30 pm' into a datetime."""
    if not raw_str:
        return None
    m_date = _DATE_RE.search(raw_str)
    if not m_date:
        return None
    day, month_name, year = int(m_date.group(1)), m_date.group(2), int(m_date.group(3))

    hour, minute = 23, 59
    m_time = _TIME_RE.search(raw_str)
    if m_time:
        h = int(m_time.group(1))
        minute = int(m_time.group(2))
        meridiem = m_time.group(3).lower()
        if meridiem == "pm" and h < 12:
            h += 12
        elif meridiem == "am" and h == 12:
            h = 0
        hour = h
    for fmt, text in (("%d %B %Y %H:%M", f"{day} {month_name} {year} {hour:02d}:{minute:02d}"),
                      ("%d %b %Y %H:%M", f"{day} {month_name[:3]} {year} {hour:02d}:{minute:02d}")):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def deadline_of(item: dict) -> Optional[datetime]:
    return parse_deadline_datetime(item.get("due_date", ""))


def days_until(dt: Optional[datetime], now: Optional[datetime] = None) -> Optional[int]:
    if dt is None:
        return None
    now = now or datetime.now()
    return (dt.date() - now.date()).days


def is_open_pending(item: dict) -> bool:
    """Pending means not submitted and the portal has not marked the deadline as exceeded."""
    return not item.get("is_submitted") and "exceeded" not in (item.get("status") or "").lower()


def classify(item: dict, now: Optional[datetime] = None) -> dict:
    """
    Returns {'key': ..., 'label': ..., 'days': ...} where key is one of
    submitted | missed | today | soon | week | later | unknown.
    """
    now = now or datetime.now()
    dt = deadline_of(item)
    days = days_until(dt, now)
    time_txt = dt.strftime("%I:%M %p").lstrip("0").lower() if dt else ""

    if item.get("is_submitted"):
        return {"key": "submitted", "label": "Submitted", "days": days}
    if "exceeded" in (item.get("status") or "").lower() or (dt and dt < now):
        return {"key": "missed", "label": "Overdue", "days": days}
    if dt is None:
        return {"key": "unknown", "label": "No deadline", "days": None}
    if days == 0:
        return {"key": "today", "label": f"Due today at {time_txt}", "days": 0}
    if days == 1:
        return {"key": "soon", "label": f"Due tomorrow at {time_txt}", "days": 1}
    if days <= 3:
        return {"key": "soon", "label": f"Due in {days} days", "days": days}
    if days <= 7:
        return {"key": "week", "label": f"Due in {days} days", "days": days}
    return {"key": "later", "label": f"Due in {days} days", "days": days}


def sort_key(item: dict):
    """Sorts open work first by nearest deadline, then everything else by latest deadline."""
    dt = deadline_of(item)
    stamp = dt.timestamp() if dt else float("inf")
    if is_open_pending(item):
        return (0, stamp)
    return (1, -stamp if dt else float("inf"))
