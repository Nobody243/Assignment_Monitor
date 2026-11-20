"""Share with my phone: the PC writes the phone's summary file to the student's private repository after a check,
unless Cloud checks already does; the token is stored encrypted, a failure never fails a check, and an unchanged
summary is not sent again. GitHub is never called: every cloud function is replaced."""
import json
import threading

import pytest

import cloud
import config
import jobs
import phone_share
import settings_api

TOKEN = "gho_thisisaverysecrettoken"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    config.ENV_PATH.unlink(missing_ok=True)
    monkeypatch.setattr(phone_share, "GITHUB_CLIENT_ID", "abc")
    monkeypatch.setattr(cloud, "GITHUB_CLIENT_ID", "abc")
    monkeypatch.setattr(cloud, "whoami", lambda token: "alex")
    monkeypatch.setattr(cloud, "ensure_repo", lambda token, login: f"{login}/assignment-monitor-cloud")
    state = {"n": 0}
    monkeypatch.setattr(phone_share, "build_summary", lambda: {"schema": 1, "generated_at": f"t{state['n']}", "assignments": [{"id": "a"}]})
    monkeypatch.setattr(phone_share, "_state", state, raising=False)
    sent = []
    monkeypatch.setattr(cloud, "put_file", lambda token, repo, path, content, message:
                        sent.append((token, repo, path, json.loads(content), message)))
    yield sent
    config.ENV_PATH.unlink(missing_ok=True)


def _enable():
    return phone_share.enable(TOKEN)


def test_enabling_stores_the_token_encrypted_and_sends_the_first_summary(_fresh):
    info = _enable()
    assert info == {"repo": "alex/assignment-monitor-cloud", "login": "alex", "pushed": True, "covered_by_cloud": False}
    text = config.ENV_PATH.read_text(encoding="utf-8")
    assert TOKEN not in text and "PHONE_SHARE_TOKEN_ENC=" in text          # never in plain text
    env = config.load_env()
    assert env["PHONE_SHARE"] is True and env["PHONE_SHARE_TOKEN"] == TOKEN and env["PHONE_SHARE_LOGIN"] == "alex"
    token, repo, path, content, _ = _fresh[0]
    assert (token, repo, path) == (TOKEN, "alex/assignment-monitor-cloud", "state/summary.json")
    assert content["schema"] == 1
    assert phone_share.status(env)["last"]


def test_a_check_pushes_once_and_an_unchanged_summary_is_not_sent_again(_fresh):
    _enable()
    assert len(_fresh) == 1
    phone_share._state["n"] = 1                                              # only generated_at moved
    assert phone_share.push() == {"pushed": False, "reason": "unchanged"}
    assert len(_fresh) == 1
    phone_share.build_summary = lambda: {"schema": 1, "generated_at": "t9", "assignments": [{"id": "a"}, {"id": "b"}]}
    assert phone_share.push()["pushed"] is True
    assert len(_fresh) == 2


def test_after_a_sync_the_push_runs_in_its_own_thread(_fresh):
    _enable()
    phone_share.build_summary = lambda: {"schema": 1, "generated_at": "x", "assignments": [{"id": "new"}]}
    t = phone_share.share_after_sync()
    assert isinstance(t, threading.Thread) and t.name == "phone-share"
    t.join(5)
    assert len(_fresh) == 2


def test_process_sync_triggers_the_share(monkeypatch, _fresh):
    _enable()
    called = []
    monkeypatch.setattr(phone_share, "share_after_sync", lambda env=None: called.append(1))
    jobs.process_sync({"assignments": []}, config.load_env(), notify=False)
    assert called == [1]


