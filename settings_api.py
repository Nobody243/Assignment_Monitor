"""
Settings for the new interface, served by engine.py.

What this module guarantees:
  * a secret never leaves the engine: the view says only whether a password, an email app password or a GitHub
    sign-in exists, and a write-only field accepts a new value (an empty one means "leave it alone");
  * a settings update is checked against an allow-list with types and bounds, so the line-based settings file can
    never be given a line break or an unknown key;
  * the background tasks of an installed copy are never touched by a source-tree run, for turning on or off.

Routes return (status, json) for an immediate answer, or a function to run as a background job.
"""

import base64
import io
import logging
import re
import threading
from pathlib import Path
from typing import Callable

import automation
import channels
import cloud
import config
import tracker
import updater
from config import (
    APP_NAME,
    APP_VERSION,
    CAMPUS_NAME_BY_ID,
    CAMPUSES,
    FROZEN,
    GITHUB_CLIENT_ID,
    REPO_URL,
    SITE_URL,
    TAGLINE,
    load_env,
    save_env,
)

log = logging.getLogger("settings")

# ---------------------------------------------------------------------------- the allow-list: ui name -> (settings key, type)
FIELDS: dict[str, tuple[str, str]] = {
    "enrollment": ("ENROLLMENT", "enrollment"),
    "institute_id": ("INSTITUTE_ID", "campus"),
    "password": ("PASSWORD", "secret"),
    "voice": ("ENABLE_VOICE", "bool"),
    "toast": ("ENABLE_WINDOWS_TOAST", "bool"),
    "notify_days_ahead": ("NOTIFY_DAYS_AHEAD", "int"),
    "voice_name": ("VOICE_NAME", "text"),
    "voice_volume": ("VOICE_VOLUME", "int"),
    "voice_rate": ("VOICE_RATE", "int"),
    "track_attendance": ("TRACK_ATTENDANCE", "bool"),
    "track_exams": ("TRACK_EXAMS", "bool"),
    "track_announcements": ("TRACK_ANNOUNCEMENTS", "bool"),
    "track_lectures": ("TRACK_LECTURES", "bool"),
    "track_timetable": ("TRACK_TIMETABLE", "bool"),
    "track_results": ("TRACK_RESULTS", "bool"),
    "attendance_min": ("ATTENDANCE_MIN", "int"),
    "exam_remind_days": ("EXAM_REMIND_DAYS", "int"),
    "close_to_tray": ("CLOSE_TO_TRAY", "bool"),
    "check_updates": ("CHECK_UPDATES", "bool"),
    "email_enabled": ("EMAIL_ENABLED", "bool"),
    "email_to": ("EMAIL_TO", "email"),
    "email_pass": ("EMAIL_PASS", "secret"),
    "email_host": ("EMAIL_HOST", "host"),
    "email_port": ("EMAIL_PORT", "int"),
    "push_enabled": ("PUSH_ENABLED", "bool"),
    "calendar_enabled": ("CALENDAR_ENABLED", "bool"),
    "calendar_invites": ("CALENDAR_INVITES", "bool"),
    "lectures_dir": ("LECTURES_DIR", "path"),
    "animations": ("ANIMATIONS", "bool"),
    "remind_leads": ("REMIND_LEADS", "leads"),
    "setup_done": ("SETUP_DONE", "bool"),
    "weekly_summary": ("WEEKLY_SUMMARY", "bool"),
    "digest_enabled": ("DIGEST_ENABLED", "bool"),
}
_ENROLLMENT = re.compile(r"^[A-Za-z0-9\-]{3,30}$")
_HOST = re.compile(r"^[A-Za-z0-9.\-]{0,253}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_text(v, limit=300) -> str:
    if not isinstance(v, str):
        raise ValueError("must be text")
    if "\n" in v or "\r" in v or "\x00" in v:
        raise ValueError("must be a single line")
    if len(v) > limit:
        raise ValueError("is too long")
    return v.strip()


def coerce(name: str, value):
    """One value, checked and converted for its setting. Raises ValueError with a reason."""
    key, kind = FIELDS[name]
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError("must be true or false")
        return value
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be a whole number")
        lo, hi = config._INT_KEYS[key]
        if not lo <= value <= hi:
            raise ValueError(f"must be between {lo} and {hi}")
        return value
    if kind == "secret":
        v = value if isinstance(value, str) else ""
        if "\n" in v or "\r" in v or len(v) > 300:
            raise ValueError("is not valid")
        return v
    if kind == "leads":
        v = _clean_text(value, 40).lower()
        if v in ("off", "none", ""):
            return "off"
        parts = [p.strip() for p in v.split(",")]
        if not all(p.isdigit() and 1 <= int(p) <= 168 for p in parts) or len(parts) > 6:
            raise ValueError("must be whole hours between 1 and 168, separated by commas")
        return ",".join(str(n) for n in sorted({int(p) for p in parts}, reverse=True))
    if kind == "campus":
        v = _clean_text(value, 10)
        if v not in CAMPUS_NAME_BY_ID:
            raise ValueError("is not a known campus")
        return v
    v = _clean_text(value, 500 if kind == "path" else 300)
    if kind == "enrollment" and not _ENROLLMENT.match(v):
        raise ValueError("looks wrong (letters, digits and dashes only)")
    if kind == "email" and v and not _EMAIL.match(v):
        raise ValueError("is not an email address")
    if kind == "host" and not _HOST.match(v):
        raise ValueError("is not a host name")
    if kind == "path" and v and not Path(v).is_absolute():
        raise ValueError("must be a full folder path")
    return v


# ---------------------------------------------------------------------------- view
def view() -> dict:
    """Everything the Settings page shows. Secrets appear only as yes/no."""
    env = load_env()
    push_device = ""
    try:
        push_device = channels.push_device(env) if env.get("PUSH_SUB") else ""
    except Exception:  # noqa: BLE001
        pass
    return {
        "account": {
            "enrollment": env["ENROLLMENT"],
            "institute_id": str(env["INSTITUTE_ID"]),
            "campus": config.campus_name(env["INSTITUTE_ID"]),
            "password_set": bool(env["PASSWORD"]),
        },
        "campuses": [{"id": cid, "name": name} for name, cid in CAMPUSES],
        "setup_done": env["SETUP_DONE"],
        "appearance": {"animations": env["ANIMATIONS"]},
        "alerts": {
            "voice": env["ENABLE_VOICE"],
            "toast": env["ENABLE_WINDOWS_TOAST"],
            "notify_days_ahead": env["NOTIFY_DAYS_AHEAD"],
            "voice_name": env["VOICE_NAME"],
            "voice_volume": env["VOICE_VOLUME"],
            "voice_rate": env["VOICE_RATE"],
            "weekly_summary": env["WEEKLY_SUMMARY"],
            "digest_enabled": env["DIGEST_ENABLED"],
        },
        "tracking": {
            "track_attendance": env["TRACK_ATTENDANCE"],
            "track_exams": env["TRACK_EXAMS"],
            "track_announcements": env["TRACK_ANNOUNCEMENTS"],
            "track_lectures": env["TRACK_LECTURES"],
            "track_timetable": env["TRACK_TIMETABLE"],
            "track_results": env["TRACK_RESULTS"],
            "attendance_min": env["ATTENDANCE_MIN"],
            "exam_remind_days": env["EXAM_REMIND_DAYS"],
            "remind_leads": config.remind_leads(env["REMIND_LEADS"]),
        },
        "background": {
            "close_to_tray": env["CLOSE_TO_TRAY"],
            "check_updates": env["CHECK_UPDATES"],
            "lectures_dir": env["LECTURES_DIR"],
            "downloads_default": str(config.lectures_dir({"LECTURES_DIR": ""})),
            "starts_with_windows": automation.starts_with_windows(),
            "automatic_checks": automation.is_enabled(),
            "owned_by_installed_app": bool(automation.installed_owner()),
        },
        "channels": {
            "email_enabled": env["EMAIL_ENABLED"],
            "email_to": env["EMAIL_TO"],
            "email_pass_set": bool(env["EMAIL_PASS"]),
            "email_host": env["EMAIL_HOST"],
            "email_port": env["EMAIL_PORT"],
            "push_enabled": env["PUSH_ENABLED"],
            "push_paired": bool(env["PUSH_SUB"]),
            "push_device": push_device,
            "calendar_enabled": env["CALENDAR_ENABLED"],
            "calendar_invites": env["CALENDAR_INVITES"],
        },
        "about": {
            "version": APP_VERSION,
            "tagline": TAGLINE,
            "installed": bool(FROZEN),
            "repo": REPO_URL,
            "site": SITE_URL,
            "author": "Nobody243",
            "license": "MIT",
        },
        "cloud": {
            "available": bool(GITHUB_CLIENT_ID),
            "enabled": cloud.enabled(env),
            "repo": env["CLOUD_REPO"],
            "login": env["CLOUD_LOGIN"],
        },
    }


# ---------------------------------------------------------------------------- update
def apply_patch(patch) -> tuple[dict, dict]:
    """Validates and saves a partial update. Returns (changed, errors); nothing is saved if anything is invalid."""
    if not isinstance(patch, dict):
        return {}, {"_": "expected an object"}
    errors, values = {}, {}
    for name, raw in patch.items():
        if name not in FIELDS:
            errors[name] = "unknown setting"
            continue
        try:
            values[name] = coerce(name, raw)
        except ValueError as e:
            errors[name] = f"{name.replace('_', ' ')} {e}"
    if errors:
        return {}, errors
    env = load_env()
    changed = {}
    for name, v in values.items():
        key, kind = FIELDS[name]
        if kind == "secret" and v == "":
            continue  # an empty secret field means "keep what is stored"
        if key == "PUSH_ENABLED" and v and not env.get("PUSH_SUB"):
            errors[name] = "pair a phone first"
            continue
        env[key] = v
        changed[name] = "set" if kind == "secret" else v
        if key == "EMAIL_TO":
            env["EMAIL_USER"] = v
    if errors:
        return {}, errors
    if changed:
        save_env(env)
        _cloud_sync_later()
    return changed, {}


_sync_timer: threading.Timer | None = None


def _cloud_sync_later() -> None:
    """Changed settings reach the cloud copy a few seconds after the last change, off the request thread."""
    global _sync_timer
    try:
        if not cloud.enabled(load_env()):
            return
    except Exception:  # noqa: BLE001
        return
    if _sync_timer:
        _sync_timer.cancel()
    _sync_timer = threading.Timer(3.0, lambda: cloud.sync_secrets(load_env()))
    _sync_timer.daemon = True
    _sync_timer.start()


# ---------------------------------------------------------------------------- actions
def _flag(qs, name="enable") -> bool:
    return (qs.get(name) or ["0"])[0] == "1"


def account_verify(qs, body):
    import lms_scraper

    def job(progress):
        progress("Signing in…")
        return lms_scraper.verify_login()

    return job


def automation_set(qs, body):
    want = _flag(qs)
    owner = automation.installed_owner()
    if owner and not want:
        return 409, {"error": "These background tasks belong to the installed app. Turn them off there."}

    def job(progress):
        progress("Working…")
        ok, msg = automation.enable() if want else automation.disable()
        return {"ok": bool(ok), "message": msg or ("Automatic checks are on." if want else "Automatic checks are off.")}

    return job


def startup_set(qs, body):
    ok = automation.set_start_with_windows(_flag(qs))
    return 200, {"ok": bool(ok), "starts_with_windows": automation.starts_with_windows()}


def test_alert(qs, body):
    from notifier import send_toast, speak_voice

    def run():
        send_toast(APP_NAME, "Test alert: notifications are working.")
        speak_voice("Assignment Monitor alerts are working.", force=True)

    threading.Thread(target=run, daemon=True).start()
    return 202, {"ok": True}


def test_email(qs, body):
    env = load_env()
    if not env.get("EMAIL_TO") or not env.get("EMAIL_PASS"):
        return 422, {"error": "Enter your address and an app password first."}

    def job(progress):
        progress("Sending…")
        try:
            channels.send_email(f"{APP_NAME} is connected", "This is the test email. Alerts from the app will arrive like this.", env)
            return {"ok": True, "message": "Sent. Check your inbox."}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "message": f"Failed: {str(e)[:140]}"}

    return job


