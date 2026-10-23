"""Cloud checks: the same check job, run on GitHub's machines from a private repository in the student's own
GitHub account, so alerts still arrive when the PC is off.

What lives where
  - The student's private repository (`assignment-monitor-cloud`) holds one workflow file, a README and the
    `state/` folder (the cached assignments, attendance, exams, announcements, lectures and timetable, the same
    JSON files the PC keeps). The workflow runs twice a day, checks out this project at the pinned release and
    runs `cloud_check.py`, then commits the updated state back.
  - The portal login and the channel keys (phone subscription, push signing key, mail password) are stored as
    GitHub Actions secrets on that repository, encrypted with the repository's public key before they leave the
    PC (libsodium sealed box, the only form GitHub's API accepts).
  - The PC keeps the GitHub token encrypted with DPAPI like the other secrets. Scopes: `repo` (private repo,
    contents, secrets) and `workflow` (writing the workflow file).

Nothing here runs a server of ours: the PC talks to api.github.com and github.com only.
"""
import base64
import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from config import (APP_NAME, APP_VERSION, DATA_DIR, GITHUB_CLIENT_ID, PROJECT_REPO, SITE_URL, load_env, save_env)

log = logging.getLogger("bahria.cloud")

API = "https://api.github.com"
REPO_NAME = "assignment-monitor-cloud"
WORKFLOW_PATH = ".github/workflows/check.yml"
SCOPES = "repo workflow"
# Settings travel to the runner as AM_<KEY> environment variables. The secret ones are repository secrets; the
# plain ones are written into the workflow file itself. (GitHub masks every occurrence of a secret's value in the
# logs, so a campus id of "1" stored as a secret would turn every "1" in the log into ***.)
SECRET_KEYS = ("ENROLLMENT", "PASSWORD", "PUSH_SUB", "PUSH_VAPID", "EMAIL_PASS")
PLAIN_KEYS = ("INSTITUTE_ID", "NOTIFY_DAYS_AHEAD", "ATTENDANCE_MIN", "EXAM_REMIND_DAYS",
              "TRACK_ATTENDANCE", "TRACK_EXAMS", "TRACK_ANNOUNCEMENTS", "TRACK_LECTURES", "TRACK_TIMETABLE",
              "PUSH_ENABLED", "EMAIL_ENABLED", "EMAIL_TO", "EMAIL_USER", "EMAIL_HOST", "EMAIL_PORT")
CLOUD_KEYS = SECRET_KEYS + PLAIN_KEYS
STATE_FILES = ("assignments.json", "attendance.json", "exams.json", "announcements.json", "lectures.json",
               "timetable.json", "reminders.json", "meta.json")


class CloudError(RuntimeError):
    pass


