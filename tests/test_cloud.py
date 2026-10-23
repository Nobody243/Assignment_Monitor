"""Cloud checks: the pieces that can be tested without GitHub (the workflow text, secret sealing, the device
flow's answers, the fingerprinted secret sync and the no-writes rule in the cloud)."""
import base64
import json

import pytest
import yaml

import cloud
import config


def test_workflow_runs_twice_a_day_from_the_pinned_release():
    d = yaml.safe_load(cloud.workflow_yaml("1.5.0"))
    d["on"] = d.pop(True)                      # YAML 1.1 reads the bare key "on" as a boolean
    assert [t["cron"] for t in d["on"]["schedule"]] == ["0 3 * * *", "0 14 * * *"]     # 08:00 and 19:00 PKT
    assert d["on"]["workflow_dispatch"]["inputs"]["mode"]["options"] == ["check", "verify"]
    assert d["permissions"] == {"contents": "write"}
    steps = d["jobs"]["check"]["steps"]
    app = next(s for s in steps if s.get("with", {}).get("repository"))
    assert app["with"] == {"repository": "Nobody243/Assignment_Monitor", "ref": "v1.5.0", "path": "app"}
    check = next(s for s in steps if s.get("name") == "Check")
    env = check["env"]
    assert env["ASSIGNMENT_MONITOR_RUNNER"] == "cloud"
    assert env["AM_ENABLE_WINDOWS_TOAST"] == "False" and env["AM_ENABLE_VOICE"] == "False"
    for key in cloud.SECRET_KEYS:
        assert env[f"AM_{key}"] == "${{ secrets.AM_%s }}" % key
    for key in cloud.PLAIN_KEYS:
        assert env[f"AM_{key}"] == ""                     # no settings given: empty, so the runner keeps defaults
    d2 = yaml.safe_load(cloud.workflow_yaml("1.5.0", {"INSTITUTE_ID": "3", "TRACK_EXAMS": False, "EMAIL_PORT": 465,
                                                    "EMAIL_TO": 'a"b@x.pk'}))
    env2 = next(s for s in d2["jobs"]["check"]["steps"] if s.get("name") == "Check")["env"]
    assert env2["AM_INSTITUTE_ID"] == "3" and env2["AM_TRACK_EXAMS"] == "False" and env2["AM_EMAIL_PORT"] == "465"
    assert env2["AM_EMAIL_TO"] == 'a"b@x.pk'
    assert "cloud_check.py" in check["run"]
    assert steps[-1]["if"] == "always()" and "git push" in steps[-1]["run"]


def test_only_real_secrets_become_repository_secrets():
    env = {"ENROLLMENT": "01-1-1", "PASSWORD": "p", "TRACK_EXAMS": False, "EMAIL_PORT": 465, "PUSH_SUB": "",
           "INSTITUTE_ID": "1"}
    v = cloud.secret_values(env)
    assert v["AM_ENROLLMENT"] == "01-1-1" and v["AM_PUSH_SUB"] == ""
    assert set(v) == {f"AM_{k}" for k in cloud.SECRET_KEYS}
    assert "AM_INSTITUTE_ID" not in v                     # "1" as a secret would mask every 1 in the logs
    p = cloud.plain_values(env)
    assert p["AM_INSTITUTE_ID"] == "1" and p["AM_TRACK_EXAMS"] == "False" and p["AM_EMAIL_PORT"] == "465"
    assert not (set(p) & set(v))


def test_seal_is_a_libsodium_sealed_box_for_the_repo_key():
    from nacl import encoding, public
    private = public.PrivateKey.generate()
    pk_b64 = private.public_key.encode(encoding.Base64Encoder()).decode()
    sealed = cloud.seal(pk_b64, "hunter2")
    assert public.SealedBox(private).decrypt(base64.b64decode(sealed)) == b"hunter2"


def test_device_poll_waits_slows_down_and_returns_the_token(monkeypatch):
    answers = iter([
        (200, {"error": "authorization_pending"}, {}),
        (200, {"error": "slow_down", "interval": 10}, {}),
        (200, {"access_token": "gho_x", "token_type": "bearer"}, {}),
    ])
    monkeypatch.setattr(cloud, "_request", lambda *a, **k: next(answers))
    monkeypatch.setattr(cloud, "GITHUB_CLIENT_ID", "abc")
    flow = {"device_code": "d", "interval": 5}
    assert cloud.device_poll(flow) is None
    assert cloud.device_poll(flow) is None and flow["interval"] == 11
    assert cloud.device_poll(flow) == "gho_x"


