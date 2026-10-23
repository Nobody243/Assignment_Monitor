"""Phone and email delivery for the alerts the app already raises on Windows.

Email goes through the student's own mailbox (Gmail, Outlook, the university's Microsoft 365, or any SMTP server)
with an app password, so no third party ever sees a message. Phone pushes go straight from this PC to the phone's
browser push service with keys made on this PC; the website's /phone page only hands the subscription over once,
encrypted, through a throw-away ntfy.sh topic shown as a QR code.
"""
from __future__ import annotations

import base64
import json
import logging
import secrets
import smtplib
import ssl
import threading
import time
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from config import APP_NAME, SITE_URL, load_env, save_env

log = logging.getLogger("bahria.channels")

NTFY = "https://ntfy.sh"
# Public ntfy relays, tried in this order by the phone page; the PC polls all of them. ntfy rate-limits by public
# address, and on mobile networks thousands of phones share one, so the first relay often answers 429 for a phone
# that has never used it. Pairing is the only thing that touches a relay; the pushes themselves go straight from the
# PC to the phone's browser push service.
RELAYS = (NTFY, "https://ntfy.envs.net", "https://ntfy.hostux.net", "https://ntfy.mzte.de")
SMTP_BY_DOMAIN = {
    "gmail.com": ("smtp.gmail.com", 587), "googlemail.com": ("smtp.gmail.com", 587),
    "outlook.com": ("smtp.office365.com", 587), "hotmail.com": ("smtp.office365.com", 587),
    "live.com": ("smtp.office365.com", 587), "msn.com": ("smtp.office365.com", 587),
    "bahria.edu.pk": ("smtp.office365.com", 587), "student.bahria.edu.pk": ("smtp.office365.com", 587),
    "yahoo.com": ("smtp.mail.yahoo.com", 587), "icloud.com": ("smtp.mail.me.com", 587),
}
APP_PASSWORD_HELP = {
    "smtp.gmail.com": "Gmail: turn on 2-Step Verification, then Google Account → Security → App passwords.",
    "smtp.office365.com": "Outlook / Microsoft 365: Security → Advanced security options → App passwords "
                          "(or your normal password if the account allows it).",
    "smtp.mail.yahoo.com": "Yahoo: Account Security → Generate app password.",
    "smtp.mail.me.com": "iCloud: appleid.apple.com → Sign-In and Security → App-Specific Passwords.",
}


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    text = text.strip()
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ---------------------------------------------------------------------------- email
def smtp_for(address: str, env: dict | None = None) -> tuple:
    """(host, port) for an address: the explicit setting if one is saved, else guessed from the domain."""
    env = env or load_env()
    host = (env.get("EMAIL_HOST") or "").strip()
    if host:
        return host, int(env.get("EMAIL_PORT") or 587)
    domain = address.rsplit("@", 1)[-1].lower().strip()
    return SMTP_BY_DOMAIN.get(domain, (f"smtp.{domain}" if domain else "", 587))


def email_ready(env: dict | None = None) -> bool:
    env = env or load_env()
    return bool(env.get("EMAIL_ENABLED") and env.get("EMAIL_TO") and env.get("EMAIL_PASS"))


def send_email(subject: str, body: str, env: dict | None = None, ics: str | None = None, ics_method: str = "REQUEST",
               to: str | None = None) -> None:
    """Sends one plain-text mail from the student's mailbox to itself (or `to`). Raises on failure."""
    env = env or load_env()
    user = (env.get("EMAIL_USER") or env.get("EMAIL_TO") or "").strip()
    password = env.get("EMAIL_PASS") or ""
    to = (to or env.get("EMAIL_TO") or user).strip()
    if not user or not password or not to:
        raise RuntimeError("Email is not set up: address and app password are needed.")
    host, port = smtp_for(user, env)
    msg = EmailMessage()
    msg["From"] = f"{APP_NAME} <{user}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="assignment-monitor.local")
    msg.set_content(body + f"\n\n— {APP_NAME} on your PC")
    if ics:
        msg.add_alternative(ics, subtype="calendar", params={"method": ics_method, "charset": "utf-8"})
        msg.add_attachment(ics.encode("utf-8"), maintype="application", subtype="ics", filename="invite.ics")
    ctx = ssl.create_default_context()
    if int(port) == 465:
        with smtplib.SMTP_SSL(host, int(port), context=ctx, timeout=30) as s:
            s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, int(port), timeout=30) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
            s.login(user, password)
            s.send_message(msg)
    log.info("Email sent: %s", subject)


# ---------------------------------------------------------------------------- web push
def _vapid():
    from py_vapid import Vapid02
    return Vapid02


def vapid_keys(env: dict | None = None, save: bool = True) -> tuple:
    """(private PEM, public key base64url). Made once per PC and kept encrypted with the other secrets."""
    env = env or load_env()
    stored = env.get("PUSH_VAPID") or ""
    if stored:
        try:
            d = json.loads(stored)
            return d["private"], d["public"]
        except Exception:
            pass
    from cryptography.hazmat.primitives import serialization
    v = _vapid()()
    v.generate_keys()
    private = v.private_pem().decode("ascii") if isinstance(v.private_pem(), bytes) else v.private_pem()
    raw = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    public = b64url(raw)
    if save:
        env = dict(env)
        env["PUSH_VAPID"] = json.dumps({"private": private, "public": public})
        save_env(env)
    return private, public


