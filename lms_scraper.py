import base64
import logging
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin, unquote

from lxml import html
from playwright.sync_api import sync_playwright

from campus import (parse_announcements, parse_attendance, parse_attendance_detail, parse_exam_seats, parse_lectures,
                    parse_misc, parse_timetable, safe_name)
from config import RESULTS_URL
from results import parse_results
from config import (PROFILE_DIR, DATA_DIR, BROWSERS_DIR, LOGIN_URL, SSO_URL, ASSIGNMENTS_URL, ATTENDANCE_URL,
                    EXAMS_URL, ANNOUNCEMENTS_URL, LECTURES_URL, MISC_URL, TIMETABLE_URL, LMS_BASE_URL, load_env, save_meta,
                    campus_name)
from deadlines import parse_deadline

log = logging.getLogger("bahria.scraper")


def mask_enrollment(enrollment: str) -> str:
    """The enrollment number as it may appear in the log: last three characters only. Students paste logs into
    issues, and the log is one Open log button away."""
    e = (enrollment or "").strip()
    return ("•" * max(0, len(e) - 3)) + e[-3:] if len(e) > 3 else "•" * len(e)

LOCK_PATH = DATA_DIR / "sync.lock"
LOCK_STALE_SECONDS = 15 * 60
ALL_COLLECTORS = ("assignments", "attendance", "exams", "results", "announcements", "lectures", "timetable")


class LoginError(RuntimeError):
    """Raised when the portal rejects the credentials."""


def _acquire_lock():
    if LOCK_PATH.exists():
        age = time.time() - LOCK_PATH.stat().st_mtime
        if age < LOCK_STALE_SECONDS:
            raise RuntimeError("Another sync is already running. Please wait for it to finish.")
    LOCK_PATH.write_text(f"{os.getpid()} {datetime.now().isoformat()}", encoding="utf-8")


def _release_lock():
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def _install_chromium() -> bool:
    """Downloads Playwright's Chromium into BROWSERS_DIR (used only when Chrome is missing).
    Works from source and from the packaged exe because it calls the bundled driver directly."""
    try:
        from playwright._impl._driver import compute_driver_executable
        exe = compute_driver_executable()
        cmd = [str(x) for x in (exe if isinstance(exe, (tuple, list)) else [exe])] + ["install", "chromium"]
        log.info("Downloading a browser engine (one time, ~150 MB)...")
        env = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(BROWSERS_DIR))
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800,
                           creationflags=0x08000000)
        if r.returncode != 0:
            log.error("Browser download failed: %s", (r.stderr or r.stdout)[-300:])
            return False
        return True
    except Exception as e:
        log.error("Browser download failed: %s", e)
        return False


def _launch_browser(p, headless: bool):
    kwargs = dict(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        viewport={"width": 1280, "height": 800},
        args=["--disable-blink-features=AutomationControlled"],
    )
    try:
        return p.chromium.launch_persistent_context(channel="chrome", **kwargs)
    except Exception as chrome_err:
        log.warning("Google Chrome could not be started (%s). Trying bundled Chromium...",
                    str(chrome_err).splitlines()[0][:120])

    def bundled():
        # the full Chromium in its new headless mode first (it presents itself like Chrome); the headless shell last
        try:
            return p.chromium.launch_persistent_context(channel="chromium", **kwargs)
        except Exception:
            return p.chromium.launch_persistent_context(**kwargs)
    try:
        return bundled()
    except Exception:
        pass
    if _install_chromium():
        try:
            return bundled()
        except Exception as e:
            log.error("Chromium failed to start after download: %s", str(e).splitlines()[0][:160])
    raise RuntimeError("No browser available. Please install Google Chrome and try again.")


def _login_error_text(page) -> str:
    """The error the portal shows on the sign-in page, visible elements only: the page also carries hidden
    messages (a LinkedIn notice, for one) that have nothing to do with the sign-in."""
    texts = []
    for sel in (".text-danger", ".alert", "[id*='lblMessage']", "[id*='Message']", "[id*='lblError']"):
        try:
            loc = page.locator(sel)
            for i in range(min(loc.count(), 12)):
                el = loc.nth(i)
                if el.is_visible():
                    t = el.inner_text().strip()
                    if t:
                        texts.append(t)
        except Exception:
            pass
    return ", ".join(dict.fromkeys(texts))


