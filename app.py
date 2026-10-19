"""
Assignment Monitor - desktop application and command-line entry point.

    app.py                 open the window (sign-in screen on first run)
    app.py --check         background sync + notifications (daily / sign-in task)
    app.py --remind        hourly same-day reminder task
    app.py --status        print the saved assignments
    app.py --test-alert    test desktop notification and voice
    app.py --tray          start minimized to the system tray
    app.py --quit          ask a running instance to quit
"""
import ctypes
import logging
import os
import queue
import re
import sys
import threading
import webbrowser
from datetime import datetime

if sys.stdout is None or sys.stderr is None:          # windowed exe: no console attached
    sys.stdout = sys.stdout or open(os.devnull, "w")
    sys.stderr = sys.stderr or open(os.devnull, "w")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from config import (APP_ID, APP_NAME, APP_VERSION, TAGLINE, ASSETS_DIR, BASE_DIR, DATA_DIR, DOCS_DIR, LOG_PATH,
                    FROZEN, RELEASES_URL, REPO_URL, CAMPUS_NAMES, CAMPUS_ID_BY_NAME, campus_name,
                    load_env, save_env, has_credentials, load_meta, setup_logging)

log = logging.getLogger("bahria.app")
ENROLLMENT_RE = re.compile(r"^\d{2}-\d{6}-\d{3}$")
GEOMETRY_RE = re.compile(r"^\d{3,5}x\d{3,5}\+-?\d+\+-?\d+$")
# One instance per data folder, so a portable or demo copy can run beside the installed app.
_INSTANCE_TAG = ""
if os.environ.get("ASSIGNMENT_MONITOR_HOME"):
    import hashlib
    _INSTANCE_TAG = "." + hashlib.sha1(str(BASE_DIR).lower().encode()).hexdigest()[:8]
SHOW_EVENT_NAME = f"Local\\AssignmentMonitor.ShowWindow{_INSTANCE_TAG}"
QUIT_EVENT_NAME = f"Local\\AssignmentMonitor.Quit{_INSTANCE_TAG}"
MUTEX_NAME = f"Local\\AssignmentMonitor.MainWindow{_INSTANCE_TAG}"


# ============================================================================ command line
def main():
    import argparse
    parser = argparse.ArgumentParser(prog="AssignmentMonitor", description=f"{APP_NAME} {TAGLINE}")
    parser.add_argument("--check", action="store_true", help="sync assignments and notify, then exit")
    parser.add_argument("--remind", action="store_true", help="hourly same-day reminder, then exit")
    parser.add_argument("--status", action="store_true", help="print saved assignments, then exit")
    parser.add_argument("--test-alert", action="store_true", help="test notification and voice, then exit")
    parser.add_argument("--test", action="store_true", help="with --remind: simulate an assignment due today")
    parser.add_argument("--quiet", "-q", action="store_true", help="with --check: no notifications")
    parser.add_argument("--visible", action="store_true", help="with --check: show the browser window")
    parser.add_argument("--setup", action="store_true", help="open the sign-in screen (switch account)")
    parser.add_argument("--tray", action="store_true", help="start minimized to the system tray")
    parser.add_argument("--quit", action="store_true", help="ask a running instance to quit, then exit")
    parser.add_argument("--enable-automation", action="store_true", help="register the background tasks, then exit")
    parser.add_argument("--disable-automation", action="store_true", help="remove the background tasks, then exit")
    parser.add_argument("--view", default="dashboard", choices=["dashboard", "assignments", "settings", "activity"])
    args = parser.parse_args()
    setup_logging(to_console=not FROZEN)

    if args.check or args.remind or args.status or args.test_alert:
        import jobs
        if args.check:
            code = jobs.run_check(quiet=args.quiet, headless=False if args.visible else None)
        elif args.remind:
            code = jobs.run_reminder(test=args.test)
        elif args.status:
            code = jobs.print_status()
        else:
            code = jobs.test_alert()
        sys.exit(code)
    if args.quit:
        sys.exit(0 if _signal_event(QUIT_EVENT_NAME) else 1)
    if args.enable_automation or args.disable_automation:
        import automation
        ok, msg = automation.enable() if args.enable_automation else automation.disable()
        if args.disable_automation:
            automation.set_start_with_windows(False)
        print(msg)
        sys.exit(0 if ok else 1)

    run_gui(start_view=args.view, force_setup=args.setup, start_hidden=args.tray)


def run_gui(start_view="dashboard", force_setup=False, start_hidden=False):
    if _another_instance_running():
        log.info("Already running; bringing the existing window to the front.")
        _signal_event(SHOW_EVENT_NAME)
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass
    log.info("%s %s started (%s)", APP_NAME, APP_VERSION, "packaged" if FROZEN else "source")
    try:
        App(start_view=start_view, force_setup=force_setup, start_hidden=start_hidden).mainloop()
    except Exception:
        log.exception("The app crashed")
        raise
    finally:
        _exit_cleanly()


def _exit_cleanly():
    """The tray library runs a non-daemon thread; make sure the process really ends."""
    main_thread = threading.main_thread()
    for t in threading.enumerate():
        if t is not main_thread and not t.daemon:
            t.join(timeout=2)
    stuck = [t.name for t in threading.enumerate() if t is not main_thread and not t.daemon and t.is_alive()]
    log.info("%s quit%s", APP_NAME, f" (forcing exit; threads still alive: {stuck})" if stuck else "")
    logging.shutdown()
    if stuck:
        os._exit(0)


_MUTEX = None


def _another_instance_running() -> bool:
    global _MUTEX
    try:
        _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
        return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return False


def _signal_event(name: str) -> bool:
    """Sets a named event owned by the running instance. Returns False if nothing is running."""
    try:
        k32 = ctypes.windll.kernel32
        h = k32.OpenEventW(0x0002, False, name)  # EVENT_MODIFY_STATE
        if not h:
            return False
        k32.SetEvent(h)
        k32.CloseHandle(h)
        return True
    except Exception:
        return False


# ============================================================================ GUI
import customtkinter as ctk                      # noqa: E402  (imported after the CLI fast path)
import tkinter.font as tkfont                    # noqa: E402
from tkinter import messagebox                   # noqa: E402

import automation                                                                           # noqa: E402
import updater                                                                              # noqa: E402
from tray import TrayIcon                                                                   # noqa: E402
from tracker import load_stored_assignments, compare_assignments, clear_stored_assignments  # noqa: E402
from lms_scraper import run_lms_check, LoginError, _release_lock                            # noqa: E402
from notifier import alert_assignments, send_toast, speak_voice, list_voices               # noqa: E402
from deadlines import classify, is_open_pending, sort_key, deadline_of                     # noqa: E402

# ---------------------------------------------------------------------------- design tokens
# Direction: calm and editorial. Warm neutral surfaces, one accent, two type weights, a fixed
# type scale, hairline dividers instead of nested cards, no decorative icons.
# Every colour is a (light, dark) pair so the theme switch restyles the live window.
C = {
    "bg": ("#f4f4f1", "#121314"), "surface": ("#ffffff", "#1a1c1e"), "surface2": ("#eeeeea", "#232629"),
    "field": ("#fafaf8", "#202326"), "line": ("#e3e3de", "#2c2f33"), "line2": ("#d6d6d0", "#3a3e43"),
    "ink": ("#1b1b1a", "#ececea"), "muted": ("#62625e", "#a0a39e"), "dim": ("#9a9a94", "#6a6d69"),
    "accent": ("#1f4fd8", "#7aa2ff"), "accent_h": ("#183fae", "#93b4ff"), "on_accent": ("#ffffff", "#0e1320"),
    "red": ("#c0392b", "#ff7b6b"), "amber": ("#a85f00", "#f0b35c"), "green": ("#1e7d3e", "#5ccf7a"),
    "sky": ("#0b6e99", "#5fb8e0"), "violet": ("#5b3fb5", "#b7a3ff"),
    "red_t": ("#fbe9e6", "#2a1c1a"), "amber_t": ("#fbf0dc", "#2a2418"), "green_t": ("#e4f3e8", "#182820"),
    "sky_t": ("#e2f0f7", "#16242b"), "violet_t": ("#ece7f8", "#221e2e"), "grey_t": ("#eeeeea", "#232629"),
}
URGENCY = {"today": "red", "missed": "red", "soon": "amber", "week": "sky", "later": "dim",
           "submitted": "green", "unknown": "dim"}