# ---------------------------------------------------------------------------- HTTP
def job_log(token: str, repo: str, job_id: int) -> str:
    """A finished job's log text. GitHub answers with a redirect to a signed storage URL that must be fetched
    without the Authorization header (the storage rejects it)."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(f"{API}/repos/{repo}/actions/jobs/{job_id}/logs",
                                 headers={"Authorization": f"Bearer {token}", "User-Agent": APP_NAME})
    try:
        with opener.open(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 307) and e.headers.get("Location"):
            with urllib.request.urlopen(e.headers["Location"], timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        raise CloudError(f"GitHub answered {e.code} for the log.") from None


def _request(method: str, url: str, token: str | None = None, body: dict | None = None, form: bool = False,
             timeout: int = 30) -> tuple[int, dict | list | str, dict]:
    data = None
    headers = {"Accept": "application/json" if form else "application/vnd.github+json", "User-Agent": APP_NAME,
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            status, hdrs = r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        raw, status, hdrs = e.read(), e.code, dict(e.headers)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise CloudError(f"GitHub could not be reached ({str(e)[:80]}). Check the internet connection.") from None
    text = raw.decode("utf-8", "replace")
    try:
        parsed = json.loads(text) if text else {}
    except ValueError:
        parsed = text
    return status, parsed, hdrs


def api(token: str, method: str, path: str, body: dict | None = None, ok=(200, 201, 204)) -> dict | list:
    status, data, _ = _request(method, API + path, token, body)
    if status not in ok:
        msg = data.get("message", str(data)[:200]) if isinstance(data, dict) else str(data)[:200]
        if status == 401:
            msg = "GitHub no longer accepts the saved sign-in. Set up cloud checks again."
        raise CloudError(f"GitHub answered {status}: {msg}")
    return data


# ---------------------------------------------------------------------------- device sign-in
def device_start() -> dict:
    """Begins GitHub's device flow. Returns {device_code, user_code, verification_uri, interval, expires_in}."""
    if not GITHUB_CLIENT_ID:
        raise CloudError("This build has no GitHub client id; cloud checks are not available.")
    status, data, _ = _request("POST", "https://github.com/login/device/code", form=True,
                               body={"client_id": GITHUB_CLIENT_ID, "scope": SCOPES})
    if status != 200 or not isinstance(data, dict) or "device_code" not in data:
        raise CloudError(f"GitHub did not start the sign-in ({status}): {str(data)[:160]}")
    return data


