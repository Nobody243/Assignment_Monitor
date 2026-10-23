"""Paths, settings and logging shared by every part of the app.

Works both from source (python app.py) and as the packaged executable, where the
read-only resources live next to the exe and all writable data goes to %LOCALAPPDATA%.
"""
import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path

APP_NAME = "Assignment Monitor"
TAGLINE = "for Bahria University LMS"
APP_ID = "Nobody243.AssignmentMonitor"       # Windows AppUserModelID (taskbar grouping / toasts)
APP_VERSION = "1.5.5"
REPO_URL = "https://github.com/Nobody243/Assignment_Monitor"
RELEASES_URL = REPO_URL + "/releases/latest"
SITE_URL = "https://assignment-monitor.vercel.app"

FROZEN = bool(getattr(sys, "frozen", False))
SOURCE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", SOURCE_DIR))
ASSETS_DIR = RESOURCE_DIR / "assets"
DOCS_DIR = RESOURCE_DIR / "docs" if FROZEN else SOURCE_DIR   # PRIVACY.md etc. travel with the app

_home_override = os.environ.get("ASSIGNMENT_MONITOR_HOME")   # optional: keep all data in a chosen folder
# "cloud" when running on GitHub Actions from the student's own repository (see cloud.py): settings come from
# AM_<KEY> environment variables, nothing secret is written to disk, and there is no desktop to notify.
RUNNER = os.environ.get("ASSIGNMENT_MONITOR_RUNNER", "")
IN_CLOUD = RUNNER == "cloud"
# GitHub OAuth app used for the device sign-in of cloud checks (a public identifier, not a secret). Empty hides
# the feature.
GITHUB_CLIENT_ID = os.environ.get("AM_GITHUB_CLIENT_ID") or "Ov23ctd8HzseTPqZhf8Q"
PROJECT_REPO = "Nobody243/Assignment_Monitor"
if _home_override:
    BASE_DIR = Path(_home_override)
    ENV_PATH = BASE_DIR / "settings.env"
elif FROZEN:
    _local = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    BASE_DIR = _local / APP_NAME
    _legacy = _local / "Bahria LMS Monitor"
    if not BASE_DIR.exists() and _legacy.exists():
        try:
            _legacy.rename(BASE_DIR)          # keep data from the previous app name
        except OSError:
            pass
    ENV_PATH = BASE_DIR / "settings.env"
else:
    BASE_DIR = SOURCE_DIR
    ENV_PATH = BASE_DIR / ".env"
BASE_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = BASE_DIR / "data"
PROFILE_DIR = BASE_DIR / "chrome_profile"
BROWSERS_DIR = BASE_DIR / "browsers"
DB_PATH = DATA_DIR / "assignments.json"
META_PATH = DATA_DIR / "meta.json"
ATTENDANCE_PATH = DATA_DIR / "attendance.json"
EXAMS_PATH = DATA_DIR / "exams.json"
ANNOUNCEMENTS_PATH = DATA_DIR / "announcements.json"
REMINDERS_PATH = DATA_DIR / "reminders.json"
LECTURES_PATH = DATA_DIR / "lectures.json"
TIMETABLE_PATH = DATA_DIR / "timetable.json"
LOG_PATH = DATA_DIR / "app.log"

for _d in (DATA_DIR, PROFILE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Playwright looks for a downloaded Chromium here if Google Chrome is not installed.
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BROWSERS_DIR))

LOGIN_URL = "https://cms.bahria.edu.pk/Logins/Student/Login.aspx"
CMS_BASE_URL = "https://cms.bahria.edu.pk"
LMS_BASE_URL = "https://lms.bahria.edu.pk"
SSO_URL = f"{CMS_BASE_URL}/Sys/Common/GoToLMS.aspx"
ASSIGNMENTS_URL = f"{LMS_BASE_URL}/Student/Assignments.php"
ANNOUNCEMENTS_URL = f"{LMS_BASE_URL}/Student/Announcements.php"
LECTURES_URL = f"{LMS_BASE_URL}/Student/LectureNotes.php"
MISC_URL = f"{LMS_BASE_URL}/Student/Miscellaneous.php"
ATTENDANCE_URL = f"{CMS_BASE_URL}/Sys/Student/ClassAttendance/StudentWiseAttendance.aspx"
EXAMS_URL = f"{CMS_BASE_URL}/Sys/Student/ExamSeatingPlan/ExamSeats"
TIMETABLE_URL = f"{CMS_BASE_URL}/Sys/Student/CourseRegistration/TimeTable.aspx"

# (display name, CMS institute id). Order matters for the setup dropdown.
CAMPUSES = [
    ("Islamabad E-8 Campus", "1"),
    ("Islamabad H-11 Campus", "9"),
    ("Karachi Campus", "2"),
    ("Lahore Campus", "3"),
    ("Health Sciences Campus (Islamabad)", "12"),
    ("Health Sciences Campus (Karachi)", "6"),
    ("Bahria University College of Nursing", "13"),
    ("IPP (Karachi)", "5"),
    ("NCMPR", "4"),
    ("ODL", "14"),
]
CAMPUS_NAMES = [c[0] for c in CAMPUSES]
CAMPUS_ID_BY_NAME = {c[0]: c[1] for c in CAMPUSES}
CAMPUS_NAME_BY_ID = {c[1]: c[0] for c in CAMPUSES}


