"""
The command-line jobs of the app (what the scheduled tasks run), shared by the engine so the packaged app keeps
working exactly as before: AssignmentMonitor.exe --check / --remind / --status / --test-alert / --enable-automation ...

`run(args)` returns an exit code when it handled a job, or None when no job was asked for (the caller then starts
as a normal long-running service).
"""
import argparse


def add_arguments(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--check", action="store_true", help="sync assignments and notify, then exit")
    ap.add_argument("--remind", action="store_true", help="hourly same-day reminder, then exit")
    ap.add_argument("--status", action="store_true", help="print saved assignments, then exit")
    ap.add_argument("--test-alert", action="store_true", help="test notification and voice, then exit")
    ap.add_argument("--test", action="store_true", help="with --remind: simulate an assignment due today")
    ap.add_argument("--quiet", "-q", action="store_true", help="with --check: no notifications")
    ap.add_argument("--visible", action="store_true", help="with --check: show the browser window")
    ap.add_argument("--enable-automation", action="store_true", help="register the background tasks, then exit")
    ap.add_argument("--disable-automation", action="store_true", help="remove the background tasks, then exit")
    ap.add_argument("--disable-cloud", action="store_true", help="turn off cloud checks, then exit")


def wanted(args) -> bool:
    keys = ("check", "remind", "status", "test_alert", "enable_automation", "disable_automation", "disable_cloud")
    return any(getattr(args, k, False) for k in keys)


def run(args) -> int | None:
    if args.check or args.remind or args.status or args.test_alert:
        import jobs
        if args.check:
            return jobs.run_check(quiet=args.quiet, headless=False if args.visible else None)
        if args.remind:
            return jobs.run_reminder(test=args.test)
        if args.status:
            return jobs.print_status()
        return jobs.test_alert()
    if args.disable_cloud:
        import cloud
        if not cloud.enabled():
            print("Cloud checks are not on.")
            return 0
        url = cloud.teardown()
        print(f"Cloud checks are off. The empty repository remains at {url.rsplit('/settings', 1)[0] if url else 'GitHub'}.")
        return 0
    if args.enable_automation or args.disable_automation:
        import automation
        ok, msg = automation.enable() if args.enable_automation else automation.disable()
        if args.disable_automation:
            automation.set_start_with_windows(False)
        print(msg)
        return 0 if ok else 1
    return None