def _settle(page, timeout: int = 15000, pause: float = 1.2):
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
    time.sleep(pause)


def _html(page) -> str:
    """The page's HTML, waiting out a navigation that is still in flight. A course change is a form postback and
    page.content() raises "page is navigating and changing the content" if asked a moment too soon; on a slow
    connection the settle pause after the postback is not always enough."""
    for attempt in range(6):
        try:
            return page.content()
        except Exception as e:
            if "navigating" not in str(e) or attempt == 5:
                raise
            try:
                page.wait_for_load_state("load", timeout=15000)
            except Exception:
                pass
            time.sleep(0.5 * (attempt + 1))
    return page.content()


# ---------------------------------------------------------------------------- the portal session
class PortalSession:
    """One signed-in browser for the whole sync: CMS first, then the LMS through single sign-on.
    Collectors call cms(url) / lms(url); the session re-signs in if the portal drops it."""

    def __init__(self, page, enrollment: str, password: str, institute_id: str):
        self.page = page
        self.enrollment = enrollment
        self.password = password
        self.institute_id = institute_id
        self.in_lms = False

    def sign_in(self):
        page = self.page
        log.info("Opening Bahria University CMS portal...")
        page.goto(LOGIN_URL, wait_until="networkidle")
        time.sleep(1.5)
        if page.locator("#BodyPH_tbEnrollment").count() > 0:
            log.info("Signing in as %s (%s)...", mask_enrollment(self.enrollment), campus_name(self.institute_id))
            page.fill("#BodyPH_tbEnrollment", self.enrollment)
            page.fill("#BodyPH_tbPassword", self.password)
            if page.locator("#BodyPH_ddlInstituteID").count() > 0:
                page.select_option("#BodyPH_ddlInstituteID", value=self.institute_id)
            if page.locator("#BodyPH_ddlSubUserType").count() > 0:
                page.select_option("#BodyPH_ddlSubUserType", value="None")
            page.click("#BodyPH_btnLogin")
            # the portal answers with a redirect; on a slower browser (the downloaded engine, a cold start) the
            # page can still be login.aspx for a moment after the click, so wait for it to leave before judging
            try:
                page.wait_for_url(lambda u: "login.aspx" not in u.lower(), timeout=30000)
            except Exception:
                pass
            _settle(page, 15000, 1.0)
        if "login.aspx" in page.url.lower():
            msg = _login_error_text(page) or "the portal rejected the enrollment number, password, or campus"
            raise LoginError(f"Sign-in failed: {msg}")
        self.in_lms = False
        log.info("Signed in to CMS.")

    def cms(self, url: str):
        """Opens a CMS page, signing in again if the session expired."""
        self.page.goto(url, wait_until="networkidle")
        time.sleep(0.8)
        if "login.aspx" in self.page.url.lower():
            log.info("CMS session expired; signing in again.")
            self.sign_in()
            self.page.goto(url, wait_until="networkidle")
            time.sleep(0.8)
            if "login.aspx" in self.page.url.lower():
                raise RuntimeError(f"CMS page could not be opened: {url}")
        return self.page

    def enter_lms(self):
        if self.in_lms:
            return
        log.info("Opening LMS via single sign-on...")
        self.page.goto(SSO_URL, wait_until="networkidle")
        try:
            self.page.wait_for_url(re.compile(r"lms\.bahria\.edu\.pk", re.IGNORECASE), timeout=30000)
        except Exception:
            if "login.aspx" in self.page.url.lower():
                self.sign_in()
                self.page.goto(SSO_URL, wait_until="networkidle")
                self.page.wait_for_url(re.compile(r"lms\.bahria\.edu\.pk", re.IGNORECASE), timeout=30000)
            else:
                raise RuntimeError(f"LMS single sign-on failed; the portal landed on {self.page.url}") from None
        time.sleep(1)
        self.in_lms = True

    def lms(self, url: str):
        self.enter_lms()
        self.page.goto(url, wait_until="networkidle")
        time.sleep(1)
        if "lms.bahria.edu.pk" not in self.page.url.lower():
            self.in_lms = False
            self.enter_lms()
            self.page.goto(url, wait_until="networkidle")
            time.sleep(1)
            if "lms.bahria.edu.pk" not in self.page.url.lower():
                raise RuntimeError(f"LMS session was lost; redirected to {self.page.url}")
        return self.page

    def lms_courses(self) -> List[tuple]:
        """(value, name) of every course in the current page's course selector."""
        page = self.page
        page.wait_for_selector("#courseId option[value]:not([value=''])", state="attached", timeout=20000)
        courses = []
        for opt in page.locator("#courseId option").all():
            val = opt.get_attribute("value")
            text = opt.inner_text().strip()
            if val and text and text != "Select Course":
                courses.append((val, text))
        return courses

    def select_course(self, value: str):
        self.page.select_option("#courseId", value=value)
        _settle(self.page, 15000, 1.5)