def voices(qs=None, body=None):
    from notifier import list_voices

    return 200, {"voices": list_voices()}


def voice_preview(qs, body):
    import json
    from notifier import speak_voice

    try:
        p = json.loads(body or b"{}")
        voice, volume, rate = (
            coerce("voice_name", p.get("voice_name", "")),
            coerce("voice_volume", p.get("voice_volume", 100)),
            coerce("voice_rate", p.get("voice_rate", 0)),
        )
    except (ValueError, TypeError) as e:
        return 400, {"error": str(e)}
    threading.Thread(
        target=lambda: speak_voice("This is how your assignment reminders will sound.", force=True, voice=voice, volume=volume, rate=rate),
        daemon=True,
    ).start()
    return 202, {"ok": True}


# -- phone pairing
_pairing: dict | None = None


def _qr(text: str) -> str:
    import qrcode

    qr = qrcode.QRCode(border=1, box_size=8)
    qr.add_data(text)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="#14161b", back_color="#ffffff").convert("RGB").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def pair_start(qs, body):
    global _pairing
    _pairing = channels.pairing_start(load_env())
    return 200, {"url": _pairing["url"], "code": _pairing["code"], "qr": _qr(_pairing["url"])}


def pair_poll(qs, body):
    global _pairing
    if not _pairing:
        return 409, {"error": "No pairing is in progress."}
    sub = channels.pairing_poll(_pairing, timeout=4.0)
    if sub:
        channels.save_subscription(sub)
        _pairing = None
        return 200, {"status": "paired", "device": channels.push_device(load_env())}
    return 200, {"status": "opened" if _pairing.get("opened") else "waiting"}


