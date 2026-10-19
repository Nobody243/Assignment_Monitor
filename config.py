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
APP_VERSION = "2.1.0"
REPO_URL = "https://github.com/Nobody243/Assignment_Monitor"
RELEASES_URL = REPO_URL + "/releases/latest"

FROZEN = bool(getattr(sys, "frozen", False))
SOURCE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", SOURCE_DIR))
ASSETS_DIR = RESOURCE_DIR / "assets"

if FROZEN:
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

DATA_DIR = BASE_DIR / "data"
PROFILE_DIR = BASE_DIR / "chrome_profile"
BROWSERS_DIR = BASE_DIR / "browsers"
DB_PATH = DATA_DIR / "assignments.json"
META_PATH = DATA_DIR / "meta.json"
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
}
_BOOL_KEYS = ("ENABLE_VOICE", "ENABLE_WINDOWS_TOAST", "HEADLESS", "CLOSE_TO_TRAY")


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
        elif key == "NOTIFY_DAYS_AHEAD":
            try:
                config[key] = max(0, int(val))
            except ValueError:
                pass
        elif key in ("PASSWORD", "PASSWORD_ENC"):
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
    return config


def save_env(config: dict) -> None:
    """Writes settings with the password encrypted via Windows DPAPI."""
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
    for key in _BOOL_KEYS:
        lines.append(f"{key}={'True' if merged[key] else 'False'}")
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


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
