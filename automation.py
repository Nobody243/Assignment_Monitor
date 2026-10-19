"""Windows background automation: scheduled tasks, sign-in catch-up and shortcuts.

Everything here runs as the current user and needs no administrator rights.
"""
import logging
import os
import subprocess
from pathlib import Path

from config import APP_NAME, ASSETS_DIR, FROZEN, SOURCE_DIR, app_command

log = logging.getLogger("bahria.automation")
CREATE_NO_WINDOW = 0x08000000

TASK_DAILY = "AssignmentMonitor_DailyCheck"
TASK_HOURLY = "AssignmentMonitor_HourlyReminder"
TASK_LOGON = "AssignmentMonitor_LogonCheck"
LEGACY_TASKS = ("BahriaLMS_DailyCheck", "BahriaLMS_HourlyReminder", "BahriaLMS_LogonCheck",
                "BahriaLMS_HourlyUrgentReminder")
STARTUP_SCRIPT = "AssignmentMonitor_Startup.vbs"
LEGACY_STARTUP = ("BahriaLMS_Startup.vbs",)
STARTUP_SHORTCUT = f"{APP_NAME}.lnk"


def _run(cmd, timeout=60):
    return subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW, timeout=timeout)


def _quote(parts) -> str:
    return " ".join(f'"{p}"' if (" " in p or p.endswith(".py")) else p for p in parts)


def _startup_dir() -> Path:
    return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def is_enabled() -> bool:
    try:
        return _run(["schtasks", "/Query", "/TN", TASK_DAILY], timeout=20).returncode == 0
    except Exception:
        return False


def _create_task(name, schedule_args, command):
    r = _run(["schtasks", "/Create", "/F", "/TN", name, "/TR", command, *schedule_args])
    if r.returncode != 0:
        raise RuntimeError(f"{name}: {(r.stderr or r.stdout).strip()}")


def _write_startup_script(command: str):
    """Runs the catch-up check hidden when the user signs in (works without admin rights)."""
    startup = _startup_dir()
    if not startup.exists():
        return False
    vbs_cmd = command.replace('"', '""')
    (startup / STARTUP_SCRIPT).write_text(
        f'CreateObject("WScript.Shell").Run "{vbs_cmd}", 0, False\r\n', encoding="utf-8")
    return True


def _make_shortcut(path: Path, extra_args=()):
    cmd = app_command(*extra_args)
    target, args = cmd[0], _quote(cmd[1:])
    icon = ASSETS_DIR / "icon.ico"
    workdir = Path(target).parent if FROZEN else SOURCE_DIR
    ps = f"""
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut('{path}')
$sc.TargetPath = '{target}'
$sc.Arguments = '{args}'
$sc.WorkingDirectory = '{workdir}'
{"$sc.IconLocation = '" + str(icon) + ", 0'" if icon.exists() else ""}
$sc.Description = '{APP_NAME} for Bahria University LMS'
$sc.Save()"""
    r = _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])
    return r.returncode == 0


def create_shortcuts():
    """Desktop and Start Menu shortcuts that open the app window."""
    ok = True
    for folder in (Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
                   Path.home() / "Desktop"):
        if folder.exists():
            ok = _make_shortcut(folder / f"{APP_NAME}.lnk") and ok
    return ok


def starts_with_windows() -> bool:
    return (_startup_dir() / STARTUP_SHORTCUT).exists()


def set_start_with_windows(enable: bool):
    """Opens the app minimized to the tray when the user signs in to Windows."""
    path = _startup_dir() / STARTUP_SHORTCUT
    if enable:
        ok = _make_shortcut(path, ("--tray",))
        log.info("Start with Windows %s.", "enabled" if ok else "could not be enabled")
        return ok
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    log.info("Start with Windows disabled.")
    return True


def enable():
    """Registers all background jobs. Returns (ok, message)."""
    try:
        check_cmd = _quote(app_command("--check"))
        remind_cmd = _quote(app_command("--remind"))
        _create_task(TASK_DAILY, ["/SC", "DAILY", "/ST", "19:00"], check_cmd)
        _create_task(TASK_HOURLY, ["/SC", "HOURLY", "/MO", "1"], remind_cmd)
        try:
            _create_task(TASK_LOGON, ["/SC", "ONLOGON", "/DELAY", "0002:00"], check_cmd)
            logon = "scheduled task"
        except Exception as e:
            log.info("ONLOGON task not available (%s); using the Startup folder instead.", str(e).strip()[:120])
            _write_startup_script(check_cmd)
            logon = "startup folder"
        for legacy in LEGACY_TASKS:
            _run(["schtasks", "/Delete", "/F", "/TN", legacy])
        for legacy in LEGACY_STARTUP:
            try:
                (_startup_dir() / legacy).unlink()
            except OSError:
                pass
        shortcuts = create_shortcuts()
        log.info("Background automation enabled (sign-in check via %s, shortcuts %s).",
                 logon, "created" if shortcuts else "skipped")
        return True, "Background automation is on."
    except Exception as e:
        log.error("Could not enable background automation: %s", e)
        return False, str(e)


def disable():
    """Removes the background jobs. Shortcuts are kept."""
    for name in (TASK_DAILY, TASK_HOURLY, TASK_LOGON, *LEGACY_TASKS):
        _run(["schtasks", "/Delete", "/F", "/TN", name])
    for name in (STARTUP_SCRIPT, *LEGACY_STARTUP):
        try:
            (_startup_dir() / name).unlink()
        except FileNotFoundError:
            pass
        except Exception as e:
            log.warning("Could not remove startup script: %s", e)
    log.info("Background automation disabled.")
    return not is_enabled(), "Background automation is off."