# ---------------------------------------------------------------------------- collectors
def _collect_assignments(s: PortalSession, meta: dict) -> List[dict]:
    page = s.lms(ASSIGNMENTS_URL)
    try:
        name = page.locator("a.dropdown-toggle span.hidden-xs").first.inner_text(timeout=5000).strip()
        meta["student_name"] = name.title() if name.isupper() else name
    except Exception:
        pass
    try:
        meta["semester"] = page.evaluate(
            "() => { const s = document.querySelector('#semesterId'); "
            "return s && s.selectedOptions.length ? s.selectedOptions[0].textContent.trim() : ''; }")
    except Exception:
        pass
    courses = s.lms_courses()
    meta["courses"] = [c[1] for c in courses]
    log.info("Found %d enrolled courses for %s.", len(courses), meta["semester"] or "the current semester")
    items: List[dict] = []
    for course_val, course_name in courses:
        log.info("Reading assignments: %s", course_name)
        s.select_course(course_val)
        items.extend(_parse_course_table(_html(page), course_name))
    log.info("Collected %d assignments across %d courses.", len(items), len(courses))
    return items


def _collect_attendance(s: PortalSession, previous: Optional[Dict[str, dict]] = None) -> List[dict]:
    """The attendance table, plus the per-class detail for every course whose hours changed since last time
    (the detail pages are one request each, so unchanged courses reuse what was stored)."""
    previous = previous or {}
    page = s.cms(ATTENDANCE_URL)
    courses = parse_attendance(_html(page))
    log.info("Attendance: %d courses.", len(courses))
    for c in courses:
        old = previous.get(c["code"])
        unchanged = old and old.get("present") == c["present"] and old.get("absent") == c["absent"] and old.get("sessions")
        if unchanged:
            c["sessions"] = old["sessions"]
            continue
        if not c.get("detail_url"):
            c["sessions"] = []
            continue
        try:
            detail = parse_attendance_detail(s.cms(urljoin(ATTENDANCE_URL, c["detail_url"])).content())
            c["sessions"] = detail["sessions"]
            if detail.get("contact_hours"):
                c["contact_hours"] = detail["contact_hours"]
        except Exception as e:
            log.warning("Attendance detail for %s skipped: %s", c["code"], str(e)[:120])
            c["sessions"] = (old or {}).get("sessions", [])
    return courses


def _collect_exams(s: PortalSession) -> List[dict]:
    """Every exam type offered by the seating-plan page (Mid-Term, Final-Term, ...)."""
    page = s.cms(EXAMS_URL)
    out: List[dict] = []
    types = []
    if page.locator("#BodyPH_ddlExamTypeFilter").count():
        for opt in page.locator("#BodyPH_ddlExamTypeFilter option").all():
            val, name = opt.get_attribute("value"), opt.inner_text().strip()
            if val and name:
                types.append((val, name))
    if not types:
        return parse_exam_seats(_html(page), "Exam")
    for i, (val, name) in enumerate(types):
        if i:
            page.select_option("#BodyPH_ddlExamTypeFilter", value=val)
            _settle(page, 15000, 1.5)
        out.extend(parse_exam_seats(_html(page), name))
    log.info("Exams: %d rows across %d exam type(s), %d scheduled.", len(out), len(types), sum(1 for e in out if e["scheduled"]))
    return out


