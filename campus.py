"""Parsers and small calculations for the CMS/LMS pages beyond assignments: attendance, exam seating and
announcements. Pure functions over HTML strings, so they are easy to test without a browser."""
import base64
import hashlib
import re
from urllib.parse import unquote
from datetime import datetime
from typing import List, Optional

from lxml import html

_WS = re.compile(r"\s+")
_PERCENT = re.compile(r"(-?\d+(?:\.\d+)?)\s*%")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _clean(text: str) -> str:
    return _WS.sub(" ", text or "").strip()


def _cells(row) -> List[str]:
    return [_clean(c.text_content()) for c in row.xpath("./td")]


def _num(text: str, default: float = 0.0) -> float:
    m = _NUMBER.search(text or "")
    return float(m.group(0)) if m else default


# ---------------------------------------------------------------------------- attendance
def parse_attendance(page_html: str) -> List[dict]:
    """The CMS 'Attendance' page: one row per registered course with present/absent/total hours and a
    'Detail' link to the per-class breakdown."""
    tree = html.fromstring(page_html)
    out = []
    for row in tree.xpath("//table//tr"):
        cells = _cells(row)
        if len(cells) < 12 or not cells[1] or cells[0] == "#":
            continue
        present_txt = cells[9]
        present = _num(present_txt)
        absent = _num(cells[10])
        total = _num(cells[11])
        m = _PERCENT.search(present_txt)
        percent = float(m.group(1)) if m else (round(present / total * 100, 2) if total else 0.0)
        hrefs = row.xpath(".//a/@href")
        out.append({
            "code": cells[1],
            "title": cells[2],
            "credit_hours": cells[3],
            "class": cells[6],
            "teacher": cells[7].title() if cells[7].isupper() else cells[7],
            "fee_status": cells[8],
            "present": present,
            "absent": absent,
            "total": total,
            "percent": percent,
            "detail_url": hrefs[0] if hrefs else "",
        })
    return out


def parse_attendance_detail(page_html: str) -> dict:
    """The CMS 'Attendance Summary' page for one course: course info plus one row per class held."""
    tree = html.fromstring(page_html)
    info = {}
    for row in tree.xpath("//table[not(contains(@id,'AttendanceDetails'))]//tr"):
        cells = [_clean(c.text_content()) for c in row.xpath("./th|./td")]
        for i in range(0, len(cells) - 1, 2):
            if cells[i]:
                info[cells[i].lower().replace(" ", "_")] = cells[i + 1]
    sessions = []
    for row in tree.xpath("//table[contains(@id,'AttendanceDetails')]//tr"):
        cells = _cells(row)
        if len(cells) < 8 or not cells[0].isdigit():
            continue
        remarks, topics = "", ""
        txt = cells[4]
        m = re.search(r"Remarks:\s*(.*?)\s*Topics Covered:\s*(.*)$", txt, re.I | re.S)
        if m:
            remarks, topics = m.group(1).strip(), m.group(2).strip()
        else:
            topics = txt
        sessions.append({
            "date": cells[1],
            "type": cells[2],
            "room": cells[3],
            "remarks": "" if remarks.upper() == "N/A" else remarks,
            "topics": topics,
            "hours": _num(cells[5]),
            "present": _num(cells[6]),
            "absent": _num(cells[7]),
        })
    return {"title": info.get("title", ""), "teacher": info.get("teacher_name", ""),
            "contact_hours": info.get("contact_hours", ""), "sessions": sessions}


def attendance_margin(present: float, total: float, minimum: float) -> dict:
    """How far a course is from the minimum percentage.
    can_miss: hours that can still be missed while staying at or above the minimum.
    need:     consecutive present hours required to get back to the minimum (0 when already there)."""
    if total <= 0:
        return {"percent": 0.0, "can_miss": 0.0, "need": 0.0, "ok": True}
    pct = present / total * 100
    frac = minimum / 100.0
    if pct >= minimum:
        can_miss = present / frac - total if frac > 0 else float("inf")
        return {"percent": round(pct, 2), "can_miss": max(0.0, round(can_miss, 1)), "need": 0.0, "ok": True}
    need = (frac * total - present) / (1 - frac) if frac < 1 else float("inf")
    return {"percent": round(pct, 2), "can_miss": 0.0, "need": round(need, 1), "ok": False}