def test_a_failing_push_never_fails_the_check_and_is_remembered(monkeypatch, _fresh):
    _enable()
    phone_share.build_summary = lambda: {"schema": 1, "generated_at": "y", "assignments": [{"id": "z"}]}

    def boom(*a, **k):
        raise cloud.CloudError("GitHub answered 502: bad gateway")
    monkeypatch.setattr(cloud, "put_file", boom)
    out = phone_share.push()
    assert out["pushed"] is False and out["reason"] == "error"
    assert "502" in phone_share.status()["error"]
    assert TOKEN not in json.dumps(phone_share.status())
    monkeypatch.setattr(phone_share, "build_summary", lambda: (_ for _ in ()).throw(RuntimeError("state unreadable")))
    jobs.process_sync({"assignments": []}, config.load_env(), notify=False)    # the check itself still completes
    assert phone_share.push()["reason"] == "error"


def test_when_cloud_checks_is_on_the_pc_does_not_push(monkeypatch, _fresh):
    _enable()
    n = len(_fresh)
    monkeypatch.setattr(cloud, "enabled", lambda env=None: True)
    assert phone_share.push(force=True) == {"pushed": False, "reason": "cloud"}
    assert phone_share.share_after_sync() is None
    assert len(_fresh) == n
    assert phone_share.status()["covered_by_cloud"] is True
    info = phone_share.enable(TOKEN)                                         # signing in while cloud is on pushes nothing
    assert info["covered_by_cloud"] is True and info["pushed"] is False and len(_fresh) == n


def test_nothing_happens_while_sharing_is_off(_fresh):
    assert phone_share.push() == {"pushed": False, "reason": "off"}
    assert phone_share.share_after_sync() is None
    assert _fresh == []


def test_disabling_clears_the_token_and_stops_pushes(_fresh):
    _enable()
    phone_share.disable()
    env = config.load_env()
    assert env["PHONE_SHARE"] is False and not env["PHONE_SHARE_TOKEN"] and not env["PHONE_SHARE_REPO"]
    assert "PHONE_SHARE_TOKEN_ENC" not in config.ENV_PATH.read_text(encoding="utf-8")
    assert phone_share.push()["reason"] == "off"


def test_the_hash_ignores_only_the_generated_time():
    a = {"schema": 1, "generated_at": "1", "x": [1]}
    assert phone_share.content_hash(a) == phone_share.content_hash({**a, "generated_at": "2"})
    assert phone_share.content_hash(a) != phone_share.content_hash({**a, "x": [2]})


def test_sharing_asks_github_only_for_the_repo_permission(monkeypatch):
    seen = {}
    monkeypatch.setattr(cloud, "_request", lambda method, url, token=None, body=None, **k:
                        seen.update(body=body) or (200, {"device_code": "d", "user_code": "U"}, {}))
    phone_share.device_start()
    assert seen["body"]["scope"] == "repo"
    cloud.device_start()
    assert seen["body"]["scope"] == "repo workflow"                          # Cloud checks still asks for what it needs


def test_the_api_flow_and_status(monkeypatch, _fresh):
    flow = {"device_code": "d", "user_code": "ABCD-1234", "verification_uri": "https://github.com/login/device",
            "interval": 5, "expires_in": 900}
    monkeypatch.setattr(cloud, "_request", lambda *a, **k: (200, flow, {}))
    code, body = settings_api.phone_start({}, b"")
    assert code == 200 and body["user_code"] == "ABCD-1234"
    assert settings_api.phone_enable({}, b"")[0] == 409                      # no approved sign-in yet
    monkeypatch.setattr(cloud, "device_poll", lambda flow: TOKEN)
    assert settings_api.phone_poll({}, b"") == (200, {"status": "ready"})
    job = settings_api.phone_enable({}, b"")
    assert callable(job)
    res = job(lambda m: None)
    assert res["ok"] and "alex" in res["message"]
    code, st = settings_api.phone_status()
    assert st["enabled"] and st["login"] == "alex" and "token" not in json.dumps(st).lower()
    assert settings_api.view()["phone_share"]["enabled"] is True
    code, out = settings_api.phone_push({}, b"")
    assert code == 200 and out["pushed"] is True
    code, out = settings_api.phone_disable({}, b"")
    assert code == 200 and out["status"]["enabled"] is False
    assert settings_api.phone_push({}, b"")[0] == 409
