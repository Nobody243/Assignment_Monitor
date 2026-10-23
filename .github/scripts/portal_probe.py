"""One-off feasibility probe: can the university portal be signed in to from a GitHub Actions runner?

Reads PORTAL_ENROLLMENT and PORTAL_PASSWORD from the environment, signs in with the app's own PortalSession,
crosses into the LMS and counts courses and assignments. Prints only pass/fail lines and counts; nothing is
written to disk and no page content is logged.
"""
import logging
import os
import sys
import time

sys.path.insert(0, os.getcwd())

from playwright.sync_api import sync_playwright  # noqa: E402

from lms_scraper import LoginError, PortalSession, _collect_assignments  # noqa: E402

logging.basicConfig(level=logging.WARNING)   # the scraper's info lines mention the enrollment; keep them quiet


def main() -> int:
    enrollment = os.environ.get("PORTAL_ENROLLMENT", "").strip()
    password = os.environ.get("PORTAL_PASSWORD", "").strip()
    institute = os.environ.get("PORTAL_INSTITUTE_ID", "1").strip()
    if not enrollment or not password:
        print("FAIL: PORTAL_ENROLLMENT / PORTAL_PASSWORD are not set")
        return 2
    t0 = time.time()
    with sync_playwright() as p:
        kwargs = dict(headless=True, args=["--disable-blink-features=AutomationControlled"])
        try:
            browser = p.chromium.launch(channel="chrome", **kwargs)
            print("browser: Google Chrome")
        except Exception:
            browser = p.chromium.launch(**kwargs)
            print("browser: bundled Chromium")
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        page.set_default_timeout(45000)
        session = PortalSession(page, enrollment, password, institute)
        try:
            session.sign_in()
        except LoginError as e:
            print(f"FAIL sign-in: {e}")
            return 3
        except Exception as e:
            print(f"FAIL reaching the CMS: {type(e).__name__}: {str(e).splitlines()[0][:160]}")
            return 1
        print(f"PASS sign-in to CMS ({time.time() - t0:.0f} s)")
        try:
            session.enter_lms()
        except Exception as e:
            print(f"FAIL LMS single sign-on: {type(e).__name__}: {str(e).splitlines()[0][:160]}")
            return 4
        print(f"PASS LMS single sign-on ({time.time() - t0:.0f} s)")
        meta: dict = {}
        try:
            items = _collect_assignments(session, meta)
        except Exception as e:
            print(f"FAIL reading assignments: {type(e).__name__}: {str(e).splitlines()[0][:160]}")
            return 5
        print(f"PASS assignments: {len(items)} across {len(meta.get('courses', []))} courses ({time.time() - t0:.0f} s)")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
