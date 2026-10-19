import logging
import os
import re
import subprocess
import time
from datetime import datetime
from typing import List

from lxml import html
from playwright.sync_api import sync_playwright

from config import (PROFILE_DIR, DATA_DIR, BROWSERS_DIR, LOGIN_URL, SSO_URL, ASSIGNMENTS_URL,
                    load_env, save_meta, campus_name)
from deadlines import parse_deadline

log = logging.getLogger("bahria.scraper")

LOCK_PATH = DATA_DIR / "sync.lock"
LOCK_STALE_SECONDS = 15 * 60


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


def run_lms_check(headless: bool = True, interactive: bool = False) -> List[dict]:
    """
    Full audit of the student's assignments:
      1. Sign in at the CMS portal.
      2. Follow the CMS -> LMS single sign-on.
      3. Read the assignments table for every enrolled course of the current semester.
    Also writes data/meta.json with the student name, semester, and course list.
    """
    env = load_env()
    enrollment = env.get("ENROLLMENT", "").strip()
    password = env.get("PASSWORD", "").strip()
    institute_id = str(env.get("INSTITUTE_ID", "1")).strip()
    if not enrollment or not password:
        raise LoginError("Enrollment number and password are not configured yet.")

    headless = headless and not interactive
    _acquire_lock()
    all_assignments: List[dict] = []
    meta = {
        "enrollment": enrollment,
        "institute_id": institute_id,
        "campus": campus_name(institute_id),
        "student_name": "",
        "semester": "",
        "courses": [],
        "last_sync": None,
        "last_result": "",
    }

    try:
        with sync_playwright() as p:
            log.info("Starting browser (%s mode)...", "background" if headless else "visible")
            context = _launch_browser(p, headless)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(45000)

                log.info("Opening Bahria University CMS portal...")
                page.goto(LOGIN_URL, wait_until="networkidle")
                time.sleep(1.5)

                if page.locator("#BodyPH_tbEnrollment").count() > 0:
                    log.info("Signing in as %s (%s)...", enrollment, campus_name(institute_id))
                    page.fill("#BodyPH_tbEnrollment", enrollment)
                    page.fill("#BodyPH_tbPassword", password)
                    if page.locator("#BodyPH_ddlInstituteID").count() > 0:
                        page.select_option("#BodyPH_ddlInstituteID", value=institute_id)
                    if page.locator("#BodyPH_ddlSubUserType").count() > 0:
                        page.select_option("#BodyPH_ddlSubUserType", value="None")
                    page.click("#BodyPH_btnLogin")
                    try:
                        page.wait_for_load_state("networkidle", timeout=30000)
                    except Exception:
                        pass
                    time.sleep(1.5)

                if "login.aspx" in page.url.lower():
                    msg = _login_error_text(page) or "the portal rejected the enrollment number, password, or campus"
                    raise LoginError(f"Sign-in failed: {msg}")
                log.info("Signed in to CMS. Opening LMS via single sign-on...")

                page.goto(SSO_URL, wait_until="networkidle")
                try:
                    page.wait_for_url(re.compile(r"lms\.bahria\.edu\.pk", re.IGNORECASE), timeout=30000)
                except Exception:
                    raise RuntimeError(f"LMS single sign-on failed; the portal landed on {page.url}")
                time.sleep(1)

                try:
                    name = page.locator("a.dropdown-toggle span.hidden-xs").first.inner_text(timeout=5000).strip()
                    meta["student_name"] = name.title() if name.isupper() else name
                except Exception:
                    pass

                log.info("Opening the assignments page...")
                page.goto(ASSIGNMENTS_URL, wait_until="networkidle")
                time.sleep(1)
                if "lms.bahria.edu.pk" not in page.url.lower():
                    raise RuntimeError(f"LMS session was lost; redirected to {page.url}")

                page.wait_for_selector("#courseId option[value]:not([value=''])", state="attached", timeout=20000)
                try:
                    meta["semester"] = page.evaluate(
                        "() => { const s = document.querySelector('#semesterId'); "
                        "return s && s.selectedOptions.length ? s.selectedOptions[0].textContent.trim() : ''; }")
                except Exception:
                    pass

                courses = []
                for opt in page.locator("#courseId option").all():
                    val = opt.get_attribute("value")
                    text = opt.inner_text().strip()
                    if val and text and text != "Select Course":
                        courses.append((val, text))
                meta["courses"] = [c[1] for c in courses]
                log.info("Found %d enrolled courses for %s.", len(courses), meta["semester"] or "the current semester")

                for course_val, course_name in courses:
                    log.info("Reading assignments: %s", course_name)
                    page.select_option("#courseId", value=course_val)
                    try:
                        page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass
                    time.sleep(1.5)
                    all_assignments.extend(_parse_course_table(page.content(), course_name))

                log.info("Collected %d assignments across %d courses.", len(all_assignments), len(courses))
                meta["last_sync"] = datetime.now().isoformat(timespec="seconds")
                meta["last_result"] = f"{len(all_assignments)} assignments from {len(courses)} courses"
                save_meta(meta)
                return all_assignments
            finally:
                context.close()
    finally:
        _release_lock()


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
