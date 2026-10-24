"""Email routing, pairing crypto and calendar building, without touching the network."""
import json
from datetime import datetime, timedelta

import pytest

import channels
from calendar_export import build_ics, events_from, sync_calendar
from channels import b64url, b64url_decode, pairing_start, smtp_for, vapid_keys


def test_smtp_guess_by_domain():
    assert smtp_for("someone@gmail.com", {}) == ("smtp.gmail.com", 587)
    assert smtp_for("01-123@student.bahria.edu.pk", {}) == ("smtp.office365.com", 587)
    assert smtp_for("me@example.org", {}) == ("smtp.example.org", 587)
    assert smtp_for("me@example.org", {"EMAIL_HOST": "mail.corp.local", "EMAIL_PORT": 465}) == ("mail.corp.local", 465)


def test_b64url_roundtrip():
    raw = bytes(range(40))
    assert b64url_decode(b64url(raw)) == raw
    assert "=" not in b64url(raw)


def test_pairing_payload_roundtrip(monkeypatch):
    """What the phone page will do (AES-GCM with the key from the QR code) decrypts on the PC side."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    env = {"PUSH_VAPID": ""}
    monkeypatch.setattr(channels, "save_env", lambda e: env.update(e))
    pairing = pairing_start(env)
    assert pairing["url"].startswith("https://assignment-monitor.saaddev.top/phone#t=am-")
    assert "&k=" in pairing["url"] and "&p=" in pairing["url"] and len(pairing["code"]) == 6
    private, public = vapid_keys(env, save=False)
    assert "PRIVATE KEY" in private and len(b64url_decode(public)) == 65
    sub = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": {"p256dh": "x", "auth": "y"}}
    key = b64url_decode(pairing["key"])
    iv = b"\x01" * 12
    blob = iv + AESGCM(key).encrypt(iv, json.dumps(sub).encode(), None)
    line = json.dumps({"event": "message", "message": b64url(blob)})

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return (json.dumps({"event": "open"}) + "\n" + line).encode()
    monkeypatch.setattr(channels.urllib.request, "urlopen", lambda req, timeout=0: R())
    assert channels.pairing_poll(pairing) == sub


def test_send_email_requires_setup():
    with pytest.raises(RuntimeError):
        channels.send_email("x", "y", {"EMAIL_TO": "", "EMAIL_PASS": ""})


def _assignment(title, due, course="Operating Systems"):
    return {"id": f"{course}_{title}", "title": title, "course": course, "due_date": due.strftime("%d %B %Y - %I:%M %p"),
            "is_submitted": False, "status": "Pending"}


def test_events_and_ics():
    now = datetime(2026, 10, 22, 9, 0)
    due = now + timedelta(days=2)
    exams = [{"id": "e1", "course": "Cyber Security", "date": (now + timedelta(days=5)).strftime("%d/%m/%Y"), "time": "09:00 AM",
              "type": "Mid-Term", "room": "HL-18", "row": "1", "seat": "2", "scheduled": True, "session": "I"}]
    events = events_from([_assignment("Lab 9", due), _assignment("Old", now - timedelta(days=9))], exams, now)
    kinds = [e["uid"].split("-")[1] for e in events]
    assert kinds == ["asg", "exam"], "the stale assignment is left out and events are in date order"
    assert events[0]["end"] == due
    ics = build_ics(events, now)
    assert ics.count("BEGIN:VEVENT") == 2 and "TRIGGER:-P1D" in ics and "SUMMARY:Due: Lab 9 (Operating Systems)" in ics
    invite = build_ics(events[:1], now, method="REQUEST", organizer="me@gmail.com")
    assert "METHOD:REQUEST" in invite and "ATTENDEE" in invite


def test_sync_calendar_sends_each_event_once(tmp_path, monkeypatch):
    import calendar_export
    monkeypatch.setattr(calendar_export, "calendar_path", lambda: tmp_path / "cal.ics")
    env = {"CALENDAR_ENABLED": True, "CALENDAR_INVITES": True, "EMAIL_ENABLED": True, "EMAIL_TO": "me@gmail.com"}
    sent, marks = [], set()
    due = datetime.now() + timedelta(days=3)
    res = sync_calendar([_assignment("Quiz prep", due)], [], env, send=lambda s, b, ics: sent.append(s),
                        sent_before=lambda k: k in marks, mark_sent=marks.add)
    assert res["events"] == 1 and res["invited"] == 1 and (tmp_path / "cal.ics").exists()
    res2 = sync_calendar([_assignment("Quiz prep", due)], [], env, send=lambda s, b, ics: sent.append(s),
                         sent_before=lambda k: k in marks, mark_sent=marks.add)
    assert res2["invited"] == 0 and len(sent) == 1
    assert sync_calendar([], [], {"CALENDAR_ENABLED": False})["events"] == 0


def test_send_push_signs_with_the_stored_pem_key(tmp_path, monkeypatch):
    """The private key is kept as PEM; pywebpush must receive it as a signer object, not as text. The request is
    captured instead of sent."""
    import json
    import channels

    private, public = channels.vapid_keys({}, save=False)
    assert private.startswith("-----BEGIN")
    # the content encryption needs a real P-256 point for the phone's key
    import os
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    point = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    sub = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc",
           "keys": {"p256dh": channels.b64url(point), "auth": channels.b64url(os.urandom(16))}}
    seen = {}

    class FakeResponse:
        status_code = 201
        text = ""
        headers = {}

    class FakeSession:
        def post(self, url, data=None, headers=None, timeout=None, **kw):
            seen["url"], seen["headers"], seen["body"] = url, headers, data
            return FakeResponse()

    env = {"PUSH_SUB": json.dumps(sub), "PUSH_VAPID": json.dumps({"private": private, "public": public})}
    channels.send_push("Hello", "World", env=env, requests_session=FakeSession())
    assert seen["url"] == sub["endpoint"]
    assert seen["headers"]["Authorization"].startswith("vapid t=")
    assert seen["headers"]["Content-Encoding"] == "aes128gcm"
    assert len(seen["body"]) > 32
