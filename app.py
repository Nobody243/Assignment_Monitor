"""
Bahria LMS Monitor - desktop application and command-line entry point.

    app.py                 open the window (sign-in screen on first run)
    app.py --check         background sync + notifications (daily / sign-in task)
    app.py --remind        hourly same-day reminder task
    app.py --status        print the saved assignments
    app.py --test-alert    test desktop notification and voice
    app.py --tray          start minimized to the system tray
"""
import ctypes
import logging
import os
import queue
import re
import sys
import threading
from datetime import datetime

if sys.stdout is None or sys.stderr is None:          # windowed exe: no console attached
    sys.stdout = sys.stdout or open(os.devnull, "w")
    sys.stderr = sys.stderr or open(os.devnull, "w")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from config import (APP_ID, APP_NAME, APP_VERSION, TAGLINE, ASSETS_DIR, BASE_DIR, DATA_DIR, LOG_PATH, FROZEN,
                    RELEASES_URL, REPO_URL, CAMPUS_NAMES, CAMPUS_ID_BY_NAME, campus_name,
                    load_env, save_env, has_credentials, load_meta, setup_logging)

log = logging.getLogger("bahria.app")
ENROLLMENT_RE = re.compile(r"^\d{2}-\d{6}-\d{3}$")


# ============================================================================ command line
def main():
    import argparse
    parser = argparse.ArgumentParser(prog="BahriaLMSMonitor", description=APP_NAME)
    parser.add_argument("--check", action="store_true", help="sync assignments and notify, then exit")
    parser.add_argument("--remind", action="store_true", help="hourly same-day reminder, then exit")
    parser.add_argument("--status", action="store_true", help="print saved assignments, then exit")
    parser.add_argument("--test-alert", action="store_true", help="test notification and voice, then exit")
    parser.add_argument("--test", action="store_true", help="with --remind: simulate an assignment due today")
    parser.add_argument("--quiet", "-q", action="store_true", help="with --check: no notifications")
    parser.add_argument("--visible", action="store_true", help="with --check: show the browser window")
    parser.add_argument("--setup", action="store_true", help="open the sign-in screen (switch account)")
    parser.add_argument("--tray", action="store_true", help="start minimized to the system tray")
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
    if args.enable_automation or args.disable_automation:
        import automation
        ok, msg = automation.enable() if args.enable_automation else automation.disable()
        if args.disable_automation:
            automation.set_start_with_windows(False)
        print(msg)
        sys.exit(0 if ok else 1)

    run_gui(start_view=args.view, force_setup=args.setup, start_hidden=args.tray)


SHOW_EVENT_NAME = "Local\\AssignmentMonitor.ShowWindow"


def run_gui(start_view="dashboard", force_setup=False, start_hidden=False):
    if _another_instance_running():
        log.info("Already running; bringing the existing window to the front.")
        _signal_existing_window()
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


_MUTEX = None


def _another_instance_running() -> bool:
    global _MUTEX
    try:
        _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\BahriaLMSMonitor.MainWindow")
        return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return False


def _signal_existing_window():
    """Asks the running instance (possibly hidden in the tray) to show its window."""
    try:
        k32 = ctypes.windll.kernel32
        h = k32.OpenEventW(0x0002, False, SHOW_EVENT_NAME)  # EVENT_MODIFY_STATE
        if h:
            k32.SetEvent(h)
            k32.CloseHandle(h)
    except Exception:
        pass


# ============================================================================ GUI
import customtkinter as ctk                      # noqa: E402  (imported after the CLI fast path)
from tkinter import messagebox                   # noqa: E402

import automation                                 # noqa: E402
from tray import TrayIcon                                                                   # noqa: E402
from tracker import load_stored_assignments, compare_assignments, clear_stored_assignments  # noqa: E402
from lms_scraper import run_lms_check, LoginError, _release_lock                            # noqa: E402
from notifier import alert_assignments, send_toast, speak_voice                            # noqa: E402
from deadlines import classify, is_open_pending, sort_key, deadline_of                     # noqa: E402

# Every colour is a (light, dark) pair, so switching the appearance mode restyles the
# whole window instantly without rebuilding it.
C = {
    "bg": ("#f3f5fa", "#0b1220"), "side": ("#ffffff", "#0e172a"),
    "card": ("#ffffff", "#121c31"), "card2": ("#eef2f8", "#1a2740"), "field": ("#f8fafc", "#1a2740"),
    "line": ("#e3e8f0", "#233250"), "text": ("#0f172a", "#eef2ff"),
    "muted": ("#64748b", "#93a3bd"), "dim": ("#94a3b8", "#5b6b86"),
    "accent": ("#2563eb", "#3b82f6"), "accent_h": ("#1d4ed8", "#2563eb"),
    "green": ("#16a34a", "#22c55e"), "amber": ("#d97706", "#f59e0b"), "red": ("#dc2626", "#ef4444"),
    "sky": ("#0284c7", "#38bdf8"), "violet": ("#7c3aed", "#a78bfa"),
    "green_t": ("#dcfce7", "#0f2a1b"), "amber_t": ("#fff1cf", "#2b2414"), "red_t": ("#fee2e2", "#2d1518"),
    "sky_t": ("#e0f2fe", "#0f2436"), "violet_t": ("#ede9fe", "#221a3a"), "grey_t": ("#eef2f8", "#1a2740"),
}
URGENCY = {"today": C["red"], "missed": ("#b91c1c", "#b91c1c"), "soon": C["amber"], "week": C["sky"],
           "later": ("#94a3b8", "#475569"), "submitted": ("#16a34a", "#15803d"), "unknown": ("#94a3b8", "#475569")}
