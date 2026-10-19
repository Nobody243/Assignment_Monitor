import logging
import subprocess

from config import load_env, APP_NAME
from deadlines import classify

log = logging.getLogger("bahria.notifier")
CREATE_NO_WINDOW = 0x08000000


def send_toast(title: str, message: str) -> None:
    """Native Windows 10/11 desktop notification."""
    try:
        from winotify import Notification
        toast = Notification(app_id=APP_NAME, title=title, msg=message, duration="short")
        toast.show()
    except Exception as e:
        log.warning("Toast notification failed: %s", e)


def _ps(script: str, timeout: int = 30):
    return subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                          check=False, timeout=timeout, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)


def list_voices() -> list:
    """Names of the speech voices installed on this PC (Windows built-in synthesizer)."""
    try:
        r = _ps("Add-Type -AssemblyName System.Speech; "
                "(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | "
                "Where-Object { $_.Enabled } | ForEach-Object { $_.VoiceInfo.Name }", timeout=20)
        return [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
    except Exception as e:
        log.warning("Could not list voices: %s", e)
        return []


def speak_voice(message: str, force: bool = False, voice: str = None, volume: int = None, rate: int = None) -> None:
    """Speaks aloud using the Windows built-in speech synthesizer, with the user's voice, volume and speed."""
    env = load_env()
    if not force and not env.get("ENABLE_VOICE", True):
        return
    voice = env.get("VOICE_NAME", "") if voice is None else voice
    volume = int(env.get("VOICE_VOLUME", 100)) if volume is None else int(volume)
    rate = int(env.get("VOICE_RATE", 0)) if rate is None else int(rate)
    try:
        clean_msg = message.replace("'", "''")
        clean_voice = (voice or "").replace("'", "''")
        select = f"try {{ $s.SelectVoice('{clean_voice}') }} catch {{ }}; " if clean_voice else ""
        _ps("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"{select}$s.Volume = {min(100, max(0, volume))}; $s.Rate = {min(5, max(-5, rate))}; $s.Speak('{clean_msg}')")
    except Exception as e:
        log.warning("Voice alert failed: %s", e)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def alert_assignments(pending: list, extended: list) -> None:
    """Builds and sends a toast plus a voice alert summarising the state after a sync."""
    env = load_env()
    days_ahead = int(env.get("NOTIFY_DAYS_AHEAD", 3))

    due_today = [p for p in pending if classify(p)["key"] == "today"]
    due_soon = [p for p in pending if (classify(p)["days"] or 99) <= days_ahead and classify(p)["key"] != "today"]

    if pending:
        first = due_today[0] if due_today else (sorted(pending, key=lambda p: classify(p)["days"] or 999)[0])
        voice = f"You have {_plural(len(pending), 'pending assignment')} on Bahria LMS."
        if due_today:
            voice += f" {first['title']} in {first['course']} is due today!"
        elif due_soon:
            voice += f" {first['title']} is due in {_plural(classify(first)['days'], 'day')}."
        if extended:
            voice += f" {_plural(len(extended), 'deadline')} extended."
        title = "Assignment due today!" if due_today else f"{_plural(len(pending), 'pending assignment')}"
        body = "\n".join(f"- {p['title']} ({classify(p)['label']})" for p in sorted(
            pending, key=lambda p: classify(p)["days"] if classify(p)["days"] is not None else 999)[:3])
    elif extended:
        voice = f"{_plural(len(extended), 'assignment deadline')} extended on Bahria LMS."
        title = "Deadline extended"
        body = "\n".join(f"- {e['title']}: now {e['due_date']}" for e in extended[:3])
    else:
        voice = ""
        title = "All caught up"
        body = "No pending assignments on Bahria LMS."

    log.info("Alert: %s - %s", title, body.replace("\n", " | "))
    if env.get("ENABLE_WINDOWS_TOAST", True):
        send_toast(f"{APP_NAME}: {title}", body)
    if voice:
        speak_voice(voice)
