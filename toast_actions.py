"""The buttons on a reminder notification.

A Windows notification can carry buttons that open a link. The installer registers the link scheme
`assignment-monitor:` for the installed program, so pressing Snooze or Done runs
`AssignmentMonitor.exe "assignment-monitor://snooze?id=...&h=1"`, which the app hands to the engine (see cli.py).

Only an installed program has the scheme registered, so a source run shows plain notifications without buttons.
A web page can also open such a link, so every link is checked: a known action, and an id that exists in the stored
assignments. The worst a stranger could do is silence one reminder."""
import logging
import os
from urllib.parse import parse_qs, quote, urlparse

import config
import reminders
import tracker

log = logging.getLogger("bahria.toast")
SCHEME = "assignment-monitor"


def available() -> bool:
    """True where the buttons would work: an installed program that owns the scheme."""
    return bool(config.FROZEN or os.environ.get("AM_SHELL_EXE"))


def actions_for(item: dict, hours: int = 1) -> list:
    """[(label, link)] for the notification about one assignment, or [] when buttons would do nothing."""
    if not available() or not item.get("id"):
        return []
    i = quote(str(item["id"]), safe="")
    return [(f"Snooze {hours} h", f"{SCHEME}://snooze?id={i}&h={hours}"), ("Done", f"{SCHEME}://done?id={i}")]


def handle(link: str) -> tuple:
    """Carries out a button press. Returns (ok, message); nothing is raised for a bad link."""
    try:
        u = urlparse(link)
    except ValueError:
        return False, "That link is not valid."
    if u.scheme != SCHEME or u.netloc not in ("snooze", "done"):
        return False, "That link is not an action this app knows."
    q = parse_qs(u.query)
    item_id = (q.get("id") or [""])[0]
    item = tracker.load_stored_assignments().get(item_id)
    if not item:
        return False, "That assignment is not in the saved list any more."
    if u.netloc == "snooze":
        try:
            hours = int((q.get("h") or ["1"])[0])
        except ValueError:
            hours = 1
        until = reminders.snooze(item_id, hours)
        log.info("Snoozed %s until %s", item.get("title"), until)
        return True, f"Snoozed until {until:%I:%M %p}".replace(" 0", " ")
    reminders.acknowledge(item)
    log.info("Marked done (reminders off): %s", item.get("title"))
    return True, "Okay: no more reminders for this one"