def session_date(text: str) -> Optional[datetime]:
    """'Monday, 31 August 2026' -> datetime."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text or "")
    if not m:
        return None
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)[:3] if fmt == '%d %b %Y' else m.group(2)} {m.group(3)}", fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------- exams
def parse_exam_seats(page_html: str, exam_type: str = "") -> List[dict]:
    """The CMS 'Exam Seating Plan' grid for one exam type. Unscheduled courses have an empty date."""
    tree = html.fromstring(page_html)
    out = []
    for row in tree.xpath("//table[contains(@id,'ExamSeats')]//tr"):
        cells = _cells(row)
        if len(cells) < 12 or not cells[0].isdigit():
            continue
        na = lambda v: "" if v.upper() == "N/A" else v  # noqa: E731
        item = {
            "title": cells[1], "class": cells[2], "date": cells[3], "session": cells[4], "start_time": cells[5],
            "room": na(cells[6]), "row": na(cells[7]), "column": na(cells[8]), "status": na(cells[9]),
            "fee_defaulter": cells[10].lower().startswith("y"), "surveys": cells[11], "exam_type": exam_type,
        }
        item["id"] = f"{exam_type}#{item['title']}".replace(" ", "_")
        item["scheduled"] = bool(item["date"])
        out.append(item)
    return out


def exam_datetime(exam: dict) -> Optional[datetime]:
    """'26/10/2026' + '09:00 AM' -> datetime (date only when the time is missing)."""
    d = (exam.get("date") or "").strip()
    if not d:
        return None
    t = (exam.get("start_time") or "").strip()
    for fmt in ("%d/%m/%Y %I:%M %p", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(f"{d} {t}".strip() if "%I" in fmt or "%H" in fmt else d, fmt)
        except ValueError:
            continue
    return None


def upcoming_exams(exams: List[dict], now: Optional[datetime] = None) -> List[dict]:
    """Scheduled exams from today onwards, soonest first, each with 'when' and 'days' attached."""
    now = now or datetime.now()
    out = []
    for e in exams:
        dt = exam_datetime(e)
        if not dt:
            continue
        if dt.date() < now.date():
            continue
        item = dict(e)
        item["when"] = dt
        item["days"] = (dt.date() - now.date()).days
        out.append(item)
    out.sort(key=lambda x: x["when"])
    return out


def seat_text(exam: dict) -> str:
    bits = []
    if exam.get("room"):
        bits.append(f"Room {exam['room']}")
    if exam.get("row") and exam.get("column"):
        bits.append(f"row {exam['row']}, seat {exam['column']}")
    return " · ".join(bits)


# ---------------------------------------------------------------------------- announcements
def parse_announcements(page_html: str, course: str) -> List[dict]:
    """The LMS 'Announcements' table for one course."""
    tree = html.fromstring(page_html)
    out = []
    for row in tree.xpath("//table//tr"):
        cells = _cells(row)
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        title, text, posted = cells[1], cells[2], cells[3]
        if not text and not title:
            continue
        key = hashlib.sha1(f"{course}|{title}|{text}|{posted}".encode("utf-8")).hexdigest()[:12]
        out.append({"id": key, "course": course, "title": title, "text": text, "posted": posted,
                    "posted_at": _posted_iso(posted)})
    return out


def _posted_iso(text: str) -> str:
    """'28-09-2026 11:27:40am' -> ISO string, or '' when unparseable."""
    t = (text or "").strip().lower().replace("am", " am").replace("pm", " pm")
    for fmt in ("%d-%m-%Y %I:%M:%S %p", "%d-%m-%Y %I:%M %p", "%d-%m-%Y"):
        try:
            return datetime.strptime(_WS.sub(" ", t), fmt).isoformat(timespec="seconds")
        except ValueError:
            continue
    return ""


# ---------------------------------------------------------------------------- lecture notes
_SAFE = re.compile(r"[^A-Za-z0-9 ._()&+-]+")


def safe_name(text: str, limit: int = 80) -> str:
    """A file-system-safe version of a course or lecture title."""
    t = _SAFE.sub(" ", text or "").strip(" .")
    t = _WS.sub(" ", t)
    return (t[:limit].rstrip(" .") or "untitled")


def filename_from_link(href: str) -> str:
    """The LMS download links carry the original file name inside their base64 'k' parameter
    (…,Lec-1-Intro-28092026-012454pm.pptx,…). Returns '' when it cannot be read."""
    m = re.search(r"[?&]k=([^&]+)", href or "")
    if not m:
        return ""
    raw = unquote(m.group(1))
    try:
        padded = raw + "=" * (-len(raw) % 4)
        decoded = base64.b64decode(padded).decode("utf-8", "replace")
    except Exception:
        return ""
    for part in decoded.split(","):
        part = part.strip()
        if re.search(r"\.[A-Za-z0-9]{2,5}$", part) and "/" not in part:
            return safe_name(part, 120)
    return ""


def parse_lectures(page_html: str, course: str) -> List[dict]:
    """The LMS 'Lecture Notes' table for one course: one row per week with its files and video links."""
    tree = html.fromstring(page_html)
    out = []
    for row in tree.xpath("//table//tr"):
        tds = row.xpath("./td")
        cells = [_clean(c.text_content()) for c in tds]
        if len(cells) < 6 or not cells[1]:
            continue
        week, title = cells[0], cells[1]
        files = []
        for i, a in enumerate(tds[2].xpath(".//a[@href]"), start=1):
            href = a.get("href") or ""
            if not href or href.startswith("#"):
                continue
            label = _clean(a.text_content()) or f"File {i}"
            files.append({"label": label, "href": href, "filename": filename_from_link(href) or f"{safe_name(title)} ({i})"})
        videos = [a.get("href") for td in tds[3:5] for a in td.xpath(".//a[@href]") if a.get("href")]
        if not files and not videos:
            continue
        key = hashlib.sha1(f"{course}|{week}|{title}|{len(files)}".encode("utf-8")).hexdigest()[:12]
        out.append({"id": key, "course": course, "week": week, "title": title, "files": files, "videos": videos,
                    "remarks": cells[5] if len(cells) > 5 else ""})
    return out


# ---------------------------------------------------------------------------- timetable
DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_TT_RANGE = re.compile(r"(\d{1,2}:\d{2})\s*([AP]M)\s*-\s*(\d{1,2}:\d{2})\s*([AP]M)", re.I)
_SEMESTER = re.compile(r"^(Spring|Fall|Summer)-\d{4}$")


def _to_24h(hhmm: str, ampm: str) -> str:
    h, m = hhmm.split(":")
    h = int(h) % 12 + (12 if ampm.upper() == "PM" else 0)
    return f"{h:02d}:{m}"


def minutes(hhmm: str) -> int:
    """'13:30' -> 810."""
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def parse_timetable(page_html: str) -> dict:
    """The CMS 'Time Table' page: one row per day; every class is a td.event whose inner div's title attribute holds
    the course, teacher, class, room and the time range, one per line. Returns {"semester", "sessions": [...]} with
    sessions sorted by day then start, times as 24-hour 'HH:MM'."""
    tree = html.fromstring(page_html)
    semester = ""
    for txt in tree.xpath("//text()"):
        t = _clean(txt)
        if _SEMESTER.match(t):
            semester = t
            break
    sessions = []
    for row in tree.xpath("//table[@id='timeTable']//tr"):
        cells = row.xpath("./td|./th")
        if not cells:
            continue
        day = _clean(cells[0].text_content())[:3].title()
        if day not in DAY_ORDER:
            continue
        for td in row.xpath("./td[contains(@class,'event')]"):
            box = td.xpath("./div[@title]")
            title = (box[0].get("title") if box else "") or ""
            lines = [ln.strip() for ln in title.split("\n") if ln.strip()]
            m = _TT_RANGE.search(title)
            if not m:
                continue

            def sub(cls, td=td):
                el = td.xpath(f".//div[contains(@class,'{cls}')]//span")
                return _clean(el[0].text_content()) if el else ""
            teacher = lines[1] if len(lines) > 1 else ""
            sessions.append({
                "day": day,
                "start": _to_24h(m.group(1), m.group(2)),
                "end": _to_24h(m.group(3), m.group(4)),
                "course": lines[0] if lines else sub("title"),
                "abbr": sub("title"),
                "teacher": teacher.title() if teacher.isupper() else teacher,
                "initials": sub("facultyMember"),
                "class": lines[2] if len(lines) > 2 else sub("class"),
                "room": sub("room") or (lines[3] if len(lines) > 3 else ""),
            })
    sessions.sort(key=lambda x: (DAY_ORDER.index(x["day"]), x["start"]))
    # the portal splits one class into back-to-back slots now and then; join them
    merged: List[dict] = []
    for x in sessions:
        last = merged[-1] if merged else None
        if (last and last["day"] == x["day"] and last["course"] == x["course"] and last["room"] == x["room"]
                and last["class"] == x["class"] and last["end"] == x["start"]):
            last["end"] = x["end"]
        else:
            merged.append(dict(x))
    return {"semester": semester, "sessions": merged}


def sessions_on(sessions: List[dict], day: str) -> List[dict]:
    """The classes of one weekday ('Mon'…'Sun'), in order."""
    return [x for x in sessions if x.get("day") == day]


# ---------------------------------------------------------------------------- miscellaneous files
def parse_misc(page_html: str, course: str) -> List[dict]:
    """The LMS 'Miscellaneous' table for one course: one row per file with a type and a remark. Returned in the
    lecture-record shape (one record per file, week 0, title = the type) so the Lectures page and the downloader
    can treat them like lecture notes; 'kind' is 'misc'."""
    tree = html.fromstring(page_html)
    out = []
    for row in tree.xpath("//table//tr"):
        cells = row.xpath("./td")
        if len(cells) < 3 or not _clean(cells[0].text_content()).isdigit():
            continue
        kind = _clean(cells[1].text_content()) or "File"
        remarks = _clean(cells[3].text_content()) if len(cells) > 3 else ""
        files = []
        for a in cells[2].xpath(".//a[@href]"):
            href = a.get("href", "")
            if "Download.php" not in href:
                continue
            name = filename_from_link(href)
            files.append({"label": name or _clean(a.text_content()), "href": href, "filename": name})
        if not files:
            continue
        ident = hashlib.sha1(f"{course}|misc|{kind}|{files[0]['filename'] or files[0]['href']}".encode("utf-8")).hexdigest()[:16]
        out.append({"id": ident, "kind": "misc", "course": course, "week": 0, "title": kind, "files": files,
                    "videos": [], "remarks": remarks})
    return out