def campus_name(institute_id: str) -> str:
    return CAMPUS_NAME_BY_ID.get(str(institute_id), f"Campus #{institute_id}")


DEFAULTS = {
    "ENROLLMENT": "",
    "PASSWORD": "",
    "INSTITUTE_ID": "1",
    "NOTIFY_DAYS_AHEAD": 3,
    "ENABLE_VOICE": True,
    "ENABLE_WINDOWS_TOAST": True,
    "HEADLESS": True,
    "THEME": "dark",
    "CLOSE_TO_TRAY": True,
    "CHECK_UPDATES": True,
    "VOICE_NAME": "",
    "VOICE_VOLUME": 100,
    "VOICE_RATE": 0,
    "WINDOW_GEOMETRY": "",
    "TRACK_ATTENDANCE": True,
    "TRACK_EXAMS": True,
    "TRACK_ANNOUNCEMENTS": True,
    "ATTENDANCE_MIN": 75,
    "EXAM_REMIND_DAYS": 1,
    "TRACK_LECTURES": True,
    "TRACK_TIMETABLE": True,
    # phone, email and calendar (secrets are stored encrypted, like the password)
    "EMAIL_ENABLED": False,
    "EMAIL_TO": "",
    "EMAIL_USER": "",
    "EMAIL_HOST": "",
    "EMAIL_PORT": 587,
    "EMAIL_PASS": "",
    "PUSH_ENABLED": False,
    "PUSH_SUB": "",
    "PUSH_VAPID": "",
    "CALENDAR_ENABLED": False,
    "CALENDAR_INVITES": False,
    "LECTURES_DIR": "",
    "ANIMATIONS": True,
    # cloud checks (GitHub Actions in the student's own account); the token is a secret like the password
    "CLOUD_ENABLED": False,
    "CLOUD_REPO": "",
    "CLOUD_LOGIN": "",
    "CLOUD_VERSION": "",
    "CLOUD_HASH": "",
    "GITHUB_TOKEN": "",
}
_BOOL_KEYS = ("ENABLE_VOICE", "ENABLE_WINDOWS_TOAST", "HEADLESS", "CLOSE_TO_TRAY", "CHECK_UPDATES",
              "TRACK_ATTENDANCE", "TRACK_EXAMS", "TRACK_ANNOUNCEMENTS", "TRACK_LECTURES", "TRACK_TIMETABLE",
              "ANIMATIONS", "EMAIL_ENABLED", "PUSH_ENABLED", "CALENDAR_ENABLED", "CALENDAR_INVITES", "CLOUD_ENABLED")
_SECRET_KEYS = ("PASSWORD", "EMAIL_PASS", "PUSH_SUB", "PUSH_VAPID", "GITHUB_TOKEN")


def _coerce(key: str, val: str):
    """A setting's text form to its typed form (the rules the settings file uses)."""
    if key in _BOOL_KEYS:
        return val.lower() in ("true", "1", "yes")
    if key in _INT_KEYS:
        lo, hi = _INT_KEYS[key]
        try:
            return min(hi, max(lo, int(val)))
        except ValueError:
            return None
    if key == "THEME":
        return "light" if val.lower() == "light" else "dark"
    return val


def env_overrides() -> dict:
    """Settings given as AM_<KEY> environment variables (the cloud runner's way in; handy for tests too)."""
    out = {}
    for key in DEFAULTS:
        raw = os.environ.get(f"AM_{key}")
        if raw is None:
            continue
        val = _coerce(key, raw.strip())
        if val is not None:
            out[key] = val
    return out
_TEXT_KEYS = ("EMAIL_TO", "EMAIL_USER", "EMAIL_HOST", "CLOUD_REPO", "CLOUD_LOGIN", "CLOUD_VERSION", "CLOUD_HASH")
_INT_KEYS = {"NOTIFY_DAYS_AHEAD": (0, 60), "VOICE_VOLUME": (0, 100), "VOICE_RATE": (-5, 5),
             "ATTENDANCE_MIN": (50, 100), "EXAM_REMIND_DAYS": (0, 14), "EMAIL_PORT": (1, 65535)}


def app_command(*args: str) -> list:
    """The command line that runs this app in background mode (used for scheduled tasks)."""
    if FROZEN:
        return [sys.executable, *args]
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    return [str(exe), str(SOURCE_DIR / "app.py"), *args]


def _read_raw_env() -> dict:
    raw = {}
    if not ENV_PATH.exists():
        return raw
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                raw[key.strip()] = val.strip().strip('"').strip("'")
    return raw


