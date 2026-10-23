"""Entry point for the cloud runner (GitHub Actions). Settings arrive as AM_<KEY> environment variables and the
state folder is ASSIGNMENT_MONITOR_HOME; see cloud.py for the picture.

    python cloud_check.py check     full sync, alerts to the phone and the mailbox, state saved
    python cloud_check.py verify    sign in, count what is there and send one test alert, state untouched

Exit codes follow jobs.run_check (0 ok, 1 sync failed, 2 no credentials, 3 sign-in rejected) so a failed run shows
red in the student's Actions tab and GitHub mails them about it.
"""
import logging
import os
import sys
import time

os.environ.setdefault("ASSIGNMENT_MONITOR_RUNNER", "cloud")
os.environ.setdefault("AM_ENABLE_WINDOWS_TOAST", "False")
os.environ.setdefault("AM_ENABLE_VOICE", "False")
os.environ.setdefault("AM_HEADLESS", "True")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_NAME, APP_VERSION, load_env, setup_logging  # noqa: E402

log = logging.getLogger("bahria.cloud_check")


def verify() -> int:
    from channels import email_ready, push_ready, send_email, send_push
    from lms_scraper import LoginError, run_sync
    env = load_env()
    t0 = time.time()
    try:
        result = run_sync(headless=True, collect=("assignments",))
    except LoginError as e:
        log.error("%s", e)
        return 3
    n = len(result.get("assignments", []))
    log.info("Verified: signed in and read %d assignments in %.0f s.", n, time.time() - t0)
    title = "Cloud checks are on"
    body = (f"GitHub will now check the portal for you twice a day, even with the PC off. "
            f"First look: {n} assignments on the LMS.")
    sent = []
    if push_ready(env):
        try:
            send_push(title, body, env=env)
            sent.append("phone")
        except Exception as e:
            log.warning("Test push failed: %s", str(e)[:200])
    if email_ready(env):
        try:
            send_email(f"{APP_NAME}: {title}", body, env=env)
            sent.append("email")
        except Exception as e:
            log.warning("Test email failed: %s", str(e)[:200])
    log.info("Test alert sent to: %s", ", ".join(sent) or "nothing (no phone or mailbox set up)")
    return 0


def main(argv) -> int:
    setup_logging(to_console=True)
    mode = (argv[1] if len(argv) > 1 else "check").strip().lower()
    log.info("%s %s cloud runner: %s", APP_NAME, APP_VERSION, mode)
    if mode == "verify":
        return verify()
    from jobs import run_check
    return run_check(headless=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
