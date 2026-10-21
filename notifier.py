import logging
import subprocess

from campus import seat_text
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


def _notify(title: str, body: str, voice: str = "") -> None:
    env = load_env()
    log.info("Alert: %s - %s", title, body.replace("\n", " | "))
    if env.get("ENABLE_WINDOWS_TOAST", True):
        send_toast(f"{APP_NAME}: {title}", body)
    if voice:
        speak_voice(voice)


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
    _notify(title, body, voice)


def alert_attendance(changes: dict, minimum: int) -> None:
    """New absences and courses that dropped under the minimum (only when something changed)."""
    new_abs = changes.get("new_absences") or []
    dropped = changes.get("dropped_below") or []
    if not new_abs and not dropped:
        return
    lines = []
    for c in new_abs[:4]:
        state = f"{c['percent']:.0f}%" + (f", can miss {c['can_miss']:g} h more" if c["ok"] else f", need {c['need']:g} h present")
        lines.append(f"- {c['code']} {c['title'][:28]}: +{c['new_absent_hours']:g} h absent ({state})")
    for c in dropped:
        if c not in new_abs:
            lines.append(f"- {c['code']} {c['title'][:28]} is now under {minimum}% ({c['percent']:.0f}%)")
    first = (new_abs or dropped)[0]
    if dropped:
        title = f"Attendance under {minimum}% in {_plural(len(dropped), 'course')}"
        voice = (f"Attention: your attendance in {first['title']} has dropped to {first['percent']:.0f} percent, "
                 f"under the {minimum} percent minimum.")
    else:
        title = f"New absence in {_plural(len(new_abs), 'course')}"
        voice = f"An absence was recorded in {first['title']}. Attendance is now {first['percent']:.0f} percent."
    _notify(title, "\n".join(lines), voice)


def alert_announcements(new_items: list) -> None:
    if not new_items:
        return
    lines = [f"- {a['course'][:26]}: {a['text'][:70]}" for a in new_items[:3]]
    first = new_items[0]
    title = f"{_plural(len(new_items), 'new announcement')} on the LMS"
    voice = f"New announcement in {first['course']}: {first['text'][:140]}"
    _notify(title, "\n".join(lines), voice)


def _exam_line(e: dict) -> str:
    when = e["when"].strftime("%a %d %b, %I:%M %p").replace(" 0", " ")
    return f"- {e['title'][:34]}: {when}" + (f" · {seat_text(e)}" if seat_text(e) else "")


def alert_exams_soon(exams: list) -> None:
    """Exams within the configured number of days (daily check). `exams` carry 'when' and 'days'."""
    if not exams:
        return
    first = exams[0]
    if first["days"] == 0:
        lead = "today"
    elif first["days"] == 1:
        lead = "tomorrow"
    else:
        lead = f"in {_plural(first['days'], 'day')}"
    title = f"Exam {lead}: {first['title'][:40]}"
    voice = (f"Reminder: your {first.get('exam_type', '').lower() or 'exam'} for {first['title']} is {lead} at "
             f"{first['when'].strftime('%I:%M %p').lstrip('0')}" + (f", {seat_text(first)}." if seat_text(first) else "."))
    _notify(title, "\n".join(_exam_line(e) for e in exams[:4]), voice)


def alert_exam_today(e: dict) -> None:
    """Morning-of reminder (hourly job, once per exam)."""
    voice = (f"Good luck: your {e.get('exam_type', '').lower() or 'exam'} for {e['title']} is today at "
             f"{e['when'].strftime('%I:%M %p').lstrip('0')}" + (f", {seat_text(e)}." if seat_text(e) else "."))
    _notify(f"Exam today: {e['title'][:40]}", _exam_line(e), voice)


def alert_exams_scheduled(exams: list) -> None:
    """The seating plan appeared or changed for these exams."""
    if not exams:
        return
    ups = [e for e in exams if e.get("scheduled")]
    if not ups:
        return
    title = f"Exam schedule posted: {_plural(len(ups), 'paper')}"
    body = "\n".join(f"- {e['title'][:34]}: {e['date']} {e['start_time']}" + (f" · {seat_text(e)}" if seat_text(e) else "")
                     for e in ups[:4])
    _notify(title, body, f"The exam seating plan is out for {_plural(len(ups), 'paper')}. "
                         "Open Assignment Monitor to see your rooms and seats.")