def device_poll(flow: dict) -> str | None:
    """One poll of the device flow. Returns the token once the student has approved, None while waiting; raises
    when the code expired or the request was denied. Respects GitHub's slow_down by bumping flow['interval']."""
    status, data, _ = _request("POST", "https://github.com/login/oauth/access_token", form=True,
                               body={"client_id": GITHUB_CLIENT_ID, "device_code": flow["device_code"],
                                     "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
    if isinstance(data, dict) and data.get("access_token"):
        return data["access_token"]
    err = data.get("error", "") if isinstance(data, dict) else ""
    if err == "authorization_pending":
        return None
    if err == "slow_down":
        flow["interval"] = int(data.get("interval", flow.get("interval", 5))) + 1
        return None
    if err == "expired_token":
        raise CloudError("The code expired. Start again to get a new one.")
    if err == "access_denied":
        raise CloudError("The request was declined on GitHub.")
    raise CloudError(f"GitHub sign-in failed: {err or str(data)[:120]}")


def whoami(token: str) -> str:
    return api(token, "GET", "/user")["login"]


# ---------------------------------------------------------------------------- repository and files
def ensure_repo(token: str, login: str) -> str:
    """The student's private repository, created on first use. Returns 'login/name'."""
    full = f"{login}/{REPO_NAME}"
    status, data, _ = _request("GET", f"{API}/repos/{full}", token)
    if status == 200:
        if not data.get("private"):
            raise CloudError(f"The repository {full} exists but is public. Make it private or delete it, then retry.")
        return full
    if status != 404:
        raise CloudError(f"GitHub answered {status} for {full}.")
    api(token, "POST", "/user/repos", {
        "name": REPO_NAME, "private": True, "auto_init": True, "has_issues": False, "has_projects": False,
        "has_wiki": False,
        "description": f"{APP_NAME}: scheduled portal checks for this account. Managed by the app; nothing to edit here.",
    }, ok=(201,))
    for _ in range(20):                      # auto_init creates the default branch a moment later
        status, _, _ = _request("GET", f"{API}/repos/{full}/contents/README.md", token)
        if status == 200:
            break
        time.sleep(0.5)
    return full


def put_file(token: str, repo: str, path: str, content: bytes, message: str) -> None:
    """Creates or updates one file through the contents API (one commit per file; a handful at setup only)."""
    status, data, _ = _request("GET", f"{API}/repos/{repo}/contents/{path}", token)
    body = {"message": message, "content": base64.b64encode(content).decode("ascii")}
    if status == 200 and isinstance(data, dict) and data.get("sha"):
        if base64.b64decode(data.get("content", "").encode()) == content:
            return                           # unchanged
        body["sha"] = data["sha"]
    api(token, "PUT", f"/repos/{repo}/contents/{path}", body, ok=(200, 201))


def delete_file(token: str, repo: str, path: str, message: str) -> None:
    status, data, _ = _request("GET", f"{API}/repos/{repo}/contents/{path}", token)
    if status == 200 and isinstance(data, dict) and data.get("sha"):
        api(token, "DELETE", f"/repos/{repo}/contents/{path}", {"message": message, "sha": data["sha"]})


# ---------------------------------------------------------------------------- secrets
def seal(public_key_b64: str, value: str) -> str:
    """Encrypts a secret value for GitHub with the repository's public key (libsodium sealed box)."""
    from nacl import encoding, public
    key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed = public.SealedBox(key).encrypt(value.encode("utf-8"))
    return base64.b64encode(sealed).decode("utf-8")


def set_secrets(token: str, repo: str, values: dict) -> int:
    """Writes every non-empty value as a repository secret and removes the ones that are empty now. Returns the
    number written."""
    pk = api(token, "GET", f"/repos/{repo}/actions/secrets/public-key")
    written = 0
    for name, value in values.items():
        if value is None or value == "":
            _request("DELETE", f"{API}/repos/{repo}/actions/secrets/{name}", token)
            continue
        api(token, "PUT", f"/repos/{repo}/actions/secrets/{name}",
            {"encrypted_value": seal(pk["key"], str(value)), "key_id": pk["key_id"]}, ok=(201, 204))
        written += 1
    return written


def _text(v) -> str:
    if isinstance(v, bool):
        return "True" if v else "False"
    return "" if v is None else str(v)


def secret_values(env: dict) -> dict:
    """The secret settings, as AM_<KEY> repository secrets."""
    return {f"AM_{key}": _text(env.get(key, "")) for key in SECRET_KEYS}


def plain_values(env: dict) -> dict:
    """The non-secret settings, written into the workflow file as AM_<KEY> environment values."""
    return {f"AM_{key}": _text(env.get(key, "")) for key in PLAIN_KEYS}


# ---------------------------------------------------------------------------- the workflow
def _yaml_str(v: str) -> str:
    return json.dumps(v)                     # a JSON string is a valid double-quoted YAML scalar


def workflow_yaml(version: str = APP_VERSION, env: dict | None = None) -> str:
    """The student's workflow: twice a day (08:00 and 19:00 Pakistan time), or on demand. It checks out this
    project at the pinned release, runs the check with the settings in the environment (secrets from the
    repository, plain settings written here) and commits the state."""
    env = env if env is not None else {}
    secrets_env = "\n".join(f"          {k}: ${{{{ secrets.{k} }}}}" for k in secret_values({}).keys())
    plain_env = "\n".join(f"          {k}: {_yaml_str(v)}" for k, v in plain_values(env).items())
    return f"""# {APP_NAME} cloud checks. Written by the app; it is replaced on every app update, so edits here are lost.
# Runs the same check the PC runs, on GitHub's machines, so alerts reach the phone and the mailbox when the PC is off.
name: {APP_NAME} check

on:
  schedule:
    - cron: "0 3 * * *"     # 08:00 Pakistan time
    - cron: "0 14 * * *"    # 19:00 Pakistan time
  workflow_dispatch:
    inputs:
      mode:
        description: "check (full sync and alerts) or verify (sign in, count, send a test alert)"
        default: check
        type: choice
        options: [check, verify]

permissions:
  contents: write

env:
  PLAYWRIGHT_BROWSERS_PATH: ${{{{ github.workspace }}}}/browsers

concurrency:
  group: check
  cancel-in-progress: false

jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - name: This repository (state)
        uses: actions/checkout@v4
      - name: {APP_NAME} {version}
        uses: actions/checkout@v4
        with:
          repository: {PROJECT_REPO}
          ref: v{version}
          path: app
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install
        run: |
          python -m pip install --quiet --upgrade pip
          pip install --quiet playwright==1.64.0 lxml==6.1.3 pywebpush==2.5.0
          python -m playwright install --with-deps chromium
      - name: Check
        env:
          ASSIGNMENT_MONITOR_HOME: ${{{{ github.workspace }}}}/state
          ASSIGNMENT_MONITOR_RUNNER: cloud
          AM_ENABLE_WINDOWS_TOAST: "False"
          AM_ENABLE_VOICE: "False"
          AM_HEADLESS: "True"
{plain_env}
{secrets_env}
        run: python app/cloud_check.py ${{{{ inputs.mode || 'check' }}}}
      - name: Save state
        if: always()
        run: |
          git config user.name "{APP_NAME}"
          git config user.email "noreply@users.noreply.github.com"
          git add state
          git diff --cached --quiet || (git commit -q -m "state $(date -u +%Y-%m-%dT%H:%MZ)" && git push -q)
"""


def readme_text(login: str) -> str:
    return f"""# {APP_NAME} cloud checks

This private repository belongs to {login}'s {APP_NAME} setup. A scheduled workflow signs in to the Bahria portal
twice a day from GitHub's machines and sends the usual alerts to the paired phone and mailbox, so they arrive when the
PC is off. The `state` folder is the cache of what was last seen (the same files the PC keeps). The portal login and
channel keys are repository secrets, encrypted by GitHub.

Managed by the app: turn it off from Settings > Cloud checks. Project: https://github.com/{PROJECT_REPO}
Website: {SITE_URL}
"""


# ---------------------------------------------------------------------------- set-up, update, tear-down
def setup(token: str, env: dict | None = None, progress=None) -> dict:
    """Creates or refreshes everything in the student's account. Returns {"repo", "login", "run_url"}."""
    env = dict(env or load_env())
    say = progress or (lambda m: None)
    say("Checking the GitHub sign-in…")
    login = whoami(token)
    say("Preparing your private repository…")
    repo = ensure_repo(token, login)
    say("Writing the workflow…")
    put_file(token, repo, "README.md", readme_text(login).encode("utf-8"), "README")
    ignore = "state/settings.env\nstate/chrome_profile/\nstate/browsers/\nstate/data/app.log*\nstate/data/sync.lock\n"
    put_file(token, repo, ".gitignore", ignore.encode("ascii"), "ignore local files")
    put_file(token, repo, WORKFLOW_PATH, workflow_yaml(APP_VERSION, env).encode("utf-8"),
             f"workflow for {APP_NAME} {APP_VERSION}")
    say("Copying what this PC has seen so far…")
    seeded = 0
    for name in STATE_FILES:
        p = DATA_DIR / name
        if p.exists():
            put_file(token, repo, f"state/data/{name}", p.read_bytes(), f"seed {name} from the PC")
            seeded += 1
    say("Storing your login and channel keys as encrypted secrets…")
    set_secrets(token, repo, secret_values(env))
    env.update({"CLOUD_ENABLED": True, "CLOUD_REPO": repo, "CLOUD_LOGIN": login, "CLOUD_VERSION": APP_VERSION,
                "CLOUD_HASH": fingerprint(env), "GITHUB_TOKEN": token})
    save_env(env)
    say("Starting the first cloud check…")
    run_url = ""
    try:
        api(token, "POST", f"/repos/{repo}/actions/workflows/check.yml/dispatches", {"ref": "main", "inputs": {"mode": "verify"}})
        run_url = f"https://github.com/{repo}/actions"
    except CloudError as e:
        log.warning("First cloud run could not be started: %s", e)
    log.info("Cloud checks set up in %s (%d state files seeded).", repo, seeded)
    return {"repo": repo, "login": login, "run_url": run_url}


def enabled(env: dict | None = None) -> bool:
    env = env or load_env()
    return bool(env.get("CLOUD_ENABLED") and env.get("CLOUD_REPO") and env.get("GITHUB_TOKEN"))


def fingerprint(env: dict) -> str:
    """What the cloud copy depends on: the secrets, the plain settings and the app version (the workflow pins it)."""
    blob = json.dumps([secret_values(env), plain_values(env), APP_VERSION], sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def sync_secrets(env: dict | None = None, force: bool = False) -> bool:
    """Brings the cloud copy up to date with this PC: the secrets, the workflow (plain settings and the pinned
    app version). Skipped when nothing changed since the last sync. Call after settings change and once at
    start-up. Returns True when something was sent; errors are logged, not raised."""
    env = dict(env or load_env())
    if not enabled(env):
        return False
    fp = fingerprint(env)
    if not force and fp == env.get("CLOUD_HASH"):
        return False
    try:
        set_secrets(env["GITHUB_TOKEN"], env["CLOUD_REPO"], secret_values(env))
        put_file(env["GITHUB_TOKEN"], env["CLOUD_REPO"], WORKFLOW_PATH, workflow_yaml(APP_VERSION, env).encode("utf-8"),
                 f"workflow for {APP_NAME} {APP_VERSION}")
    except Exception as e:
        log.warning("Cloud settings could not be updated: %s", str(e)[:200])
        return False
    env["CLOUD_HASH"] = fp
    env["CLOUD_VERSION"] = APP_VERSION
    save_env(env)
    log.info("Cloud settings updated (%s).", APP_VERSION)
    return True


def refresh_if_outdated(env: dict | None = None) -> bool:
    """After an app update the workflow must pin the version now installed; the fingerprint includes it."""
    return sync_secrets(env)


def run_now(env: dict | None = None, mode: str = "check") -> None:
    env = env or load_env()
    if not enabled(env):
        raise CloudError("Cloud checks are not set up.")
    api(env["GITHUB_TOKEN"], "POST", f"/repos/{env['CLOUD_REPO']}/actions/workflows/check.yml/dispatches",
        {"ref": "main", "inputs": {"mode": mode}})


def last_run(env: dict | None = None) -> dict | None:
    """The most recent cloud run: {"when": datetime, "status", "conclusion", "url", "mode"} or None."""
    env = env or load_env()
    if not enabled(env):
        return None
    data = api(env["GITHUB_TOKEN"], "GET", f"/repos/{env['CLOUD_REPO']}/actions/runs?per_page=1")
    runs = data.get("workflow_runs") or []
    if not runs:
        return None
    r = runs[0]
    when = datetime.strptime(r["run_started_at"] or r["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return {"when": when.astimezone(), "status": r["status"], "conclusion": r["conclusion"], "url": r["html_url"],
            "event": r["event"]}


def teardown(env: dict | None = None, progress=None) -> str:
    """Switches cloud checks off: deletes the secrets, removes the workflow and forgets the token on this PC. The
    repository itself stays (deleting repositories needs a scope we do not ask for); returns its settings URL so
    the student can delete it in one click."""
    env = dict(env or load_env())
    say = progress or (lambda m: None)
    token, repo = env.get("GITHUB_TOKEN", ""), env.get("CLOUD_REPO", "")
    if token and repo:
        try:
            say("Removing the secrets…")
            set_secrets(token, repo, {k: "" for k in secret_values({}).keys()})
            say("Removing the workflow…")
            delete_file(token, repo, WORKFLOW_PATH, "cloud checks turned off")
        except Exception as e:
            log.warning("Cloud tear-down was incomplete: %s", str(e)[:200])
    env.update({"CLOUD_ENABLED": False, "CLOUD_REPO": "", "CLOUD_LOGIN": "", "CLOUD_VERSION": "", "CLOUD_HASH": "",
                "GITHUB_TOKEN": ""})
    save_env(env)
    log.info("Cloud checks turned off.")
    return f"https://github.com/{repo}/settings" if repo else ""
