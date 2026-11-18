"""The settings the new interface reads and writes: secrets stay in the engine, every update is validated, the
installed app's background tasks are never touched from a source run, and the cloud and phone flows work with their
network calls stubbed. Settings live in the throw-away folder conftest.py sets up."""

import json
import threading
import urllib.error
import urllib.request

import pytest

import automation
import channels
import cloud
import engine
import settings_api
import config
from config import load_env


@pytest.fixture()
def srv(monkeypatch):
    config.ENV_PATH.unlink(missing_ok=True)  # every test starts from empty settings
    monkeypatch.setattr(engine, "JOBS", engine.Jobs())
    monkeypatch.setattr(automation, "is_enabled", lambda: False)
    monkeypatch.setattr(automation, "installed_owner", lambda: "")
    monkeypatch.setattr(automation, "starts_with_windows", lambda: False)
    monkeypatch.setattr(settings_api, "_pairing", None)
    monkeypatch.setattr(settings_api, "_flow", None)
    monkeypatch.setattr(settings_api, "_token", None)
    s = engine.Engine(0, "tok", ())
    threading.Thread(target=s.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{s.server_address[1]}"

    def call(method, path, body=None):
        data = json.dumps(body).encode() if isinstance(body, (dict, list)) else body
        req = urllib.request.Request(base + path, data=data, method=method, headers={"Authorization": "Bearer tok"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def job(jid, timeout=10):
        import time

        end = time.time() + timeout
        while time.time() < end:
            st, j = call("GET", f"/api/jobs/{jid}")
            if j["status"] == "done":
                return j["result"]
            time.sleep(0.05)
        raise AssertionError("job did not finish")

    yield call, job
    s.shutdown()


def test_the_view_never_contains_a_secret(srv):
    call, _j = srv
    st, body = call(
        "POST",
        "/api/settings",
        {"enrollment": "01-123456-789", "password": "Sup3rSecret!", "email_to": "me@example.com", "email_pass": "app-pass-xyz"},
    )
    assert st == 200
    blob = json.dumps(call("GET", "/api/settings")[1]) + json.dumps(body)
    assert "Sup3rSecret!" not in blob and "app-pass-xyz" not in blob
    view = call("GET", "/api/settings")[1]
    assert view["account"]["password_set"] is True and view["channels"]["email_pass_set"] is True
    assert load_env()["PASSWORD"] == "Sup3rSecret!"  # stored, just never returned


def test_an_empty_secret_field_keeps_what_is_stored(srv):
    call, _j = srv
    call("POST", "/api/settings", {"password": "keep-me-1"})
    assert call("POST", "/api/settings", {"password": "", "attendance_min": 80})[0] == 200
    assert load_env()["PASSWORD"] == "keep-me-1" and load_env()["ATTENDANCE_MIN"] == 80


def test_every_update_is_checked_and_nothing_is_saved_when_one_is_wrong(srv):
    call, _j = srv
    before = load_env()["ATTENDANCE_MIN"]
    bad = [
        {"nope": 1},
        {"attendance_min": 5},
        {"attendance_min": "80"},
        {"track_exams": "yes"},
        {"enrollment": "a\nb"},
        {"enrollment": "x y!"},
        {"institute_id": "999"},
        {"lectures_dir": "relative/path"},
        {"email_to": "not-an-email"},
        {"email_host": "bad host"},
    ]
    for patch in bad:
        st, body = call("POST", "/api/settings", patch)
        assert st == 422 and body["errors"], patch
    st, body = call("POST", "/api/settings", {"attendance_min": 90, "enrollment": "bad\nline"})
    assert st == 422 and load_env()["ATTENDANCE_MIN"] == before  # the valid half was not saved either


def test_valid_updates_are_saved_and_the_email_login_follows_the_address(srv):
    call, _j = srv
    st, body = call("POST", "/api/settings", {"track_exams": False, "notify_days_ahead": 5, "email_to": "a@b.co", "institute_id": "9"})
    assert st == 200 and set(body["changed"]) == {"track_exams", "notify_days_ahead", "email_to", "institute_id"}
    env = load_env()
    assert env["TRACK_EXAMS"] is False and env["NOTIFY_DAYS_AHEAD"] == 5 and env["EMAIL_USER"] == "a@b.co" and env["INSTITUTE_ID"] == "9"
    assert body["settings"]["account"]["campus"].startswith("Islamabad H-11")


def test_a_phone_cannot_be_switched_on_before_it_is_paired(srv):
    call, _j = srv
    st, body = call("POST", "/api/settings", {"push_enabled": True})
    assert st == 422 and "pair a phone" in json.dumps(body)


def test_automatic_checks_run_as_a_job(srv, monkeypatch):
    call, job = srv
    calls = []
    monkeypatch.setattr(automation, "enable", lambda: calls.append("on") or (True, "Background automation is on."))
    monkeypatch.setattr(automation, "disable", lambda: calls.append("off") or (True, "off"))
    st, body = call("POST", "/api/automation?enable=1")
    assert st == 202 and job(body["job"])["ok"] and calls == ["on"]
    st, body = call("POST", "/api/automation?enable=0")
    assert st == 202 and job(body["job"])["ok"] and calls == ["on", "off"]


def test_a_source_run_never_turns_off_the_installed_apps_tasks(srv, monkeypatch):
    call, _j = srv
    monkeypatch.setattr(
        automation, "installed_owner", lambda: r"C:\Users\x\AppData\Local\Programs\Assignment Monitor\AssignmentMonitor.exe"
    )
    monkeypatch.setattr(
        automation, "disable", lambda: (_ for _ in ()).throw(AssertionError("the installed app's tasks must be left alone"))
    )
    st, body = call("POST", "/api/automation?enable=0")
    assert st == 409 and "installed app" in body["error"]
    assert call("GET", "/api/settings")[1]["background"]["owned_by_installed_app"] is True


def test_test_email_needs_an_address_and_a_password(srv, monkeypatch):
    call, job = srv
    assert call("POST", "/api/test/email")[0] == 422
    call("POST", "/api/settings", {"email_to": "me@example.com", "email_pass": "app-pass"})
    sent = []
    monkeypatch.setattr(channels, "send_email", lambda subject, body, env=None, **k: sent.append(subject))
    st, body = call("POST", "/api/test/email")
    assert st == 202 and job(body["job"])["ok"] and len(sent) == 1


def test_phone_pairing_gives_a_qr_and_saves_the_subscription(srv, monkeypatch):
    call, _j = srv
    st, body = call("POST", "/api/pair/start")
    assert st == 200 and body["qr"].startswith("data:image/png;base64,") and body["url"].startswith("https://") and len(body["code"]) == 6
    monkeypatch.setattr(channels, "pairing_poll", lambda pairing, timeout=4.0: None)
    assert call("POST", "/api/pair/poll")[1]["status"] == "waiting"
    sub = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": {"p256dh": "k", "auth": "a"}}
    monkeypatch.setattr(channels, "pairing_poll", lambda pairing, timeout=4.0: sub)
    assert call("POST", "/api/pair/poll")[1] == {"status": "paired", "device": "Android (Chrome or Samsung Internet)"}
    assert call("GET", "/api/settings")[1]["channels"]["push_paired"] is True
    assert call("POST", "/api/pair/poll")[0] == 409  # nothing in progress any more
    assert call("POST", "/api/unpair")[0] == 200
    assert call("GET", "/api/settings")[1]["channels"]["push_paired"] is False


def test_cloud_sign_in_never_exposes_the_device_code_or_the_token(srv, monkeypatch):
    call, job = srv
    assert call("POST", "/api/cloud/poll")[0] == 409 and call("POST", "/api/cloud/setup")[0] == 409
    monkeypatch.setattr(
        cloud,
        "device_start",
        lambda: {
            "device_code": "DEVSECRET",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "interval": 5,
            "expires_in": 900,
        },
    )
    st, body = call("POST", "/api/cloud/start")
    assert st == 200 and body["user_code"] == "ABCD-1234" and "DEVSECRET" not in json.dumps(body)
    monkeypatch.setattr(cloud, "device_poll", lambda flow: None)
    assert call("POST", "/api/cloud/poll")[1]["status"] == "pending"
    monkeypatch.setattr(cloud, "device_poll", lambda flow: "gho_TOKENSECRET")
    st, body = call("POST", "/api/cloud/poll")
    assert body == {"status": "ready"} and "TOKENSECRET" not in json.dumps(body)
    seen = {}
    monkeypatch.setattr(
        cloud, "setup", lambda token, env=None, progress=None: seen.update(token=token) or {"repo": "me/am", "login": "me", "run_url": "u"}
    )
    st, body = call("POST", "/api/cloud/setup")
    result = job(body["job"])
    assert result["ok"] and "me" in result["message"] and seen["token"] == "gho_TOKENSECRET" and "TOKENSECRET" not in json.dumps(result)
    assert call("POST", "/api/cloud/setup")[0] == 409  # the token was used up


def test_cloud_errors_come_back_as_messages(srv, monkeypatch):
    call, _j = srv
    monkeypatch.setattr(
        cloud, "device_start", lambda: {"device_code": "d", "user_code": "U", "verification_uri": "https://x", "interval": 5}
    )
    call("POST", "/api/cloud/start")

    def expired(flow):
        raise cloud.CloudError("The code expired. Start again to get a new one.")

    monkeypatch.setattr(cloud, "device_poll", expired)
    st, body = call("POST", "/api/cloud/poll")
    assert st == 400 and "expired" in body["error"]


def test_clearing_data_empties_the_stored_files(srv):
    import tracker

    call, _j = srv
    tracker.save_assignments({"k": {"id": "k"}})
    assert call("POST", "/api/data/clear")[0] == 200
    assert tracker.load_stored_assignments() == {}