def test_device_poll_reports_expiry_and_denial(monkeypatch):
    monkeypatch.setattr(cloud, "GITHUB_CLIENT_ID", "abc")
    monkeypatch.setattr(cloud, "_request", lambda *a, **k: (200, {"error": "expired_token"}, {}))
    with pytest.raises(cloud.CloudError, match="expired"):
        cloud.device_poll({"device_code": "d"})
    monkeypatch.setattr(cloud, "_request", lambda *a, **k: (200, {"error": "access_denied"}, {}))
    with pytest.raises(cloud.CloudError, match="declined"):
        cloud.device_poll({"device_code": "d"})


def test_put_file_skips_an_unchanged_file_and_sends_the_sha_otherwise(monkeypatch):
    calls = []
    existing = {"sha": "abc", "content": base64.b64encode(b"same").decode()}

    def fake(method, url, token=None, body=None, **kw):
        calls.append((method, url.rsplit("/", 1)[-1], body))
        if method == "GET":
            return 200, existing, {}
        return 200, {}, {}
    monkeypatch.setattr(cloud, "_request", fake)
    cloud.put_file("t", "me/r", "README.md", b"same", "m")
    assert [c[0] for c in calls] == ["GET"]
    cloud.put_file("t", "me/r", "README.md", b"new", "m")
    assert calls[-1][0] == "PUT" and calls[-1][2]["sha"] == "abc"
    assert base64.b64decode(calls[-1][2]["content"]) == b"new"


def test_set_secrets_writes_non_empty_and_deletes_empty(monkeypatch):
    from nacl import encoding, public
    private = public.PrivateKey.generate()
    pk = {"key": private.public_key.encode(encoding.Base64Encoder()).decode(), "key_id": "k1"}
    calls = []

    def fake(method, url, token=None, body=None, **kw):
        calls.append((method, url.rsplit("/", 1)[-1], body))
        if method == "GET":
            return 200, pk, {}
        return 204, {}, {}
    monkeypatch.setattr(cloud, "_request", fake)
    n = cloud.set_secrets("t", "me/r", {"AM_PASSWORD": "p", "AM_PUSH_SUB": ""})
    assert n == 1
    put = next(c for c in calls if c[0] == "PUT")
    assert put[1] == "AM_PASSWORD" and put[2]["key_id"] == "k1"
    assert public.SealedBox(private).decrypt(base64.b64decode(put[2]["encrypted_value"])) == b"p"
    assert ("DELETE", "AM_PUSH_SUB", None) in calls


def test_sync_secrets_only_sends_when_the_settings_changed(monkeypatch):
    sent = []
    saved = {}
    monkeypatch.setattr(cloud, "set_secrets", lambda t, r, v: sent.append(v) or len(v))
    monkeypatch.setattr(cloud, "put_file", lambda *a, **k: None)
    monkeypatch.setattr(cloud, "save_env", lambda env: saved.update(env))
    env = {"CLOUD_ENABLED": True, "CLOUD_REPO": "me/r", "GITHUB_TOKEN": "t", "PASSWORD": "a", "CLOUD_HASH": ""}
    assert cloud.sync_secrets(env) is True and len(sent) == 1
    env["CLOUD_HASH"] = saved["CLOUD_HASH"]
    assert cloud.sync_secrets(env) is False and len(sent) == 1          # nothing changed
    env["PASSWORD"] = "b"
    assert cloud.sync_secrets(env) is True and len(sent) == 2
    env["CLOUD_HASH"] = saved["CLOUD_HASH"]
    env["ATTENDANCE_MIN"] = 80                                           # a plain setting counts too
    assert cloud.sync_secrets(env) is True and saved["CLOUD_VERSION"] == cloud.APP_VERSION
    assert cloud.sync_secrets({"CLOUD_ENABLED": False}) is False


def test_env_overrides_feed_the_cloud_runner(monkeypatch):
    monkeypatch.setenv("AM_PASSWORD", "secret")
    monkeypatch.setenv("AM_ATTENDANCE_MIN", "80")
    monkeypatch.setenv("AM_TRACK_EXAMS", "False")
    monkeypatch.setenv("AM_PUSH_SUB", json.dumps({"endpoint": "https://x"}))
    o = config.env_overrides()
    assert o["PASSWORD"] == "secret" and o["ATTENDANCE_MIN"] == 80 and o["TRACK_EXAMS"] is False
    assert json.loads(o["PUSH_SUB"])["endpoint"] == "https://x"
    assert config.load_env()["PASSWORD"] == "secret"


def test_save_env_writes_nothing_in_the_cloud(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "IN_CLOUD", True)
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / "settings.env")
    config.save_env({"ENROLLMENT": "01-1-1", "PASSWORD": "p"})
    assert not (tmp_path / "settings.env").exists()