def _collect_results(s: PortalSession) -> dict:
    """The Provisional Result page: every semester's grades with the GPA and CGPA the portal prints."""
    data = parse_results(_html(s.cms(RESULTS_URL)))
    done = [x for x in data["semesters"] if x["complete"]]
    cgpa = done[-1].get("cgpa") if done else None
    log.info("Results: %d semesters, %d graded%s.", len(data["semesters"]), len(done), f", CGPA {cgpa}" if cgpa is not None else "")
    return data


def _collect_lectures(s: PortalSession) -> List[dict]:
    """Lecture notes and the Miscellaneous files of every course, in one list (misc records carry kind='misc')."""
    page = s.lms(LECTURES_URL)
    out: List[dict] = []
    for course_val, course_name in s.lms_courses():
        s.select_course(course_val)
        out.extend(parse_lectures(_html(page), course_name))
    log.info("Lecture notes: %d weeks across all courses.", len(out))
    page = s.lms(MISC_URL)
    n = 0
    for course_val, course_name in s.lms_courses():
        s.select_course(course_val)
        items = parse_misc(_html(page), course_name)
        n += len(items)
        out.extend(items)
    log.info("Miscellaneous files: %d across all courses.", n)
    return out


def _collect_timetable(s: PortalSession) -> dict:
    page = s.cms(TIMETABLE_URL)
    data = parse_timetable(_html(page))
    log.info("Timetable: %d classes a week (%s).", len(data["sessions"]), data.get("semester") or "semester unknown")
    return data


def _collect_announcements(s: PortalSession) -> List[dict]:
    page = s.lms(ANNOUNCEMENTS_URL)
    out: List[dict] = []
    for course_val, course_name in s.lms_courses():
        s.select_course(course_val)
        out.extend(parse_announcements(_html(page), course_name))
    log.info("Announcements: %d across all courses.", len(out))
    return out


# ---------------------------------------------------------------------------- entry points
def run_sync(headless: bool = True, interactive: bool = False, collect=ALL_COLLECTORS,
             previous_attendance: Optional[Dict[str, dict]] = None,
             progress: Optional[Callable[[str], None]] = None) -> dict:
    """
    One signed-in session that reads everything the app tracks:
      assignments (LMS), attendance (CMS), exam seating (CMS), announcements (LMS).
    Returns {"assignments": [...], "attendance": [...], "exams": [...], "announcements": [...], "errors": {...}}.
    A collector that fails leaves its key absent and its error in "errors"; the others still return.
    Also writes data/meta.json with the student name, semester and course list.
    """
    env = load_env()
    enrollment = env.get("ENROLLMENT", "").strip()
    password = env.get("PASSWORD", "").strip()
    institute_id = str(env.get("INSTITUTE_ID", "1")).strip()
    if not enrollment or not password:
        raise LoginError("Enrollment number and password are not configured yet.")
    headless = headless and not interactive
    say = progress or (lambda msg: None)

    _acquire_lock()
    result: dict = {"errors": {}}
    meta = {
        "enrollment": enrollment, "institute_id": institute_id, "campus": campus_name(institute_id),
        "student_name": "", "semester": "", "courses": [], "last_sync": None, "last_result": "",
    }
    try:
        with sync_playwright() as p:
            log.info("Starting browser (%s mode)...", "background" if headless else "visible")
            context = _launch_browser(p, headless)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(45000)
                session = PortalSession(page, enrollment, password, institute_id)
                session.sign_in()

                steps = [
                    ("assignments", "Reading assignments", lambda: _collect_assignments(session, meta)),
                    ("attendance", "Reading attendance", lambda: _collect_attendance(session, previous_attendance)),
                    ("exams", "Reading the exam schedule", lambda: _collect_exams(session)),
                    ("results", "Reading results", lambda: _collect_results(session)),
                    ("announcements", "Reading announcements", lambda: _collect_announcements(session)),
                    ("lectures", "Reading lecture notes", lambda: _collect_lectures(session)),
                    ("timetable", "Reading the timetable", lambda: _collect_timetable(session)),
                ]
                for key, label, fn in steps:
                    if key not in collect:
                        continue
                    say(label + "…")
                    try:
                        result[key] = fn()
                    except LoginError:
                        raise
                    except Exception as e:
                        log.error("%s failed: %s", label, str(e)[:200])
                        result["errors"][key] = str(e)[:200]
                        if key == "assignments":
                            raise

                summary = []
                if "assignments" in result:
                    summary.append(f"{len(result['assignments'])} assignments from {len(meta['courses'])} courses")
                if "attendance" in result:
                    summary.append(f"attendance for {len(result['attendance'])} courses")
                if "exams" in result:
                    summary.append(f"{sum(1 for e in result['exams'] if e['scheduled'])} scheduled exams")
                if "results" in result:
                    graded = [x for x in result["results"]["semesters"] if x["complete"]]
                    summary.append(f"CGPA {graded[-1]['cgpa']}" if graded and graded[-1].get("cgpa") is not None else "no results yet")
                if "announcements" in result:
                    summary.append(f"{len(result['announcements'])} announcements")
                if "lectures" in result:
                    summary.append(f"{len(result['lectures'])} lecture weeks")
                if "timetable" in result:
                    summary.append(f"{len(result['timetable'].get('sessions', []))} classes a week")
                result["semester"] = meta["semester"]
                result["courses"] = list(meta["courses"])
                meta["last_sync"] = datetime.now().isoformat(timespec="seconds")
                meta["last_result"] = ", ".join(summary)
                save_meta(meta)
                return result
            finally:
                context.close()
    finally:
        _release_lock()