def pair_cancel(qs, body):
    global _pairing
    _pairing = None
    return 200, {"ok": True}


def unpair(qs, body):
    channels.save_subscription(None)
    return 200, {"ok": True}


def test_push(qs, body):
    env = load_env()
    if not channels.push_ready(env):
        return 422, {"error": "Pair a phone first."}

    def job(progress):
        progress("Sending…")
        try:
            channels.send_push(APP_NAME, "Test: your phone is connected.", env=env)
            return {"ok": True, "message": "Sent. It should arrive on your phone in a moment."}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "message": f"Failed: {str(e)[:140]}"}

    return job


# -- cloud checks (GitHub Actions in the student's own account)
_flow: dict | None = None
_token: str | None = None


def cloud_start(qs, body):
    global _flow, _token
    try:
        _flow, _token = cloud.device_start(), None
    except cloud.CloudError as e:
        return 400, {"error": str(e)}
    return 200, {
        "user_code": _flow["user_code"],
        "verification_uri": _flow["verification_uri"],
        "interval": int(_flow.get("interval", 5)),
        "expires_in": int(_flow.get("expires_in", 900)),
    }


def cloud_poll(qs, body):
    global _token
    if not _flow:
        return 409, {"error": "Start the sign-in first."}
    try:
        token = cloud.device_poll(_flow)
    except cloud.CloudError as e:
        return 400, {"error": str(e)}
    if token:
        _token = token
        return 200, {"status": "ready"}
    return 200, {"status": "pending", "interval": int(_flow.get("interval", 5))}


