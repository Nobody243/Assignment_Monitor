"""Background jobs run by the scheduled tasks (and available from the command line)."""
import logging
from datetime import datetime

from campus import seat_text
from config import APP_NAME, DB_PATH, has_credentials, load_env
from deadlines import classify, is_open_pending, sort_key
from lms_scraper import LoginError, run_sync
from notifier import (alert_assignments, alert_announcements, alert_attendance, alert_exam_today,
                      alert_exams_scheduled, alert_exams_soon, alert_lectures, send_toast, speak_voice)
from tracker import (compare_announcements, compare_assignments, compare_attendance, compare_lectures, exams_within,
                     load_attendance, load_stored_assignments, mark_reminder, reminder_sent, save_exams)

log = logging.getLogger("bahria.jobs")


def collectors_for(env: dict) -> tuple:
    out = ["assignments"]
    if env.get("TRACK_ATTENDANCE", True):
        out.append("attendance")
    if env.get("TRACK_EXAMS", True):
        out.append("exams")
    if env.get("TRACK_ANNOUNCEMENTS", True):
        out.append("announcements")
    if env.get("TRACK_LECTURES", True):
        out.append("lectures")
    return tuple(out)


def process_sync(result: dict, env: dict, notify: bool = True) -> dict:
    """Merges a run_sync result into the local stores and sends the alerts. Shared by the scheduled check and
    the window's Sync button. Returns a summary dict."""
    pending, extended, new_items = compare_assignments(result.get("assignments", []))
    summary = {"assignments": len(result.get("assignments", [])), "pending": len(pending), "new": len(new_items),
               "extended": len(extended)}
    log.info("Sync complete: %d assignments, %d pending, %d extended, %d new.",
             summary["assignments"], len(pending), len(extended), len(new_items))
    for p in sorted(pending, key=sort_key):
        log.info("  pending  %-40s %-30s %s", p["title"][:40], p["course"][:30], classify(p)["label"])
    for e in extended:
        log.info("  extended %-40s now %s (was %s)", e["title"][:40], e["due_date"],
                 e.get("previous_due_date") or e.get("original_due_date"))
    if notify:
        alert_assignments(pending, extended)

    minimum = int(env.get("ATTENDANCE_MIN", 75))
    if "attendance" in result:
        changes = compare_attendance(result["attendance"], minimum)
        summary["attendance"] = len(result["attendance"])
        summary["below"] = len(changes["below"])
        for c in changes["new_absences"]:
            log.info("  absence  %-8s %-32s +%g h, now %.0f%%", c["code"], c["title"][:32], c["new_absent_hours"], c["percent"])
        for c in changes["below"]:
            log.info("  under %d%% %-8s %-32s %.0f%% (need %g h present)", minimum, c["code"], c["title"][:32], c["percent"], c["need"])
        if notify:
            alert_attendance(changes, minimum)

    if "exams" in result:
        newly = save_exams(result["exams"])
        soon = exams_within(int(env.get("EXAM_REMIND_DAYS", 1)), result["exams"])
        summary["exams"] = sum(1 for e in result["exams"] if e.get("scheduled"))
        for e in soon:
            log.info("  exam     %-40s %s %s", e["title"][:40], e["when"].strftime("%d %b %I:%M %p"), seat_text(e))
        if notify:
            alert_exams_scheduled(newly)
            alert_exams_soon([e for e in soon if not reminder_sent(f"exam-soon:{e['id']}:{e['date']}")])
            for e in soon:
                mark_reminder(f"exam-soon:{e['id']}:{e['date']}")

    if "announcements" in result:
        new_ann = compare_announcements(result["announcements"])
        summary["announcements"] = len(result["announcements"])
        summary["new_announcements"] = len(new_ann)
        for a in new_ann:
            log.info("  announce %-30s %s", a["course"][:30], a["text"][:80])
        if notify:
            alert_announcements(new_ann)
    if "lectures" in result:
        new_lec = compare_lectures(result["lectures"])
        summary["lectures"] = len(result["lectures"])
        summary["new_lectures"] = len(new_lec)
        for x in new_lec:
            log.info("  lecture  %-30s week %s: %s", x["course"][:30], x["week"], x["title"][:60])
        if notify:
            alert_lectures(new_lec)
    for key, err in (result.get("errors") or {}).items():
        log.warning("  %s could not be read this time: %s", key, err)
    return summary


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
        result = run_sync(headless=headless, collect=collectors_for(env), previous_attendance=load_attendance())
    except LoginError as e:
        log.error("%s", e)
        send_toast(f"{APP_NAME}: Sign-in failed", f"{e}\nOpen the app to update your credentials.")
        return 3
    except Exception as e:
        log.error("Sync failed: %s", e)
        send_toast(f"{APP_NAME}: Sync failed", str(e)[:200])
        return 1
    process_sync(result, env, notify=not quiet)
    return 0


def find_due_today_pending(assignments: dict) -> list:
    now = datetime.now()
    return [item for item in assignments.values()
            if is_open_pending(item) and classify(item, now)["key"] == "today"]


def run_reminder(test: bool = False) -> int:
    """Hourly job: voice + toast while an unsubmitted assignment is due today, plus a once-a-day
    morning reminder on exam days."""
    env = load_env()
    if test:
        log.info("Hourly reminder TEST run.")
        due_items = [{"title": "Sample Assignment", "course": "Sample Course",
                      "due_date": f"{datetime.now().strftime('%d %B %Y')} - 11:59 pm"}]
    else:
        due_items = find_due_today_pending(load_stored_assignments())
        if env.get("TRACK_EXAMS", True):
            _exam_day_reminders()

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


def _exam_day_reminders() -> None:
    """From 6 am on an exam day, one reminder per paper (the hourly task runs every hour; this fires once)."""
    now = datetime.now()
    if now.hour < 6:
        return
    for e in exams_within(0, now=now):
        if e["when"] < now:
            continue
        key = f"exam-day:{e['id']}:{e['date']}"
        if reminder_sent(key):
            continue
        log.info("Exam-day reminder: %s at %s", e["title"], e["when"].strftime("%I:%M %p"))
        alert_exam_today(e)
        mark_reminder(key)


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
    att = load_attendance()
    if att:
        print(f"\nAttendance ({len(att)} courses):\n")
        for c in sorted(att.values(), key=lambda c: c.get("percent", 0)):
            flag = "" if c.get("ok", True) else "  <- under minimum"
            print(f"{c.get('code', ''):<9} {c.get('title', '')[:40]:<42} {c.get('percent', 0):5.1f}%  "
                  f"({c.get('present', 0):g}/{c.get('total', 0):g} h){flag}")
    upcoming = exams_within(60)
    if upcoming:
        print("\nUpcoming exams:\n")
        for e in upcoming:
            print(f"{e['when'].strftime('%a %d %b %I:%M %p'):<22} {e['title'][:40]:<42} {seat_text(e)}")
    print()
    return 0