def live_file(lec: dict, f: dict, live_items: List[dict]) -> dict:
    """The current listing's entry for a stored file, so the fresh (unexpired) link is used: matched by file name,
    then by link, then by label when it is the only file with that label in the week. Every file in a week usually
    carries the same label ("Download Lecture"), so a label alone is not an identity; matching on it lost every file
    but one when a week had several. Falls back to the stored entry."""
    week_files = [lf for x in live_items if str(x.get("week")) == str(lec.get("week")) and x.get("title") == lec.get("title")
                  for lf in x.get("files", [])]
    name = f.get("filename")
    if name:
        for lf in week_files:
            if lf.get("filename") == name:
                return lf
    if f.get("href"):
        for lf in week_files:
            if lf.get("href") == f["href"]:
                return lf
    same = [lf for lf in week_files if lf.get("label") == f.get("label")]
    if len(same) == 1:
        return same[0]
    return f


def _fetch_file(page, href: str, folder, name: str, result: dict) -> None:
    """Downloads one portal file into folder/name (the portal's own file name lends an extension when the listing
    gave none) and records the outcome in result."""
    url = urljoin(LMS_BASE_URL + "/Student/", href)
    target = folder / name
    try:
        resp = page.request.get(url, timeout=120000)
        ctype = (resp.headers.get("content-type") or "").lower()
        body = resp.body()
        if not resp.ok or ("text/html" in ctype and len(body) < 200000):
            raise RuntimeError(f"portal answered {resp.status} ({ctype.split(';')[0] or 'unknown type'})")
        cd = resp.headers.get("content-disposition") or ""
        m = re.search(r"filename\*?=(?:UTF-8\'\')?\"?([^\";]+)", cd, re.I)
        if m and "." in m.group(1):
            served = safe_name(m.group(1).strip(), 120)
            if "." not in name:
                target = folder / (name + os.path.splitext(served)[1] if name else served)
        folder.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        result["saved"].append(str(target))
        log.info("Downloaded %s (%d KB)", target.name, len(body) // 1024)
    except Exception as e:
        log.warning("Download failed for %s: %s", name, str(e)[:160])
        result["failed"].append((name, str(e)[:120]))


def assignment_folder(dest_dir, a: dict):
    """dest / <course> / Assignments / <NN - title>"""
    from pathlib import Path
    no = str(a.get("assign_no") or "").strip()
    sub = (f"{no.zfill(2)} - " if no.isdigit() else "") + safe_name(a.get("title", "assignment"), 60)
    return Path(dest_dir) / safe_name(a.get("course", "Course")) / "Assignments" / sub


def download_assignment_files(selection: List[tuple], dest_dir, progress: Optional[Callable[[str, int, int], None]] = None,
                              should_stop: Optional[Callable[[], bool]] = None) -> dict:
    """Downloads assignment files. `selection` is a list of (assignment record, kind) with kind one of
    ASSIGNMENT_FILE_KINDS. The links expire daily, so each course's table is re-read in a fresh signed-in session
    and the row is matched by id. Returns {"saved": [paths], "skipped": n, "failed": [(name, reason)]}."""
    env = load_env()
    enrollment, password = env.get("ENROLLMENT", "").strip(), env.get("PASSWORD", "").strip()
    institute_id = str(env.get("INSTITUTE_ID", "1")).strip()
    if not enrollment or not password:
        raise LoginError("Enrollment number and password are not configured yet.")
    say = progress or (lambda msg, done, total: None)
    stop = should_stop or (lambda: False)
    by_course = {}
    for a, kind in selection:
        by_course.setdefault(a["course"], []).append((a, kind))
    total = len(selection)
    result = {"saved": [], "skipped": 0, "failed": []}
    if not total:
        return result
    _acquire_lock()
    try:
        with sync_playwright() as p:
            context = _launch_browser(p, True)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(45000)
                session = PortalSession(page, enrollment, password, institute_id)
                session.sign_in()
                session.lms(ASSIGNMENTS_URL)
                courses = dict((name, val) for val, name in session.lms_courses())
                done = 0
                for course, items in by_course.items():
                    if stop():
                        break
                    val = courses.get(course)
                    if not val:
                        for a, kind in items:
                            result["failed"].append((f"{a['title'][:40]} ({FILE_KIND_LABELS[kind]})", "course is no longer on the LMS"))
                        done += len(items)
                        continue
                    session.select_course(val)
                    fresh = {x["id"]: x for x in _parse_course_table(_html(page), course)}
                    for a, kind in items:
                        if stop():
                            break
                        done += 1
                        live = (fresh.get(a["id"]) or a).get("files", {}).get(kind) or (a.get("files") or {}).get(kind)
                        label = FILE_KIND_LABELS.get(kind, kind)
                        if not live:
                            result["failed"].append((f"{a['title'][:40]} ({label})", "no such file on the portal any more"))
                            continue
                        name = live.get("filename") or f"{safe_name(a['title'], 60)} - {label}"
                        folder = assignment_folder(dest_dir, a)
                        say(f"{course[:30]} · {a['title'][:30]} · {label}", done, total)
                        target = folder / name
                        if target.exists() and target.stat().st_size > 0:
                            result["skipped"] += 1
                            continue
                        _fetch_file(page, live["href"], folder, name, result)
            finally:
                context.close()
    finally:
        _release_lock()
    return result


def download_lectures(selection: List[dict], dest_dir, progress: Optional[Callable[[str, int, int], None]] = None,
                      should_stop: Optional[Callable[[], bool]] = None) -> dict:
    """
    Downloads lecture files into dest_dir/<course>/<Week NN - title>/<file>. `selection` is a list of lecture
    records (as stored) whose files should be fetched; already-present files are skipped. The download links on
    the LMS expire daily, so the course page is re-read in a fresh signed-in session and files are matched by
    week + title + label. Returns {"saved": [paths], "skipped": n, "failed": [(name, reason)]}.
    """
    from pathlib import Path
    env = load_env()
    enrollment, password = env.get("ENROLLMENT", "").strip(), env.get("PASSWORD", "").strip()
    institute_id = str(env.get("INSTITUTE_ID", "1")).strip()
    if not enrollment or not password:
        raise LoginError("Enrollment number and password are not configured yet.")
    say = progress or (lambda msg, done, total: None)
    stop = should_stop or (lambda: False)
    dest = Path(dest_dir)
    wanted = {}
    for lec in selection:
        for f in lec.get("files", []):
            wanted.setdefault((lec["course"], lec.get("kind", "lecture")), []).append((lec, f))
    total = sum(len(v) for v in wanted.values())
    result = {"saved": [], "skipped": 0, "failed": []}
    if not total:
        return result
    _acquire_lock()
    try:
        with sync_playwright() as p:
            context = _launch_browser(p, True)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(45000)
                session = PortalSession(page, enrollment, password, institute_id)
                session.sign_in()
                session.lms(LECTURES_URL)
                courses = dict((name, val) for val, name in session.lms_courses())
                done = 0
                current_kind = "lecture"
                for (course, kind), items in wanted.items():
                    if stop():
                        break
                    if kind != current_kind:
                        session.lms(MISC_URL if kind == "misc" else LECTURES_URL)
                        current_kind = kind
                    val = courses.get(course)
                    if not val:
                        for _lec, f in items:
                            result["failed"].append((f["filename"], "course is no longer on the LMS"))
                        done += len(items)
                        continue
                    session.select_course(val)
                    live_items = parse_misc(_html(page), course) if kind == "misc" else parse_lectures(_html(page), course)
                    for lec, f in items:
                        if stop():
                            break
                        done += 1
                        name = f.get("filename") or safe_name(lec["title"])
                        sub = (f"Miscellaneous - {safe_name(lec['title'], 60)}" if kind == "misc"
                               else f"Week {str(lec['week']).zfill(2)} - {safe_name(lec['title'], 60)}")
                        folder = dest / safe_name(course) / sub
                        target = folder / name
                        say(f"{course[:30]} · week {lec['week']} · {name[:40]}", done, total)
                        if target.exists() and target.stat().st_size > 0:
                            result["skipped"] += 1
                            continue
                        live = live_file(lec, f, live_items)
                        _fetch_file(page, live["href"], folder, name if f.get("filename") else "", result)
            finally:
                context.close()
    finally:
        _release_lock()
    return result


def run_lms_check(headless: bool = True, interactive: bool = False) -> List[dict]:
    """Assignments only (kept for callers that just verify the sign-in)."""
    return run_sync(headless=headless, interactive=interactive, collect=("assignments",))["assignments"]


ASSIGNMENT_FILE_KINDS = ("brief", "submission", "returned", "solution")
FILE_KIND_LABELS = {"brief": "Brief", "submission": "My submission", "returned": "Returned", "solution": "Solution"}


def decode_download_key(href: str) -> dict:
    """The LMS download link carries a base64 key of the form 'id,date,kind,0,filename,page'. Returns
    {"date", "kind", "filename"} or {} when the link is not of that shape."""
    try:
        key = unquote(href.split("k=", 1)[1])
        parts = base64.b64decode(key + "=" * (-len(key) % 4)).decode("utf-8", "replace").split(",")
        if len(parts) >= 5:
            return {"date": parts[1], "kind": parts[2], "filename": parts[4]}
    except Exception:
        pass
    return {}


def _assignment_files(tds) -> dict:
    """The files linked from an assignment row: the teacher's brief (and a solution file once posted) in the
    third column, the student's own submission in the fourth, the returned submission in the sixth. Links expire
    daily, so they are re-read at download time; the file name comes from the link's key."""
    out = {}
    def add(kind, a):
        href = a.get("href") or ""
        if "Download" not in href:
            return
        out[kind] = {"href": href, "label": re.sub(r"\s+", " ", a.text_content()).strip(),
                     "filename": decode_download_key(href).get("filename", "")}
    for a in tds[2].xpath(".//a[@href]"):
        label = a.text_content().lower()
        add("solution" if "solution" in label else "brief", a)
    for a in tds[3].xpath(".//a[@href]"):
        add("submission", a)
    for a in tds[5].xpath(".//a[@href]"):
        add("returned", a)
    return out


def _parse_course_table(page_html: str, course_name: str) -> List[dict]:
    tree = html.fromstring(page_html)
    items = []
    for row in tree.xpath("//table//tr"):
        tds = row.xpath("./td")
        cells = [re.sub(r"\s+", " ", c.text_content()).strip() for c in tds]
        if len(cells) < 8:
            continue
        assign_no, title, _, added_sub, marks, _, action, raw_deadline = cells[:8]
        if not title:
            continue
        active_dl, is_extended, original_dl = parse_deadline(raw_deadline)
        sub_lower = added_sub.lower()
        is_submitted = "submission" in sub_lower and "no submission" not in sub_lower
        is_exceeded = "exceeded" in action.lower() or "exceeded" in active_dl.lower()
        status = "Submitted" if is_submitted else ("Missed (Exceeded)" if is_exceeded else "Pending")
        items.append({
            "id": f"{course_name}#{assign_no}#{title}".replace(" ", "_"),
            "course": course_name,
            "assign_no": assign_no,
            "title": title,
            "due_date": active_dl,
            "raw_deadline": raw_deadline,
            "is_extended": is_extended,
            "original_due_date": original_dl,
            "submission_status": added_sub,
            "action": action,
            "marks": marks,
            "status": status,
            "is_submitted": is_submitted,
            "files": _assignment_files(tds),
        })
    return items