def cloud_setup(qs, body):
    global _token, _flow
    token = _token
    if not token:
        return 409, {"error": "Sign in to GitHub first."}

    def job(progress):
        global _token, _flow
        try:
            info = cloud.setup(token, load_env(), progress)
        except cloud.CloudError as e:
            return {"ok": False, "message": str(e)}
        _token = _flow = None
        return {"ok": True, "message": f"Cloud checks are on, as {info['login']}.", "repo": info["repo"], "url": info.get("run_url", "")}

    return job


def cloud_disable(qs, body):
    def job(progress):
        url = cloud.teardown(load_env(), progress)
        return {"ok": True, "message": "Cloud checks are off.", "url": url}

    return job


def cloud_run(qs, body):
    try:
        cloud.run_now(load_env())
    except Exception as e:  # noqa: BLE001
        return 400, {"error": str(e)[:160]}
    return 202, {"ok": True}


def cloud_status(qs=None, body=None):
    env = load_env()
    if not cloud.enabled(env):
        return 200, {"enabled": False}
    out = {"enabled": True, "login": env.get("CLOUD_LOGIN", ""), "repo": env.get("CLOUD_REPO", "")}
    try:
        run = cloud.last_run(env)
        if run:
            out["last"] = {"when": run["when"].isoformat(), "status": run["status"], "conclusion": run["conclusion"], "url": run["url"]}
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)[:100]
    return 200, out


