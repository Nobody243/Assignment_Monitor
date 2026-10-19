"""Update check against the project's GitHub releases, and a one-click installer download.

Only the latest *numbered* release counts (GitHub's /releases/latest ignores pre-releases),
so the rolling "latest build" pre-release never triggers an update prompt.
"""
import json
import logging
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from config import APP_NAME, APP_VERSION, REPO_URL

log = logging.getLogger("bahria.updater")
USER_AGENT = f"{APP_NAME.replace(' ', '')}/{APP_VERSION}"
ALLOWED_HOSTS = {"github.com", "api.github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}


def api_url() -> str:
    m = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", REPO_URL)
    if not m:
        raise ValueError("REPO_URL is not a GitHub repository URL")
    return f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}/releases/latest"


def parse_version(text: str) -> tuple:
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


def is_newer(latest: str, current: str = APP_VERSION) -> bool:
    return parse_version(latest) > parse_version(current)


def parse_release(payload: dict, current: str = APP_VERSION) -> dict:
    """Turns a GitHub release JSON object into {version, newer, setup_url, page}."""
    tag = str(payload.get("tag_name") or payload.get("name") or "")
    setup_url = None
    for asset in payload.get("assets") or []:
        name = str(asset.get("name", ""))
        if name.lower().endswith("-setup.exe"):
            setup_url = asset.get("browser_download_url")
            break
    return {
        "version": tag.lstrip("vV"),
        "newer": bool(tag) and is_newer(tag, current),
        "setup_url": setup_url,
        "page": payload.get("html_url") or f"{REPO_URL}/releases/latest",
    }


def _fetch_json(url: str, timeout: int) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:   # noqa: S310 - https URL built from REPO_URL
        return json.loads(r.read().decode("utf-8"))


def check_latest(timeout: int = 8, fetch=_fetch_json):
    """Returns the parsed release dict, or None when offline or anything goes wrong."""
    try:
        info = parse_release(fetch(api_url(), timeout))
        log.info("Update check: latest release %s (%s)", info["version"] or "?", "newer" if info["newer"] else "up to date")
        return info
    except Exception as e:
        log.info("Update check skipped: %s", str(e).splitlines()[0][:120])
        return None


def _safe_url(url: str) -> bool:
    try:
        u = urlparse(url)
        return u.scheme == "https" and (u.hostname in ALLOWED_HOSTS or (u.hostname or "").endswith(".githubusercontent.com"))
    except Exception:
        return False


def download_installer(setup_url: str, progress=None, timeout: int = 30) -> Path:
    """Downloads the Setup.exe to the temp folder. `progress(done_bytes, total_bytes)` is optional."""
    if not _safe_url(setup_url):
        raise ValueError("Refusing to download from an unexpected host")
    target = Path(tempfile.gettempdir()) / "AssignmentMonitor-Setup.exe"
    req = urllib.request.Request(setup_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(target, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if target.stat().st_size < 1_000_000:
        raise ValueError("Downloaded installer looks incomplete")
    return target


def run_installer(path: Path) -> None:
    """Starts the installer; it closes the running app itself and relaunches it afterwards."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([str(path), "/SILENT", "/NORESTART", "/SUPPRESSMSGBOXES", "/RELAUNCH=1"],
                     close_fds=True, creationflags=flags, cwd=os.path.dirname(path))
