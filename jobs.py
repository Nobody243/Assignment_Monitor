"""Background jobs run by the scheduled tasks (and available from the command line)."""
import logging
from datetime import datetime

from config import APP_NAME, DB_PATH, has_credentials, load_env
from deadlines import classify, is_open_pending, sort_key
from lms_scraper import LoginError, run_lms_check
from notifier import alert_assignments, send_toast, speak_voice
from tracker import compare_assignments, load_stored_assignments

log = logging.getLogger("bahria.jobs")


def run_check(quiet: bool = False, headless: bool = None) -> int:
    """Full sync followed by notifications. Returns a process exit code."""
    env = load_env()
    if not has_credentials(env):
        log.error("No credentials saved. Open %s and sign in first.", APP_NAME)
        return 2
    if headless is None:
        headless = env.get("HEADLESS", True)
    log.info("=== Sync started %s ===", datetime.now().strftime("%Y-%m-%d %H:%M"))
    try:
        current = run_lms_check(headless=headless)
    except LoginError as e:
        log.error("%s", e)
        send_toast(f"{APP_NAME}: Sign-in failed", f"{e}\nOpen the app to update your credentials.")
        return 3
    except Exception as e:
        log.error("Sync failed: %s", e)
        send_toast(f"{APP_NAME}: Sync failed", str(e)[:200])
        return 1

    pending, extended, new_items = compare_assignments(current)
    log.info("Sync complete: %d assignments, %d pending, %d extended, %d new.",
             len(current), len(pending), len(extended), len(new_items))
    for p in sorted(pending, key=sort_key):
        log.info("  pending  %-40s %-30s %s", p["title"][:40], p["course"][:30], classify(p)["label"])
    for e in extended:
        log.info("  extended %-40s now %s (was %s)", e["title"][:40], e["due_date"],
                 e.get("previous_due_date") or e.get("original_due_date"))
    if not quiet:
        alert_assignments(pending, extended)
    return 0


def find_due_today_pending(assignments: dict) -> list:
    now = datetime.now()
    return [item for item in assignments.values()
            if is_open_pending(item) and classify(item, now)["key"] == "today"]


def run_reminder(test: bool = False) -> int:
    """Hourly job: voice + toast while an unsubmitted assignment is due today."""
    env = load_env()
    if test:
        log.info("Hourly reminder TEST run.")
        due_items = [{"title": "Sample Assignment", "course": "Sample Course",
                      "due_date": f"{datetime.now().strftime('%d %B %Y')} - 11:59 pm"}]
    else:
        due_items = find_due_today_pending(load_stored_assignments())

    if not due_items:
        log.info("Hourly check: nothing due today.")
        return 0

    count = len(due_items)
    first = due_items[0]
    if count == 1:
        voice = f"Reminder: {first['title']} for {first['course']} is due today. Don't forget to submit it."
        title = f"{APP_NAME}: Assignment due today!"
        body = f"{first['title']} ({first['course']})\n{first.get('due_date', '')}"
    else:
        voice = f"Reminder: you have {count} assignments due today on Bahria LMS."
        title = f"{APP_NAME}: {count} assignments due today!"
        body = "\n".join(f"- {i['title']} ({i['course']})" for i in due_items[:3])

    log.info("Hourly reminder fired for %d assignment(s): %s", count, ", ".join(i["title"] for i in due_items))
    if env.get("ENABLE_WINDOWS_TOAST", True):
        send_toast(title, body)
    if env.get("ENABLE_VOICE", True):
        speak_voice(voice)
    return 0


def test_alert() -> int:
    send_toast(APP_NAME, "Test alert: notifications are working.")
    speak_voice("Bahria LMS Monitor alerts are working.", force=True)
    return 0


def print_status() -> int:
    stored = load_stored_assignments()
    if not stored:
        print("No assignments stored yet. Run a sync first.")
        return 0
    print(f"\nTracking {len(stored)} assignments ({DB_PATH}):\n")
    print(f"{'Course':<34} | {'Title':<38} | {'Due':<26} | Status")
    print("-" * 118)
    for item in sorted(stored.values(), key=sort_key):
        info = classify(item)
        status = "Submitted" if item.get("is_submitted") else info["label"]
        print(f"{item.get('course', '')[:32]:<34} | {item.get('title', '')[:36]:<38} | "
              f"{item.get('due_date', '')[:24]:<26} | {status}")
    print()
    return 0
