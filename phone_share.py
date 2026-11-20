"""Share with my phone: a PC that does not use Cloud checks can still feed the phone app.

After each successful check the PC writes the phone's `state/summary.json` (built by `summary.build`, schema v1) into the
student's own PRIVATE GitHub repository `assignment-monitor-cloud`, the same file and place the cloud runner writes. The
phone app reads it with the student's GitHub sign-in. Nothing else goes into the repository: no workflow, no secrets and
no password (the portal password never leaves the PC).

  - Sign-in is GitHub's device flow (the same one Cloud checks uses) asking only for the `repo` permission, the
    narrowest GitHub offers for reading and writing a private repository. The token is kept DPAPI-encrypted like the
    other secrets, is never logged and never leaves this module except in requests to api.github.com.
  - If Cloud checks is on, the cloud runner already writes the file, so the PC does not: sharing then reports
    "already shared through Cloud checks".
  - A push never fails or slows a check: it runs in its own thread, errors are logged and remembered for the Settings
    page, and an unchanged summary (ignoring its generated_at time) is not sent again.
"""
import hashlib
import json
import logging
import threading
from datetime import datetime

import cloud
from config import GITHUB_CLIENT_ID, IN_CLOUD, load_env, save_env

log = logging.getLogger("bahria.phone")

SUMMARY_PATH = "state/summary.json"
SCOPES = "repo"
_lock = threading.Lock()


def available() -> bool:
    return bool(GITHUB_CLIENT_ID)


def covered_by_cloud(env: dict | None = None) -> bool:
    return cloud.enabled(env if env is not None else load_env())


def is_on(env: dict | None = None) -> bool:
    env = env if env is not None else load_env()
    return bool(env.get("PHONE_SHARE") and env.get("PHONE_SHARE_REPO") and env.get("PHONE_SHARE_TOKEN"))


def is_active(env: dict | None = None) -> bool:
    """On, and the PC is the one that writes the file (not the cloud runner)."""
    env = env if env is not None else load_env()
    return is_on(env) and not covered_by_cloud(env) and not IN_CLOUD


def build_summary() -> dict:
    import engine
    import summary
    return summary.build(engine.build_state())


def content_hash(data: dict) -> str:
    """A hash of the summary without its generated_at time, so a check that found nothing new sends nothing."""
    body = {k: v for k, v in data.items() if k != "generated_at"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:32]


def device_start() -> dict:
    return cloud.device_start(SCOPES)


def enable(token: str, progress=None) -> dict:
    """Signs in with a fresh token, makes sure the private repository exists and turns sharing on. Returns
    {"repo", "login", "pushed", "covered_by_cloud"}. Raises cloud.CloudError with a message fit to show."""
    say = progress or (lambda m: None)
    say("Checking the GitHub sign-in…")
    login = cloud.whoami(token)
    say("Preparing your private repository…")
    repo = cloud.ensure_repo(token, login)
    env = load_env()
    env["PHONE_SHARE"] = True
    env["PHONE_SHARE_REPO"] = repo
    env["PHONE_SHARE_LOGIN"] = login
    env["PHONE_SHARE_TOKEN"] = token
    env["PHONE_SHARE_HASH"] = ""
    env["PHONE_SHARE_ERR"] = ""
    save_env(env)
    log.info("Sharing with the phone is on (%s).", repo)
    covered = covered_by_cloud(env)
    pushed = False
    if not covered:
        say("Sending the first summary…")
        pushed = bool(push(force=True).get("pushed"))
    return {"repo": repo, "login": login, "pushed": pushed, "covered_by_cloud": covered}


def disable() -> None:
    """Turns sharing off and forgets the sign-in. The repository and the file already in it are left alone."""
    env = load_env()
    for key, value in (("PHONE_SHARE", False), ("PHONE_SHARE_TOKEN", ""), ("PHONE_SHARE_REPO", ""), ("PHONE_SHARE_LOGIN", ""),
                       ("PHONE_SHARE_HASH", ""), ("PHONE_SHARE_ERR", "")):
        env[key] = value
    save_env(env)
    log.info("Sharing with the phone is off.")


def push(force: bool = False) -> dict:
    """Writes the summary to the repository when sharing is on and the PC is the writer. Returns
    {"pushed": bool, "reason": str}; never raises."""
    with _lock:
        try:
            env = load_env()
            if not is_on(env):
                return {"pushed": False, "reason": "off"}
            if covered_by_cloud(env) or IN_CLOUD:
                return {"pushed": False, "reason": "cloud"}
            data = build_summary()
            digest = content_hash(data)
            if not force and digest == env.get("PHONE_SHARE_HASH"):
                return {"pushed": False, "reason": "unchanged"}
            payload = json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8")
            cloud.put_file(env["PHONE_SHARE_TOKEN"], env["PHONE_SHARE_REPO"], SUMMARY_PATH, payload, "summary for the phone")
            env["PHONE_SHARE_HASH"] = digest
            env["PHONE_SHARE_AT"] = datetime.now().isoformat(timespec="seconds")
            env["PHONE_SHARE_ERR"] = ""
            save_env(env)
            log.info("Shared the summary with the phone.")
            return {"pushed": True, "reason": "sent"}
        except Exception as e:  # noqa: BLE001 - nothing here may fail a check
            message = " ".join(str(e).split())[:200]
            log.warning("Could not share the summary with the phone: %s", message)
            try:
                env = load_env()
                env["PHONE_SHARE_ERR"] = message
                save_env(env)
            except Exception:  # noqa: BLE001
                pass
            return {"pushed": False, "reason": "error", "error": message}


def share_after_sync(env: dict | None = None) -> threading.Thread | None:
    """Called after a successful check: starts the push in its own thread and returns at once (None when there is
    nothing to do). The thread is not a daemon, so a scheduled check that is about to exit lets it finish."""
    try:
        if not is_active(env):
            return None
    except Exception:  # noqa: BLE001
        return None
    t = threading.Thread(target=push, name="phone-share", daemon=False)
    t.start()
    return t


def status(env: dict | None = None) -> dict:
    env = env if env is not None else load_env()
    return {
        "available": available(),
        "enabled": is_on(env),
        "covered_by_cloud": covered_by_cloud(env),
        "login": env.get("PHONE_SHARE_LOGIN", ""),
        "repo": env.get("PHONE_SHARE_REPO", ""),
        "last": env.get("PHONE_SHARE_AT", "") or None,
        "error": env.get("PHONE_SHARE_ERR", "") or None,
    }
