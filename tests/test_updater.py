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


def _releases(*tags, **kw):
    return [{"tag_name": t, "draft": kw.get("draft", False), "prerelease": kw.get("pre", False),
             "html_url": f"https://github.com/x/y/releases/tag/{t}",
             "assets": [{"name": "AssignmentMonitor-Setup.exe",
                         "browser_download_url": f"https://github.com/x/y/releases/download/{t}/AssignmentMonitor-Setup.exe"}]}
            for t in tags]


def test_a_phone_release_as_latest_does_not_hide_the_desktop_update():
    # GitHub's latest release was the phone app's (phone-v1.0.8): the app used to read 1.0.8 as older than 1.9.5 and say it was up to date
    listing = _releases("phone-v1.0.8", "v1.9.7", "phone-v1.0.7", "v1.9.6", "v1.9.5")
    info = updater.check_latest(fetch=lambda url, timeout: listing, latest_tag=lambda timeout: "phone-v1.0.8")
    assert info["version"] == "1.9.7"
    assert info["newer"] is True or info["version"] == updater.APP_VERSION   # newer than whatever this build is
    assert info["setup_url"].endswith("v1.9.7/AssignmentMonitor-Setup.exe")


def test_only_published_desktop_releases_are_offered():
    listing = _releases("v2.0.0", draft=True) + _releases("v1.9.9", pre=True) + _releases("phone-v9.9.9") + _releases("v1.9.8")
    assert updater.newest_desktop_release(listing)["version"] == "1.9.8"
    assert updater.newest_desktop_release(_releases("phone-v1.0.1")) is None
    assert updater.newest_desktop_release([]) is None
    assert updater.newest_desktop_release("nonsense") is None


@pytest.mark.parametrize("tag, ok", [
    ("v1.9.7", True), ("1.9.7", True), ("V2.0.0", True), ("phone-v1.0.8", False), ("v1.9", False), ("latest", False), ("", False),
])
def test_which_tags_are_desktop_releases(tag, ok):
    assert bool(updater.DESKTOP_TAG.match(tag)) is ok


def test_a_phone_release_with_no_desktop_release_at_all_offers_nothing():
    info = updater.check_latest(fetch=lambda url, timeout: _releases("phone-v1.0.8"), latest_tag=lambda timeout: "phone-v1.0.8")
    assert info is None


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
