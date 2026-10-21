import logging
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin

from lxml import html
from playwright.sync_api import sync_playwright

from campus import (parse_announcements, parse_attendance, parse_attendance_detail, parse_exam_seats, parse_lectures,
                    safe_name)
from config import (PROFILE_DIR, DATA_DIR, BROWSERS_DIR, LOGIN_URL, SSO_URL, ASSIGNMENTS_URL, ATTENDANCE_URL,
                    EXAMS_URL, ANNOUNCEMENTS_URL, LECTURES_URL, LMS_BASE_URL, load_env, save_meta, campus_name)
from deadlines import parse_deadline

log = logging.getLogger("bahria.scraper")

LOCK_PATH = DATA_DIR / "sync.lock"
LOCK_STALE_SECONDS = 15 * 60
ALL_COLLECTORS = ("assignments", "attendance", "exams", "announcements", "lectures")


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
    try:
        return p.chromium.launch_persistent_context(**kwargs)
    except Exception:
        pass
    if _install_chromium():
        try:
            return p.chromium.launch_persistent_context(**kwargs)
        except Exception as e:
            log.error("Chromium failed to start after download: %s", str(e).splitlines()[0][:160])
    raise RuntimeError("No browser available. Please install Google Chrome and try again.")


def _login_error_text(page) -> str:
    texts = []
    for sel in (".text-danger", ".alert", "[id*='lblMessage']", "[id*='Message']", "[id*='lblError']"):
        try:
            texts += [t.strip() for t in page.locator(sel).all_inner_texts() if t.strip()]
        except Exception:
            pass
    return ", ".join(dict.fromkeys(texts))


def _settle(page, timeout: int = 15000, pause: float = 1.2):
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
    time.sleep(pause)


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
            log.info("Signing in as %s (%s)...", self.enrollment, campus_name(self.institute_id))
            page.fill("#BodyPH_tbEnrollment", self.enrollment)
            page.fill("#BodyPH_tbPassword", self.password)
            if page.locator("#BodyPH_ddlInstituteID").count() > 0:
                page.select_option("#BodyPH_ddlInstituteID", value=self.institute_id)
            if page.locator("#BodyPH_ddlSubUserType").count() > 0:
                page.select_option("#BodyPH_ddlSubUserType", value="None")
            page.click("#BodyPH_btnLogin")
            _settle(page, 30000, 1.5)
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
        items.extend(_parse_course_table(page.content(), course_name))
    log.info("Collected %d assignments across %d courses.", len(items), len(courses))
    return items


def _collect_attendance(s: PortalSession, previous: Optional[Dict[str, dict]] = None) -> List[dict]:
    """The attendance table, plus the per-class detail for every course whose hours changed since last time
    (the detail pages are one request each, so unchanged courses reuse what was stored)."""
    previous = previous or {}
    page = s.cms(ATTENDANCE_URL)
    courses = parse_attendance(page.content())
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
        return parse_exam_seats(page.content(), "Exam")
    for i, (val, name) in enumerate(types):
        if i:
            page.select_option("#BodyPH_ddlExamTypeFilter", value=val)
            _settle(page, 15000, 1.5)
        out.extend(parse_exam_seats(page.content(), name))
    log.info("Exams: %d rows across %d exam type(s), %d scheduled.", len(out), len(types), sum(1 for e in out if e["scheduled"]))
    return out


def _collect_lectures(s: PortalSession) -> List[dict]:
    page = s.lms(LECTURES_URL)
    out: List[dict] = []
    for course_val, course_name in s.lms_courses():
        s.select_course(course_val)
        out.extend(parse_lectures(page.content(), course_name))
    log.info("Lecture notes: %d weeks across all courses.", len(out))
    return out


def _collect_announcements(s: PortalSession) -> List[dict]:
    page = s.lms(ANNOUNCEMENTS_URL)
    out: List[dict] = []
    for course_val, course_name in s.lms_courses():
        s.select_course(course_val)
        out.extend(parse_announcements(page.content(), course_name))
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
                    ("announcements", "Reading announcements", lambda: _collect_announcements(session)),
                    ("lectures", "Reading lecture notes", lambda: _collect_lectures(session)),
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
                if "announcements" in result:
                    summary.append(f"{len(result['announcements'])} announcements")
                if "lectures" in result:
                    summary.append(f"{len(result['lectures'])} lecture weeks")
                meta["last_sync"] = datetime.now().isoformat(timespec="seconds")
                meta["last_result"] = ", ".join(summary)
                save_meta(meta)
                return result
            finally:
                context.close()
    finally:
        _release_lock()


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
            wanted.setdefault(lec["course"], []).append((lec, f))
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
                for course, items in wanted.items():
                    if stop():
                        break
                    val = courses.get(course)
                    if not val:
                        for _lec, f in items:
                            result["failed"].append((f["filename"], "course is no longer on the LMS"))
                        done += len(items)
                        continue
                    session.select_course(val)
                    fresh = {}
                    for lec in parse_lectures(page.content(), course):
                        for f in lec["files"]:
                            fresh[(lec["week"], lec["title"], f["label"])] = f
                    for lec, f in items:
                        if stop():
                            break
                        done += 1
                        name = f.get("filename") or safe_name(lec["title"])
                        folder = dest / safe_name(course) / f"Week {str(lec['week']).zfill(2)} - {safe_name(lec['title'], 60)}"
                        target = folder / name
                        say(f"{course[:30]} · week {lec['week']} · {name[:40]}", done, total)
                        if target.exists() and target.stat().st_size > 0:
                            result["skipped"] += 1
                            continue
                        live = fresh.get((lec["week"], lec["title"], f["label"])) or f
                        url = urljoin(LMS_BASE_URL + "/Student/", live["href"])
                        try:
                            resp = page.request.get(url, timeout=120000)
                            ctype = (resp.headers.get("content-type") or "").lower()
                            body = resp.body()
                            if not resp.ok or ("text/html" in ctype and len(body) < 200000):
                                raise RuntimeError(f"portal answered {resp.status} ({ctype.split(';')[0] or 'unknown type'})")
                            cd = resp.headers.get("content-disposition") or ""
                            m = re.search(r"filename\*?=(?:UTF-8\'\')?\"?([^\";]+)", cd, re.I)
                            if m and "." in m.group(1):
                                target = folder / safe_name(m.group(1).strip(), 120)
                            folder.mkdir(parents=True, exist_ok=True)
                            target.write_bytes(body)
                            result["saved"].append(str(target))
                            log.info("Downloaded %s (%d KB)", target.name, len(body) // 1024)
                        except Exception as e:
                            log.warning("Download failed for %s: %s", name, str(e)[:160])
                            result["failed"].append((name, str(e)[:120]))
            finally:
                context.close()
    finally:
        _release_lock()
    return result


def run_lms_check(headless: bool = True, interactive: bool = False) -> List[dict]:
    """Assignments only (kept for callers that just verify the sign-in)."""
    return run_sync(headless=headless, interactive=interactive, collect=("assignments",))["assignments"]


def _parse_course_table(page_html: str, course_name: str) -> List[dict]:
    tree = html.fromstring(page_html)
    items = []
    for row in tree.xpath("//table//tr"):
        cells = [re.sub(r"\s+", " ", c.text_content()).strip() for c in row.xpath("./td")]
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
        })
    return items
