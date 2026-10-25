"""Windows background automation: scheduled tasks, sign-in catch-up and shortcuts.

Everything here runs as the current user and needs no administrator rights.
"""
import logging
import os
import re
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

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


def installed_owner() -> str:
    """The installed program that owns the background tasks, when this is a source-tree run and the tasks point at
    an AssignmentMonitor.exe that still exists; "" otherwise. Running the source next to an installation (tests,
    screenshots, development) must never re-point the installed app's tasks and shortcuts at the source tree:
    that is exactly what happened once, and the student ended up in a copy of the app with none of their setup."""
    if FROZEN:
        return ""
    try:
        r = _run(["schtasks", "/Query", "/TN", TASK_DAILY, "/XML"], timeout=20)
    except Exception:
        return ""
    if r.returncode != 0:
        return ""
    m = re.search(r"<Command>(.*?)</Command>", r.stdout or "", re.S)
    cmd = (m.group(1) if m else "").strip()
    if cmd.lower().endswith("assignmentmonitor.exe") and Path(cmd).exists():
        return cmd
    return ""


def is_enabled() -> bool:
    try:
        return _run(["schtasks", "/Query", "/TN", TASK_DAILY], timeout=20).returncode == 0
    except Exception:
        return False


def _create_task(name, schedule_args, command):
    r = _run(["schtasks", "/Create", "/F", "/TN", name, "/TR", command, *schedule_args])
    if r.returncode != 0:
        raise RuntimeError(f"{name}: {(r.stderr or r.stdout).strip()}")


# ---- task definitions as XML. schtasks /Create has switches for the schedule only; the settings that matter on a
# laptop (run on battery, wake the machine, run a missed check as soon as possible) exist only in the XML form.
TASK_MARK = "<WakeToRun>"          # present in every task registered from XML; its absence means the old format


def _current_user() -> str:
    domain, user = os.environ.get("USERDOMAIN", ""), os.environ.get("USERNAME", "")
    return f"{domain}\\{user}" if domain else user


def _task_xml(cmd: list, triggers: str, *, wake: bool, limit: str, restart: bool) -> str:
    """A Task Scheduler definition for the current user: runs on battery, is not stopped for going on battery,
    runs a missed start as soon as the PC is back, and optionally wakes the PC and retries on failure."""
    exe, args = cmd[0], _quote(cmd[1:])
    user = escape(_current_user())
    retry = "<RestartOnFailure><Interval>PT10M</Interval><Count>3</Count></RestartOnFailure>" if restart else ""
    arguments = f"<Arguments>{escape(args)}</Arguments>" if args else ""
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>{user}</Author>
    <Description>{APP_NAME}: runs under your own account; turn it off in the app's Settings.</Description>
  </RegistrationInfo>
  <Triggers>{triggers}</Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>{"true" if wake else "false"}</WakeToRun>
    <ExecutionTimeLimit>{limit}</ExecutionTimeLimit>
    <Priority>7</Priority>
    {retry}
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(exe)}</Command>
      {arguments}
    </Exec>
  </Actions>
</Task>
"""


def _daily_trigger(hour: int = 19) -> str:
    start = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
    return (f"<CalendarTrigger><StartBoundary>{start:%Y-%m-%dT%H:%M:%S}</StartBoundary>"
            "<ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>")


def _hourly_trigger() -> str:
    start = (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return (f"<TimeTrigger><StartBoundary>{start:%Y-%m-%dT%H:%M:%S}</StartBoundary>"
            "<Repetition><Interval>PT1H</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>"
            "</TimeTrigger>")


def _logon_trigger() -> str:
    return f"<LogonTrigger><Delay>PT2M</Delay><UserId>{escape(_current_user())}</UserId></LogonTrigger>"


def _create_task_xml(name: str, xml: str):
    """Registers a task from XML (schtasks /XML). Raises with schtasks' message on failure."""
    fd, path = tempfile.mkstemp(suffix=".xml", prefix="am_task_")
    try:
        with os.fdopen(fd, "w", encoding="utf-16") as f:
            f.write(xml)
        r = _run(["schtasks", "/Create", "/F", "/TN", name, "/XML", path])
        if r.returncode != 0:
            raise RuntimeError(f"{name}: {(r.stderr or r.stdout).strip()}")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _register(name: str, xml: str, fallback_args: list, command: str):
    """XML first; the plain schtasks form if XML registration is refused, so nothing is lost on an odd machine."""
    try:
        _create_task_xml(name, xml)
    except Exception as e:
        log.warning("%s: XML registration failed (%s); registering the basic form.", name, str(e).strip()[:160])
        _create_task(name, fallback_args, command)


def is_outdated() -> bool:
    """True when the background tasks exist but were registered by an older version (no battery / wake settings)."""
    try:
        r = _run(["schtasks", "/Query", "/TN", TASK_DAILY, "/XML"], timeout=20)
    except Exception:
        return False
    return r.returncode == 0 and TASK_MARK not in (r.stdout or "")


def refresh_if_outdated() -> bool:
    """Re-registers tasks left by an older version so they get the laptop-friendly settings. Returns True if done."""
    if not is_outdated() or installed_owner():
        return False
    ok, msg = enable()
    log.info("Background tasks re-registered with the current settings: %s", msg)
    return ok


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
    owner = installed_owner()
    if owner:
        log.info("Background tasks belong to the installed app (%s); this source run leaves them alone.", owner)
        return True, "Background automation is on (run by the installed app)."
    try:
        check, remind = app_command("--check"), app_command("--remind")
        check_cmd, remind_cmd = _quote(check), _quote(remind)
        # the daily check wakes a sleeping PC, runs on battery, runs late if 19:00 was missed and retries a failed sync
        _register(TASK_DAILY, _task_xml(check, _daily_trigger(), wake=True, limit="PT30M", restart=True),
                  ["/SC", "DAILY", "/ST", "19:00"], check_cmd)
        # the hourly reminder must not wake the PC (it would do so every hour); it runs only while the PC is awake
        _register(TASK_HOURLY, _task_xml(remind, _hourly_trigger(), wake=False, limit="PT5M", restart=False),
                  ["/SC", "HOURLY", "/MO", "1"], remind_cmd)
        try:
            _register(TASK_LOGON, _task_xml(check, _logon_trigger(), wake=False, limit="PT30M", restart=False),
                      ["/SC", "ONLOGON", "/DELAY", "0002:00"], check_cmd)
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
