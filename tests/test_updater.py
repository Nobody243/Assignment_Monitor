import pytest

import updater


def test_api_url_is_derived_from_repo_url():
    assert updater.api_url().startswith("https://api.github.com/repos/")
    assert updater.api_url().endswith("/releases/latest")


@pytest.mark.parametrize("latest, current, newer", [
    ("v1.1.0", "1.0.0", True),
    ("1.0.1", "1.0.0", True),
    ("v1.0.0", "1.0.0", False),
    ("v0.9.9", "1.0.0", False),
    ("v2.0", "1.9.9", True),
    ("", "1.0.0", False),
])
def test_is_newer(latest, current, newer):
    assert updater.is_newer(latest, current) is newer


def test_parse_release_picks_setup_asset():
    payload = {
        "tag_name": "v9.9.9",
        "html_url": "https://github.com/x/y/releases/tag/v9.9.9",
        "assets": [
            {"name": "AssignmentMonitor-portable.zip", "browser_download_url": "https://github.com/x/y/releases/download/v9.9.9/AssignmentMonitor-portable.zip"},
            {"name": "AssignmentMonitor-Setup.exe", "browser_download_url": "https://github.com/x/y/releases/download/v9.9.9/AssignmentMonitor-Setup.exe"},
        ],
    }
    info = updater.parse_release(payload, current="1.0.0")
    assert info["version"] == "9.9.9" and info["newer"] is True
    assert info["setup_url"].endswith("AssignmentMonitor-Setup.exe")
    assert info["page"].endswith("v9.9.9")


def _offline(*a, **k):
    raise OSError("offline")


def test_check_latest_swallows_network_errors():
    assert updater.check_latest(fetch=_offline, latest_tag=_offline) is None


def test_check_latest_prefers_the_redirect_and_needs_no_api():
    info = updater.check_latest(fetch=_offline, latest_tag=lambda timeout: "v9.9.9")
    assert info["version"] == "9.9.9" and info["newer"] is True
    assert info["setup_url"] == f"{updater.REPO_URL}/releases/download/v9.9.9/AssignmentMonitor-Setup.exe"
    assert info["page"].endswith("/releases/tag/v9.9.9")
    assert updater._safe_url(info["setup_url"])


def test_check_latest_falls_back_to_the_api_when_the_redirect_fails():
    info = updater.check_latest(fetch=lambda url, timeout: {"tag_name": "v0.0.1", "assets": []}, latest_tag=_offline)
    assert info["version"] == "0.0.1" and info["newer"] is False and info["setup_url"] is None


def test_check_latest_uses_the_api_when_there_is_no_release_to_redirect_to():
    info = updater.check_latest(fetch=lambda url, timeout: {"tag_name": "v0.0.2", "assets": []}, latest_tag=lambda timeout: "")
    assert info["version"] == "0.0.2"


def test_release_from_tag_handles_an_empty_tag():
    info = updater.release_from_tag("")
    assert info["newer"] is False and info["setup_url"] is None and info["page"] == updater.LATEST_URL


@pytest.mark.parametrize("url, ok", [
    ("https://github.com/x/y/releases/download/v1/AssignmentMonitor-Setup.exe", True),
    ("https://objects.githubusercontent.com/abc", True),
    ("http://github.com/x", False),
    ("https://evil.example.com/Setup.exe", False),
])
def test_download_host_allowlist(url, ok):
    assert updater._safe_url(url) is ok