def pairing_start(env: dict | None = None) -> dict:
    """A fresh pairing: a throw-away ntfy topic, an AES key that only the QR code carries, and the URL to open on
    the phone. Returns {"topic", "key", "url", "code"}."""
    _, public = vapid_keys(env)
    topic = "am-" + secrets.token_urlsafe(18).replace("-", "x").replace("_", "y")
    key = secrets.token_bytes(32)
    url = f"{SITE_URL}/phone#t={topic}&k={b64url(key)}&p={public}"
    return {"topic": topic, "key": b64url(key), "url": url, "code": topic[3:9].upper(), "started": time.time()}


def _relay_lines(relay: str, topic: str, timeout: float) -> list[str]:
    req = urllib.request.Request(f"{relay}/{topic}/json?poll=1&since=30m", headers={"User-Agent": APP_NAME})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace").splitlines()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log.debug("pairing poll %s: %s", relay, e)
        return []


def pairing_poll(pairing: dict, timeout: float = 6.0) -> dict | None:
    """Looks for the phone's encrypted subscription on the pairing topic, on every relay at once (the phone uses the
    first one that accepts it). Returns the subscription dict or None; marks pairing["opened"] when the phone has
    opened the page."""
    import threading
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    results: dict[str, list[str]] = {}
    workers = [threading.Thread(target=lambda r=r: results.__setitem__(r, _relay_lines(r, pairing["topic"], timeout)), daemon=True)
               for r in RELAYS]
    for w in workers:
        w.start()
    for w in workers:
        w.join(timeout + 1)
    lines = [ln for r in RELAYS for ln in results.get(r, [])]
    if any('"message":"opened"' in ln for ln in lines):   # the page said hello; the dialog tells the user what to tap
        pairing["opened"] = True
    key = b64url_decode(pairing["key"])
    for line in reversed(lines):
        try:
            evt = json.loads(line)
            if evt.get("event") != "message" or evt.get("message") == "opened":
                continue
            blob = b64url_decode(evt.get("message", ""))
            plain = AESGCM(key).decrypt(blob[:12], blob[12:], None)
            sub = json.loads(plain.decode("utf-8"))
            if sub.get("endpoint") and sub.get("keys", {}).get("p256dh"):
                return sub
        except Exception:
            continue
    return None


def save_subscription(sub: dict | None, env: dict | None = None) -> None:
    env = dict(env or load_env())
    env["PUSH_SUB"] = json.dumps(sub) if sub else ""
    env["PUSH_ENABLED"] = bool(sub)
    save_env(env)


def push_ready(env: dict | None = None) -> bool:
    env = env or load_env()
    return bool(env.get("PUSH_ENABLED") and env.get("PUSH_SUB"))


def push_device(env: dict | None = None) -> str:
    """A short description of the paired phone from its push endpoint host."""
    env = env or load_env()
    try:
        host = json.loads(env.get("PUSH_SUB") or "{}").get("endpoint", "").split("/")[2]
    except Exception:
        return ""
    if "google" in host or "fcm" in host:
        return "Android (Chrome or Samsung Internet)"
    if "apple" in host or "push.apple" in host:
        return "iPhone or iPad"
    if "mozilla" in host:
        return "Firefox"
    return host


def send_push(title: str, body: str, url: str | None = None, env: dict | None = None) -> None:
    """One notification to the paired phone, encrypted end to end by the push protocol. Raises on failure; a phone
    that has withdrawn its subscription (404/410) is unpaired automatically."""
    from pywebpush import WebPushException, webpush
    env = env or load_env()
    sub = json.loads(env.get("PUSH_SUB") or "{}")
    if not sub:
        raise RuntimeError("No phone is paired.")
    private, _ = vapid_keys(env, save=False)
    payload = json.dumps({"title": title, "body": body, "url": url or SITE_URL, "tag": f"am-{abs(hash(title)) % 10000}"})
    try:
        webpush(subscription_info=sub, data=payload, vapid_private_key=private, ttl=86400,
                vapid_claims={"sub": SITE_URL, "aud": "/".join(sub["endpoint"].split("/")[:3])})
    except WebPushException as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (404, 410):
            log.warning("The paired phone dropped its subscription; unpairing.")
            save_subscription(None, env)
        raise
    log.info("Push sent: %s", title)


# ---------------------------------------------------------------------------- fan-out
def send_all(title: str, body: str, url: str | None = None) -> None:
    """Delivers an alert to every linked channel without blocking the caller; failures are logged, never raised."""
    env = load_env()
    jobs = []
    if email_ready(env):
        jobs.append(("email", lambda: send_email(f"{APP_NAME}: {title}", body, env)))
    if push_ready(env):
        jobs.append(("phone", lambda: send_push(title, body, url, env)))
    if not jobs:
        return

    def run():
        for name, fn in jobs:
            try:
                fn()
            except Exception as e:
                log.warning("%s delivery failed: %s", name, str(e)[:200])
    threading.Thread(target=run, name="channels", daemon=True).start()
