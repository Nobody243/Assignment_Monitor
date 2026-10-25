import sys

import pytest

import config

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows only")


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.env"
    monkeypatch.setattr(config, "ENV_PATH", path)
    return path


@windows_only
def test_dpapi_round_trip_and_blob_is_not_plain_text():
    from secure_store import decrypt_secret, encrypt_secret
    secret = "p@ss wörd'\"<>&"
    token = encrypt_secret(secret)
    assert secret not in token
    assert decrypt_secret(token) == secret
    assert encrypt_secret("") == "" and decrypt_secret("") == ""


@windows_only
def test_password_is_never_written_in_plain_text(env_file):
    config.save_env({"ENROLLMENT": "01-123456-001", "PASSWORD": "hunter2", "INSTITUTE_ID": "9"})
    raw = env_file.read_text(encoding="utf-8")
    assert "hunter2" not in raw
    assert "PASSWORD_ENC=" in raw
    loaded = config.load_env()
    assert loaded["PASSWORD"] == "hunter2"
    assert loaded["ENROLLMENT"] == "01-123456-001"
    assert loaded["INSTITUTE_ID"] == "9"


@windows_only
def test_legacy_plain_text_password_is_migrated_on_load(env_file):
    env_file.write_text("ENROLLMENT=01-123456-001\nPASSWORD=oldplain\n", encoding="utf-8")
    loaded = config.load_env()
    assert loaded["PASSWORD"] == "oldplain"
    raw = env_file.read_text(encoding="utf-8")
    assert "oldplain" not in raw and "PASSWORD_ENC=" in raw


def test_defaults_and_validation(env_file):
    env_file.write_text("NOTIFY_DAYS_AHEAD=banana\nTHEME=PURPLE\nENABLE_VOICE=no\n", encoding="utf-8")
    loaded = config.load_env()
    assert loaded["NOTIFY_DAYS_AHEAD"] == 3            # invalid number falls back to default
    assert loaded["THEME"] == "dark"                    # unknown theme falls back to dark
    assert loaded["ENABLE_VOICE"] is False
    assert loaded["CLOSE_TO_TRAY"] is True
    assert config.has_credentials(loaded) is False


def test_only_known_keys_are_saved(env_file):
    config.save_env({"ENROLLMENT": "x", "PASSWORD": "", "EVIL": "1"})
    raw = env_file.read_text(encoding="utf-8")
    assert "EVIL" not in raw


def test_portal_urls_are_https_and_bahria_only():
    for url in (config.LOGIN_URL, config.SSO_URL, config.ASSIGNMENTS_URL, config.CMS_BASE_URL, config.LMS_BASE_URL):
        assert url.startswith("https://")
        assert ".bahria.edu.pk" in url


def test_app_command_points_at_this_app():
    cmd = config.app_command("--check")
    assert cmd[-1] == "--check"
    assert cmd[0].lower().endswith(".exe")


def test_campus_lookup():
    assert config.campus_name("1") == "Islamabad E-8 Campus"
    assert config.campus_name("999").startswith("Campus #")


def test_saves_merge_only_what_each_process_changed(env_file):
    """Two loaded copies: each saves its own change; neither wipes the other's. A stale window that saves its
    geometry hours later must not put an old token back over a newer one."""
    first = config.load_env()
    first["ENROLLMENT"] = "01-000000-001"
    first["GITHUB_TOKEN"] = "new-token"
    config.save_env(first)
    stale = config.load_env()
    stale.dirty.clear()
    fresh = config.load_env()
    fresh["GITHUB_TOKEN"] = "newer-token"
    config.save_env(fresh)
    stale["WINDOW_GEOMETRY"] = "900x700+1+1"      # the only thing this copy changed
    config.save_env(stale)
    final = config.load_env()
    assert final["WINDOW_GEOMETRY"] == "900x700+1+1"
    assert final["GITHUB_TOKEN"] == "newer-token"      # not the stale copy's "new-token"
    assert final["ENROLLMENT"] == "01-000000-001"
    # a plain dict still writes everything (first-run setup builds one)
    config.save_env({"ENROLLMENT": "01-000000-002", "PASSWORD": "pw"})
    assert config.load_env()["ENROLLMENT"] == "01-000000-002"
