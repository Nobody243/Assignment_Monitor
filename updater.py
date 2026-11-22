"""Update check against the project's GitHub releases, and a one-click installer download.

Only the latest *numbered* release counts (GitHub's "latest" ignores pre-releases), so the rolling "latest build"
pre-release never triggers an update prompt.

The check does not need the GitHub API: github.com/<repo>/releases/latest answers with a redirect to the release's
tag, and that works without a token and without the API's 60-requests-an-hour limit per address (which a shared
network, or a few other tools on the same PC, can use up). The API is only the fallback.
"""
import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

from config import APP_NAME, APP_VERSION, REPO_URL

log = logging.getLogger("bahria.updater")
USER_AGENT = f"{APP_NAME.replace(' ', '')}/{APP_VERSION}"
ALLOWED_HOSTS = {"github.com", "api.github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
SETUP_NAME = "AssignmentMonitor-Setup.exe"
LATEST_URL = f"{REPO_URL}/releases/latest"


def _repo_api() -> str:
    m = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", REPO_URL)
    if not m:
        raise ValueError("REPO_URL is not a GitHub repository URL")
    return f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}"


def api_url() -> str:
    return _repo_api() + "/releases/latest"


def releases_api_url() -> str:
    return _repo_api() + "/releases?per_page=30"


# A desktop release is tagged v1.9.7. The phone app's releases live in the same repository, tagged phone-v1.0.8, and GitHub's
# "latest release" can be either: this app only ever offers its own.
DESKTOP_TAG = re.compile(r"^[vV]?\d+\.\d+\.\d+$")


def parse_version(text: str) -> tuple:
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


def is_newer(latest: str, current: str = APP_VERSION) -> bool:
    return parse_version(latest) > parse_version(current)


def release_from_tag(tag: str, current: str = APP_VERSION) -> dict:
    """The release dict for a tag, without asking the API: the installer's address follows from the tag."""
    tag = (tag or "").strip()
    return {
        "version": tag.lstrip("vV"),
        "newer": bool(tag) and is_newer(tag, current),
        "setup_url": f"{REPO_URL}/releases/download/{tag}/{SETUP_NAME}" if tag else None,
        "page": f"{REPO_URL}/releases/tag/{tag}" if tag else LATEST_URL,
    }


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
        "page": payload.get("html_url") or LATEST_URL,
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _latest_tag(timeout: int) -> str:
    """The tag the releases/latest page redirects to, e.g. 'v1.5.7'. Raises when GitHub cannot be reached;
    returns '' when there is no release yet."""
    req = urllib.request.Request(LATEST_URL, method="HEAD", headers={"User-Agent": USER_AGENT})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            m = re.search(r"/releases/tag/([^/?#]+)", e.headers.get("Location") or "")
            if m:
                return unquote(m.group(1))
            return ""
        raise
    return ""


def _https(url: str) -> str:
    """Refuses anything but an https URL before it is opened (file:, ftp: and custom schemes are never wanted)."""
    if not str(url).lower().startswith("https://"):
        raise ValueError(f"refusing a non-https URL: {str(url)[:60]}")
    return url


def _fetch_json(url: str, timeout: int) -> dict:
    req = urllib.request.Request(_https(url), headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 - https only
        return json.loads(r.read().decode("utf-8"))


def newest_desktop_release(payload) -> dict | None:
    """The highest desktop release in a releases list (or a single release object): published, not a pre-release, tagged v1.2.3.
    Phone releases (phone-v1.0.8), drafts and the rolling pre-release are skipped."""
    items = payload if isinstance(payload, list) else [payload]
    best = None
    for r in items:
        if not isinstance(r, dict) or r.get("draft") or r.get("prerelease"):
            continue
        tag = str(r.get("tag_name") or "")
        if not DESKTOP_TAG.match(tag):
            continue
        if best is None or parse_version(tag) > parse_version(str(best.get("tag_name"))):
            best = r
    return parse_release(best) if best else None


def check_latest(timeout: int = 8, fetch=_fetch_json, latest_tag=_latest_tag):
    """Returns the parsed release dict, or None when GitHub cannot be reached at all. The redirect check comes first (no API, no
    rate limit); when "latest" is not a desktop release (the phone app's releases are in the same repository) or the redirect
    fails, the releases list is searched for the newest desktop release."""
    try:
        tag = latest_tag(timeout)
        if tag and DESKTOP_TAG.match(tag):
            info = release_from_tag(tag)
            log.info("Update check: latest release %s (%s)", info["version"], "newer" if info["newer"] else "up to date")
            return info
        if tag:
            log.info("Update check: the latest release is %s, not a desktop release; looking through the list", tag)
    except Exception as e:
        log.info("Update check (redirect) failed: %s", str(e).splitlines()[0][:120])
    try:
        info = newest_desktop_release(fetch(releases_api_url(), timeout))
        if info:
            log.info("Update check (API): latest desktop release %s (%s)", info["version"], "newer" if info["newer"] else "up to date")
            return info
    except Exception as e:
        log.info("Update check (list) failed: %s", str(e).splitlines()[0][:120])
    try:
        info = newest_desktop_release(fetch(api_url(), timeout))
        if info:
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


def fetch_checksum(setup_url: str, timeout: int = 15) -> str | None:
    """The SHA-256 the release publishes next to the installer (AssignmentMonitor-Setup.exe.sha256), or None when the release
    has none (older releases). The file holds the hash, optionally followed by the file name."""
    url = setup_url + ".sha256"
    if not _safe_url(url):
        return None
    try:
        req = urllib.request.Request(_https(url), headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 - https only
            m = re.match(r"\s*([0-9a-fA-F]{64})", r.read(512).decode("ascii", "ignore"))
    except Exception as e:  # noqa: BLE001
        log.info("No checksum published for the installer: %s", str(e).splitlines()[0][:100])
        return None
    return m.group(1).lower() if m else None


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_installer(setup_url: str, progress=None, timeout: int = 30, expected_sha256: str | None = None) -> Path:
    """Downloads the Setup.exe to the temp folder. `progress(done_bytes, total_bytes)` is optional."""
    if not _safe_url(setup_url):
        raise ValueError("Refusing to download from an unexpected host")
    target = Path(tempfile.gettempdir()) / SETUP_NAME
    req = urllib.request.Request(_https(setup_url), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(target, "wb") as f:  # nosec B310 - https only
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
    if expected_sha256 and sha256_of(target) != expected_sha256.lower():
        target.unlink(missing_ok=True)
        raise ValueError("The downloaded installer does not match its published checksum, so it was discarded.")
    return target


def run_installer(path: Path) -> None:
    """Starts the installer; it closes the running app itself and relaunches it afterwards."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([str(path), "/SILENT", "/NORESTART", "/SUPPRESSMSGBOXES", "/RELAUNCH=1"],
                     close_fds=True, creationflags=flags, cwd=os.path.dirname(path))