def update_check(qs=None, body=None):
    """Asks GitHub for the latest release. {"version", "newer", "page"} or {"error"} when it cannot be reached."""
    info = updater.check_latest()
    if not info:
        return 200, {"error": "GitHub could not be reached."}
    return 200, {"version": info["version"], "newer": bool(info["newer"]), "page": info["page"], "current": APP_VERSION}


def update_install(qs, body):
    """Downloads the newest installer, checks it against the checksum the release publishes, and starts it. The installer
    closes this app, replaces it and starts it again."""
    if not FROZEN:
        return 409, {"error": "Updates install into the installed app. This copy runs from source."}

    def job(progress):
        progress("Looking for the newest version…")
        info = updater.check_latest()
        if not info:
            return {"ok": False, "message": "GitHub could not be reached."}
        if not info["newer"] or not info.get("setup_url"):
            return {"ok": True, "message": "You already have the latest version."}
        progress(f"Downloading version {info['version']}…")
        want = updater.fetch_checksum(info["setup_url"])

        def pct(done, total):
            progress(f"Downloading version {info['version']}… {int(done * 100 / total)}%" if total else "Downloading…")
        path = updater.download_installer(info["setup_url"], pct, expected_sha256=want)
        progress("Starting the installer…")
        updater.run_installer(path)
        return {"ok": True, "message": f"Installing version {info['version']}. The app restarts by itself.", "restarting": True}

    return job


def clear_data(qs, body):
    tracker.clear_stored_assignments()
    return 200, {"ok": True}


def update(qs, body):
    import json

    try:
        patch = json.loads(body or b"{}")
    except ValueError:
        return 400, {"error": "bad request"}
    changed, errors = apply_patch(patch)
    if errors:
        return 422, {"errors": errors}
    return 200, {"changed": list(changed), "settings": view()}


# ---------------------------------------------------------------------------- route tables (engine.py dispatches on these)
Route = Callable[[dict, bytes], object]
GET: dict[str, Route] = {
    "/api/settings": lambda qs, body: (200, view()),
    "/api/voices": voices,
    "/api/cloud/status": cloud_status,
    "/api/update": update_check,
}
POST: dict[str, tuple[str, Route]] = {
    "/api/settings": ("settings", update),
    "/api/update/install": ("update", update_install),
    "/api/account/verify": ("verify", account_verify),
    "/api/automation": ("automation", automation_set),
    "/api/startup": ("startup", startup_set),
    "/api/test/alert": ("alert", test_alert),
    "/api/test/email": ("email", test_email),
    "/api/test/push": ("push", test_push),
    "/api/voice/preview": ("voice", voice_preview),
    "/api/pair/start": ("pair", pair_start),
    "/api/pair/poll": ("pair", pair_poll),
    "/api/pair/cancel": ("pair", pair_cancel),
    "/api/unpair": ("pair", unpair),
    "/api/cloud/start": ("cloud", cloud_start),
    "/api/cloud/poll": ("cloud", cloud_poll),
    "/api/cloud/setup": ("cloud", cloud_setup),
    "/api/cloud/disable": ("cloud", cloud_disable),
    "/api/cloud/run": ("cloud", cloud_run),
    "/api/data/clear": ("data", clear_data),
}

__all__ = ["view", "apply_patch", "GET", "POST", "coerce", "FIELDS"]