FONTS = {"body": "Segoe UI", "display": "Segoe UI", "mono": "Consolas"}


def pick_fonts():
    try:
        fams = set(tkfont.families())
    except Exception:
        return
    if "Segoe UI Variable Text" in fams:
        FONTS["body"] = "Segoe UI Variable Text"
    if "Segoe UI Variable Display" in fams:
        FONTS["display"] = "Segoe UI Variable Display"
    if "Cascadia Mono" in fams:
        FONTS["mono"] = "Cascadia Mono"


def F(size=13, weight="normal", display=False):
    return ctk.CTkFont(family=FONTS["display" if display else "body"], size=size, weight=weight)


# type scale: 11 caption · 13 body · 14 lead · 17 section · 22 page · 30 display


def urgency_color(key):
    return C[URGENCY[key]]


def urgency_tint(key):
    name = URGENCY[key]
    return C[f"{name}_t"] if f"{name}_t" in C else C["grey_t"]


def pill(parent, text, key_or_color, size=11):
    color = C[URGENCY[key_or_color]] if key_or_color in URGENCY else key_or_color
    tint = urgency_tint(key_or_color) if key_or_color in URGENCY else C["surface2"]
    return ctk.CTkLabel(parent, text=f"  {text}  ", font=F(size, "bold"), fg_color=tint, text_color=color,
                        corner_radius=6, height=24)


def surface(parent, **kw):
    opts = dict(fg_color=C["surface"], corner_radius=12, border_width=1, border_color=C["line"])
    opts.update(kw)
    return ctk.CTkFrame(parent, **opts)


def hairline(parent, padx=20):
    ctk.CTkFrame(parent, fg_color=C["line"], height=1, corner_radius=0).pack(fill="x", padx=padx)


def heading(parent, text, sub=None, size=17):
    box = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(box, text=text, font=F(size, "bold", display=True), text_color=C["ink"]).pack(anchor="w")
    if sub:
        ctk.CTkLabel(box, text=sub, font=F(12), text_color=C["muted"]).pack(anchor="w", pady=(1, 0))
    return box


def soft_button(parent, text, cmd, width=None):
    kw = dict(width=width) if width else {}
    return ctk.CTkButton(parent, text=text, font=F(12, "bold"), height=34, fg_color=C["surface2"],
                         hover_color=C["line2"], text_color=C["ink"], corner_radius=8, command=cmd, **kw)


def primary_button(parent, text, cmd, height=38, width=None):
    kw = dict(width=width) if width else {}
    return ctk.CTkButton(parent, text=text, font=F(13, "bold"), height=height, fg_color=C["accent"],
                         hover_color=C["accent_h"], text_color=C["on_accent"], corner_radius=8, command=cmd, **kw)


def bind_click(widget, cb):
    widget.bind("<Button-1>", lambda e: cb())
    try:
        widget.configure(cursor="hand2")
    except Exception:
        pass
    for child in widget.winfo_children():
        bind_click(child, cb)


def fmt_due(item):
    dt = deadline_of(item)
    if not dt:
        return item.get("due_date", "No deadline")
    return dt.strftime("%a %d %b · %I:%M %p").replace(" 0", " ").replace("AM", "am").replace("PM", "pm")


def open_doc(name, fallback_url=None):
    path = DOCS_DIR / name
    if path.exists():
        os.startfile(path)
    elif fallback_url:
        webbrowser.open(fallback_url)


def theme_switch(parent, app):
    sw = ctk.CTkSwitch(parent, text="Dark theme", font=F(12), text_color=C["muted"], progress_color=C["accent"],
                       command=lambda: app.set_theme("dark" if sw.get() else "light"))
    sw.select() if app.theme == "dark" else sw.deselect()
    return sw


class QueueHandler(logging.Handler):
    def __init__(self, q):
        super().__init__()
        self.q = q
        self.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))

    def emit(self, record):
        try:
            self.q.put(self.format(record))
        except Exception:
            pass


