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


def speak_voice(message: str, force: bool = False) -> None:
    """Speaks aloud using the Windows built-in speech synthesizer."""
    env = load_env()
    if not force and not env.get("ENABLE_VOICE", True):
        return
    try:
        clean_msg = message.replace("'", "''")
        cmd = ["powershell.exe", "-NoProfile", "-Command",
               f"& {{ Add-Type -AssemblyName System.Speech; "
               f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{clean_msg}') }}"]
        subprocess.run(cmd, check=False, timeout=30, creationflags=CREATE_NO_WINDOW)
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