TINT = {"today": C["red_t"], "missed": C["red_t"], "soon": C["amber_t"], "week": C["sky_t"],
        "later": C["grey_t"], "submitted": C["green_t"], "unknown": C["grey_t"]}
FONT_FAMILY = "Segoe UI"


def F(size=13, weight="normal"):
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def pill(parent, text, color, fg="#ffffff", size=11):
    return ctk.CTkLabel(parent, text=f"  {text}  ", font=F(size, "bold"), fg_color=color,
                        text_color=fg, corner_radius=7, height=24)


def card(parent, **kw):
    opts = dict(fg_color=C["card"], corner_radius=16, border_width=1, border_color=C["line"])
    opts.update(kw)
    return ctk.CTkFrame(parent, **opts)


def section_title(parent, text, sub=None):
    box = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(box, text=text, font=F(17, "bold"), text_color=C["text"]).pack(anchor="w")
    if sub:
        ctk.CTkLabel(box, text=sub, font=F(12), text_color=C["muted"]).pack(anchor="w")
    return box


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
        return item.get("due_date", "N/A")
    return dt.strftime("%a, %d %b %Y · %I:%M %p").replace(" 0", " ").replace("AM", "am").replace("PM", "pm")


def theme_switch(parent, app):
    sw = ctk.CTkSwitch(parent, text="Dark mode", font=F(12), text_color=C["muted"], progress_color=C["accent"],
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
        left = ctk.CTkFrame(self, fg_color=C["side"], corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        inner = ctk.CTkFrame(left, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.78)

        logo = ctk.CTkLabel(inner, text="🎓", font=ctk.CTkFont(size=30), width=64, height=64,
                            fg_color=C["sky_t"], corner_radius=18)
        logo.pack(anchor="w")
        ctk.CTkLabel(inner, text=APP_NAME, font=F(30, "bold"), text_color=C["text"]).pack(anchor="w", pady=(14, 0))
        ctk.CTkLabel(inner, text=TAGLINE, font=F(14, "bold"), text_color=C["accent"]).pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(inner, text="Your assignments, deadlines and reminders\nin one place. Set it up once, it runs on its own.",
                     font=F(14), text_color=C["muted"], justify="left").pack(anchor="w", pady=(0, 26))

        features = [
            ("🔄", C["sky_t"], "Automatic daily sync", "Signs in to CMS and LMS every evening at 7 PM and whenever your PC starts."),
            ("⏰", C["amber_t"], "Same-day voice reminders", "Speaks up every hour while an unsubmitted assignment is due today."),
            ("⚡", C["violet_t"], "Deadline extension alerts", "Spots when a teacher moves a deadline, even when the portal hides it."),
            ("🔒", C["green_t"], "Private by design", "Your password is encrypted with Windows and only ever sent to cms.bahria.edu.pk."),
        ]
        for icon, tint, title, desc in features:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=7)
            ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=16), width=38, height=38, fg_color=tint,
                         corner_radius=11).pack(side="left", anchor="n", padx=(0, 12))
            txt = ctk.CTkFrame(row, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(txt, text=title, font=F(14, "bold"), text_color=C["text"]).pack(anchor="w")
            ctk.CTkLabel(txt, text=desc, font=F(12), text_color=C["muted"], justify="left",
                         wraplength=340).pack(anchor="w")

    def _build_right(self):
        right = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        theme_switch(right, self.app).place(relx=1.0, rely=0.0, anchor="ne", x=-24, y=18)
        box = card(right)
        box.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.74)
        pad = {"padx": 32}

        ctk.CTkLabel(box, text="Sign in to your student portal", font=F(21, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(28, 2), **pad)
        ctk.CTkLabel(box, text="Use the same enrollment number and password as cms.bahria.edu.pk.",
                     font=F(12), text_color=C["muted"]).pack(anchor="w", pady=(0, 18), **pad)

        env = self.app.env
        self.enroll = self._field(box, "Enrollment number", "01-135232-000", pad)
        if env.get("ENROLLMENT"):
            self.enroll.insert(0, env["ENROLLMENT"])

        ctk.CTkLabel(box, text="Portal password", font=F(12, "bold"), text_color=C["muted"]).pack(anchor="w", **pad)
        pw_row = ctk.CTkFrame(box, fg_color="transparent")
        pw_row.pack(fill="x", pady=(2, 12), **pad)
        self.password = ctk.CTkEntry(pw_row, placeholder_text="Your CMS password", show="•", height=40,
                                     font=F(13), fg_color=C["field"], border_color=C["line"], text_color=C["text"])
        self.password.pack(side="left", fill="x", expand=True)
        self.show_pw = ctk.CTkCheckBox(pw_row, text="Show", font=F(12), width=70, text_color=C["muted"],
                                       command=self._toggle_pw)
        self.show_pw.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(box, text="Campus", font=F(12, "bold"), text_color=C["muted"]).pack(anchor="w", **pad)
        self.campus = ctk.CTkOptionMenu(box, values=CAMPUS_NAMES, height=40, font=F(13), fg_color=C["field"],
                                        text_color=C["text"], button_color=C["accent"],
                                        button_hover_color=C["accent_h"], dropdown_font=F(12))
        self.campus.set(campus_name(env.get("INSTITUTE_ID", "1")))
        self.campus.pack(fill="x", pady=(2, 14), **pad)

        self.automation = ctk.CTkCheckBox(box, text="Run automatically (daily 7 PM check, hourly reminders, startup check)",
                                          font=F(12), text_color=C["text"])
        self.automation.select()
        self.automation.pack(anchor="w", pady=(0, 18), **pad)

        self.button = ctk.CTkButton(box, text="Connect & start monitoring", font=F(15, "bold"), height=46,
                                    fg_color=C["accent"], hover_color=C["accent_h"], command=self.connect)
        self.button.pack(fill="x", **pad)
        self.enroll.bind("<Return>", lambda e: self.connect())
        self.password.bind("<Return>", lambda e: self.connect())

        self.progress = ctk.CTkProgressBar(box, mode="indeterminate", height=6, progress_color=C["accent"],
                                           fg_color=C["card2"])
        self.status = ctk.CTkLabel(box, text="", font=F(12), text_color=C["muted"], wraplength=440, justify="left")
        self.status.pack(anchor="w", pady=(12, 0), **pad)
        self.console = ctk.CTkTextbox(box, height=96, font=ctk.CTkFont(family="Consolas", size=11),
                                      fg_color=C["bg"], text_color=C["muted"], state="disabled")
        ctk.CTkLabel(box, text="", height=14).pack()

    def _field(self, parent, label, placeholder, pad):
        ctk.CTkLabel(parent, text=label, font=F(12, "bold"), text_color=C["muted"]).pack(anchor="w", **pad)
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder, height=40, font=F(13), fg_color=C["field"],
                             border_color=C["line"], text_color=C["text"])
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
            self.status.configure(text="Please enter both your enrollment number and password.", text_color=C["red"])
            return
        if not ENROLLMENT_RE.match(enroll):
            self.status.configure(text="Enrollment numbers look like 01-135232-000. Please check it.", text_color=C["amber"])
            return
        env = dict(self.app.env)
        env.update({"ENROLLMENT": enroll, "PASSWORD": pwd,
                    "INSTITUTE_ID": CAMPUS_ID_BY_NAME.get(self.campus.get(), "1")})
        save_env(env)
        self.app.env = load_env()

        self.button.configure(state="disabled", text="Connecting to the portal…")
        self.status.configure(text="Signing in and reading your assignments. This takes about a minute.",
                              text_color=C["sky"])
        self.progress.pack(fill="x", padx=32, pady=(12, 0), before=self.status)
        self.progress.start()
        self.console.pack(fill="x", padx=32, pady=(10, 0))
        self.app.setup_console = self
        threading.Thread(target=self._worker, args=(self.automation.get() == 1,), daemon=True).start()

    def _worker(self, enable_automation):
        try:
            items = run_lms_check(headless=True)
            pending, extended, _ = compare_assignments(items)
            note = ""
            if enable_automation:
                ok, msg = automation.enable()
                note = "" if ok else " Background automation could not be registered; you can retry from Settings."
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
        env = self.app.env
        now = datetime.now()

        hour = now.hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        first_name = (meta.get("student_name") or "").split(" ")[0].title() or "there"
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", pady=(2, 16))
        ctk.CTkLabel(head, text=f"{greeting}, {first_name}", font=F(26, "bold"), text_color=C["text"]).pack(anchor="w")
        bits = [env.get("ENROLLMENT", ""), campus_name(env.get("INSTITUTE_ID", "1"))]
        if meta.get("semester"):
            bits.append(meta["semester"])
        if meta.get("courses"):
            bits.append(f"{len(meta['courses'])} courses")
        ctk.CTkLabel(head, text="  ·  ".join(b for b in bits if b), font=F(13), text_color=C["muted"]).pack(anchor="w")

        if not data:
            empty = card(self)
            empty.pack(fill="x", pady=10)
            ctk.CTkLabel(empty, text="No assignments yet", font=F(18, "bold"), text_color=C["text"]).pack(pady=(30, 4))
            ctk.CTkLabel(empty, text="Press “Sync now” to read your assignments from the LMS.",
                         font=F(13), text_color=C["muted"]).pack(pady=(0, 30))
            return

        infos = {id(a): classify(a, now) for a in data}
        open_items = sorted([a for a in data if is_open_pending(a)], key=sort_key)
        counts = {
            "pending": len(open_items),
            "today": sum(1 for a in open_items if infos[id(a)]["key"] == "today"),
            "week": sum(1 for a in open_items if infos[id(a)]["key"] in ("today", "soon", "week")),
            "extended": sum(1 for a in data if a.get("is_extended") or a.get("previous_due_date")),
            "missed": sum(1 for a in data if infos[id(a)]["key"] == "missed"),
            "submitted": sum(1 for a in data if a.get("is_submitted")),
        }

        # ---- hero: up next
        self._hero(open_items[0] if open_items else None, infos)

        # ---- tiles
        tiles = ctk.CTkFrame(self, fg_color="transparent")
        tiles.pack(fill="x", pady=(14, 0))
        spec = [
            ("Pending", counts["pending"], "⏳", C["amber"], C["amber_t"], "Pending"),
            ("Due today", counts["today"], "🔥", C["red"], C["red_t"], "Pending"),
            ("Due this week", counts["week"], "📅", C["sky"], C["sky_t"], "Due soon"),
            ("Extended", counts["extended"], "⚡", C["violet"], C["violet_t"], "Extended"),
            ("Overdue", counts["missed"], "⚠", ("#b91c1c", "#f87171"), C["red_t"], "Overdue"),
            ("Submitted", counts["submitted"], "✓", C["green"], C["green_t"], "Submitted"),
        ]
        for i, (label, value, glyph, color, tint, flt) in enumerate(spec):
            tiles.grid_columnconfigure(i, weight=1, uniform="tile")
            tile = card(tiles, corner_radius=14)
            tile.grid(row=0, column=i, padx=(0 if i == 0 else 10, 0), sticky="nsew")
            top = ctk.CTkFrame(tile, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(14, 0))
            ctk.CTkLabel(top, text=glyph, font=ctk.CTkFont(size=15), width=34, height=34, fg_color=tint,
                         text_color=color, corner_radius=10).pack(side="left")
            ctk.CTkLabel(tile, text=str(value), font=F(28, "bold"), text_color=C["text"]).pack(anchor="w", padx=14, pady=(8, 0))
            ctk.CTkLabel(tile, text=label, font=F(12), text_color=C["muted"]).pack(anchor="w", padx=14, pady=(0, 14))
            bind_click(tile, lambda f=flt: self.app.navigate("assignments", filter_name=f))

        # ---- needs attention
        box = card(self)
        box.pack(fill="x", pady=(18, 0))
        section_title(box, "Needs your attention",
                      "Unsubmitted assignments, nearest deadline first").pack(anchor="w", padx=22, pady=(20, 10))
        if not open_items:
            ok = ctk.CTkFrame(box, fg_color="transparent")
            ok.pack(fill="x", padx=22, pady=(4, 22))
            ctk.CTkLabel(ok, text="✓", font=ctk.CTkFont(size=18, weight="bold"), width=40, height=40, fg_color=C["green_t"],
                         text_color=C["green"], corner_radius=12).pack(side="left", padx=(0, 14))
            ctk.CTkLabel(ok, text="All caught up. Nothing is waiting for a submission.",
                         font=F(14), text_color=C["text"]).pack(side="left")
        else:
            for a in open_items[:8]:
                self._attention_row(box, a, infos[id(a)])
            ctk.CTkLabel(box, text="", height=10).pack()

        # ---- courses
        courses = {}
        for a in data:
            c = courses.setdefault(a.get("course", "Unknown"), {"total": 0, "submitted": 0, "open": 0})
            c["total"] += 1
            c["submitted"] += 1 if a.get("is_submitted") else 0
            c["open"] += 1 if is_open_pending(a) else 0
        section_title(self, "Courses", f"{meta.get('semester') or 'Current semester'} · submission progress per course"
                      ).pack(anchor="w", pady=(24, 10))
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x")
        cols = 3
        for i in range(cols):
            grid.grid_columnconfigure(i, weight=1, uniform="course")
        for idx, (name_, c) in enumerate(sorted(courses.items())):
            cc = card(grid, corner_radius=14)
            cc.grid(row=idx // cols, column=idx % cols, padx=(0 if idx % cols == 0 else 10, 0), pady=(0, 10), sticky="nsew")
            ctk.CTkLabel(cc, text=name_, font=F(13, "bold"), text_color=C["text"], anchor="w",
                         wraplength=250, justify="left").pack(anchor="w", padx=16, pady=(16, 2))
            ratio = c["submitted"] / c["total"] if c["total"] else 0
            ctk.CTkLabel(cc, text=f"{c['submitted']} of {c['total']} submitted"
                         + (f"  ·  {c['open']} pending" if c["open"] else ""),
                         font=F(12), text_color=C["amber"] if c["open"] else C["muted"]).pack(anchor="w", padx=16)
            bar = ctk.CTkProgressBar(cc, height=6, progress_color=C["green"] if ratio == 1 else C["accent"],
                                     fg_color=C["card2"])
            bar.set(ratio)
            bar.pack(fill="x", padx=16, pady=(10, 16))
            bind_click(cc, lambda n=name_: self.app.navigate("assignments", course=n))

    def _hero(self, item, infos):
        if item is None:
            hero = card(self, fg_color=C["green_t"], border_color=C["green_t"])
            hero.pack(fill="x")
            ctk.CTkLabel(hero, text="ALL CAUGHT UP", font=F(11, "bold"), text_color=C["green"]).pack(anchor="w", padx=24, pady=(20, 2))
            ctk.CTkLabel(hero, text="No pending assignments right now.", font=F(20, "bold"), text_color=C["text"]).pack(anchor="w", padx=24, pady=(0, 20))
            return
        info = infos[id(item)]
        color, tint = URGENCY[info["key"]], TINT[info["key"]]
        hero = card(self, fg_color=tint, border_color=tint)
        hero.pack(fill="x")
        hero.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=24, pady=20)
        ctk.CTkLabel(left, text="UP NEXT", font=F(11, "bold"), text_color=color).pack(anchor="w")
        ctk.CTkLabel(left, text=item.get("title", ""), font=F(21, "bold"), text_color=C["text"]).pack(anchor="w", pady=(2, 2))
        ctk.CTkLabel(left, text=f"{item.get('course', '')}   ·   {fmt_due(item)}", font=F(13), text_color=C["muted"]).pack(anchor="w")
        right = ctk.CTkFrame(hero, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e", padx=24)
        days = info["days"]
        big = "Today" if days == 0 else "Tomorrow" if days == 1 else f"{days} days" if days is not None else "—"
        ctk.CTkLabel(right, text=big, font=F(30, "bold"), text_color=color).pack(anchor="e")
        pill(right, info["label"], color).pack(anchor="e")
        bind_click(hero, lambda: self.app.navigate("assignments", filter_name="Pending"))

    def _attention_row(self, parent, a, info):
        color = URGENCY[info["key"]]
        row = ctk.CTkFrame(parent, fg_color=C["card2"], corner_radius=12)
        row.pack(fill="x", padx=22, pady=4)
        ctk.CTkFrame(row, fg_color=color, width=5, height=2, corner_radius=3).pack(side="left", fill="y", padx=(10, 0), pady=10)
        txt = ctk.CTkFrame(row, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True, padx=12, pady=10)
        ctk.CTkLabel(txt, text=a.get("title", ""), font=F(14, "bold"), text_color=C["text"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(txt, text=f"{a.get('course', '')}   ·   {fmt_due(a)}", font=F(12),
                     text_color=C["muted"], anchor="w").pack(anchor="w")
        pill(row, info["label"], color).pack(side="right", padx=14)


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
        self.seg = ctk.CTkSegmentedButton(bar, values=FILTERS, font=F(12, "bold"), height=34,
                                          selected_color=C["accent"], selected_hover_color=C["accent_h"],
                                          unselected_color=C["card"], unselected_hover_color=C["card2"],
                                          fg_color=C["line"], command=self._set_filter)
        self.seg.set("All")
        self.seg.pack(side="left")
        self.search = ctk.CTkEntry(bar, placeholder_text="Search title or course…", height=34, width=240,
                                   font=F(12), fg_color=C["card"], border_color=C["line"], text_color=C["text"])
        self.search.pack(side="right")
        self.search.bind("<KeyRelease>", lambda e: self._set_query(self.search.get()))
        self.course_menu = ctk.CTkOptionMenu(bar, values=["All courses"], height=34, width=250, font=F(12),
                                             fg_color=C["card"], text_color=C["text"], button_color=C["card2"],
                                             button_hover_color=C["line"], dropdown_font=F(12), command=self._set_course)
        self.course_menu.pack(side="right", padx=(0, 10))

        self.summary = ctk.CTkLabel(self, text="", font=F(12), text_color=C["muted"], anchor="w")
        self.summary.pack(fill="x", pady=(0, 6))
        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.pack(fill="both", expand=True)

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
        for a, info in sorted(rows, key=lambda r: sort_key(r[0])):
            self._row(a, info)

    def _row(self, a, info):
        color = URGENCY[info["key"]]
        row = card(self.list, corner_radius=14)
        row.pack(fill="x", pady=4)
        ctk.CTkFrame(row, fg_color=color, width=5, height=2, corner_radius=3).pack(side="left", fill="y", padx=(12, 0), pady=12)
        body = ctk.CTkFrame(row, fg_color="transparent")
        body.pack(side="left", fill="x", expand=True, padx=14, pady=12)

        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x")
        pill(top, a.get("course", ""), C["sky_t"], fg=C["sky"]).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(top, text=f"#{a.get('assign_no', '')}  {a.get('title', '')}", font=F(14, "bold"),
                     text_color=C["text"], anchor="w").pack(side="left")

        due = f"Due {fmt_due(a)}"
        if a.get("is_extended") and a.get("original_due_date"):
            due += f"     ⚡ extended from {a['original_due_date']}"
        elif a.get("previous_due_date"):
            due += f"     ⚡ changed from {a['previous_due_date']}"
        marks = a.get("marks", "")
        if marks and marks.lower() != "not marked yet":
            due += f"     ·  Marks: {marks}"
        ctk.CTkLabel(body, text=due, font=F(12), text_color=C["muted"], anchor="w").pack(anchor="w", pady=(4, 0))

        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right", padx=14)
        pill(right, info["label"], color).pack(anchor="e")


# ---------------------------------------------------------------------------- settings
class SettingsView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        env = app.env

        acc = self._card("Portal account", "Changing these re-verifies the sign-in when you save.")
        self.enroll = self._entry(acc, "Enrollment number", env.get("ENROLLMENT", ""))
        self.password = self._entry(acc, "Portal password", env.get("PASSWORD", ""), show="•")
        ctk.CTkLabel(acc, text="Campus", font=F(12, "bold"), text_color=C["muted"]).pack(anchor="w", padx=22)
        self.campus = ctk.CTkOptionMenu(acc, values=CAMPUS_NAMES, height=38, font=F(13), fg_color=C["field"],
                                        text_color=C["text"], button_color=C["accent"], button_hover_color=C["accent_h"],
                                        dropdown_font=F(12))
        self.campus.set(campus_name(env.get("INSTITUTE_ID", "1")))
        self.campus.pack(fill="x", padx=22, pady=(2, 12))
        row = ctk.CTkFrame(acc, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(0, 20))
        ctk.CTkButton(row, text="Save & verify sign-in", font=F(13, "bold"), height=38, fg_color=C["accent"],
                      hover_color=C["accent_h"], command=self._save_account).pack(side="left")
        self.acc_msg = ctk.CTkLabel(row, text="", font=F(12), text_color=C["muted"])
        self.acc_msg.pack(side="left", padx=14)

        look = self._card("Appearance", "Pick the look you prefer. The choice is remembered.")
        theme_switch(look, self.app).pack(anchor="w", padx=22, pady=(0, 20))

        bg = self._card("Running in the background",
                        "Keep the app in the system tray so it is always one click away. "
                        "Right-click the tray icon to open, sync or quit.")
        self.tray_sw = self._switch(bg, "Keep running in the tray when the window is closed",
                                    env.get("CLOSE_TO_TRAY", True))
        self.startup_sw = ctk.CTkSwitch(bg, text="Start with Windows, minimized to the tray", font=F(13),
                                        text_color=C["text"], progress_color=C["accent"], command=self._toggle_startup)
        self.startup_sw.select() if automation.starts_with_windows() else self.startup_sw.deselect()
        self.startup_sw.pack(anchor="w", padx=22, pady=(4, 20))

        notif = self._card("Notifications", "How the app gets your attention after a sync or an hourly check.")
        self.voice = self._switch(notif, "Voice alerts through the speakers", env.get("ENABLE_VOICE", True))
        self.toast = self._switch(notif, "Windows desktop notifications", env.get("ENABLE_WINDOWS_TOAST", True))
        days_row = ctk.CTkFrame(notif, fg_color="transparent")
        days_row.pack(fill="x", padx=22, pady=(6, 4))
        ctk.CTkLabel(days_row, text="Mention assignments due within", font=F(13), text_color=C["text"]).pack(side="left")
        self.days = ctk.CTkOptionMenu(days_row, values=["1", "2", "3", "5", "7", "14"], width=80, height=32, font=F(12),
                                      fg_color=C["field"], text_color=C["text"], button_color=C["line"],
                                      button_hover_color=C["dim"], command=lambda v: self._save_prefs())
        self.days.set(str(env.get("NOTIFY_DAYS_AHEAD", 3)))
        self.days.pack(side="left", padx=10)
        ctk.CTkLabel(days_row, text="days", font=F(13), text_color=C["text"]).pack(side="left")
        self._soft_button(notif, "Send a test alert", self._test_alert).pack(anchor="w", padx=22, pady=(8, 20))

        auto = self._card("Background automation",
                          "Windows runs a check every day at 7:00 PM and when you sign in, plus an hourly reminder "
                          "while something is due today. Also adds Desktop and Start Menu shortcuts.")
        row = ctk.CTkFrame(auto, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(0, 20))
        self.auto_status = ctk.CTkLabel(row, text="Checking…", font=F(13, "bold"), text_color=C["muted"])
        self.auto_status.pack(side="left")
        self.auto_btn = ctk.CTkButton(row, text="…", font=F(12, "bold"), height=34, width=150, fg_color=C["card2"],
                                      hover_color=C["line"], text_color=C["text"], command=self._toggle_automation,
                                      state="disabled")
        self.auto_btn.pack(side="right")
        self.after(300, lambda: threading.Thread(target=self._refresh_automation, daemon=True).start())

        data = self._card("Data & diagnostics", f"Everything is stored locally in {BASE_DIR}")
        row = ctk.CTkFrame(data, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(0, 20))
        self._soft_button(row, "Open data folder", lambda: os.startfile(DATA_DIR)).pack(side="left", padx=(0, 10))
        self._soft_button(row, "Open log file", lambda: os.startfile(LOG_PATH) if LOG_PATH.exists() else None).pack(side="left", padx=(0, 10))
        self._soft_button(row, "Switch account", lambda: self.app.show_setup()).pack(side="left", padx=(0, 10))
        self._soft_button(row, "Clear local data", self._clear_data).pack(side="left")

        about = self._card("About", f"{APP_NAME} {APP_VERSION} {TAGLINE} · "
                           f"{'installed build' if FROZEN else 'running from source'} · made by Nobody243")
        row = ctk.CTkFrame(about, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(0, 20))
        if "<" not in REPO_URL:
            import webbrowser
            self._soft_button(row, "Check for updates", lambda: webbrowser.open(RELEASES_URL)).pack(side="left", padx=(0, 10))
            self._soft_button(row, "Project on GitHub", lambda: webbrowser.open(REPO_URL)).pack(side="left")

    # -- builders
    def _card(self, title, sub):
        box = card(self)
        box.pack(fill="x", pady=(2, 12))
        section_title(box, title, sub).pack(anchor="w", padx=22, pady=(20, 12))
        return box

    def _entry(self, parent, label, value, show=None):
        ctk.CTkLabel(parent, text=label, font=F(12, "bold"), text_color=C["muted"]).pack(anchor="w", padx=22)
        e = ctk.CTkEntry(parent, height=38, font=F(13), fg_color=C["field"], border_color=C["line"],
                         text_color=C["text"], show=show or "")
        e.insert(0, value)
        e.pack(fill="x", padx=22, pady=(2, 12))
        return e

    def _switch(self, parent, text, value):
        sw = ctk.CTkSwitch(parent, text=text, font=F(13), text_color=C["text"], progress_color=C["accent"],
                           command=self._save_prefs)
        sw.select() if value else sw.deselect()
        sw.pack(anchor="w", padx=22, pady=4)
        return sw

    def _soft_button(self, parent, text, cmd):
        return ctk.CTkButton(parent, text=text, font=F(12, "bold"), height=34, fg_color=C["card2"],
                             hover_color=C["line"], text_color=C["text"], command=cmd)

    # -- actions
    def _save_prefs(self):
        env = dict(self.app.env)
        env["ENABLE_VOICE"] = bool(self.voice.get())
        env["ENABLE_WINDOWS_TOAST"] = bool(self.toast.get())
        env["NOTIFY_DAYS_AHEAD"] = int(self.days.get())
        if hasattr(self, "tray_sw"):
            env["CLOSE_TO_TRAY"] = bool(self.tray_sw.get())
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
        self.acc_msg.configure(text="Saved. Verifying sign-in…", text_color=C["sky"])
        self.app.start_sync(on_done=lambda ok, msg: self.acc_msg.configure(
            text="Sign-in verified." if ok else msg, text_color=C["green"] if ok else C["red"]))

    def _test_alert(self):
        self.app.set_status("Sending test alert…")
        threading.Thread(target=lambda: (send_toast(APP_NAME, "Test alert: notifications are working."),
                                         speak_voice("Bahria LMS Monitor alerts are working.", force=True)),
                         daemon=True).start()

    def _refresh_automation(self):
        enabled = automation.is_enabled()
        try:
            self.after(0, self._show_automation, enabled)
        except RuntimeError:
            pass  # window closed before the check finished

    def _show_automation(self, enabled):
        self.auto_status.configure(text="●  Enabled" if enabled else "○  Not enabled",
                                   text_color=C["green"] if enabled else C["amber"])
        self.auto_btn.configure(text="Turn off" if enabled else "Turn on", state="normal",
                                fg_color=C["card2"] if enabled else C["accent"],
                                text_color=C["text"] if enabled else "#ffffff",
                                hover_color=C["line"] if enabled else C["accent_h"])
        self._auto_enabled = enabled

    def _toggle_automation(self):
        self.auto_btn.configure(state="disabled", text="Working…")
        target = not getattr(self, "_auto_enabled", False)

        def work():
            ok, msg = automation.enable() if target else automation.disable()
            self.after(0, self._show_automation, automation.is_enabled())
            self.after(0, lambda: self.app.set_status(msg))
            if not ok:
                self.after(0, lambda: messagebox.showerror(APP_NAME, f"Could not change automation.\n\n{msg[-600:]}"))
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
        ctk.CTkLabel(bar, text="Everything the app did, newest at the bottom. Scheduled background runs appear here too.",
                     font=F(12), text_color=C["muted"]).pack(side="left")
        ctk.CTkButton(bar, text="Open log file", font=F(12, "bold"), height=32, width=120, fg_color=C["card2"],
                      hover_color=C["line"], text_color=C["text"],
                      command=lambda: os.startfile(LOG_PATH) if LOG_PATH.exists() else None).pack(side="right")
        ctk.CTkButton(bar, text="Reload", font=F(12, "bold"), height=32, width=90, fg_color=C["card2"],
                      hover_color=C["line"], text_color=C["text"], command=self.refresh).pack(side="right", padx=(0, 8))
        self.box = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=12), fg_color=C["card"],
                                  text_color=C["muted"], corner_radius=14, border_width=1, border_color=C["line"],
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
    NAV = [("dashboard", "Dashboard", "▦"), ("assignments", "Assignments", "☰"),
           ("settings", "Settings", "⚙"), ("activity", "Activity", "≡")]

    def __init__(self, start_view="dashboard", force_setup=False, start_hidden=False):
        self.env = load_env()
        self.theme = self.env.get("THEME", "dark")
        ctk.set_appearance_mode(self.theme)
        super().__init__(fg_color=C["bg"])
        self.title(APP_NAME)
        try:
            scale = ctk.ScalingTracker.get_window_scaling(self)
        except Exception:
            scale = 1.0
        sw, sh = int(self.winfo_screenwidth() / scale), int(self.winfo_screenheight() / scale)
        w, h = min(1280, sw - 60), min(840, sh - 120)
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 30)}")
        self.minsize(min(1000, w), min(640, h))
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
        self.log_queue = queue.Queue()
        logging.getLogger("bahria").addHandler(QueueHandler(self.log_queue))

        self.tray = None
        self._tray_hint_shown = False
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
        self._start_tray()
        self.update_tray_tooltip()
        self._listen_for_show_requests()
        if start_hidden and signed_in and self.tray:
            self.after(50, self.hide_to_tray)

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

    def _listen_for_show_requests(self):
        """A second launch of the app sets a named event; we answer by showing the window."""
        try:
            k32 = ctypes.windll.kernel32
            self._show_event = k32.CreateEventW(None, False, False, SHOW_EVENT_NAME)
        except Exception:
            self._show_event = None
            return

        def wait():
            while True:
                if k32.WaitForSingleObject(self._show_event, 0xFFFFFFFF) != 0:
                    break
                try:
                    self.after(0, self.show_window)
                except RuntimeError:
                    break
        threading.Thread(target=wait, daemon=True).start()

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
        self.withdraw()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            if self.tray:
                self.tray.notify("Still running in the tray. Right-click the icon to open or quit.", APP_NAME)

    def quit_app(self):
        if self.syncing:
            _release_lock()
        if self.tray:
            self.tray.stop()
        self.destroy()

    def update_tray_tooltip(self):
        if not self.tray:
            return
        pending = sum(1 for a in self.data.values() if is_open_pending(a))
        self.tray.set_tooltip(f"{APP_NAME} · {pending} pending" if self.data else APP_NAME)

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

        side = ctk.CTkFrame(self.container, fg_color=C["side"], corner_radius=0, width=240)
        side.grid(row=0, column=0, sticky="nsw")
        side.grid_propagate(False)
        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(22, 18))
        ctk.CTkLabel(brand, text="🎓", font=ctk.CTkFont(size=16), width=36, height=36, fg_color=C["sky_t"],
                     corner_radius=10).pack(side="left", padx=(0, 10))
        bt = ctk.CTkFrame(brand, fg_color="transparent")
        bt.pack(side="left")
        ctk.CTkLabel(bt, text=APP_NAME, font=F(16, "bold"), text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(bt, text="Bahria University LMS", font=F(11), text_color=C["muted"]).pack(anchor="w")

        self.nav_buttons = {}
        for key, label, glyph in self.NAV:
            b = ctk.CTkButton(side, text=f"{glyph}   {label}", font=F(14), height=42, anchor="w", corner_radius=10,
                              fg_color="transparent", hover_color=C["card2"], text_color=C["muted"],
                              command=lambda k=key: self.navigate(k))
            b.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = b

        foot = ctk.CTkFrame(side, fg_color="transparent")
        foot.pack(side="bottom", fill="x", padx=16, pady=16)
        theme_switch(foot, self).pack(anchor="w", padx=4, pady=(0, 12))
        user = ctk.CTkFrame(foot, fg_color=C["card2"], corner_radius=12)
        user.pack(fill="x")
        name = self.meta.get("student_name") or "Student"
        initials = "".join(p[0] for p in name.split()[:2]).upper() or "S"
        ctk.CTkLabel(user, text=initials, font=F(13, "bold"), width=36, height=36, fg_color=C["accent"],
                     text_color="#ffffff", corner_radius=18).pack(side="left", padx=10, pady=10)
        ut = ctk.CTkFrame(user, fg_color="transparent")
        ut.pack(side="left", pady=10)
        ctk.CTkLabel(ut, text=name, font=F(12, "bold"), text_color=C["text"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(ut, text=self.env.get("ENROLLMENT", ""), font=F(11), text_color=C["muted"]).pack(anchor="w")

        content = ctk.CTkFrame(self.container, fg_color="transparent")
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(1, weight=1)
        content.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(content, fg_color="transparent", height=64)
        top.grid(row=0, column=0, sticky="ew", padx=28, pady=(18, 4))
        tt = ctk.CTkFrame(top, fg_color="transparent")
        tt.pack(side="left")
        self.page_title = ctk.CTkLabel(tt, text="", font=F(22, "bold"), text_color=C["text"])
        self.page_title.pack(anchor="w")
        self.last_sync_lbl = ctk.CTkLabel(tt, text="", font=F(12), text_color=C["muted"])
        self.last_sync_lbl.pack(anchor="w")
        self.sync_btn = ctk.CTkButton(top, text="⟳  Sync now", font=F(13, "bold"), height=38, width=130,
                                      fg_color=C["accent"], hover_color=C["accent_h"], command=self.start_sync)
        self.sync_btn.pack(side="right")

        self.body = ctk.CTkFrame(content, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=28, pady=(6, 0))

        status = ctk.CTkFrame(content, fg_color=C["side"], corner_radius=0, height=30)
        status.grid(row=2, column=0, sticky="ew")
        self.status_lbl = ctk.CTkLabel(status, text="Ready.", font=F(11), text_color=C["muted"], anchor="w")
        self.status_lbl.pack(side="left", padx=28, pady=5)
        ctk.CTkLabel(status, text=f"v{APP_VERSION}", font=F(11), text_color=C["dim"]).pack(side="right", padx=28)

        self.views = {
            "dashboard": DashboardView(self.body, self),
            "assignments": AssignmentsView(self.body, self),
            "settings": SettingsView(self.body, self),
            "activity": ActivityView(self.body, self),
        }
        self.reload_data()
        self.navigate("dashboard")
        if self.syncing:
            self.sync_btn.configure(state="disabled", text="Syncing…")

    def navigate(self, key, **kwargs):
        if not self.views:
            return
        for k, b in self.nav_buttons.items():
            b.configure(fg_color=C["card2"] if k == key else "transparent",
                        text_color=C["text"] if k == key else C["muted"])
        if self.current:
            self.views[self.current].pack_forget()
        self.current = key
        view = self.views[key]
        view.pack(fill="both", expand=True)
        self.page_title.configure(text=dict((k, l) for k, l, _ in self.NAV)[key])
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
            self.last_sync_lbl.configure(text=f"Last sync: {ls}" if ls else "Not synced yet")
        self.update_tray_tooltip()
        if self.current and self.current in self.views and hasattr(self.views[self.current], "refresh"):
            self.views[self.current].refresh()

    def set_status(self, text):
        if "status_lbl" in self.__dict__:
            self.status_lbl.configure(text=text)

    # ---- sync
    def start_sync(self, on_done=None):
        if self.syncing:
            return
        self.syncing = True
        if "sync_btn" in self.__dict__:
            self.sync_btn.configure(state="disabled", text="Syncing…")
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
        self.after(0, self._sync_done, result, on_done)

    def _sync_done(self, result, on_done):
        ok, msg = result
        self.syncing = False
        if "sync_btn" in self.__dict__:
            self.sync_btn.configure(state="normal", text="⟳  Sync now")
        self.set_status(msg)
        self.reload_data()
        if not ok and on_done is None and "status_lbl" in self.__dict__:
            messagebox.showwarning(APP_NAME, msg)
        if on_done:
            on_done(ok, msg)

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