def load_env() -> dict:
    """Loads settings, decrypting the password. A plain-text password left by an
    older version is migrated to the encrypted form on first load."""
    config = dict(DEFAULTS)
    raw = _read_raw_env()
    for key, val in raw.items():
        if key in _BOOL_KEYS:
            config[key] = val.lower() in ("true", "1", "yes")
        elif key in _INT_KEYS:
            lo, hi = _INT_KEYS[key]
            try:
                config[key] = min(hi, max(lo, int(val)))
            except ValueError:
                pass
        elif key in _SECRET_KEYS or key.endswith("_ENC"):
            continue
        elif key == "THEME":
            config[key] = "light" if val.lower() == "light" else "dark"
        else:
            config[key] = val

    password = ""
    if raw.get("PASSWORD_ENC"):
        try:
            from secure_store import decrypt_secret
            password = decrypt_secret(raw["PASSWORD_ENC"])
        except Exception as e:
            logging.getLogger("bahria.config").warning(
                "Stored password could not be decrypted (%s). Please sign in again.", e)
    if not password and raw.get("PASSWORD"):
        password = raw["PASSWORD"]
        config["PASSWORD"] = password
        try:
            save_env(config)
        except Exception:
            pass
    config["PASSWORD"] = password
    for key in _SECRET_KEYS[1:]:
        if raw.get(key + "_ENC"):
            try:
                from secure_store import decrypt_secret
                config[key] = decrypt_secret(raw[key + "_ENC"])
            except Exception as e:
                logging.getLogger("bahria.config").warning("Stored %s could not be decrypted (%s).", key, e)
    config.update(env_overrides())
    return config


def save_env(config: dict) -> None:
    """Writes settings with the password encrypted via Windows DPAPI. In the cloud nothing is written: the
    settings live in the repository's secrets and the state folder is committed, so a plain-text secret must
    never reach it."""
    if IN_CLOUD:
        return
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in config.items() if k in DEFAULTS})
    password = merged.pop("PASSWORD", "") or ""
    lines = [f"# {APP_NAME} settings. The password is encrypted for this Windows user only."]
    lines.append(f"ENROLLMENT={merged['ENROLLMENT']}")
    enc = ""
    if password:
        try:
            from secure_store import encrypt_secret
            enc = encrypt_secret(password)
        except Exception:
            enc = ""
    if enc:
        lines.append(f"PASSWORD_ENC={enc}")
    elif password:
        lines.append(f"PASSWORD={password}")
    lines.append(f"INSTITUTE_ID={merged['INSTITUTE_ID']}")
    lines.append(f"NOTIFY_DAYS_AHEAD={int(merged['NOTIFY_DAYS_AHEAD'])}")
    lines.append(f"THEME={merged['THEME']}")
    lines.append(f"VOICE_NAME={merged['VOICE_NAME']}")
    lines.append(f"VOICE_VOLUME={int(merged['VOICE_VOLUME'])}")
    lines.append(f"VOICE_RATE={int(merged['VOICE_RATE'])}")
    lines.append(f"ATTENDANCE_MIN={int(merged['ATTENDANCE_MIN'])}")
    lines.append(f"EXAM_REMIND_DAYS={int(merged['EXAM_REMIND_DAYS'])}")
    if merged.get("LECTURES_DIR"):
        lines.append(f"LECTURES_DIR={merged['LECTURES_DIR']}")
    if merged.get("WINDOW_GEOMETRY"):
        lines.append(f"WINDOW_GEOMETRY={merged['WINDOW_GEOMETRY']}")
    for key in _TEXT_KEYS:
        if merged.get(key):
            lines.append(f"{key}={merged[key]}")
    lines.append(f"EMAIL_PORT={int(merged['EMAIL_PORT'])}")
    for key in _SECRET_KEYS[1:]:
        value = merged.get(key) or ""
        if value:
            try:
                from secure_store import encrypt_secret
                lines.append(f"{key}_ENC={encrypt_secret(value)}")
            except Exception:
                pass
    for key in _BOOL_KEYS:
        lines.append(f"{key}={'True' if merged[key] else 'False'}")
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def lectures_dir(config: dict = None) -> Path:
    """Where downloaded lecture files go: the user's choice, else Documents / Assignment Monitor / Lectures."""
    config = config or load_env()
    custom = (config.get("LECTURES_DIR") or "").strip()
    if custom:
        return Path(custom)
    docs = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents"
    return docs / APP_NAME / "Lectures"


def has_credentials(config: dict = None) -> bool:
    config = config or load_env()
    return bool(config.get("ENROLLMENT", "").strip() and config.get("PASSWORD", "").strip())


def load_meta() -> dict:
    if META_PATH.exists():
        try:
            with open(META_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_meta(meta: dict) -> None:
    meta = dict(meta)
    meta["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


_LOGGING_READY = False


def setup_logging(to_console: bool = False) -> logging.Logger:
    """Rotating log file at data/app.log, optionally mirrored to the console."""
    global _LOGGING_READY
    root = logging.getLogger("bahria")
    if not _LOGGING_READY:
        root.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
        fh = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=512_000, backupCount=2, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
        _LOGGING_READY = True
    if to_console and sys.stdout is not None and not any(
            isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(sh)
    return root
