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


def _notify(title: str, body: str, voice: str = "", channels: bool = True) -> None:
    """Desktop notification, optional voice line and, unless `channels` is False, the phone and the mailbox."""
    env = load_env()
    log.info("Alert: %s - %s", title, body.replace("\n", " | "))
    if env.get("ENABLE_WINDOWS_TOAST", True):
        send_toast(f"{APP_NAME}: {title}", body)
    if voice:
        speak_voice(voice)
    if not channels:
        return
    try:
        from channels import send_all
        send_all(title, body)
    except Exception as e:
        log.warning("Channel delivery could not start: %s", e)


def alert_assignments(pending: list, extended: list) -> None:
    """Builds and sends a toast plus a voice alert summarising the state after a sync."""
    env = load_env()
    days_ahead = int(env.get("NOTIFY_DAYS_AHEAD", 3))
    fan_out = True

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
        fan_out = False      # a desktop note after each check; not worth a phone buzz or an email twice a day
    _notify(title, body, voice, channels=fan_out)


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
    if dropped:
        title = f"Attendance under {minimum}% in {_plural(len(dropped), 'course')}"
    else:
        title = f"New absence in {_plural(len(new_abs), 'course')}"
    _notify(title, "\n".join(lines))


def alert_assignment_files(posted: list) -> None:
    """A teacher posted a solution file or returned marked work (notification only). `posted` is [(assignment, kinds)]."""
    if not posted:
        return
    words = {"solution": "solution posted", "returned": "returned with comments"}
    lines = [f"- {a['title'][:40]}: {' and '.join(words.get(k, k) for k in kinds)}" for a, kinds in posted[:3]]
    n = len(posted)
    _notify("Returned work" if all(k == ["returned"] for _a, k in posted) else f"{_plural(n, 'assignment')} updated by the teacher",
            "\n".join(lines))


def alert_announcements(new_items: list) -> None:
    if not new_items:
        return
    lines = [f"- {a['course'][:26]}: {a['text'][:70]}" for a in new_items[:3]]
    title = f"{_plural(len(new_items), 'new announcement')} on the LMS"
    _notify(title, "\n".join(lines))


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
    _notify(title, "\n".join(_exam_line(e) for e in exams[:4]))


def alert_exam_today(e: dict) -> None:
    """Morning-of reminder (hourly job, once per exam)."""
    _notify(f"Exam today: {e['title'][:40]}", _exam_line(e))


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
    _notify(title, body)


def alert_lectures(new_items: list) -> None:
    """New lecture notes (notification only)."""
    if not new_items:
        return
    by_course = {}
    for x in new_items:
        by_course.setdefault(x["course"], []).append(x)
    lines = []
    for c, xs in list(by_course.items())[:3]:
        more = f" +{len(xs) - 2}" if len(xs) > 2 else ""
        lines.append(f"- {c[:28]}: " + ", ".join(
            (f"{x['title'][:24]} file" if x.get("kind") == "misc" else f"week {x['week']} {x['title'][:24]}") for x in xs[:2]) + more)
    _notify(f"New lecture notes in {_plural(len(by_course), 'course')}", "\n".join(lines))