# ---------------------------------------------------------------------------- sign-in screen
class SetupView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=C["bg"])
        self.app = app
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(0, weight=1)
        self._build_left()
        self._build_right()

    def _build_left(self):
        left = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        ctk.CTkFrame(self, fg_color=C["line"], width=1, corner_radius=0).grid(row=0, column=0, sticky="nse")
        inner = ctk.CTkFrame(left, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.76)

        if self.app.logo:
            ctk.CTkLabel(inner, text="", image=self.app.logo).pack(anchor="w")
        ctk.CTkLabel(inner, text=APP_NAME, font=F(30, "bold", display=True), text_color=C["ink"]).pack(anchor="w", pady=(14, 0))
        ctk.CTkLabel(inner, text=TAGLINE, font=F(14), text_color=C["accent"]).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(inner, text="Your assignments, deadlines and reminders in one place.\nSet it up once; it runs on its own.",
                     font=F(14), text_color=C["muted"], justify="left").pack(anchor="w", pady=(0, 28))

        for title, desc in [
            ("Checks the LMS for you", "Signs in every evening at 7 PM and whenever your PC starts, then tells you what is pending."),
            ("Catches extended deadlines", "The portal hides them in a merged date string. The app reads both dates."),
            ("Reminds you on the day", "Hourly voice and desktop reminders while an unsubmitted assignment is due today."),
            ("Stays on your PC", "Your password is encrypted by Windows for your account and only ever sent to cms.bahria.edu.pk."),
        ]:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkFrame(row, fg_color=C["accent"], width=3, height=2, corner_radius=2).pack(side="left", fill="y", pady=3)
            txt = ctk.CTkFrame(row, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True, padx=(14, 0))
            ctk.CTkLabel(txt, text=title, font=F(14, "bold"), text_color=C["ink"]).pack(anchor="w")
            ctk.CTkLabel(txt, text=desc, font=F(12), text_color=C["muted"], justify="left", wraplength=340).pack(anchor="w")

    def _build_right(self):
        right = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        theme_switch(right, self.app).place(relx=1.0, rely=0.0, anchor="ne", x=-24, y=18)
        box = surface(right)
        box.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72)
        pad = {"padx": 32}

        ctk.CTkLabel(box, text="Sign in to your student portal", font=F(22, "bold", display=True),
                     text_color=C["ink"]).pack(anchor="w", pady=(28, 2), **pad)
        ctk.CTkLabel(box, text="The same enrollment number and password you use on cms.bahria.edu.pk.",
                     font=F(12), text_color=C["muted"]).pack(anchor="w", pady=(0, 18), **pad)

        env = self.app.env
        self.enroll = self._field(box, "Enrollment number", "01-123456-001", pad)
        if env.get("ENROLLMENT"):
            self.enroll.insert(0, env["ENROLLMENT"])

        ctk.CTkLabel(box, text="Portal password", font=F(12, "bold"), text_color=C["muted"]).pack(anchor="w", **pad)
        pw_row = ctk.CTkFrame(box, fg_color="transparent")
        pw_row.pack(fill="x", pady=(2, 12), **pad)
        self.password = ctk.CTkEntry(pw_row, placeholder_text="Password", show="•", height=40, font=F(13),
                                     fg_color=C["field"], border_color=C["line2"], text_color=C["ink"])
        self.password.pack(side="left", fill="x", expand=True)
        self.show_pw = ctk.CTkCheckBox(pw_row, text="Show", font=F(12), width=70, text_color=C["muted"],
                                       command=self._toggle_pw)
        self.show_pw.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(box, text="Campus", font=F(12, "bold"), text_color=C["muted"]).pack(anchor="w", **pad)
        self.campus = ctk.CTkOptionMenu(box, values=CAMPUS_NAMES, height=40, font=F(13), fg_color=C["field"],
                                        text_color=C["ink"], button_color=C["accent"], button_hover_color=C["accent_h"],
                                        dropdown_font=F(12))
        self.campus.set(campus_name(env.get("INSTITUTE_ID", "1")))
        self.campus.pack(fill="x", pady=(2, 14), **pad)

        self.automation = ctk.CTkCheckBox(box, text="Check automatically (daily at 7 PM, at sign-in, hourly on due days)",
                                          font=F(12), text_color=C["ink"])
        self.automation.select()
        self.automation.pack(anchor="w", pady=(0, 16), **pad)

        self.button = primary_button(box, "Connect and start monitoring", self.connect, height=44)
        self.button.pack(fill="x", **pad)
        self.enroll.bind("<Return>", lambda e: self.connect())
        self.password.bind("<Return>", lambda e: self.connect())

        legal = ctk.CTkFrame(box, fg_color="transparent")
        legal.pack(fill="x", pady=(10, 0), **pad)
        ctk.CTkLabel(legal, text="Unofficial app, not affiliated with Bahria University. Use your own account only.",
                     font=F(11), text_color=C["dim"], wraplength=440, justify="left").pack(anchor="w")
        link = ctk.CTkLabel(legal, text="Privacy & terms", font=F(11, "bold"), text_color=C["accent"], cursor="hand2")
        link.pack(anchor="w")
        link.bind("<Button-1>", lambda e: open_doc("PRIVACY.md", f"{REPO_URL}/blob/main/PRIVACY.md"))

        self.progress = ctk.CTkProgressBar(box, mode="indeterminate", height=4, progress_color=C["accent"],
                                           fg_color=C["surface2"])
        self.status = ctk.CTkLabel(box, text="", font=F(12), text_color=C["muted"], wraplength=430, justify="left")
        self.status.pack(anchor="w", pady=(10, 0), **pad)
        self.console = ctk.CTkTextbox(box, height=90, font=ctk.CTkFont(family=FONTS["mono"], size=11),
                                      fg_color=C["bg"], text_color=C["muted"], state="disabled")
        ctk.CTkLabel(box, text="", height=12).pack()

    def _field(self, parent, label, placeholder, pad):
        ctk.CTkLabel(parent, text=label, font=F(12, "bold"), text_color=C["muted"]).pack(anchor="w", **pad)
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder, height=40, font=F(13), fg_color=C["field"],
                             border_color=C["line2"], text_color=C["ink"])
        entry.pack(fill="x", pady=(2, 12), **pad)
        return entry

    def _toggle_pw(self):
        self.password.configure(show="" if self.show_pw.get() else "•")

    def console_write(self, line):
        self.console.configure(state="normal")
        self.console.insert("end", line + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def connect(self):
        enroll = self.enroll.get().strip()
        pwd = self.password.get()
        if not enroll or not pwd:
            self.status.configure(text="Enter both your enrollment number and password.", text_color=C["red"])
            return
        if not ENROLLMENT_RE.match(enroll):
            self.status.configure(text="Enrollment numbers look like 01-123456-001.", text_color=C["amber"])
            return
        env = dict(self.app.env)
        env.update({"ENROLLMENT": enroll, "PASSWORD": pwd,
                    "INSTITUTE_ID": CAMPUS_ID_BY_NAME.get(self.campus.get(), "1")})
        save_env(env)
        self.app.env = load_env()

        self.button.configure(state="disabled", text="Connecting…")
        self.status.configure(text="Signing in and reading your assignments. About a minute.", text_color=C["muted"])
        self.progress.pack(fill="x", padx=32, pady=(10, 0), before=self.status)
        self.progress.start()
        self.console.pack(fill="x", padx=32, pady=(8, 0))
        self.app.setup_console = self
        threading.Thread(target=self._worker, args=(self.automation.get() == 1,), daemon=True).start()

    def _worker(self, enable_automation):
        try:
            items = run_lms_check(headless=True)
            pending, extended, _ = compare_assignments(items)
            note = ""
            if enable_automation:
                ok, _ = automation.enable()
                note = "" if ok else " Automatic checks could not be registered; retry from Settings."
            result = (True, f"Connected. {len(items)} assignments found, {len(pending)} pending.{note}")
        except LoginError as e:
            result = (False, str(e))
        except Exception as e:
            result = (False, f"Could not finish the first sync: {e}")
        self.app.after(0, self._done, result)

    def _done(self, result):
        ok, msg = result
        self.progress.stop()
        self.app.setup_console = None
        if ok:
            self.status.configure(text=msg, text_color=C["green"])
            self.app.after(600, self.app.show_main)
        else:
            self.progress.pack_forget()
            self.status.configure(text=msg, text_color=C["red"])
            self.button.configure(state="normal", text="Try again")


# ---------------------------------------------------------------------------- dashboard
class DashboardView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

    def refresh(self):
        for w in self.winfo_children():
            w.destroy()
        try:
            self._parent_canvas.yview_moveto(0)
        except Exception:
            pass
        data = list(self.app.data.values())
        meta = self.app.meta
        now = datetime.now()

        hour = now.hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        first_name = (meta.get("student_name") or "").split(" ")[0].title() or "there"
        ctk.CTkLabel(self, text=f"{greeting}, {first_name}.", font=F(22, "bold", display=True),
                     text_color=C["ink"]).pack(anchor="w", pady=(2, 0))
        bits = [meta.get("semester"), f"{len(meta.get('courses', []))} courses" if meta.get("courses") else None,
                campus_name(self.app.env.get("INSTITUTE_ID", "1"))]
        ctk.CTkLabel(self, text="  ·  ".join(b for b in bits if b), font=F(13), text_color=C["muted"]).pack(anchor="w", pady=(0, 18))

        if not data:
            box = surface(self)
            box.pack(fill="x")
            ctk.CTkLabel(box, text="Nothing here yet", font=F(17, "bold", display=True), text_color=C["ink"]).pack(pady=(28, 2))
            ctk.CTkLabel(box, text="Press Sync now (or F5) to read your assignments from the LMS.",
                         font=F(13), text_color=C["muted"]).pack(pady=(0, 28))
            return

        infos = {id(a): classify(a, now) for a in data}
        open_items = sorted([a for a in data if is_open_pending(a)], key=sort_key)
        counts = [
            ("Pending", len(open_items), "Pending"),
            ("Due today", sum(1 for a in open_items if infos[id(a)]["key"] == "today"), "Pending"),
            ("Due this week", sum(1 for a in open_items if infos[id(a)]["key"] in ("today", "soon", "week")), "Due soon"),
            ("Extended", sum(1 for a in data if a.get("is_extended") or a.get("previous_due_date")), "Extended"),
            ("Overdue", sum(1 for a in data if infos[id(a)]["key"] == "missed"), "Overdue"),
            ("Submitted", sum(1 for a in data if a.get("is_submitted")), "Submitted"),
        ]

        self._next_deadline(open_items[0] if open_items else None, infos)
        self._stats(counts)

        box = surface(self)
        box.pack(fill="x", pady=(14, 0))
        heading(box, "Needs your attention", "Unsubmitted work, nearest deadline first").pack(anchor="w", padx=20, pady=(18, 12))
        if not open_items:
            ctk.CTkLabel(box, text="All caught up. Nothing is waiting for a submission.", font=F(14),
                         text_color=C["muted"]).pack(anchor="w", padx=20, pady=(0, 20))
        else:
            for i, a in enumerate(open_items[:8]):
                if i:
                    hairline(box)
                self._attention_row(box, a, infos[id(a)])
            ctk.CTkLabel(box, text="", height=6).pack()

        courses = {}
        for a in data:
            c = courses.setdefault(a.get("course", "Unknown"), {"total": 0, "submitted": 0, "open": 0})
            c["total"] += 1
            c["submitted"] += 1 if a.get("is_submitted") else 0
            c["open"] += 1 if is_open_pending(a) else 0
        heading(self, "Courses", "Submission progress this semester").pack(anchor="w", pady=(22, 10))
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x")
        cols = 3
        for i in range(cols):
            grid.grid_columnconfigure(i, weight=1, uniform="course")
        for idx, (name_, c) in enumerate(sorted(courses.items())):
            cc = surface(grid)
            cc.grid(row=idx // cols, column=idx % cols, padx=(0 if idx % cols == 0 else 10, 0), pady=(0, 10), sticky="nsew")
            ctk.CTkLabel(cc, text=name_, font=F(13, "bold"), text_color=C["ink"], anchor="w", wraplength=250,
                         justify="left").pack(anchor="w", padx=16, pady=(14, 2))
            ratio = c["submitted"] / c["total"] if c["total"] else 0
            ctk.CTkLabel(cc, text=f"{c['submitted']} of {c['total']} submitted" + (f"  ·  {c['open']} pending" if c["open"] else ""),
                         font=F(12), text_color=C["amber"] if c["open"] else C["muted"]).pack(anchor="w", padx=16)
            bar = ctk.CTkProgressBar(cc, height=4, progress_color=C["green"] if ratio == 1 else C["accent"],
                                     fg_color=C["surface2"], corner_radius=2)
            bar.set(ratio)
            bar.pack(fill="x", padx=16, pady=(10, 14))
            bind_click(cc, lambda n=name_: self.app.navigate("assignments", course=n))

    def _next_deadline(self, item, infos):
        if item is None:
            box = surface(self, fg_color=C["green_t"], border_color=C["green_t"])
            box.pack(fill="x")
            ctk.CTkLabel(box, text="ALL CAUGHT UP", font=F(11, "bold"), text_color=C["green"]).pack(anchor="w", padx=20, pady=(18, 0))
            ctk.CTkLabel(box, text="No pending assignments right now.", font=F(20, "bold", display=True),
                         text_color=C["ink"]).pack(anchor="w", padx=20, pady=(2, 18))
            return
        info = infos[id(item)]
        color = urgency_color(info["key"])
        box = surface(self, fg_color=urgency_tint(info["key"]), border_color=urgency_tint(info["key"]))
        box.pack(fill="x")
        box.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(box, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=20, pady=18)
        ctk.CTkLabel(left, text="NEXT DEADLINE", font=F(11, "bold"), text_color=color).pack(anchor="w")
        ctk.CTkLabel(left, text=item.get("title", ""), font=F(20, "bold", display=True), text_color=C["ink"],
                     wraplength=640, justify="left").pack(anchor="w", pady=(2, 2))
        ctk.CTkLabel(left, text=f"{item.get('course', '')}   ·   {fmt_due(item)}", font=F(13), text_color=C["muted"]).pack(anchor="w")
        right = ctk.CTkFrame(box, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e", padx=20)
        days = info["days"]
        big = "Today" if days == 0 else "Tomorrow" if days == 1 else f"{days} days" if days is not None else "—"
        ctk.CTkLabel(right, text=big, font=F(30, "bold", display=True), text_color=color).pack(anchor="e")
        ctk.CTkLabel(right, text=info["label"], font=F(12), text_color=C["muted"]).pack(anchor="e")
        bind_click(box, lambda: self.app.navigate("assignments", filter_name="Pending"))

    def _stats(self, counts):
        strip = surface(self)
        strip.pack(fill="x", pady=(10, 0))
        for i, (label, value, flt) in enumerate(counts):
            strip.grid_columnconfigure(i, weight=1, uniform="stat")
            cell = ctk.CTkFrame(strip, fg_color="transparent")
            cell.grid(row=0, column=i, sticky="nsew")
            if i:
                ctk.CTkFrame(cell, fg_color=C["line"], width=1, height=2, corner_radius=0).pack(side="left", fill="y", pady=16)
            inner = ctk.CTkFrame(cell, fg_color="transparent")
            inner.pack(side="left", fill="x", expand=True, padx=18, pady=14)
            ctk.CTkLabel(inner, text=str(value), font=F(26, "bold", display=True),
                         text_color=C["ink"] if value else C["dim"]).pack(anchor="w")
            ctk.CTkLabel(inner, text=label, font=F(12), text_color=C["muted"]).pack(anchor="w")
            bind_click(cell, lambda f=flt: self.app.navigate("assignments", filter_name=f))

    def _attention_row(self, parent, a, info):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=10)
        ctk.CTkFrame(row, fg_color=urgency_color(info["key"]), width=8, height=8, corner_radius=4).pack(side="left", pady=6)
        txt = ctk.CTkFrame(row, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True, padx=(12, 0))
        ctk.CTkLabel(txt, text=a.get("title", ""), font=F(14, "bold"), text_color=C["ink"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(txt, text=f"{a.get('course', '')}   ·   {fmt_due(a)}", font=F(12), text_color=C["muted"], anchor="w").pack(anchor="w")
        pill(row, info["label"], info["key"]).pack(side="right")
        bind_click(row, lambda: self.app.navigate("assignments", filter_name="Pending"))


# ---------------------------------------------------------------------------- assignments
FILTERS = ["All", "Pending", "Due soon", "Extended", "Overdue", "Submitted"]


class AssignmentsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.filter_name = "All"
        self.course = "All courses"
        self.query = ""

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(2, 10))
        self.seg = ctk.CTkSegmentedButton(bar, values=FILTERS, font=F(12, "bold"), height=34, corner_radius=8,
                                          selected_color=C["accent"], selected_hover_color=C["accent_h"],
                                          unselected_color=C["surface"], unselected_hover_color=C["surface2"],
                                          text_color=C["ink"], fg_color=C["line"], command=self._set_filter)
        self.seg.set("All")
        self.seg.pack(side="left")
        self.search = ctk.CTkEntry(bar, placeholder_text="Search  (Ctrl+F)", height=34, width=220, font=F(12),
                                   fg_color=C["surface"], border_color=C["line2"], text_color=C["ink"])
        self.search.pack(side="right")
        self.search.bind("<KeyRelease>", lambda e: self._set_query(self.search.get()))
        self.search.bind("<Escape>", lambda e: (self.search.delete(0, "end"), self._set_query("")))
        self.course_menu = ctk.CTkOptionMenu(bar, values=["All courses"], height=34, width=250, font=F(12),
                                             fg_color=C["surface"], text_color=C["ink"], button_color=C["surface2"],
                                             button_hover_color=C["line2"], dropdown_font=F(12), command=self._set_course)
        self.course_menu.pack(side="right", padx=(0, 10))

        self.summary = ctk.CTkLabel(self, text="", font=F(12), text_color=C["muted"], anchor="w")
        self.summary.pack(fill="x", pady=(0, 6))
        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.pack(fill="both", expand=True)

    def focus_search(self):
        self.search.focus_set()

    def apply(self, filter_name=None, course=None):
        if filter_name:
            self.filter_name = filter_name
            self.seg.set(filter_name)
        if course:
            self.course = course
            self.course_menu.set(course)
        self.refresh()

    def _set_filter(self, v):
        self.filter_name = v
        self.refresh()

    def _set_course(self, v):
        self.course = v
        self.refresh()

    def _set_query(self, v):
        self.query = v.strip().lower()
        self.refresh()

    def refresh(self):
        data = list(self.app.data.values())
        courses = ["All courses"] + sorted({a.get("course", "") for a in data if a.get("course")})
        self.course_menu.configure(values=courses)
        if self.course not in courses:
            self.course = "All courses"
            self.course_menu.set(self.course)

        now = datetime.now()
        rows = []
        for a in data:
            info = classify(a, now)
            k, f = info["key"], self.filter_name
            if f == "Pending" and not is_open_pending(a):
                continue
            if f == "Due soon" and k not in ("today", "soon", "week"):
                continue
            if f == "Extended" and not (a.get("is_extended") or a.get("previous_due_date")):
                continue
            if f == "Overdue" and k != "missed":
                continue
            if f == "Submitted" and not a.get("is_submitted"):
                continue
            if self.course != "All courses" and a.get("course") != self.course:
                continue
            if self.query and self.query not in (a.get("title", "") + " " + a.get("course", "")).lower():
                continue
            rows.append((a, info))

        for w in self.list.winfo_children():
            w.destroy()
        self.summary.configure(text=f"{len(rows)} of {len(data)} assignments")
        if not rows:
            ctk.CTkLabel(self.list, text="Nothing matches this filter.", font=F(14), text_color=C["dim"]).pack(pady=50)
            return
        box = surface(self.list)
        box.pack(fill="x")
        for i, (a, info) in enumerate(sorted(rows, key=lambda r: sort_key(r[0]))):
            if i:
                hairline(box)
            self._row(box, a, info)

    def _row(self, parent, a, info):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=12)
        ctk.CTkFrame(row, fg_color=urgency_color(info["key"]), width=8, height=8, corner_radius=4).pack(side="left", pady=6)
        body = ctk.CTkFrame(row, fg_color="transparent")
        body.pack(side="left", fill="x", expand=True, padx=(12, 0))
        ctk.CTkLabel(body, text=a.get("title", ""), font=F(14, "bold"), text_color=C["ink"], anchor="w").pack(anchor="w")
        meta = f"{a.get('course', '')}   ·   #{a.get('assign_no', '')}   ·   Due {fmt_due(a)}"
        if a.get("is_extended") and a.get("original_due_date"):
            meta += f"   ·   extended from {a['original_due_date']}"
        elif a.get("previous_due_date"):
            meta += f"   ·   changed from {a['previous_due_date']}"
        marks = a.get("marks", "")
        if marks and marks.lower() != "not marked yet":
            meta += f"   ·   {marks}"
        ctk.CTkLabel(body, text=meta, font=F(12), text_color=C["muted"], anchor="w").pack(anchor="w", pady=(2, 0))
        pill(row, info["label"], info["key"]).pack(side="right")


# ---------------------------------------------------------------------------- settings
class SettingsView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        env = app.env

        acc = self._section("Portal account", "Changing these re-verifies the sign-in when you save.")
        self.enroll = self._entry(acc, "Enrollment number", env.get("ENROLLMENT", ""))
        self.password = self._entry(acc, "Portal password", env.get("PASSWORD", ""), show="•")
        ctk.CTkLabel(acc, text="Campus", font=F(12, "bold"), text_color=C["muted"]).pack(anchor="w", padx=20)
        self.campus = ctk.CTkOptionMenu(acc, values=CAMPUS_NAMES, height=38, font=F(13), fg_color=C["field"],
                                        text_color=C["ink"], button_color=C["accent"], button_hover_color=C["accent_h"],
                                        dropdown_font=F(12))
        self.campus.set(campus_name(env.get("INSTITUTE_ID", "1")))
        self.campus.pack(fill="x", padx=20, pady=(2, 12))
        row = ctk.CTkFrame(acc, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        primary_button(row, "Save and verify sign-in", self._save_account).pack(side="left")
        self.acc_msg = ctk.CTkLabel(row, text="", font=F(12), text_color=C["muted"])
        self.acc_msg.pack(side="left", padx=14)
        soft_button(row, "Switch account", lambda: self.app.show_setup()).pack(side="right")

        look = self._section("Appearance", "Remembered across restarts.")
        theme_switch(look, self.app).pack(anchor="w", padx=20, pady=(0, 18))

        bg = self._section("Running in the background",
                           "Closing the window keeps the app in the system tray; right-click the icon to open, sync or quit.")
        self.tray_sw = self._switch(bg, "Keep running in the tray when the window is closed", env.get("CLOSE_TO_TRAY", True))
        self.updates_sw = self._switch(bg, "Check for updates when the app starts (asks api.github.com)",
                                       env.get("CHECK_UPDATES", True))
        self.startup_sw = ctk.CTkSwitch(bg, text="Start with Windows, minimized to the tray", font=F(13),
                                        text_color=C["ink"], progress_color=C["accent"], command=self._toggle_startup)
        self.startup_sw.select() if automation.starts_with_windows() else self.startup_sw.deselect()
        self.startup_sw.pack(anchor="w", padx=20, pady=(4, 18))

        notif = self._section("Notifications", "How the app gets your attention after a sync or an hourly check.")
        self.voice = self._switch(notif, "Voice alerts through the speakers", env.get("ENABLE_VOICE", True))
        self.toast = self._switch(notif, "Windows desktop notifications", env.get("ENABLE_WINDOWS_TOAST", True))
        days_row = ctk.CTkFrame(notif, fg_color="transparent")
        days_row.pack(fill="x", padx=20, pady=(6, 4))
        ctk.CTkLabel(days_row, text="Mention assignments due within", font=F(13), text_color=C["ink"]).pack(side="left")
        self.days = ctk.CTkOptionMenu(days_row, values=["1", "2", "3", "5", "7", "14"], width=80, height=32, font=F(12),
                                      fg_color=C["field"], text_color=C["ink"], button_color=C["line2"],
                                      button_hover_color=C["dim"], command=lambda v: self._save_prefs())
        self.days.set(str(env.get("NOTIFY_DAYS_AHEAD", 3)))
        self.days.pack(side="left", padx=10)
        ctk.CTkLabel(days_row, text="days", font=F(13), text_color=C["ink"]).pack(side="left")
        voice_row = ctk.CTkFrame(notif, fg_color="transparent")
        voice_row.pack(fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(voice_row, text="Voice", font=F(13), text_color=C["ink"], width=60, anchor="w").pack(side="left")
        self.voice_menu = ctk.CTkOptionMenu(voice_row, values=["Default"], width=260, height=32, font=F(12),
                                            fg_color=C["field"], text_color=C["ink"], button_color=C["line2"],
                                            button_hover_color=C["dim"], dropdown_font=F(12), command=lambda v: self._save_prefs())
        self.voice_menu.set(env.get("VOICE_NAME") or "Default")
        self.voice_menu.pack(side="left", padx=(10, 0))
        self.after(400, lambda: threading.Thread(target=self._load_voices, daemon=True).start())

        vol_row = ctk.CTkFrame(notif, fg_color="transparent")
        vol_row.pack(fill="x", padx=20, pady=(6, 4))
        ctk.CTkLabel(vol_row, text="Volume", font=F(13), text_color=C["ink"], width=60, anchor="w").pack(side="left")
        self.volume = ctk.CTkSlider(vol_row, from_=0, to=100, number_of_steps=20, width=260, height=16,
                                    progress_color=C["accent"], button_color=C["accent"], button_hover_color=C["accent_h"],
                                    fg_color=C["surface2"], command=self._volume_changed)
        self.volume.set(int(env.get("VOICE_VOLUME", 100)))
        self.volume.pack(side="left", padx=(10, 10))
        self.volume_lbl = ctk.CTkLabel(vol_row, text=f"{int(env.get('VOICE_VOLUME', 100))}%", font=F(12),
                                       text_color=C["muted"], width=40, anchor="w")
        self.volume_lbl.pack(side="left")
        self.volume.bind("<ButtonRelease-1>", lambda e: self._save_prefs())

        rate_row = ctk.CTkFrame(notif, fg_color="transparent")
        rate_row.pack(fill="x", padx=20, pady=(6, 4))
        ctk.CTkLabel(rate_row, text="Speed", font=F(13), text_color=C["ink"], width=60, anchor="w").pack(side="left")
        self.rate = ctk.CTkSegmentedButton(rate_row, values=["Slow", "Normal", "Fast"], font=F(12, "bold"), height=30,
                                           selected_color=C["accent"], selected_hover_color=C["accent_h"],
                                           unselected_color=C["surface"], unselected_hover_color=C["surface2"],
                                           text_color=C["ink"], fg_color=C["line"], command=lambda v: self._save_prefs())
        self.rate.set({-2: "Slow", 0: "Normal", 2: "Fast"}.get(int(env.get("VOICE_RATE", 0)), "Normal"))
        self.rate.pack(side="left", padx=(10, 0))

        btns = ctk.CTkFrame(notif, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(10, 18))
        soft_button(btns, "Preview voice", self._preview_voice).pack(side="left", padx=(0, 8))
        soft_button(btns, "Send a test alert", self._test_alert).pack(side="left")

        auto = self._section("Automatic checks",
                             "Windows runs a check daily at 7:00 PM and two minutes after you sign in, plus an hourly "
                             "reminder while something is due today. These run even when the app is closed.")
        row = ctk.CTkFrame(auto, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        self.auto_status = ctk.CTkLabel(row, text="Checking…", font=F(13, "bold"), text_color=C["muted"])
        self.auto_status.pack(side="left")
        self.auto_btn = soft_button(row, "…", self._toggle_automation, width=140)
        self.auto_btn.configure(state="disabled")
        self.auto_btn.pack(side="right")
        self.after(300, lambda: threading.Thread(target=self._refresh_automation, daemon=True).start())

        data = self._section("Data", f"Stored only on this PC, in {BASE_DIR}")
        row = ctk.CTkFrame(data, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        soft_button(row, "Open data folder", lambda: os.startfile(DATA_DIR)).pack(side="left", padx=(0, 8))
        soft_button(row, "Open log file", lambda: os.startfile(LOG_PATH) if LOG_PATH.exists() else None).pack(side="left", padx=(0, 8))
        soft_button(row, "Clear local data", self._clear_data).pack(side="left")

        about = self._section("About", f"{APP_NAME} {APP_VERSION} {TAGLINE}  ·  "
                              f"{'installed build' if FROZEN else 'running from source'}  ·  made by Nobody243  ·  MIT license")
        ctk.CTkLabel(about, text="Unofficial app. Not affiliated with, endorsed by, or supported by Bahria University.",
                     font=F(12), text_color=C["dim"]).pack(anchor="w", padx=20, pady=(0, 10))
        row = ctk.CTkFrame(about, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        docs = [("Check for updates", lambda: self.app.check_for_updates(quiet=False)),
                ("Privacy & terms", lambda: open_doc("PRIVACY.md", f"{REPO_URL}/blob/main/PRIVACY.md")),
                ("Security", lambda: open_doc("SECURITY.md", f"{REPO_URL}/blob/main/SECURITY.md")),
                ("Licenses", lambda: open_doc("THIRD_PARTY_LICENSES.md", f"{REPO_URL}/blob/main/THIRD_PARTY_LICENSES.md")),
                ("Source on GitHub", lambda: webbrowser.open(REPO_URL))]
        for text, cmd in docs:
            soft_button(row, text, cmd).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(self, text="", height=6).pack()

    # -- builders
    def _section(self, title, sub):
        box = surface(self)
        box.pack(fill="x", pady=(2, 12))
        heading(box, title, sub).pack(anchor="w", padx=20, pady=(18, 12))
        return box

    def _entry(self, parent, label, value, show=None):
        ctk.CTkLabel(parent, text=label, font=F(12, "bold"), text_color=C["muted"]).pack(anchor="w", padx=20)
        e = ctk.CTkEntry(parent, height=38, font=F(13), fg_color=C["field"], border_color=C["line2"],
                         text_color=C["ink"], show=show or "")
        e.insert(0, value)
        e.pack(fill="x", padx=20, pady=(2, 12))
        return e

    def _switch(self, parent, text, value):
        sw = ctk.CTkSwitch(parent, text=text, font=F(13), text_color=C["ink"], progress_color=C["accent"],
                           command=self._save_prefs)
        sw.select() if value else sw.deselect()
        sw.pack(anchor="w", padx=20, pady=4)
        return sw

    # -- actions
    def _save_prefs(self):
        env = dict(self.app.env)
        env["ENABLE_VOICE"] = bool(self.voice.get())
        env["ENABLE_WINDOWS_TOAST"] = bool(self.toast.get())
        env["NOTIFY_DAYS_AHEAD"] = int(self.days.get())
        env["CLOSE_TO_TRAY"] = bool(self.tray_sw.get())
        env["CHECK_UPDATES"] = bool(self.updates_sw.get())
        if hasattr(self, "rate"):
            env["VOICE_NAME"], env["VOICE_VOLUME"], env["VOICE_RATE"] = self._voice_prefs()
        save_env(env)
        self.app.env = load_env()
        self.app.set_status("Preferences saved.")

    def _toggle_startup(self):
        want = bool(self.startup_sw.get())
        ok = automation.set_start_with_windows(want)
        if not ok:
            self.startup_sw.deselect()
        self.app.set_status("Start with Windows " + ("enabled." if want and ok else "disabled." if not want else "could not be enabled."))

    def _save_account(self):
        enroll = self.enroll.get().strip()
        pwd = self.password.get()
        if not enroll or not pwd:
            self.acc_msg.configure(text="Enrollment and password are required.", text_color=C["red"])
            return
        env = dict(self.app.env)
        env.update({"ENROLLMENT": enroll, "PASSWORD": pwd,
                    "INSTITUTE_ID": CAMPUS_ID_BY_NAME.get(self.campus.get(), "1")})
        save_env(env)
        self.app.env = load_env()
        self.acc_msg.configure(text="Saved. Verifying sign-in…", text_color=C["muted"])
        self.app.start_sync(on_done=lambda ok, msg: self.acc_msg.configure(
            text="Sign-in verified." if ok else msg, text_color=C["green"] if ok else C["red"]))

    def _load_voices(self):
        voices = list_voices()
        if not voices:
            return
        try:
            self.after(0, lambda: self._show_voices(voices))
        except RuntimeError:
            pass

    def _show_voices(self, voices):
        current = self.voice_menu.get()
        self.voice_menu.configure(values=["Default"] + voices)
        if current not in voices:
            self.voice_menu.set("Default" if not self.app.env.get("VOICE_NAME") else self.app.env["VOICE_NAME"])

    def _volume_changed(self, value):
        self.volume_lbl.configure(text=f"{int(value)}%")

    def _voice_prefs(self):
        name = self.voice_menu.get()
        return ("" if name == "Default" else name, int(self.volume.get()), {"Slow": -2, "Normal": 0, "Fast": 2}[self.rate.get()])

    def _preview_voice(self):
        voice, volume, rate = self._voice_prefs()
        self.app.set_status("Playing voice preview…")
        threading.Thread(target=lambda: speak_voice("This is how your assignment reminders will sound.",
                                                    force=True, voice=voice, volume=volume, rate=rate), daemon=True).start()

    def _test_alert(self):
        self.app.set_status("Sending test alert…")
        threading.Thread(target=lambda: (send_toast(APP_NAME, "Test alert: notifications are working."),
                                         speak_voice("Assignment Monitor alerts are working.", force=True)),
                         daemon=True).start()

    def _refresh_automation(self):
        enabled = automation.is_enabled()
        try:
            self.after(0, self._show_automation, enabled)
        except RuntimeError:
            pass

    def _show_automation(self, enabled):
        self.auto_status.configure(text="Enabled" if enabled else "Not enabled",
                                   text_color=C["green"] if enabled else C["amber"])
        self.auto_btn.configure(text="Turn off" if enabled else "Turn on", state="normal",
                                fg_color=C["surface2"] if enabled else C["accent"],
                                text_color=C["ink"] if enabled else C["on_accent"],
                                hover_color=C["line2"] if enabled else C["accent_h"])
        self._auto_enabled = enabled

    def _toggle_automation(self):
        self.auto_btn.configure(state="disabled", text="Working…")
        target = not getattr(self, "_auto_enabled", False)

        def work():
            ok, msg = automation.enable() if target else automation.disable()
            self.after(0, self._show_automation, automation.is_enabled())
            self.after(0, lambda: self.app.set_status(msg))
            if not ok:
                self.after(0, lambda: messagebox.showerror(APP_NAME, f"Could not change automatic checks.\n\n{msg[-600:]}"))
        threading.Thread(target=work, daemon=True).start()

    def _clear_data(self):
        if messagebox.askyesno(APP_NAME, "Delete the locally saved assignments? The next sync will rebuild them."):
            clear_stored_assignments()
            self.app.reload_data()
            self.app.set_status("Local data cleared.")


# ---------------------------------------------------------------------------- activity
class ActivityView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(2, 10))
        ctk.CTkLabel(bar, text="Everything the app did, newest at the bottom, including the scheduled background runs.",
                     font=F(12), text_color=C["muted"]).pack(side="left")
        soft_button(bar, "Open log file", lambda: os.startfile(LOG_PATH) if LOG_PATH.exists() else None, width=110).pack(side="right")
        soft_button(bar, "Reload", self.refresh, width=80).pack(side="right", padx=(0, 8))
        self.box = ctk.CTkTextbox(self, font=ctk.CTkFont(family=FONTS["mono"], size=12), fg_color=C["surface"],
                                  text_color=C["muted"], corner_radius=12, border_width=1, border_color=C["line"],
                                  state="disabled", wrap="none")
        self.box.pack(fill="both", expand=True)

    def refresh(self):
        text = ""
        if LOG_PATH.exists():
            try:
                with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                    text = "".join(f.readlines()[-400:])
            except Exception as e:
                text = f"Could not read the log file: {e}"
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        self.box.insert("end", text or "No activity recorded yet.\n")
        self.box.see("end")
        self.box.configure(state="disabled")

    def append(self, line):
        self.box.configure(state="normal")
        self.box.insert("end", line + "\n")
        self.box.see("end")
        self.box.configure(state="disabled")


# ---------------------------------------------------------------------------- main window
class App(ctk.CTk):
    NAV = [("dashboard", "Dashboard"), ("assignments", "Assignments"), ("settings", "Settings"), ("activity", "Activity")]
    CONTENT_MAX = 1120

    def __init__(self, start_view="dashboard", force_setup=False, start_hidden=False):
        self.env = load_env()
        self.theme = self.env.get("THEME", "dark")
        ctk.set_appearance_mode(self.theme)
        super().__init__(fg_color=C["bg"])
        pick_fonts()
        self.title(APP_NAME)
        self._place_window()
        self.logo = self._load_logo()
        icon = ASSETS_DIR / "icon.ico"
        if icon.exists():
            try:
                self.iconbitmap(str(icon))
            except Exception:
                pass

        self.meta = load_meta()
        self.data = {}
        self.syncing = False
        self.views = {}
        self.current = None
        self.setup_console = None
        self.tray = None
        self._tray_hint_shown = False
        self.update_info = None
        self.log_queue = queue.Queue()
        logging.getLogger("bahria").addHandler(QueueHandler(self.log_queue))

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        signed_in = has_credentials(self.env) and not force_setup
        if signed_in:
            self.show_main()
            if start_view in self.views:
                self.navigate(start_view)
        else:
            self.show_setup()
        self.after(250, self._drain_logs)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._bind_shortcuts()
        self._start_tray()
        self.update_tray_tooltip()
        self._listen_for_events()
        if start_hidden and signed_in and self.tray:
            self.after(50, self.hide_to_tray)
        if self.env.get("CHECK_UPDATES", True):
            self.after(4000, lambda: self.check_for_updates(quiet=True))

    # ---- updates
    def check_for_updates(self, quiet=False):
        def work():
            info = updater.check_latest()
            try:
                self.after(0, self._update_checked, info, quiet)
            except RuntimeError:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _update_checked(self, info, quiet):
        self.update_info = info
        if info and info.get("newer"):
            text = f"Update {info['version']} available  ·  Install"
            if "update_lbl" in self.__dict__:
                self.update_lbl.configure(text=text)
            self.set_status(f"Version {info['version']} is available. Click Install at the top to update.")
            if self.tray:
                self.tray.set_tooltip(f"{APP_NAME} · update {info['version']} available")
        elif not quiet:
            if info is None:
                self.set_status("Could not reach GitHub to check for updates.")
                webbrowser.open(RELEASES_URL)
            else:
                self.set_status(f"You have the latest version ({APP_VERSION}).")

    def install_update(self):
        info = self.update_info
        if not info or not info.get("newer"):
            return
        if not info.get("setup_url"):
            webbrowser.open(info.get("page") or RELEASES_URL)
            return
        if not messagebox.askyesno(APP_NAME, f"Download and install version {info['version']} now?\n\n"
                                   "The app will close, update itself and reopen."):
            return
        self.set_status("Downloading update…")

        def work():
            try:
                def progress(done, total):
                    pct = f" {done * 100 // total}%" if total else ""
                    try:
                        self.after(0, self.set_status, f"Downloading update…{pct}")
                    except RuntimeError:
                        pass
                path = updater.download_installer(info["setup_url"], progress)
                log.info("Installing update %s", info["version"])
                updater.run_installer(path)
                self.after(0, self.quit_app)
            except Exception as e:
                err = str(e)
                log.error("Update failed: %s", err)
                self.after(0, lambda: messagebox.showerror(APP_NAME, f"The update could not be installed.\n\n{err}"))
                self.after(0, self.set_status, "Update failed.")
        threading.Thread(target=work, daemon=True).start()

    # ---- window
    def _place_window(self):
        try:
            scale = ctk.ScalingTracker.get_window_scaling(self)
        except Exception:
            scale = 1.0
        sw, sh = int(self.winfo_screenwidth() / scale), int(self.winfo_screenheight() / scale)
        saved = self.env.get("WINDOW_GEOMETRY", "")
        if saved and GEOMETRY_RE.match(saved):
            w, h, x, y = (int(v) for v in re.split(r"[x+]", saved))
            if 900 <= w <= sw and 560 <= h <= sh and 0 <= x < sw - 200 and 0 <= y < sh - 200:
                self.geometry(saved)
                self.minsize(900, 560)
                return
        w, h = min(1280, sw - 60), min(840, sh - 120)
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 30)}")
        self.minsize(min(900, w), min(560, h))

    def _remember_geometry(self):
        try:
            geo = self.geometry()
            if GEOMETRY_RE.match(geo) and self.state() == "normal":
                env = dict(self.env)
                env["WINDOW_GEOMETRY"] = geo
                save_env(env)
                self.env = load_env()
        except Exception:
            pass

    def _load_logo(self):
        try:
            from PIL import Image
            img = Image.open(ASSETS_DIR / "icon.ico").convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(44, 44))
        except Exception:
            return None

    def _bind_shortcuts(self):
        self.bind("<F5>", lambda e: self.start_sync())
        for i, (key, _) in enumerate(self.NAV, start=1):
            self.bind(f"<Control-Key-{i}>", lambda e, k=key: self.navigate(k))
        self.bind("<Control-f>", lambda e: (self.navigate("assignments"), self.views["assignments"].focus_search()))

    # ---- theme
    def set_theme(self, theme):
        self.theme = theme
        ctk.set_appearance_mode(theme)
        env = dict(self.env)
        env["THEME"] = theme
        save_env(env)
        self.env = load_env()

    # ---- screens
    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()
        self.views = {}
        self.current = None

    def show_setup(self):
        self._clear()
        SetupView(self.container, self).pack(fill="both", expand=True)

    def show_main(self):
        self._clear()
        self.env = load_env()
        self.meta = load_meta()
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(self.container, fg_color=C["surface"], corner_radius=0, width=224)
        side.grid(row=0, column=0, sticky="nsw")
        side.grid_propagate(False)
        ctk.CTkFrame(self.container, fg_color=C["line"], width=1, corner_radius=0).grid(row=0, column=0, sticky="nse")
        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(22, 22))
        if self.logo:
            small = ctk.CTkImage(light_image=self.logo._light_image, dark_image=self.logo._dark_image, size=(30, 30))
            ctk.CTkLabel(brand, text="", image=small).pack(side="left", padx=(0, 10))
        bt = ctk.CTkFrame(brand, fg_color="transparent")
        bt.pack(side="left")
        ctk.CTkLabel(bt, text=APP_NAME, font=F(15, "bold", display=True), text_color=C["ink"]).pack(anchor="w")
        ctk.CTkLabel(bt, text="Bahria University LMS", font=F(11), text_color=C["muted"]).pack(anchor="w")

        self.nav_buttons = {}
        for key, label in self.NAV:
            item = ctk.CTkFrame(side, fg_color="transparent")
            item.pack(fill="x", padx=(0, 12), pady=1)
            bar = ctk.CTkFrame(item, fg_color="transparent", width=3, height=2, corner_radius=2)
            bar.pack(side="left", fill="y", pady=8)
            b = ctk.CTkButton(item, text=label, font=F(14), height=40, anchor="w", corner_radius=8,
                              fg_color="transparent", hover_color=C["surface2"], text_color=C["muted"],
                              command=lambda k=key: self.navigate(k))
            b.pack(side="left", fill="x", expand=True, padx=(9, 0))
            self.nav_buttons[key] = (b, bar)

        foot = ctk.CTkFrame(side, fg_color="transparent")
        foot.pack(side="bottom", fill="x", padx=16, pady=16)
        theme_switch(foot, self).pack(anchor="w", padx=4, pady=(0, 12))
        user = ctk.CTkFrame(foot, fg_color=C["surface2"], corner_radius=10)
        user.pack(fill="x")
        name = self.meta.get("student_name") or "Student"
        initials = "".join(p[0] for p in name.split()[:2]).upper() or "S"
        ctk.CTkLabel(user, text=initials, font=F(12, "bold"), width=34, height=34, fg_color=C["accent"],
                     text_color=C["on_accent"], corner_radius=17).pack(side="left", padx=10, pady=10)
        ut = ctk.CTkFrame(user, fg_color="transparent")
        ut.pack(side="left", pady=10)
        ctk.CTkLabel(ut, text=name, font=F(12, "bold"), text_color=C["ink"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(ut, text=self.env.get("ENROLLMENT", ""), font=F(11), text_color=C["muted"]).pack(anchor="w")

        content = ctk.CTkFrame(self.container, fg_color="transparent")
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(2, weight=1)
        content.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(content, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=32, pady=(20, 6))
        tt = ctk.CTkFrame(top, fg_color="transparent")
        tt.pack(side="left")
        self.page_title = ctk.CTkLabel(tt, text="", font=F(22, "bold", display=True), text_color=C["ink"])
        self.page_title.pack(anchor="w")
        self.last_sync_lbl = ctk.CTkLabel(tt, text="", font=F(12), text_color=C["muted"])
        self.last_sync_lbl.pack(anchor="w")
        self.sync_btn = primary_button(top, "Sync now", self.start_sync, width=120)
        self.sync_btn.pack(side="right")
        self.update_lbl = ctk.CTkLabel(top, text="", font=F(12, "bold"), text_color=C["accent"], cursor="hand2")
        self.update_lbl.pack(side="right", padx=14)
        self.update_lbl.bind("<Button-1>", lambda e: self.install_update())
        if self.update_info and self.update_info.get("newer"):
            self.update_lbl.configure(text=f"Update {self.update_info['version']} available  ·  Install")

        self.sync_bar = ctk.CTkProgressBar(content, mode="indeterminate", height=3, corner_radius=0,
                                           progress_color=C["accent"], fg_color=C["bg"])
        self.sync_bar.grid(row=1, column=0, sticky="ew", padx=32)
        self.sync_bar.grid_remove()

        self.body = ctk.CTkFrame(content, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", padx=32, pady=(6, 0))

        status = ctk.CTkFrame(content, fg_color=C["surface"], corner_radius=0, height=28)
        status.grid(row=3, column=0, sticky="ew")
        ctk.CTkFrame(status, fg_color=C["line"], height=1, corner_radius=0).pack(fill="x", side="top")
        self.status_lbl = ctk.CTkLabel(status, text="Ready.", font=F(11), text_color=C["muted"], anchor="w")
        self.status_lbl.pack(side="left", padx=32, pady=4)
        ctk.CTkLabel(status, text=f"F5 sync  ·  Ctrl+1–4 pages  ·  v{APP_VERSION}", font=F(11),
                     text_color=C["dim"]).pack(side="right", padx=32)

        self.views = {
            "dashboard": DashboardView(self.body, self),
            "assignments": AssignmentsView(self.body, self),
            "settings": SettingsView(self.body, self),
            "activity": ActivityView(self.body, self),
        }
        self.reload_data()
        self.navigate("dashboard")
        if self.syncing:
            self._show_syncing(True)

    def navigate(self, key, **kwargs):
        if not self.views:
            return
        for k, (b, bar) in self.nav_buttons.items():
            active = k == key
            b.configure(fg_color=C["surface2"] if active else "transparent",
                        text_color=C["ink"] if active else C["muted"],
                        font=F(14, "bold" if active else "normal"))
            bar.configure(fg_color=C["accent"] if active else "transparent")
        if self.current:
            self.views[self.current].pack_forget()
        self.current = key
        view = self.views[key]
        view.pack(fill="both", expand=True)
        self.page_title.configure(text=dict(self.NAV)[key])
        if key == "assignments" and kwargs:
            view.apply(kwargs.get("filter_name"), kwargs.get("course"))
        elif hasattr(view, "refresh"):
            view.refresh()

    # ---- data
    def reload_data(self):
        self.data = load_stored_assignments()
        self.meta = load_meta()
        if "last_sync_lbl" in self.__dict__:
            ls = self.meta.get("last_sync")
            if ls:
                try:
                    ls = datetime.fromisoformat(ls).strftime("%d %b, %I:%M %p").replace(" 0", " ")
                except ValueError:
                    pass
            self.last_sync_lbl.configure(text=f"Last sync {ls}" if ls else "Not synced yet")
        self.update_tray_tooltip()
        if self.current and self.current in self.views and hasattr(self.views[self.current], "refresh"):
            self.views[self.current].refresh()

    def set_status(self, text):
        if "status_lbl" in self.__dict__:
            self.status_lbl.configure(text=text)

    # ---- sync
    def _show_syncing(self, on):
        if "sync_btn" not in self.__dict__:
            return
        self.sync_btn.configure(state="disabled" if on else "normal", text="Syncing…" if on else "Sync now")
        if on:
            self.sync_bar.grid()
            self.sync_bar.start()
        else:
            self.sync_bar.stop()
            self.sync_bar.grid_remove()

    def start_sync(self, on_done=None):
        if self.syncing:
            return
        self.syncing = True
        self._show_syncing(True)
        threading.Thread(target=self._sync_worker, args=(on_done,), daemon=True).start()

    def _sync_worker(self, on_done):
        try:
            items = run_lms_check(headless=True)
            pending, extended, new_items = compare_assignments(items)
            alert_assignments(pending, extended)
            result = (True, f"Synced {len(items)} assignments · {len(pending)} pending · {len(new_items)} new")
        except LoginError as e:
            result = (False, str(e))
        except Exception as e:
            log.error("Sync failed: %s", e)
            result = (False, f"Sync failed: {e}")
        try:
            self.after(0, self._sync_done, result, on_done)
        except RuntimeError:
            pass

    def _sync_done(self, result, on_done):
        ok, msg = result
        self.syncing = False
        self._show_syncing(False)
        self.set_status(msg)
        self.reload_data()
        if not ok and on_done is None and "status_lbl" in self.__dict__:
            messagebox.showwarning(APP_NAME, msg)
        if on_done:
            on_done(ok, msg)

    # ---- tray / background
    def _start_tray(self):
        try:
            self.tray = TrayIcon(APP_NAME, ASSETS_DIR / "icon.ico",
                                 on_open=lambda: self.after(0, self.show_window),
                                 on_sync=lambda: self.after(0, self.start_sync),
                                 on_quit=lambda: self.after(0, self.quit_app))
            self.tray.start()
        except Exception as e:
            log.warning("Tray icon unavailable: %s", e)
            self.tray = None

    def _listen_for_events(self):
        """Other launches talk to us through named events: show the window, or quit (used by the installer)."""
        try:
            k32 = ctypes.windll.kernel32
            events = [(k32.CreateEventW(None, False, False, SHOW_EVENT_NAME), self.show_window),
                      (k32.CreateEventW(None, False, False, QUIT_EVENT_NAME), self.quit_app)]
        except Exception:
            return

        def wait(handle, action):
            while True:
                if k32.WaitForSingleObject(handle, 0xFFFFFFFF) != 0:
                    break
                try:
                    self.after(0, action)
                except RuntimeError:
                    break
        self._event_handles = events
        for handle, action in events:
            threading.Thread(target=wait, args=(handle, action), daemon=True).start()

    def show_window(self):
        self.deiconify()
        self.lift()
        try:
            self.attributes("-topmost", True)
            self.after(200, lambda: self.attributes("-topmost", False))
            self.focus_force()
        except Exception:
            pass

    def hide_to_tray(self):
        self._remember_geometry()
        self.withdraw()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            if self.tray:
                self.tray.notify("Still running in the tray. Right-click the icon to open or quit.", APP_NAME)

    def quit_app(self):
        self._remember_geometry()
        if self.syncing:
            _release_lock()
        if self.tray:
            self.tray.stop()
            self.tray = None
        try:
            self.destroy()
        except Exception:
            pass

    def update_tray_tooltip(self):
        if not self.tray:
            return
        pending = sum(1 for a in self.data.values() if is_open_pending(a))
        self.tray.set_tooltip(f"{APP_NAME} · {pending} pending" if self.data else APP_NAME)

    # ---- log plumbing
    def _drain_logs(self):
        try:
            while True:
                line = self.log_queue.get_nowait()
                if self.setup_console is not None:
                    self.setup_console.console_write(line)
                if "activity" in self.views:
                    self.views["activity"].append(line)
                self.set_status(line.split("  ", 1)[-1])
        except queue.Empty:
            pass
        self.after(250, self._drain_logs)

    def _on_close(self):
        if self.tray and self.env.get("CLOSE_TO_TRAY", True) and self.views:
            self.hide_to_tray()
            return
        if self.syncing:
            if not messagebox.askyesno(APP_NAME, "A sync is still running. Close anyway?"):
                return
        self.quit_app()


if __name__ == "__main__":
    main()
