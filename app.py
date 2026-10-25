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
import time
import webbrowser
from datetime import datetime, timedelta

if sys.stdout is None or sys.stderr is None:          # windowed exe: no console attached
    sys.stdout = sys.stdout or open(os.devnull, "w")
    sys.stderr = sys.stderr or open(os.devnull, "w")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from config import (APP_ID, APP_NAME, APP_VERSION, TAGLINE, ASSETS_DIR, BASE_DIR, DATA_DIR, DOCS_DIR, LOG_PATH, lectures_dir,
                    GITHUB_CLIENT_ID,
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
    parser.add_argument("--disable-cloud", action="store_true",
                        help="turn off cloud checks (remove the secrets and workflow from your GitHub repository), then exit")
    parser.add_argument("--view", default="dashboard",
                        choices=["dashboard", "assignments", "attendance", "exams", "results", "timetable", "announcements",
                                 "lectures", "settings",
                                 "activity"])
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
    if args.disable_cloud:
        import cloud
        if not cloud.enabled():
            print("Cloud checks are not on.")
            sys.exit(0)
        url = cloud.teardown()
        print(f"Cloud checks are off. The empty repository remains at {url.rsplit('/settings', 1)[0] if url else 'GitHub'}.")
        sys.exit(0)
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
        app = App(start_view=start_view, force_setup=force_setup, start_hidden=start_hidden)
        crash.install(app, app.show_crash)
        app.mainloop()
    except Exception:
        log.exception("The app crashed")
        crash.last_resort(sys.exc_info())
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
import tkinter as tk                             # noqa: E402
import tkinter.font as tkfont                    # noqa: E402
from ctypes import wintypes                      # noqa: E402
from tkinter import Text as tk_text_cls, Entry as tk_entry_cls  # noqa: E402
from PIL import Image, ImageTk                   # noqa: E402
from tkinter import filedialog, messagebox, simpledialog  # noqa: E402

import automation                                                                           # noqa: E402
import updater                                                                              # noqa: E402
from tray import TrayIcon                                                                   # noqa: E402
from results import GRADES, apply_overrides, gpa_of, grade_needed, project, required_gpa, totals, uniform_scenarios
from tracker import load_results
from tracker import (load_stored_assignments, clear_stored_assignments, load_attendance,    # noqa: E402
                     load_exams, load_announcements, load_lectures, load_timetable)
from lms_scraper import run_sync, download_lectures, download_assignment_files, FILE_KIND_LABELS, LoginError, _release_lock              # noqa: E402
from notifier import send_toast, speak_voice, list_voices                                   # noqa: E402
from deadlines import classify, is_open_pending, sort_key, deadline_of                     # noqa: E402
from campus import upcoming_exams, seat_text, session_date, sessions_on, minutes            # noqa: E402
from timetable_render import render_timetable, save_timetable                              # noqa: E402
import channels                                                                             # noqa: E402
import cloud                                                                                # noqa: E402
from calendar_export import calendar_path                                                   # noqa: E402
from jobs import process_sync, collectors_for                                               # noqa: E402
import crash                                                                                  # noqa: E402

# ---------------------------------------------------------------------------- design tokens
# Direction: calm and editorial. Warm neutral surfaces, one accent, three type weights (regular, medium, semibold;
# never bold), hairline dividers instead of nested cards, no decorative icons.
# Colour: cool slate neutrals (a touch of blue in every grey, so the surfaces read as one material) with a single
# indigo accent, and the five state hues spaced a golden angle (137.5°) apart from it round the wheel so they never
# clash: red 42 · green 180 · violet 317 · amber 95 · sky 232. Every colour is a (light, dark) pair so the theme switch
# restyles the live window. Inks sit at L≈.48 on the light surfaces and L≈.80 on the dark ones (AA on both); tints
# are the same hue at L .96 / .22. "side" is the sidebar and status bar: a shade off the content so the shell
# frames the page instead of merging with it.
C = {
    "bg": ("#f3f4f7", "#0d0f13"), "surface": ("#ffffff", "#15181d"), "surface2": ("#eceef3", "#1c2027"),
    "side": ("#f8f9fb", "#101318"), "field": ("#f7f8fb", "#1a1e25"), "line": ("#e3e6ec", "#252a32"), "line2": ("#cfd4de", "#343a45"),
    "ink": ("#14161b", "#eef0f4"), "muted": ("#5b6170", "#9aa1ad"), "dim": ("#9096a3", "#666d79"),
    "accent": ("#2f5bea", "#8aa7ff"), "accent_h": ("#2449cc", "#a3baff"), "on_accent": ("#ffffff", "#0b1024"),
    "red": ("#c2410c", "#ff9b78"), "amber": ("#946200", "#e3c75c"), "green": ("#0f766e", "#4fd6bf"),
    "sky": ("#0369a1", "#67c6f5"), "violet": ("#7e3fb8", "#d9a3f2"),
    "red_t": ("#fdeee6", "#33201a"), "amber_t": ("#fbf3dc", "#2a2412"), "green_t": ("#dcf5f0", "#0f2a26"),
    "sky_t": ("#e0f2fe", "#122633"), "violet_t": ("#f3e8fb", "#2a1f31"), "grey_t": ("#eceef3", "#1c2027"),
}
URGENCY = {"today": "red", "missed": "red", "soon": "amber", "week": "sky", "later": "dim",
           "submitted": "green", "unknown": "dim"}

# type scale: 13px × φ^(n/4) → 11 caption · 12 small · 13 body · 15 lead · 17 · 21 · 24 page · 27 · 30 display
XS, SM, MD, LG, XL, H3, H2, H1, D1 = 11, 12, 13, 15, 17, 21, 24, 27, 30

# Inter (bundled, SIL OFL) with Segoe UI as the fallback. Weight lives in the family name because Tk only knows
# normal/bold; "bold" deliberately maps to semibold.
FONTS = {"normal": "Segoe UI", "medium": "Segoe UI", "semibold": "Segoe UI", "bold": "Segoe UI", "display": "Segoe UI",
         "mono": "Consolas"}
WEIGHTS = {"normal": "normal", "medium": "normal", "semibold": "bold", "bold": "bold", "display": "bold"}


def load_fonts():
    """Register the bundled Inter faces for this process only (FR_PRIVATE: nothing is installed, no admin rights,
    and they vanish when the app exits). Must run before Tk creates its first font."""
    folder = ASSETS_DIR / "fonts"
    if os.name != "nt" or not folder.is_dir():
        return 0
    loaded = 0
    try:
        gdi = ctypes.windll.gdi32
        for path in sorted(folder.glob("*.ttf")):
            if gdi.AddFontResourceExW(str(path), 0x10, 0):
                loaded += 1
    except Exception:
        log.debug("font registration failed", exc_info=True)
    return loaded


def pick_fonts():
    _FONTS.clear()
    try:
        fams = set(tkfont.families())
    except Exception:
        return
    if {"Inter", "Inter Medium", "Inter SemiBold", "Inter Display SemiBold"} <= fams:
        FONTS.update(normal="Inter", medium="Inter Medium", semibold="Inter SemiBold", bold="Inter SemiBold",
                     display="Inter Display SemiBold")
        WEIGHTS.update(semibold="normal", bold="normal", display="normal")
    else:
        if "Segoe UI Variable Text" in fams:
            FONTS.update(normal="Segoe UI Variable Text", medium="Segoe UI Variable Text")
        if "Segoe UI Semibold" in fams:
            FONTS.update(semibold="Segoe UI Semibold", bold="Segoe UI Semibold")
            WEIGHTS.update(semibold="normal", bold="normal")
        if "Segoe UI Variable Display" in fams:
            FONTS["display"] = "Segoe UI Variable Display"
    if "Cascadia Mono" in fams:
        FONTS["mono"] = "Cascadia Mono"


_FONTS = {}


def F(size=MD, weight="normal", display=False):
    """Shared CTkFont per (size, weight): creating a font per widget was the single biggest cost of a page build."""
    key = ("display" if display else weight, size)
    f = _FONTS.get(key)
    if f is None:
        f = _FONTS[key] = ctk.CTkFont(family=FONTS[key[0]], size=size, weight=WEIGHTS[key[0]])
    return f


# ---------------------------------------------------------------------------- motion
ANIMATE = {"on": True}


def ease_out(t):
    return 1 - (1 - t) ** 3


def animate(widget, duration, step, done=None):
    """Runs step(t) with t eased 0..1 over `duration` seconds on the Tk loop (33 ms frames, 30 fps). With animations
    off, jumps straight to the end state."""
    if not ANIMATE["on"]:
        try:
            step(1.0)
        except Exception:
            return
        if done:
            done()
        return
    start = time.perf_counter()

    def tick():
        t = min(1.0, (time.perf_counter() - start) / duration)
        try:
            if not widget.winfo_exists():
                return
            step(ease_out(t))
        except Exception:
            return
        if t < 1:
            widget.after(33, tick)
        elif done:
            done()
    tick()


def count_up(label, value, suffix="", duration=0.7):
    """Animates a number label from 0 to value."""
    if not value:
        label.configure(text=f"0{suffix}")
        return
    animate(label, duration, lambda t: label.configure(text=f"{int(round(value * t))}{suffix}"))


def fill_bar(bar, ratio, duration=0.6):
    """Animates a progress bar from empty to ratio."""
    bar.set(0)
    animate(bar, duration, lambda t: bar.set(ratio * t))


class _BitmapInfo(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


def snapshot(widget):
    """A picture of a widget as it stands on screen (Windows PrintWindow with full content), or None. Tk cannot
    fade or move hundreds of widgets smoothly, but it can move one picture of them."""
    try:
        w, h = widget.winfo_width(), widget.winfo_height()
        if w < 2 or h < 2 or not widget.winfo_viewable():
            return None
        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        hdc = user32.GetDC(0)
        mdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        old = gdi32.SelectObject(mdc, bmp)
        try:
            if not user32.PrintWindow(widget.winfo_id(), mdc, 2):          # PW_RENDERFULLCONTENT
                return None
            info = _BitmapInfo(ctypes.sizeof(_BitmapInfo), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
            buf = ctypes.create_string_buffer(w * h * 4)
            gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(info), 0)
            return Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1).copy()
        finally:
            gdi32.SelectObject(mdc, old)
            gdi32.DeleteObject(bmp)
            gdi32.DeleteDC(mdc)
            user32.ReleaseDC(0, hdc)
    except Exception:
        return None


def cover_over(app, widget, image):
    """A borderless window exactly over `widget` showing `image` (a picture of the page being left). The new page
    lays out and paints underneath, unseen, and the cover then fades away through window alpha, which Windows
    composites on the GPU: smooth and cheap, where fading hundreds of widgets is impossible in Tk. Returns None if
    the window cannot be made."""
    try:
        top = tk.Toplevel(app)
        top.withdraw()
        top.overrideredirect(True)
        top.transient(app)
        top._img = ImageTk.PhotoImage(image)
        tk.Label(top, image=top._img, bd=0, highlightthickness=0).pack()
        top.geometry(f"{image.width}x{image.height}+{widget.winfo_rootx()}+{widget.winfo_rooty()}")
        top.attributes("-alpha", 1.0)
        top.deiconify()
        top.lift()
        return top
    except Exception:
        return None


def fade_cover(cover, duration=0.22):
    """Fades a cover window out and destroys it. Falls back to destroying it at once."""
    def step(t):
        try:
            cover.attributes("-alpha", max(0.0, 1.0 - t))
        except Exception:
            finish()

    def finish():
        try:
            cover.destroy()
        except Exception:
            pass
    animate(cover, duration, step, finish)


class Lazy:
    """Builds a long list in parts: the first units now, the rest as the user scrolls towards what is built (or
    while the built part is still shorter than the viewport). The page opens fast and repaints fast, because only
    what has been looked at exists as widgets. A unit is any callable that packs widgets into the list."""
    FIRST, MORE = 8, 8

    def __init__(self, frame):
        self.frame, self.canvas, self.queue, self.job = frame, frame._parent_canvas, [], None
        if not getattr(frame, "_lazy_hooked", False):
            frame._lazy_hooked = True
            bar = frame._scrollbar

            def moved(a, b):
                bar.set(a, b)
                lazy = getattr(frame, "_lazy", None)
                if lazy is not None and float(b) > 0.7:
                    lazy.more()
            self.canvas.configure(yscrollcommand=moved)
        frame._lazy = self

    def add(self, builder):
        self.queue.append(builder)

    def start(self):
        self._build(self.FIRST)
        self.more()

    def more(self):
        if self.queue and self.job is None and self.frame._lazy is self:
            self.job = self.frame.after_idle(self._step)

    def _step(self):
        self.job = None
        if self.frame._lazy is self:
            self._build(self.MORE)       # the scroll region then grows and `moved` fires again if still near the end

    def _build(self, n):
        for _ in range(min(n, len(self.queue))):
            try:
                self.queue.pop(0)()
            except Exception:
                pass

    def build_all(self):
        self._build(len(self.queue))


SCROLL = {"t": 0.0}          # time of the last wheel event; hover effects pause briefly after it


def note_scroll(_event=None):
    SCROLL["t"] = time.monotonic()


def scrolling() -> bool:
    return time.monotonic() - SCROLL["t"] < 0.35


def _owns_wheel(self, widget):
    """Whether this scrollable frame should take a wheel event that happened over `widget`: inside it (the stock
    rule), or anywhere else on a page whose one list it is, so the wheel also works over the page's toolbar."""
    if self._check_if_valid_scroll(widget):
        return True
    w = widget
    while w is not None:
        if isinstance(w, (ctk.CTkScrollbar, ctk.CTkSlider, ctk.CTkTextbox, ctk.CTkScrollableFrame)):
            return False
        owner = getattr(w, "_page_scroller", None)
        if owner is not None:
            return owner is self
        w = w.master
    return False


def _wheel_coalesced(self, event):
    """Replaces CTkScrollableFrame's wheel handler on Windows. Wheel events arrive in bursts (several per notch from
    precision wheels and touchpads) and the stock handler scrolls and repaints the whole page for each one, which
    is the stutter and torn text during a fast scroll. The deltas are summed and applied once per frame, each step
    waits for its repaint to finish before the next is applied, and a notch moves 40 px instead of 20."""
    if not _owns_wheel(self, event.widget):
        return
    canvas = self._parent_canvas
    axis = "x" if self._shift_pressed else "y"
    if (canvas.xview() if axis == "x" else canvas.yview()) == (0.0, 1.0):
        return
    pend = self.__dict__.setdefault("_wheel_pending", {"x": 0, "y": 0, "job": None, "painting": False})
    pend[axis] -= int(event.delta / 3)
    if pend["job"] is None and not pend["painting"]:
        pend["job"] = canvas.after(16, lambda: _wheel_flush(self))


def _wheel_flush(self):
    pend = self._wheel_pending
    pend["job"] = None
    canvas = self._parent_canvas
    try:
        dx, dy = pend["x"], pend["y"]
        pend["x"] = pend["y"] = 0
        if dx:
            canvas.xview("scroll", dx, "units")
        if dy:
            canvas.yview("scroll", dy, "units")
        # a page of a few hundred widgets takes 20-80 ms to repaint after a move, longer than a frame: finish the
        # repaint now, so the next step never lands on a half-painted page (that was the torn, striped text)
        pend["painting"] = True
        try:
            canvas.update()
        finally:
            pend["painting"] = False
        if (pend["x"] or pend["y"]) and pend["job"] is None:
            pend["job"] = canvas.after(1, lambda: _wheel_flush(self))
    except Exception:
        pass


def page_scroll(view, what):
    """Keyboard scrolling of the page's list: what is ("page", +/-1) or ("edge", 0 top / 1 bottom)."""
    target = view if isinstance(view, ctk.CTkScrollableFrame) else getattr(view, "_page_scroller", None)
    if target is None:
        return
    canvas = target._parent_canvas
    kind, amount = what
    try:
        lazy = getattr(target, "_lazy", None)
        if lazy is not None and kind == "edge" and amount:
            lazy.build_all()
            target.update_idletasks()
        if kind == "page":
            canvas.yview("scroll", amount, "pages")
        else:
            canvas.yview_moveto(amount)
    except Exception:
        pass


if sys.platform.startswith("win"):
    ctk.CTkScrollableFrame._mouse_wheel_all = _wheel_coalesced


_scrollbar_set = ctk.CTkScrollbar.set


def _scrollbar_set_coalesced(self, start, end):
    """CTkScrollbar.set redraws the bar and forces every pending layout to finish (update_idletasks) each time it
    is called, and the canvas calls it for every widget added to a list, which made building a long page cost far
    more than the widgets themselves. The bar is updated once per idle cycle instead."""
    self._set_pending = (start, end)
    if getattr(self, "_set_job", None) is None:
        self._set_job = self.after_idle(lambda: _scrollbar_set_flush(self))


def _scrollbar_set_flush(self):
    self._set_job = None
    try:
        _scrollbar_set(self, *self._set_pending)
    except Exception:
        pass


ctk.CTkScrollbar.set = _scrollbar_set_coalesced


def hover_lift(widget, fg=None, border=None):
    """Hover feedback for a card or row: the border brightens (and optionally the fill) while the pointer is over it,
    including over its children. Cheap, no reflow. Paused while the wheel is turning."""
    try:
        base_fg = widget.cget("fg_color")
        base_border = widget.cget("border_color")
    except Exception:
        return
    hover_fg = fg or base_fg
    hover_border = border or C["line2"]
    state = {"in": False}

    def enter(_e=None):
        if scrolling():
            return
        if not state["in"]:
            state["in"] = True
            try:
                widget.configure(border_color=hover_border, fg_color=hover_fg)
            except Exception:
                pass

    def leave(_e=None):
        if scrolling() and not state["in"]:
            return
        # ignore leaves that are really moves onto a child
        try:
            x, y = widget.winfo_pointerxy()
            wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
            if wx <= x < wx + widget.winfo_width() and wy <= y < wy + widget.winfo_height():
                return
        except Exception:
            pass
        state["in"] = False
        try:
            widget.configure(border_color=base_border, fg_color=base_fg)
        except Exception:
            pass

    def bind_all(w):
        w.bind("<Enter>", enter, add="+")
        w.bind("<Leave>", leave, add="+")
        for c in w.winfo_children():
            bind_all(c)
    bind_all(widget)


def urgency_color(key):
    return C[URGENCY[key]]


def urgency_tint(key):
    name = URGENCY[key]
    return C[f"{name}_t"] if f"{name}_t" in C else C["grey_t"]


def pill(parent, text, key_or_color, size=11):
    color = C[URGENCY[key_or_color]] if key_or_color in URGENCY else key_or_color
    tint = urgency_tint(key_or_color) if key_or_color in URGENCY else C["surface2"]
    return ctk.CTkLabel(parent, text=f"  {text}  ", font=F(size, "semibold"), fg_color=tint, text_color=color,
                        corner_radius=12, height=24)


def surface(parent, hover=False, **kw):
    opts = dict(fg_color=C["surface"], corner_radius=14, border_width=1, border_color=C["line"])
    opts.update(kw)
    box = ctk.CTkFrame(parent, **opts)
    if hover:
        box.after(50, lambda: hover_lift(box))
    return box


def solid(color):
    """The colour for the current theme out of a (light, dark) pair, for plain Tk widgets."""
    if isinstance(color, (tuple, list)):
        return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
    return color


def hairline(parent, padx=20):
    # a plain Tk frame: one window and no canvas drawing, which matters with a hundred of them on a page
    tk.Frame(parent, height=1, bg=solid(C["line"]), bd=0, highlightthickness=0).pack(fill="x", padx=padx)


def heading(parent, text, sub=None, size=17):
    box = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(box, text=text, font=F(size, "semibold", display=True), text_color=C["ink"]).pack(anchor="w")
    if sub:
        # long subtitles wrap instead of being clipped on both sides (Settings sections at a narrow window)
        ctk.CTkLabel(box, text=sub, font=F(SM), text_color=C["muted"], justify="left", anchor="w",
                     wraplength=900).pack(anchor="w", pady=(1, 0))
    return box


def soft_button(parent, text, cmd, width=None):
    kw = dict(width=width) if width else {}
    return ctk.CTkButton(parent, text=text, font=F(SM, "semibold"), height=34, fg_color=C["surface2"],
                         hover_color=C["line2"], text_color=C["ink"], corner_radius=8, command=cmd, **kw)


def primary_button(parent, text, cmd, height=38, width=None):
    kw = dict(width=width) if width else {}
    return ctk.CTkButton(parent, text=text, font=F(MD, "semibold"), height=height, fg_color=C["accent"],
                         hover_color=C["accent_h"], text_color=C["on_accent"], corner_radius=8, command=cmd, **kw)


def bind_click(widget, cb, lift=True):
    """Makes a whole card clickable (and, for frames, gives it hover feedback). Tk occasionally delivers the
    binding without an event (seen on the Dashboard while another page was being rebuilt); that is not a click
    and is ignored, not acted on and not reported."""
    def on_click(*event):
        if not event:
            log.debug("click binding fired without an event on %s", widget)
            return None
        return cb()
    widget.bind("<Button-1>", on_click)
    try:
        widget.configure(cursor="hand2")
    except Exception:
        pass
    for child in widget.winfo_children():
        bind_click(child, cb, lift=False)
    if lift and isinstance(widget, ctk.CTkFrame):
        try:
            if widget.cget("border_width"):
                hover_lift(widget)
            else:
                hover_lift(widget, fg=C["surface2"], border=C["surface2"])
        except Exception:
            pass


def fmt_due(item):
    dt = deadline_of(item)
    if not dt:
        return item.get("due_date", "No deadline")
    return dt.strftime("%a %d %b · %I:%M %p").replace(" 0", " ").replace("AM", "am").replace("PM", "pm")


def rel_time(iso):
    """'3 days ago' style label for an ISO timestamp (empty when unknown)."""
    try:
        dt = datetime.fromisoformat(iso)
    except Exception:
        return ""
    d = datetime.now() - dt
    secs = int(d.total_seconds())
    if secs < 3600:
        return "just now" if secs < 120 else f"{secs // 60} min ago"
    if secs < 86400:
        return f"{secs // 3600} h ago"
    days = secs // 86400
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    return dt.strftime("%d %b %Y")


def att_color(c):
    """Colour key for an attendance record: red under the minimum, amber when one more absence would do it."""
    if not c.get("ok", True):
        return C["red"], C["red_t"], "Under minimum"
    if c.get("total", 0) and c.get("can_miss", 0) < 3:
        return C["amber"], C["amber_t"], "At risk"
    return C["green"], C["green_t"], "On track"


def countdown(days):
    return "Today" if days == 0 else "Tomorrow" if days == 1 else f"{days} days"


def short_path(path, limit=44) -> str:
    """A folder path for a label: whole when short, else '…\\last two parts'."""
    text = str(path)
    if len(text) <= limit:
        return text
    parts = text.replace("/", "\\").split("\\")
    return "…\\" + "\\".join(parts[-2:]) if len(parts) > 2 else text


def open_doc(name, fallback_url=None):
    path = DOCS_DIR / name
    if path.exists():
        os.startfile(path)
    elif fallback_url:
        webbrowser.open(fallback_url)


def theme_switch(parent, app):
    sw = ctk.CTkSwitch(parent, text="Dark theme", font=F(SM), text_color=C["muted"], progress_color=C["accent"],
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
def empty_semester_box(parent, app, title="No courses registered yet"):
    """What every page shows after a check that found no courses on the portal (between semesters)."""
    box = surface(parent)
    box.pack(fill="x")
    ctk.CTkLabel(box, text=title, font=F(XL, "semibold", display=True), text_color=C["ink"]).pack(pady=(28, 2))
    ctk.CTkLabel(box, text=app.empty_semester_text(), font=F(MD), text_color=C["muted"], wraplength=700,
                 justify="center").pack(padx=24, pady=(0, 28))
    return box


class SetupView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=C["bg"])
        self.app = app
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(0, weight=1)
        self._wrap_left, self._wrap_card, self._gaps = [], [], []
        self._build_left()
        self._build_right()
        self._size = (0, 0)
        self.bind("<Configure>", lambda e: self._layout())
        self.after(80, self._layout)

    def _layout(self):
        """Fits the card to the window: width from the right column, wrapped lines from the card, tighter gaps on
        short windows (a 1366x768 laptop at 125 % gives the window about 530 px)."""
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50 or (w, h) == self._size:
            return
        self._size = (w, h)
        right_w = w * 6 / 11
        card_w = int(min(470, max(330, right_w - 48)))
        self.card.place_configure(relwidth=0, width=card_w)
        inner = card_w - 64
        for lbl in self._wrap_card:
            lbl.configure(wraplength=inner)
        left_inner = int(w * 5 / 11 * 0.76) - 20
        for lbl in self._wrap_left:
            lbl.configure(wraplength=max(220, left_inner))
        compact = h < 600
        for widget, normal, tight in self._gaps:
            widget.pack_configure(pady=tight if compact else normal)
        self.title_lbl.configure(font=F(H3 if compact or card_w < 400 else H2, "semibold", display=True))
        if right_w - card_w < 2 * 24 + 130:
            # no room beside the card: bottom left of the left panel, or nowhere when that panel is full too
            # (the theme can still be changed from the sidebar later)
            if self._left_inner.winfo_reqheight() + 64 < h:
                self.theme_sw.place_configure(in_=self._left, relx=0.0, rely=1.0, anchor="sw", x=20, y=-14)
            else:
                self.theme_sw.place_forget()
                return
        else:
            self.theme_sw.place_configure(in_=self._right, relx=1.0, rely=0.0, anchor="ne", x=-24, y=18)
        self.theme_sw.lift()

    def _build_left(self):
        left = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        self._left = left
        ctk.CTkFrame(self, fg_color=C["line"], width=1, corner_radius=0).grid(row=0, column=0, sticky="nse")
        inner = ctk.CTkFrame(left, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.76)
        self._left_inner = inner

        if self.app.logo:
            ctk.CTkLabel(inner, text="", image=self.app.logo).pack(anchor="w")
        ctk.CTkLabel(inner, text=APP_NAME, font=F(D1, "semibold", display=True), text_color=C["ink"]).pack(anchor="w", pady=(14, 0))
        ctk.CTkLabel(inner, text=TAGLINE, font=F(LG), text_color=C["accent"]).pack(anchor="w", pady=(0, 10))
        intro = "Assignments, attendance, exams, announcements and lecture notes, read for you. Set it up once; it runs on its own."
        intro_lbl = ctk.CTkLabel(inner, text=intro, font=F(LG), text_color=C["muted"], justify="left", wraplength=340)
        intro_lbl.pack(anchor="w", pady=(0, 28))
        self._wrap_left.append(intro_lbl)
        self._gaps.append((intro_lbl, (0, 28), (0, 16)))

        for title, desc in [
            ("Checks the portal for you", "Signs in every evening at 7 PM and whenever your PC starts, then tells you only what changed."),
            ("Catches what the LMS hides",
             "Extended deadlines merged into one date string, a new absence, a posted exam seat, a fresh announcement."),
            ("Reminds you on the day",
             "Hourly voice reminders while an assignment is due today; quiet notifications for everything else."),
            ("Stays on your PC", "Your password is encrypted by Windows for your account and only ever sent to cms.bahria.edu.pk."),
        ]:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkFrame(row, fg_color=C["accent"], width=3, height=2, corner_radius=2).pack(side="left", fill="y", pady=3)
            txt = ctk.CTkFrame(row, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True, padx=(14, 0))
            ctk.CTkLabel(txt, text=title, font=F(LG, "semibold"), text_color=C["ink"]).pack(anchor="w")
            d = ctk.CTkLabel(txt, text=desc, font=F(SM), text_color=C["muted"], justify="left", wraplength=340)
            d.pack(anchor="w")
            self._wrap_left.append(d)

    def _build_right(self):
        right = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        self._right = right
        self.theme_sw = theme_switch(self, self.app)
        self.theme_sw.place(in_=right, relx=1.0, rely=0.0, anchor="ne", x=-24, y=18)
        box = surface(right)
        box.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72)
        self.card = box
        pad = {"padx": 32}

        self.title_lbl = ctk.CTkLabel(box, text="Sign in to your student portal", font=F(H2, "semibold", display=True),
                                      text_color=C["ink"], justify="left", wraplength=400)
        self.title_lbl.pack(anchor="w", pady=(28, 2), **pad)
        self._gaps.append((self.title_lbl, (28, 2), (16, 2)))
        sub = ctk.CTkLabel(box, text="The same enrollment number and password you use on cms.bahria.edu.pk.",
                           font=F(SM), text_color=C["muted"], justify="left", wraplength=400)
        sub.pack(anchor="w", pady=(0, 18), **pad)
        self._wrap_card += [self.title_lbl, sub]
        self._gaps.append((sub, (0, 18), (0, 10)))

        env = self.app.env
        self.enroll = self._field(box, "Enrollment number", "01-123456-001", pad)
        self._gaps.append((self.enroll, (2, 12), (2, 8)))
        if env.get("ENROLLMENT"):
            self.enroll.insert(0, env["ENROLLMENT"])

        ctk.CTkLabel(box, text="Portal password", font=F(SM, "medium"), text_color=C["muted"]).pack(anchor="w", **pad)
        pw_row = ctk.CTkFrame(box, fg_color="transparent")
        pw_row.pack(fill="x", pady=(2, 12), **pad)
        self._gaps.append((pw_row, (2, 12), (2, 8)))
        self.password = ctk.CTkEntry(pw_row, placeholder_text="Password", show="•", height=40, font=F(MD),
                                     fg_color=C["field"], border_color=C["line2"], text_color=C["ink"])
        self.password.pack(side="left", fill="x", expand=True)
        self.show_pw = ctk.CTkCheckBox(pw_row, text="Show", font=F(SM), width=70, text_color=C["muted"],
                                       command=self._toggle_pw)
        self.show_pw.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(box, text="Campus", font=F(SM, "medium"), text_color=C["muted"]).pack(anchor="w", **pad)
        self.campus = ctk.CTkOptionMenu(box, values=CAMPUS_NAMES, height=40, font=F(MD), fg_color=C["field"],
                                        text_color=C["ink"], button_color=C["accent"], button_hover_color=C["accent_h"],
                                        dropdown_font=F(SM))
        self.campus.set(campus_name(env.get("INSTITUTE_ID", "1")))
        self.campus.pack(fill="x", pady=(2, 14), **pad)
        self._gaps.append((self.campus, (2, 14), (2, 10)))

        self.automation = ctk.CTkCheckBox(box, text="Check automatically", font=F(SM), text_color=C["ink"])
        self.automation.select()
        self.automation.pack(anchor="w", **pad)
        note = ctk.CTkLabel(box, text="Daily at 7 PM, at sign-in, and hourly on days something is due.", font=F(XS),
                            text_color=C["dim"], justify="left", wraplength=400)
        note.pack(anchor="w", pady=(0, 14), padx=(32 + 30, 32))
        self._wrap_card.append(note)
        self._gaps.append((note, (0, 14), (0, 10)))

        self.button = primary_button(box, "Connect and start monitoring", self.connect, height=44)
        self.button.pack(fill="x", **pad)
        self.enroll.bind("<Return>", lambda e: self.connect())
        self.password.bind("<Return>", lambda e: self.connect())

        legal = ctk.CTkFrame(box, fg_color="transparent")
        legal.pack(fill="x", pady=(10, 0), **pad)
        self._gaps.append((legal, (10, 0), (6, 0)))
        legal_lbl = ctk.CTkLabel(legal, text="Unofficial app, not affiliated with Bahria University. Use your own account only.",
                                 font=F(XS), text_color=C["dim"], wraplength=440, justify="left")
        legal_lbl.pack(anchor="w")
        self._wrap_card.append(legal_lbl)
        link = ctk.CTkLabel(legal, text="Privacy & terms", font=F(XS, "semibold"), text_color=C["accent"], cursor="hand2")
        link.pack(anchor="w")
        link.bind("<Button-1>", lambda e: open_doc("PRIVACY.md", f"{REPO_URL}/blob/main/PRIVACY.md"))

        self.progress = ctk.CTkProgressBar(box, mode="indeterminate", height=4, progress_color=C["accent"],
                                           fg_color=C["surface2"])
        self.status = ctk.CTkLabel(box, text="", font=F(SM), text_color=C["muted"], wraplength=430, justify="left")
        self.status.pack(anchor="w", pady=(10, 0), **pad)
        self._wrap_card.append(self.status)
        self.console = ctk.CTkTextbox(box, height=90, font=ctk.CTkFont(family=FONTS["mono"], size=XS),
                                      fg_color=C["bg"], text_color=C["muted"], state="disabled")
        ctk.CTkLabel(box, text="", height=12).pack()

    def _field(self, parent, label, placeholder, pad):
        ctk.CTkLabel(parent, text=label, font=F(SM, "medium"), text_color=C["muted"]).pack(anchor="w", **pad)
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder, height=40, font=F(MD), fg_color=C["field"],
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
            env = load_env()
            data = run_sync(headless=True, collect=collectors_for(env), progress=lambda m: self.app.after(0, self.console_write, m))
            s = process_sync(data, env, notify=False)
            items, pending = data.get("assignments", []), range(s["pending"])
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
        ctk.CTkLabel(self, text=f"{greeting}, {first_name}.", font=F(H2, "semibold", display=True),
                     text_color=C["ink"]).pack(anchor="w", pady=(2, 0))
        bits = [meta.get("semester"), f"{len(meta.get('courses', []))} courses" if meta.get("courses") else None,
                campus_name(self.app.env.get("INSTITUTE_ID", "1"))]
        ctk.CTkLabel(self, text="  ·  ".join(b for b in bits if b), font=F(MD), text_color=C["muted"]).pack(anchor="w", pady=(0, 18))

        if self.app.semester_empty:
            empty_semester_box(self, self.app)
            return
        if not data:
            box = surface(self)
            box.pack(fill="x")
            ctk.CTkLabel(box, text="Nothing here yet", font=F(XL, "semibold", display=True), text_color=C["ink"]).pack(pady=(28, 2))
            ctk.CTkLabel(box, text="Press Sync now (or F5) to read your assignments from the LMS.",
                         font=F(MD), text_color=C["muted"]).pack(pady=(0, 28))
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
        self._campus_cards(now)

        box = surface(self)
        box.pack(fill="x", pady=(14, 0))
        heading(box, "Needs your attention", "Unsubmitted work, nearest deadline first").pack(anchor="w", padx=20, pady=(18, 12))
        if not open_items:
            ctk.CTkLabel(box, text="All caught up. Nothing is waiting for a submission.", font=F(LG),
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
            ctk.CTkLabel(cc, text=name_, font=F(MD, "semibold"), text_color=C["ink"], anchor="w", wraplength=250,
                         justify="left").pack(anchor="w", padx=16, pady=(14, 2))
            ratio = c["submitted"] / c["total"] if c["total"] else 0
            ctk.CTkLabel(cc, text=f"{c['submitted']} of {c['total']} submitted" + (f"  ·  {c['open']} pending" if c["open"] else ""),
                         font=F(SM), text_color=C["amber"] if c["open"] else C["muted"]).pack(anchor="w", padx=16)
            bar = ctk.CTkProgressBar(cc, height=4, progress_color=C["green"] if ratio == 1 else C["accent"],
                                     fg_color=C["surface2"], corner_radius=2)
            bar.pack(fill="x", padx=16, pady=(10, 14))
            fill_bar(bar, ratio)
            bind_click(cc, lambda n=name_: self.app.navigate("assignments", course=n))

    def _campus_cards(self, now):
        """Attendance (left) and next exam (right), then the latest announcements. Each card is skipped when
        its tracking is off or nothing has been read yet."""
        env = self.app.env
        att = [c for c in self.app.attendance.values() if c.get("total")]
        exams = self.app.exams if env.get("TRACK_EXAMS", True) else []
        anns = self.app.announcements if env.get("TRACK_ANNOUNCEMENTS", True) else []
        show_att = env.get("TRACK_ATTENDANCE", True) and att
        if env.get("TRACK_TIMETABLE", True) and (self.app.timetable or {}).get("sessions"):
            self._today_card(now)
        if show_att or exams:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", pady=(10, 0))
            row.grid_columnconfigure(0, weight=3, uniform="camp")
            row.grid_columnconfigure(1, weight=2, uniform="camp")
            col = 0
            if show_att:
                card = self._attendance_card(row, att, int(env.get("ATTENDANCE_MIN", 75)))
                card.grid(row=0, column=0, sticky="nsew", padx=(0, 10 if exams else 0))
                col = 1
            if exams:
                self._exam_card(row, exams, now).grid(row=0, column=col, sticky="nsew", columnspan=1 if show_att else 2)
        if anns:
            box = surface(self)
            box.pack(fill="x", pady=(10, 0))
            heading(box, "Latest announcements", "From your course pages on the LMS").pack(anchor="w", padx=20, pady=(18, 10))
            for i, a in enumerate(anns[:3]):
                if i:
                    hairline(box)
                r = ctk.CTkFrame(box, fg_color="transparent")
                r.pack(fill="x", padx=20, pady=9)
                ctk.CTkLabel(r, text=f"{a.get('course', '')}   ·   {rel_time(a.get('posted_at') or a.get('first_seen', ''))}",
                             font=F(XS, "semibold"), text_color=C["accent"], anchor="w").pack(anchor="w")
                ctk.CTkLabel(r, text=a.get("text", ""), font=F(MD), text_color=C["ink"], anchor="w", justify="left",
                             wraplength=820).pack(anchor="w", pady=(2, 0))
            ctk.CTkLabel(box, text="", height=6).pack()
            bind_click(box, lambda: self.app.navigate("announcements"))

    def _today_card(self, now):
        todays = sessions_on((self.app.timetable or {}).get("sessions", []), now.strftime("%a"))
        nowm = now.hour * 60 + now.minute
        nxt = next((x for x in todays if minutes(x["end"]) > nowm), None)
        if not todays:
            sub = "No classes today"
        elif nxt is None:
            sub = f"{len(todays)} class{'es' if len(todays) != 1 else ''}, all done for today"
        elif minutes(nxt["start"]) <= nowm:
            sub = f"Now: {nxt['course']} in {nxt['room']} until {nxt['end']}"
        else:
            sub = f"Next: {nxt['course']} at {nxt['start']} in {nxt['room']}"
        box = surface(self)
        box.pack(fill="x", pady=(10, 0))
        heading(box, f"{now.strftime('%A')}'s classes", sub).pack(anchor="w", padx=20, pady=(18, 10))
        if todays:
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(0, 18))
            for x in todays:
                done = minutes(x["end"]) <= nowm
                live = minutes(x["start"]) <= nowm < minutes(x["end"])
                chip = ctk.CTkFrame(row, fg_color=C["accent"] if live else C["surface2"], corner_radius=10)
                chip.pack(side="left", padx=(0, 8))
                ink = C["on_accent"] if live else (C["dim"] if done else C["ink"])
                sub_ink = C["on_accent"] if live else (C["dim"] if done else C["muted"])
                ctk.CTkLabel(chip, text=f"{x['start']} – {x['end']}", font=F(XS, "semibold"),
                             text_color=sub_ink).pack(anchor="w", padx=12, pady=(8, 0))
                ctk.CTkLabel(chip, text=x.get("abbr") or x["course"][:18], font=F(MD, "semibold"), text_color=ink).pack(anchor="w", padx=12)
                ctk.CTkLabel(chip, text=x.get("room", ""), font=F(XS), text_color=sub_ink).pack(anchor="w", padx=12, pady=(0, 8))
        else:
            ctk.CTkLabel(box, text="", height=8).pack()
        bind_click(box, lambda: self.app.navigate("timetable"))

    def _attendance_card(self, parent, att, minimum):
        card = surface(parent)
        below = [c for c in att if not c.get("ok", True)]
        sub = (f"{len(below)} course{'s' if len(below) != 1 else ''} under {minimum}%" if below
               else f"All courses at or above {minimum}%")
        heading(card, "Attendance", sub).pack(anchor="w", padx=20, pady=(18, 8))
        for c in sorted(att, key=lambda c: c.get("percent", 0))[:5]:
            color, _, _ = att_color(c)
            r = ctk.CTkFrame(card, fg_color="transparent")
            r.pack(fill="x", padx=20, pady=(4, 0))
            top = ctk.CTkFrame(r, fg_color="transparent")
            top.pack(fill="x")
            ctk.CTkLabel(top, text=f"{c.get('code', '')}  {c.get('title', '')}", font=F(SM, "medium"), text_color=C["ink"],
                         anchor="w").pack(side="left")
            ctk.CTkLabel(top, text=f"{c.get('percent', 0):.0f}%", font=F(SM, "semibold"), text_color=color).pack(side="right")
            bar = ctk.CTkProgressBar(r, height=4, progress_color=color, fg_color=C["surface2"], corner_radius=2)
            bar.pack(fill="x", pady=(4, 4))
            fill_bar(bar, min(1.0, c.get("percent", 0) / 100))
        ctk.CTkLabel(card, text="", height=8).pack()
        bind_click(card, lambda: self.app.navigate("attendance"))
        return card

    def _exam_card(self, parent, exams, now):
        up = upcoming_exams(exams, now)
        if up:
            e = up[0]
            key = "today" if e["days"] == 0 else "soon" if e["days"] <= 3 else "week" if e["days"] <= 7 else "later"
            card = surface(parent, fg_color=urgency_tint(key), border_color=urgency_tint(key))
            color = urgency_color(key)
            ctk.CTkLabel(card, text=f"NEXT EXAM  ·  {e.get('exam_type', '').upper()}", font=F(XS, "semibold"),
                         text_color=color).pack(anchor="w", padx=20, pady=(18, 0))
            ctk.CTkLabel(card, text=e["title"], font=F(H3, "semibold", display=True), text_color=C["ink"], wraplength=360,
                         justify="left").pack(anchor="w", padx=20, pady=(2, 2))
            when = e["when"].strftime("%a %d %b  ·  %I:%M %p").replace(" 0", " ")
            ctk.CTkLabel(card, text=when, font=F(MD), text_color=C["muted"]).pack(anchor="w", padx=20)
            if seat_text(e):
                ctk.CTkLabel(card, text=seat_text(e), font=F(SM), text_color=C["muted"]).pack(anchor="w", padx=20, pady=(1, 0))
            ctk.CTkLabel(card, text=countdown(e["days"]), font=F(D1, "semibold", display=True),
                         text_color=color).pack(anchor="w", padx=20, pady=(6, 2))
            more = len(up) - 1
            ctk.CTkLabel(card, text=f"{more} more scheduled" if more else "Last one on the plan", font=F(SM),
                         text_color=C["muted"]).pack(anchor="w", padx=20, pady=(0, 18))
        else:
            card = surface(parent)
            heading(card, "Exams", "No exam is scheduled yet").pack(anchor="w", padx=20, pady=(18, 6))
            pending = sum(1 for e in exams if not e.get("scheduled"))
            ctk.CTkLabel(card, text=f"{pending} paper{'s' if pending != 1 else ''} waiting for a date on the seating plan."
                         if pending else "The seating plan will appear here once the exams section posts it.",
                         font=F(MD), text_color=C["muted"], wraplength=360, justify="left").pack(anchor="w", padx=20, pady=(0, 18))
        bind_click(card, lambda: self.app.navigate("exams"))
        return card

    def _next_deadline(self, item, infos):
        if item is None:
            box = surface(self, fg_color=C["green_t"], border_color=C["green_t"])
            box.pack(fill="x")
            ctk.CTkLabel(box, text="ALL CAUGHT UP", font=F(XS, "semibold"), text_color=C["green"]).pack(anchor="w", padx=20, pady=(18, 0))
            ctk.CTkLabel(box, text="No pending assignments right now.", font=F(H3, "semibold", display=True),
                         text_color=C["ink"]).pack(anchor="w", padx=20, pady=(2, 18))
            return
        info = infos[id(item)]
        color = urgency_color(info["key"])
        box = surface(self, fg_color=urgency_tint(info["key"]), border_color=urgency_tint(info["key"]))
        box.pack(fill="x")
        box.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(box, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=20, pady=18)
        ctk.CTkLabel(left, text="NEXT DEADLINE", font=F(XS, "semibold"), text_color=color).pack(anchor="w")
        ctk.CTkLabel(left, text=item.get("title", ""), font=F(H3, "semibold", display=True), text_color=C["ink"],
                     wraplength=640, justify="left").pack(anchor="w", pady=(2, 2))
        ctk.CTkLabel(left, text=f"{item.get('course', '')}   ·   {fmt_due(item)}", font=F(MD), text_color=C["muted"]).pack(anchor="w")
        right = ctk.CTkFrame(box, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e", padx=20)
        days = info["days"]
        if days is None:
            big = "—"
        elif days == 0:
            big = "Today"
        elif days == 1:
            big = "Tomorrow"
        elif days == -1:
            big = "Yesterday"
        elif days < 0:
            big = f"{-days} days ago"
        else:
            big = f"{days} days"
        ctk.CTkLabel(right, text=big, font=F(D1, "semibold", display=True), text_color=color).pack(anchor="e")
        ctk.CTkLabel(right, text=info["label"], font=F(SM), text_color=C["muted"]).pack(anchor="e")
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
            num = ctk.CTkLabel(inner, text="0", font=F(H1, "semibold", display=True),
                               text_color=C["ink"] if value else C["dim"])
            num.pack(anchor="w")
            count_up(num, value)
            ctk.CTkLabel(inner, text=label, font=F(SM), text_color=C["muted"]).pack(anchor="w")
            bind_click(cell, lambda f=flt: self.app.navigate("assignments", filter_name=f))

    def _attention_row(self, parent, a, info):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=10)
        ctk.CTkFrame(row, fg_color=urgency_color(info["key"]), width=8, height=8, corner_radius=4).pack(side="left", pady=6)
        txt = ctk.CTkFrame(row, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True, padx=(12, 0))
        ctk.CTkLabel(txt, text=a.get("title", ""), font=F(LG, "semibold"), text_color=C["ink"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(txt, text=f"{a.get('course', '')}   ·   {fmt_due(a)}", font=F(SM), text_color=C["muted"], anchor="w").pack(anchor="w")
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
        self.seg = ctk.CTkSegmentedButton(bar, values=FILTERS, font=F(SM, "semibold"), height=34, corner_radius=8,
                                          selected_color=C["accent"], selected_hover_color=C["accent_h"],
                                          unselected_color=C["surface"], unselected_hover_color=C["surface2"],
                                          text_color=C["ink"], fg_color=C["line"], command=self._set_filter)
        self.seg.set("All")
        self.seg.pack(side="left")
        self.search = ctk.CTkEntry(bar, placeholder_text="Search  (Ctrl+F)", height=34, width=180, font=F(SM),
                                   fg_color=C["surface"], border_color=C["line2"], text_color=C["ink"])
        self.search.pack(side="right")
        self.search.bind("<KeyRelease>", lambda e: self._set_query(self.search.get()))
        self.search.bind("<Escape>", lambda e: (self.search.delete(0, "end"), self._set_query("")))
        self.course_menu = ctk.CTkOptionMenu(bar, values=["All courses"], height=34, width=210, font=F(SM),
                                             fg_color=C["surface"], text_color=C["ink"], button_color=C["surface2"],
                                             button_hover_color=C["line2"], dropdown_font=F(SM), command=self._set_course)
        self.course_menu.pack(side="right", padx=(0, 10))
        self.dl_busy = False
        self._rows = []

        sumrow = ctk.CTkFrame(self, fg_color="transparent")
        sumrow.pack(fill="x", pady=(0, 6))
        self.summary = ctk.CTkLabel(sumrow, text="", font=F(SM), text_color=C["muted"], anchor="w")
        self.summary.pack(side="left")
        self.briefs_btn = soft_button(sumrow, "Download briefs", self._download_briefs, width=130)
        self.briefs_btn.pack(side="right")
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
        if self.app.semester_empty:
            self.summary.configure(text="")
            empty_semester_box(self.list, self.app)
            return
        self.summary.configure(text=f"{len(rows)} of {len(data)} assignments")
        self._rows = [a for a, _info in rows]
        if not rows:
            ctk.CTkLabel(self.list, text="Nothing matches this filter.", font=F(LG), text_color=C["dim"]).pack(pady=50)
            return
        box = surface(self.list)
        box.pack(fill="x")
        lazy = Lazy(self.list)
        for i, (a, info) in enumerate(sorted(rows, key=lambda r: sort_key(r[0]))):
            lazy.add(lambda i=i, a=a, info=info: (hairline(box) if i else None, self._row(box, a, info)))
        lazy.start()

    def _row(self, parent, a, info):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=12)
        row.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(row, fg_color=urgency_color(info["key"]), width=8, height=8, corner_radius=4).grid(
            row=0, column=0, rowspan=2, sticky="n", pady=(6, 0), padx=(0, 12))
        ctk.CTkLabel(row, text=a.get("title", ""), font=F(LG, "semibold"), text_color=C["ink"], anchor="w").grid(
            row=0, column=1, sticky="w")
        meta = f"{a.get('course', '')}   ·   #{a.get('assign_no', '')}   ·   Due {fmt_due(a)}"
        if a.get("is_extended") and a.get("original_due_date"):
            meta += f"   ·   extended from {a['original_due_date']}"
        elif a.get("previous_due_date"):
            meta += f"   ·   changed from {a['previous_due_date']}"
        marks = a.get("marks", "")
        if marks and marks.lower() != "not marked yet":
            meta += f"   ·   {marks}"
        ctk.CTkLabel(row, text=meta, font=F(SM), text_color=C["muted"], anchor="w").grid(row=1, column=1, sticky="w", pady=(2, 0))
        # a button per file the portal actually links for this row (brief, your submission, returned work, solution);
        # nothing is shown for a kind the row does not have
        files = {k: v for k, v in (a.get("files") or {}).items() if isinstance(v, dict) and v.get("href")}
        if files:
            fb = ctk.CTkFrame(row, fg_color="transparent")
            fb.grid(row=0, column=2, sticky="e", padx=(12, 0))
            for kind in ("brief", "submission", "returned", "solution"):
                if kind in files:
                    soft_button(fb, FILE_KIND_LABELS[kind], lambda a=a, k=kind: self._download([(a, k)]),
                                width=max(64, 8 * len(FILE_KIND_LABELS[kind]) + 20)).pack(side="left", padx=(6, 0))
        pill(row, info["label"], info["key"]).grid(row=1 if files else 0, column=2, rowspan=1 if files else 2, sticky="e", padx=(12, 0),
                                                   pady=(4, 0) if files else 0)
        hover_lift(row, fg=C["surface2"], border=C["surface2"])

    # -- files: the brief, your submission, returned work, a posted solution
    def _download_briefs(self):
        pairs = [(a, "brief") for a in self._rows if "brief" in (a.get("files") or {})]
        if not pairs:
            self.app.set_status("No assignment in this list has a brief to download.")
            return
        self._download(pairs)

    def _download(self, pairs):
        if self.dl_busy or not pairs:
            return
        self.dl_busy = True
        self.briefs_btn.configure(state="disabled", text="Downloading…")
        dest = lectures_dir(self.app.env)
        self.app.set_status(f"Downloading {len(pairs)} file{'s' if len(pairs) != 1 else ''} to {dest}…")

        def prog(msg, done, tot):
            try:
                self.after(0, lambda: self.app.set_status(f"{done}/{tot}  ·  {msg}"))
            except RuntimeError:
                pass

        def work():
            try:
                res = download_assignment_files(pairs, dest, progress=prog)
            except LoginError as e:
                res = {"saved": [], "skipped": 0, "failed": [("sign-in", str(e))]}
            except Exception as e:
                log.error("Assignment file download failed: %s", e)
                res = {"saved": [], "skipped": 0, "failed": [("download", str(e)[:200])]}
            try:
                self.after(0, self._download_done, res, dest, pairs)
            except RuntimeError:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _download_done(self, res, dest, pairs):
        self.dl_busy = False
        self.briefs_btn.configure(state="normal", text="Download briefs")
        saved, skipped, failed = len(res["saved"]), res["skipped"], res["failed"]
        bits = [f"{saved} file{'s' if saved != 1 else ''} saved"]
        if skipped:
            bits.append(f"{skipped} already there")
        if failed:
            bits.append(f"{len(failed)} failed")
        self.app.set_status("Assignment files: " + ", ".join(bits))
        if failed:
            messagebox.showwarning(APP_NAME, "Some files could not be downloaded:\n\n" +
                                   "\n".join(f"- {n}: {why}" for n, why in failed[:8]))
        elif saved or skipped:
            try:
                from lms_scraper import assignment_folder
                folder = assignment_folder(dest, pairs[0][0]) if len({a["id"] for a, _k in pairs}) == 1 else dest
                os.startfile(folder if folder.exists() else dest)
            except OSError:
                pass


# ---------------------------------------------------------------------------- attendance
ATT_FILTERS = ["All", "Under minimum", "At risk", "On track"]
ATT_VIEWS = ["Summary", "All classes", "Missed only"]


class AttendanceView(ctk.CTkFrame):
    """Every registered course in one list, weakest first. Filter by standing (all, under the minimum, at risk, on
    track); click a course for its classes, or switch the whole page to every class or only the missed ones."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.filter_name = "All"
        self.mode = "Summary"
        self.expanded = set()

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(2, 10))
        seg_style = dict(font=F(SM, "semibold"), height=34, corner_radius=8, selected_color=C["accent"],
                         selected_hover_color=C["accent_h"], unselected_color=C["surface"],
                         unselected_hover_color=C["surface2"], text_color=C["ink"], fg_color=C["line"])
        self.seg = ctk.CTkSegmentedButton(bar, values=ATT_FILTERS, command=self._set_filter, **seg_style)
        self.seg.set("All")
        self.seg.pack(side="left")
        self.mode_seg = ctk.CTkSegmentedButton(bar, values=ATT_VIEWS, command=self._set_mode, **seg_style)
        self.mode_seg.set("Summary")
        self.mode_seg.pack(side="right")

        self.summary = ctk.CTkLabel(self, text="", font=F(SM), text_color=C["muted"], anchor="w")
        self.summary.pack(fill="x", pady=(0, 6))
        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.pack(fill="both", expand=True)

    def apply(self, filter_name=None, mode=None):
        if filter_name in ATT_FILTERS:
            self.filter_name = filter_name
            self.seg.set(filter_name)
        if mode in ATT_VIEWS:
            self.mode = mode
            self.mode_seg.set(mode)
        self.refresh()

    def _set_filter(self, v):
        self.filter_name = v
        self.refresh()

    def _set_mode(self, v):
        self.mode = v
        self.refresh()

    def refresh(self):
        for w in self.list.winfo_children():
            w.destroy()
        try:
            self.list._parent_canvas.yview_moveto(0)
        except Exception:
            pass
        env = self.app.env
        minimum = int(env.get("ATTENDANCE_MIN", 75))
        if not env.get("TRACK_ATTENDANCE", True):
            self.summary.configure(text="")
            self._empty("Attendance tracking is off", "Turn it on in Settings → Campus tracking and sync again.")
            return
        if self.app.semester_empty:
            self.summary.configure(text="")
            empty_semester_box(self.list, self.app)
            return
        att = sorted(self.app.attendance.values(), key=lambda c: (c.get("total", 0) == 0, c.get("percent", 0)))
        if not att:
            self.summary.configure(text="")
            self._empty("No attendance yet", "Press Sync now (or F5). Attendance is read from the CMS with every check.")
            return
        with_hours = [c for c in att if c.get("total")]
        standing = {id(c): att_color(c)[2] for c in att}
        counts = {k: sum(1 for c in with_hours if standing[id(c)] == k) for k in ATT_FILTERS[1:]}
        shown = att if self.filter_name == "All" else [c for c in with_hours if standing[id(c)] == self.filter_name]
        total_present = sum(c.get("present", 0) for c in with_hours)
        total_hours = sum(c.get("total", 0) for c in with_hours)
        overall = total_present / total_hours * 100 if total_hours else 0
        bits = [f"{len(att)} courses" if self.filter_name == "All" else f"{len(shown)} of {len(att)} courses",
                f"overall {overall:.0f}%", f"{counts['Under minimum']} under {minimum}%", f"{counts['At risk']} at risk",
                f"{sum(c.get('absent', 0) for c in with_hours):g} of {total_hours:g} hours missed",
                f"minimum {minimum}% (Settings)"]
        self.summary.configure(text="   ·   ".join(bits))
        if not shown:
            self._empty(f"No course is {self.filter_name.lower()}", "Pick another filter to see the rest.")
            return
        lazy = Lazy(self.list)
        for c in shown:
            lazy.add(lambda c=c: self._course(c, minimum))
        lazy.start()

    def _empty(self, title, sub):
        box = surface(self.list)
        box.pack(fill="x")
        ctk.CTkLabel(box, text=title, font=F(XL, "semibold", display=True), text_color=C["ink"]).pack(pady=(28, 2))
        ctk.CTkLabel(box, text=sub, font=F(MD), text_color=C["muted"]).pack(pady=(0, 28))

    def _course(self, c, minimum):
        color, tint, label = att_color(c)
        code = c.get("code", "")
        sessions = c.get("sessions") or []
        missed = [x for x in sessions if x.get("absent")]
        opened = self.mode != "Summary" or code in self.expanded
        box = surface(self.list, hover=True)
        box.pack(fill="x", pady=(0, 8))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(12, 12))
        row.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(left, text=f"{code}  ·  {c.get('title', '')}", font=F(LG, "semibold"), text_color=C["ink"],
                     anchor="w").pack(anchor="w")
        ch = str(c.get("credit_hours", "") or "")
        credits = f"{ch} credit hour{'' if ch == '1' else 's'}" if ch else ""
        meta = [b for b in (c.get("teacher", ""), c.get("class", ""), credits) if b]
        if sessions:
            meta.append(f"{len(sessions)} classes" + (f", {len(missed)} missed" if missed else ""))
        ctk.CTkLabel(left, text="   ·   ".join(meta), font=F(SM), text_color=C["muted"], anchor="w").pack(anchor="w", pady=(1, 0))

        if c.get("total"):
            mid = ctk.CTkFrame(row, fg_color="transparent")
            mid.grid(row=0, column=1, padx=(18, 18))
            bar = ctk.CTkProgressBar(mid, width=200, height=6, progress_color=color, fg_color=C["surface2"], corner_radius=3)
            bar.pack(anchor="w", pady=(6, 4))
            fill_bar(bar, min(1.0, c.get("percent", 0) / 100))
            if c.get("ok", True):
                margin = f"Present {c.get('present', 0):g} of {c.get('total', 0):g} h  ·  can miss {c.get('can_miss', 0):g} h"
            else:
                margin = f"Present {c.get('present', 0):g} of {c.get('total', 0):g} h  ·  need {c.get('need', 0):g} h straight"
            if c.get("new_absent_hours"):
                margin += f"  ·  {c['new_absent_hours']:g} h new"
            ctk.CTkLabel(mid, text=margin, font=F(XS), text_color=C["muted"], anchor="w").pack(anchor="w")
            right = ctk.CTkFrame(row, fg_color="transparent")
            right.grid(row=0, column=2, sticky="e")
            ctk.CTkLabel(right, text=f"{c.get('percent', 0):.1f}%", font=F(H2, "semibold", display=True), text_color=color).pack(anchor="e")
            pill(right, label, color).pack(anchor="e")
        else:
            ctk.CTkLabel(row, text="No classes yet", font=F(SM), text_color=C["dim"]).grid(row=0, column=2, sticky="e")

        if self.mode == "Summary":
            bind_click(box, lambda k=code: self._toggle(k), lift=False)
        if not opened:
            return
        hairline(box, padx=18)
        rows = missed if self.mode == "Missed only" else sessions
        if not sessions:
            ctk.CTkLabel(box, text="No class record yet. It is read with the next sync.", font=F(SM), text_color=C["dim"],
                         anchor="w").pack(anchor="w", padx=18, pady=12)
            return
        if not rows:
            ctk.CTkLabel(box, text="No classes missed.", font=F(SM), text_color=C["green"], anchor="w").pack(anchor="w", padx=18, pady=12)
            return
        tbl = ctk.CTkFrame(box, fg_color="transparent")
        tbl.pack(fill="x", padx=18, pady=(4, 10))
        for i, x in enumerate(reversed(rows)):
            if i:
                hairline(tbl, padx=0)
            r = ctk.CTkFrame(tbl, fg_color="transparent")
            r.pack(fill="x", pady=6)
            r.grid_columnconfigure(1, weight=1)
            absent = bool(x.get("absent"))
            ctk.CTkFrame(r, fg_color=C["red"] if absent else C["green"], width=8, height=8, corner_radius=4).grid(
                row=0, column=0, rowspan=2, sticky="n", pady=(6, 0), padx=(0, 12))
            d = session_date(x.get("date", ""))
            when = d.strftime("%a %d %b") if d else x.get("date", "")
            ctk.CTkLabel(r, text="   ·   ".join(b for b in (when, x.get("type", ""), x.get("room", "")) if b),
                         font=F(SM, "medium"), text_color=C["ink"], anchor="w").grid(row=0, column=1, sticky="w")
            if x.get("topics"):
                ctk.CTkLabel(r, text=x["topics"], font=F(SM), text_color=C["muted"], anchor="w", justify="left",
                             wraplength=700).grid(row=1, column=1, sticky="w")
            tag = f"Absent {x.get('absent', 0):g} h" if absent else f"Present {x.get('present', 0):g} h"
            pill(r, tag, "missed" if absent else "submitted").grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))

    def _toggle(self, code):
        if code in self.expanded:
            self.expanded.discard(code)
        else:
            self.expanded.add(code)
        self.refresh()


# ---------------------------------------------------------------------------- timetable
class TimetableView(ctk.CTkFrame):
    """The week as the app draws it (the same picture the exports use), fitted to the window, with Save buttons."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._light = self._dark = None
        self._img = None
        self._last_w = 0
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(2, 8))
        self.summary = ctk.CTkLabel(bar, text="", font=F(SM), text_color=C["muted"], anchor="w")
        self.summary.pack(side="left")
        self.save_bar = ctk.CTkFrame(bar, fg_color="transparent")        # shown only when there is a timetable to save
        soft_button(self.save_bar, "Save as PDF", lambda: self._save("pdf"), width=110).pack(side="right")
        soft_button(self.save_bar, "Save as JPG", lambda: self._save("jpg"), width=110).pack(side="right", padx=(0, 8))
        soft_button(self.save_bar, "Save as PNG", lambda: self._save("png"), width=110).pack(side="right", padx=(0, 8))
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)
        self.pic = ctk.CTkLabel(self.scroll, text="")
        self.empty = ctk.CTkLabel(self.scroll, text="", font=F(LG), text_color=C["dim"], wraplength=700)
        self.scroll.bind("<Configure>", lambda e: self.after(80, self._fit), add="+")

    def _student(self):
        sessions = (self.app.timetable or {}).get("sessions", [])
        return sessions[0].get("class", "") if sessions else ""

    def refresh(self):
        env = self.app.env
        data = self.app.timetable or {}
        sessions = data.get("sessions", [])
        self.pic.pack_forget()
        self.empty.pack_forget()
        self.save_bar.pack_forget()
        self._light = self._dark = None
        if not env.get("TRACK_TIMETABLE", True):
            self.summary.configure(text="The timetable is not being read (Settings → Campus tracking).")
            self.empty.configure(text="Turn it on in Settings → Campus tracking and sync again.")
            self.empty.pack(pady=50)
            return
        if self.app.semester_empty:
            self.summary.configure(text="")
            self.empty.configure(text="No courses registered yet. " + self.app.empty_semester_text())
            self.empty.pack(pady=50)
            return
        if not sessions:
            self.summary.configure(text="")
            self.empty.configure(text="No timetable yet. Press Sync now (or F5); it is read from the CMS with every check.")
            self.empty.pack(pady=50)
            return
        days = {x["day"] for x in sessions}
        bits = [data.get("semester", ""), f"{len(sessions)} classes a week over {len(days)} days",
                f"read {rel_time(data['read_at'])}" if data.get("read_at") else ""]
        self.summary.configure(text="   ·   ".join(b for b in bits if b))
        self._light = render_timetable(data, "light", scale=2, student=self._student())
        self._dark = render_timetable(data, "dark", scale=2, student=self._student())
        self._last_w = 0
        self.save_bar.pack(side="right")
        self.pic.pack(anchor="w")
        self._fit()

    def _fit(self):
        if self._light is None:
            return
        w = max(640, self.scroll.winfo_width() - 20)
        if abs(w - self._last_w) < 6:
            return
        self._last_w = w
        h = int(self._light.height * w / self._light.width)
        self._img = ctk.CTkImage(light_image=self._light, dark_image=self._dark, size=(w, h))
        self.pic.configure(image=self._img)

    def _save(self, fmt):
        data = self.app.timetable or {}
        if not data.get("sessions"):
            return
        sem = (data.get("semester") or "timetable").replace("/", "-")
        path = filedialog.asksaveasfilename(title="Save timetable", defaultextension=f".{fmt}",
                                            initialfile=f"Timetable {sem}.{fmt}", filetypes=[(fmt.upper(), f"*.{fmt}")])
        if not path:
            return
        try:
            save_timetable(data, path, "dark" if self.app.theme == "dark" else "light", student=self._student())
            self.app.status_lbl.configure(text=f"Saved {os.path.basename(path)}")
            os.startfile(path)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not save the timetable:\n{e}")


# ---------------------------------------------------------------------------- exams
class ExamsView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

    def refresh(self):
        for w in self.winfo_children():
            w.destroy()
        env = self.app.env
        exams = self.app.exams
        if not env.get("TRACK_EXAMS", True):
            self._empty("Exam tracking is off", "Turn it on in Settings → Campus tracking and sync again.")
            return
        if self.app.semester_empty:
            empty_semester_box(self, self.app)
            return
        if not exams:
            self._empty("No exam schedule yet", "Press Sync now (or F5). The seating plan is read from the CMS with every check.")
            return
        now = datetime.now()
        up = upcoming_exams(exams, now)
        past = [e for e in exams if e.get("scheduled") and e not in up and e["id"] not in {u["id"] for u in up}]
        unscheduled = [e for e in exams if not e.get("scheduled")]
        defaulter = [e for e in exams if e.get("fee_defaulter")]
        if defaulter:
            warn = surface(self, fg_color=C["red_t"], border_color=C["red_t"])
            warn.pack(fill="x", pady=(2, 10))
            ctk.CTkLabel(warn, text="The portal marks you as a fee defaulter for some papers. "
                                    "Clear it with the accounts office before the exam.",
                         font=F(MD, "medium"), text_color=C["red"], wraplength=820, justify="left").pack(anchor="w", padx=20, pady=14)
        ctk.CTkLabel(self, text="Check class, session and room on the portal before each paper; the exams section can move them.",
                     font=F(SM), text_color=C["muted"], anchor="w").pack(fill="x", pady=(2, 8))
        if up:
            box = surface(self)
            box.pack(fill="x", pady=(0, 10))
            heading(box, "Upcoming", f"{len(up)} paper{'s' if len(up) != 1 else ''} on the seating plan").pack(
                anchor="w", padx=20, pady=(18, 8))
            for i, e in enumerate(up):
                if i:
                    hairline(box)
                self._row(box, e)
            ctk.CTkLabel(box, text="", height=6).pack()
        if unscheduled:
            box = surface(self)
            box.pack(fill="x", pady=(0, 10))
            heading(box, "Not scheduled yet", "These papers have no date on the plan").pack(anchor="w", padx=20, pady=(18, 8))
            for i, e in enumerate(unscheduled):
                if i:
                    hairline(box)
                r = ctk.CTkFrame(box, fg_color="transparent")
                r.pack(fill="x", padx=20, pady=9)
                ctk.CTkLabel(r, text=e["title"], font=F(MD, "medium"), text_color=C["ink"], anchor="w").pack(side="left")
                ctk.CTkLabel(r, text=f"{e.get('exam_type', '')}   ·   {e.get('class', '')}", font=F(SM),
                             text_color=C["muted"]).pack(side="right")
            ctk.CTkLabel(box, text="", height=6).pack()
        if past:
            box = surface(self)
            box.pack(fill="x", pady=(0, 10))
            heading(box, "Done", f"{len(past)} paper{'s' if len(past) != 1 else ''} already held").pack(anchor="w", padx=20, pady=(18, 8))
            for i, e in enumerate(sorted(past, key=lambda x: x.get("date", ""), reverse=True)):
                if i:
                    hairline(box)
                r = ctk.CTkFrame(box, fg_color="transparent")
                r.pack(fill="x", padx=20, pady=9)
                ctk.CTkLabel(r, text=e["title"], font=F(MD, "medium"), text_color=C["muted"], anchor="w").pack(side="left")
                ctk.CTkLabel(r, text=f"{e.get('date', '')}   ·   {e.get('start_time', '')}", font=F(SM),
                             text_color=C["dim"]).pack(side="right")
            ctk.CTkLabel(box, text="", height=6).pack()

    def _empty(self, title, sub):
        box = surface(self)
        box.pack(fill="x")
        ctk.CTkLabel(box, text=title, font=F(XL, "semibold", display=True), text_color=C["ink"]).pack(pady=(28, 2))
        ctk.CTkLabel(box, text=sub, font=F(MD), text_color=C["muted"]).pack(pady=(0, 28))

    def _row(self, parent, e):
        key = "today" if e["days"] == 0 else "soon" if e["days"] <= 3 else "week" if e["days"] <= 7 else "later"
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=20, pady=12)
        date_box = ctk.CTkFrame(r, fg_color=urgency_tint(key), corner_radius=10, width=64)
        date_box.pack(side="left")
        ctk.CTkLabel(date_box, text=e["when"].strftime("%d"), font=F(H2, "semibold", display=True),
                     text_color=urgency_color(key), width=64).pack(pady=(8, 0))
        ctk.CTkLabel(date_box, text=e["when"].strftime("%b").upper(), font=F(XS, "semibold"),
                     text_color=urgency_color(key)).pack(pady=(0, 8))
        body = ctk.CTkFrame(r, fg_color="transparent")
        body.pack(side="left", fill="x", expand=True, padx=(14, 0))
        ctk.CTkLabel(body, text=e["title"], font=F(LG, "semibold"), text_color=C["ink"], anchor="w").pack(anchor="w")
        when = e["when"].strftime("%A  ·  %I:%M %p").replace("  0", "  ")
        bits = [when, e.get("session", ""), seat_text(e), e.get("exam_type", "")]
        ctk.CTkLabel(body, text="   ·   ".join(b for b in bits if b), font=F(SM), text_color=C["muted"],
                     anchor="w").pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(body, text=e.get("class", ""), font=F(XS), text_color=C["dim"], anchor="w").pack(anchor="w")
        pill(r, countdown(e["days"]), key).pack(side="right")


# ---------------------------------------------------------------------------- results
def grade_color(grade: str) -> str:
    g = (grade or "").upper()
    if g.startswith("A"):
        return C["green"]
    if g.startswith("B"):
        return C["accent"]
    if g.startswith("C"):
        return C["amber"]
    return C["red"]


def grade_menu(parent, values, current, command, width=86):
    m = ctk.CTkOptionMenu(parent, values=values, width=width, height=30, font=F(SM), fg_color=C["field"],
                          button_color=C["line2"], button_hover_color=C["line2"], text_color=C["ink"],
                          dropdown_fg_color=C["surface"], dropdown_text_color=C["ink"], dropdown_hover_color=C["surface2"],
                          dropdown_font=F(SM), command=command)
    m.set(current)
    return m


class ResultsView(ctk.CTkFrame):
    """The transcript one semester at a time. A strip with the cumulative figures, a semester picker (newest
    first), and below it the chosen semester: for the running one, the calculator (the grade you expect in each
    course, a target CGPA and what it takes, same-grade scenarios); for a past one, the grades with the portal's
    GPA and CGPA and a "Try other grades" mode to see how a different grade would have moved the CGPA. Nothing
    is saved; Reset puts the real transcript back."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.picks = {}          # running semester: course code -> grade
        self.overrides = {}      # past semesters: (semester, code) -> grade
        self.trying = set()      # past semesters showing grade menus
        self.target = "3.50"
        self.selected = None     # semester name
        self.strip = None
        self.seg = None
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")

    # -- model
    def _base(self):
        return (self.app.results or {}).get("semesters") or []

    def _model(self):
        return apply_overrides(self._base(), self.overrides)

    def _dirty(self):
        return bool(self.picks or self.overrides)

    def _label(self, sem):
        compact = len(self._base()) > 8          # many semesters: names only, so the bar fits the window
        if not sem.get("complete"):
            return sem["name"] if compact else f"{sem['name']}  ·  now"
        return f"{sem['name']}  ·  {sem['gpa']:.2f}" if sem.get("gpa") is not None and not compact else sem["name"]

    # -- page
    def refresh(self):
        outer = getattr(self.body, "_parent_frame", self.body)    # a scrollable frame packs its outer frame
        for w in self.winfo_children():
            if w is not outer:
                w.destroy()
        for w in self.body.winfo_children():
            w.destroy()
        self.body.pack_forget()
        env = self.app.env
        semesters = self._base()
        if not env.get("TRACK_RESULTS", True):
            self._empty("Results tracking is off", "Turn it on in Settings → Campus tracking and sync again.")
            return
        if not semesters:
            self._empty("No results yet", "Press Sync now (or F5). The transcript is read from the CMS Provisional Result page "
                                          "with every check.")
            return
        names = [x["name"] for x in semesters]
        if self.selected not in names:
            self.selected = names[-1]
        self._stats((self.app.results or {}).get("student") or {})
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        labels = [self._label(x) for x in reversed(semesters)]
        self._by_label = {self._label(x): x["name"] for x in semesters}
        self.seg = ctk.CTkSegmentedButton(bar, values=labels, command=self._choose, font=F(SM, "semibold"), height=34,
                                          corner_radius=8, selected_color=C["accent"], selected_hover_color=C["accent_h"],
                                          unselected_color=C["surface"], unselected_hover_color=C["surface2"],
                                          text_color=C["ink"], fg_color=C["line"])
        self.seg.set(self._label(next(x for x in semesters if x["name"] == self.selected)))
        self.seg.pack(side="left")
        self.hint = ctk.CTkLabel(self, text="", font=F(SM), text_color=C["muted"], anchor="w")
        self.hint.pack(fill="x", pady=(0, 8))
        self.body.pack(fill="both", expand=True)
        self._show_semester()

    def _choose(self, label):
        self.selected = self._by_label.get(label, self.selected)
        self._show_semester()

    def _show_semester(self):
        for w in self.body.winfo_children():
            w.destroy()
        try:
            self.body._parent_canvas.yview_moveto(0)
        except Exception:
            pass
        self.sem_sub, self.pts_lbls, self.pill_lbls, self.scen_lbls = {}, {}, {}, {}
        self.proj_lbl = self.need_lbl = self.target_entry = self.scen_caption = None
        sem = next(x for x in self._base() if x["name"] == self.selected)
        if sem.get("complete"):
            self.hint.configure(text="Try other grades shows how a different grade in this semester would have moved the CGPA; "
                                     "nothing is saved.")
            self._past(sem)
        else:
            self.hint.configure(text="This semester is running: choose the grades you expect and watch the GPA, the CGPA and "
                                     "the target line.")
            self._running(sem)
        self._recompute()

    # -- pieces
    def _empty(self, title, sub):
        box = surface(self)
        box.pack(fill="x")
        ctk.CTkLabel(box, text=title, font=F(XL, "semibold", display=True), text_color=C["ink"]).pack(pady=(28, 2))
        ctk.CTkLabel(box, text=sub, font=F(MD), text_color=C["muted"], wraplength=720).pack(pady=(0, 28))

    def _stats(self, student):
        strip = surface(self)
        strip.pack(fill="x", pady=(2, 10))
        since = f" · since {student['intake_semester']}" if student.get("intake_semester") else ""
        labels = [("CGPA", "over every graded semester"), ("Credits earned", "earned / attempted"),
                  ("Semesters graded", student.get("program", "") + since)]
        self.stat_vals, self.stat_subs = [], []
        for i, (label, sub) in enumerate(labels):
            strip.grid_columnconfigure(i, weight=1, uniform="res")
            cell = ctk.CTkFrame(strip, fg_color="transparent")
            cell.grid(row=0, column=i, sticky="nsew", padx=(20, 10), pady=18)
            ctk.CTkLabel(cell, text=label.upper(), font=F(XS, "semibold"), text_color=C["muted"], anchor="w").pack(anchor="w")
            v = ctk.CTkLabel(cell, text="—", font=F(D1, "semibold", display=True), text_color=C["ink"], anchor="w")
            v.pack(anchor="w", pady=(2, 0))
            sl = ctk.CTkLabel(cell, text=sub, font=F(SM), text_color=C["dim"], anchor="w", wraplength=260, justify="left")
            sl.pack(anchor="w")
            self.stat_vals.append(v)
            self.stat_subs.append(sl)
        strip.grid_columnconfigure(3, weight=0)
        self.reset_btn = soft_button(strip, "Reset what-ifs", self._reset, width=130)
        self.reset_btn.grid(row=0, column=3, sticky="ne", padx=(0, 20), pady=18)

    def _course_row(self, parent, c, right):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=20, pady=7)
        ctk.CTkLabel(r, text=c["title"], font=F(MD, "medium"), text_color=C["ink"], anchor="w").pack(side="left")
        ctk.CTkLabel(r, text=f"{c['code']}  ·  {c['credits']:g} cr", font=F(SM), text_color=C["muted"]).pack(side="left", padx=(12, 0))
        right(r)
        return r

    def _running(self, sem):
        box = surface(self.body)
        box.pack(fill="x", pady=(0, 10))
        heading(box, f"{sem['name']}: the grade you expect", "Pick a grade per course; the projection, the scenarios and the "
                                                              "target line update as you go.").pack(anchor="w", padx=20, pady=(18, 8))
        self.proj_lbl = ctk.CTkLabel(box, text="", font=F(LG, "semibold", display=True), text_color=C["ink"], anchor="w",
                                     wraplength=820, justify="left")
        self.proj_lbl.pack(anchor="w", padx=20, pady=(4, 2))
        self.scen_caption = ctk.CTkLabel(box, text="", font=F(SM), text_color=C["muted"], anchor="w", wraplength=820, justify="left")
        self.scen_caption.pack(anchor="w", padx=20, pady=(8, 2))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(2, 6))
        for g in GRADES:
            cell = ctk.CTkFrame(row, fg_color=C["surface2"], corner_radius=10)
            cell.pack(side="left", padx=(0, 6), pady=2)
            ctk.CTkLabel(cell, text=g, font=F(XS, "semibold"), text_color=grade_color(g), width=44).pack(pady=(5, 0))
            lbl = ctk.CTkLabel(cell, text="—", font=F(SM, "semibold"), text_color=C["ink"], width=44)
            lbl.pack(pady=(0, 5))
            self.scen_lbls[g] = lbl
        tr = ctk.CTkFrame(box, fg_color="transparent")
        tr.pack(fill="x", padx=20, pady=(10, 14))
        ctk.CTkLabel(tr, text="To finish the semester with a CGPA of", font=F(MD), text_color=C["muted"]).pack(side="left")
        self.target_entry = ctk.CTkEntry(tr, width=72, height=30, font=F(MD), fg_color=C["field"], border_color=C["line2"],
                                         text_color=C["ink"], justify="center")
        self.target_entry.insert(0, self.target)
        self.target_entry.pack(side="left", padx=8)
        self.target_entry.bind("<KeyRelease>", lambda e: self._recompute())
        self.need_lbl = ctk.CTkLabel(tr, text="", font=F(MD), text_color=C["muted"], anchor="w", wraplength=560, justify="left")
        self.need_lbl.pack(side="left", fill="x", expand=True)
        hairline(box)
        for i, c in enumerate(sem["courses"]):
            if i:
                hairline(box)
            if c.get("grade"):
                def posted(r, c=c):
                    pill(r, c["grade"], grade_color(c["grade"])).pack(side="right")
                    ctk.CTkLabel(r, text="posted", font=F(SM), text_color=C["dim"]).pack(side="right", padx=(0, 10))
                self._course_row(box, c, posted)
            else:
                self._course_row(box, c, lambda r, c=c: grade_menu(r, ["—"] + GRADES, self.picks.get(c["code"], "—"),
                                                                   lambda g, code=c["code"]: self._pick(code, g)).pack(side="right"))
        ctk.CTkLabel(box, text="", height=6).pack()

    def _past(self, sem):
        box = surface(self.body)
        box.pack(fill="x", pady=(0, 10))
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(18, 8))
        h = heading(head, sem["name"], "")
        h.pack(side="left")
        self.sem_sub[sem["name"]] = [w for w in h.winfo_children() if isinstance(w, ctk.CTkLabel)][-1]
        trying = sem["name"] in self.trying
        soft_button(head, "Done trying" if trying else "Try other grades", lambda n=sem["name"]: self._toggle_try(n),
                    width=140).pack(side="right")
        for i, c in enumerate(sem["courses"]):
            if i:
                hairline(box)
            key = (sem["name"], c["code"])
            shown = self.overrides.get(key, c["grade"])

            def right(r, c=c, key=key, shown=shown):
                if trying:
                    grade_menu(r, GRADES, shown, lambda g, k=key, actual=c["grade"]: self._override(k, actual, g),
                               width=78).pack(side="right")
                else:
                    pl = pill(r, shown, grade_color(shown))
                    pl.pack(side="right")
                    self.pill_lbls[key] = pl
                pts = ctk.CTkLabel(r, text="", font=F(SM), text_color=C["dim"])
                pts.pack(side="right", padx=(0, 10))
                self.pts_lbls[key] = (pts, c)
            self._course_row(box, c, right)
        ctk.CTkLabel(box, text="", height=6).pack()

    # -- interaction
    def _pick(self, code, grade):
        if grade == "—":
            self.picks.pop(code, None)
        else:
            self.picks[code] = grade
        self._recompute()

    def _override(self, key, actual, grade):
        if grade == actual:
            self.overrides.pop(key, None)
        else:
            self.overrides[key] = grade
        self._recompute()

    def _toggle_try(self, name):
        if name in self.trying:
            self.trying.discard(name)
        else:
            self.trying.add(name)
        self._show_semester()

    def _reset(self):
        self.picks, self.overrides, self.trying = {}, {}, set()
        self.refresh()

    def _recompute(self):
        base, sems = self._base(), self._model()
        t0 = totals([x for x in base if x.get("complete")])
        t = totals([x for x in sems if x.get("complete")])
        changed = bool(self.overrides) and t["cgpa"] != t0["cgpa"]
        self.stat_vals[0].configure(text=f"{t['cgpa']:.2f}" if t["cgpa"] is not None else "—",
                                    text_color=C["accent"] if changed else C["ink"])
        self.stat_subs[0].configure(text=f"was {t0['cgpa']:.2f}: with your changes" if changed else "over every graded semester")
        self.stat_vals[1].configure(text=f"{t['earned']:g} / {t['credits']:g}")
        self.stat_vals[2].configure(text=str(sum(1 for x in base if x.get("complete"))))
        if self._dirty():
            self.reset_btn.grid()
        else:
            self.reset_btn.grid_remove()
        by_name = {x["name"]: x for x in sems}
        for name, lbl in self.sem_sub.items():
            orig = next(x for x in base if x["name"] == name)
            was = orig["gpa"] if orig.get("gpa") is not None else gpa_of(orig["courses"])
            now = gpa_of(by_name[name]["courses"])
            txt = f"GPA {was:.2f}" if was is not None else "GPA —"
            if now is not None and was is not None and abs(now - was) >= 0.005:
                txt = f"GPA {was:.2f} → {now:.2f} with your changes"
            elif orig.get("cgpa") is not None:
                txt += f"   ·   CGPA {orig['cgpa']:.2f} at the time"
            lbl.configure(text=txt)
        for key, (pts, c) in self.pts_lbls.items():
            g = self.overrides.get(key, c["grade"])
            pts.configure(text=f"{grade_points_of(g, c):g} pts")
            if key in self.pill_lbls:
                self.pill_lbls[key].configure(text=f"  {g}  ", text_color=grade_color(g))
        if self.proj_lbl is None:
            return
        pr = project(sems, self.picks)
        if pr["picked"]:
            txt = f"Projected GPA {pr['gpa']:.2f}   ·   CGPA {pr['cgpa']:.2f}"
            if pr["picked"] < pr["of"]:
                txt += f"   ·   {pr['picked']} of {pr['of']} courses picked; the rest are left out"
        else:
            txt = "Pick a grade to see the projected GPA and CGPA."
        self.proj_lbl.configure(text=txt)
        left = pr["of"] - pr["picked"]
        if not pr["picked"]:
            cap = "If every course ends with the same grade, the CGPA lands at:"
        elif left:
            head = f"If the {left} course not picked yet ends" if left == 1 else f"If the {left} courses not picked yet end"
            cap = head + " with the same grade, the CGPA lands at:"
        else:
            cap = "Every course is picked; the scenarios below use your picks:"
        self.scen_caption.configure(text=cap)
        for x in uniform_scenarios(sems, self.picks):
            self.scen_lbls[x["grade"]].configure(text=f"{x['cgpa']:.2f}" if x["cgpa"] is not None else "—")
        raw = (self.target_entry.get() or "").strip()
        try:
            target = float(raw)
            self.target = raw
        except ValueError:
            self.need_lbl.configure(text="")
            return
        need = required_gpa(sems, target)
        gn = grade_needed(sems, self.picks, target)
        if need is None:
            self.need_lbl.configure(text="")
        elif need <= 0 or (gn["remaining"] == 0 and gn["reached"]) or gn["grade"] == "F":
            if gn["remaining"] == 0:
                txt = "you are already there with the grades you picked"
            elif self.picks:
                txt = "you are already there, whatever the other courses bring"
            else:
                txt = "you are already there, whatever this semester brings"
            self.need_lbl.configure(text=txt, text_color=C["green"])
        elif not gn["reached"]:
            best = f"{gn['best']:.2f}" if gn["best"] is not None else "—"
            self.need_lbl.configure(text=f"not reachable this semester: a GPA of {need:.2f} would be needed, and straight A's "
                                         f"{'in the rest ' if self.picks else ''}end at {best}", text_color=C["red"])
        else:
            where = f"in each of the {gn['remaining']} courses not picked yet" if self.picks else "in every course"
            self.need_lbl.configure(text=f"you need a GPA of {need:.2f} this semester: at least {gn['grade']} {where}", text_color=C["ink"])


def grade_points_of(grade, course):
    from results import GRADE_POINTS
    return GRADE_POINTS.get(grade, course.get("points") or 0)


# ---------------------------------------------------------------------------- announcements
class AnnouncementsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.course = "All courses"
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(2, 10))
        self.summary = ctk.CTkLabel(bar, text="", font=F(SM), text_color=C["muted"], anchor="w")
        self.summary.pack(side="left")
        self.course_menu = ctk.CTkOptionMenu(bar, values=["All courses"], height=34, width=260, font=F(SM),
                                             fg_color=C["surface"], text_color=C["ink"], button_color=C["surface2"],
                                             button_hover_color=C["line2"], dropdown_font=F(SM), command=self._set_course)
        self.course_menu.pack(side="right")
        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.pack(fill="both", expand=True)

    def _set_course(self, v):
        self.course = v
        self.refresh()

    def refresh(self):
        env = self.app.env
        anns = self.app.announcements
        courses = ["All courses"] + sorted({a.get("course", "") for a in anns if a.get("course")})
        self.course_menu.configure(values=courses)
        if self.course not in courses:
            self.course = "All courses"
            self.course_menu.set(self.course)
        rows = [a for a in anns if self.course == "All courses" or a.get("course") == self.course]
        for w in self.list.winfo_children():
            w.destroy()
        if not env.get("TRACK_ANNOUNCEMENTS", True):
            self.summary.configure(text="Announcement tracking is off (Settings → Campus tracking).")
            return
        if self.app.semester_empty:
            self.summary.configure(text="")
            empty_semester_box(self.list, self.app)
            return
        self.summary.configure(text=f"{len(rows)} announcement{'s' if len(rows) != 1 else ''}" + ("" if not anns else "  ·  newest first"))
        if not rows:
            ctk.CTkLabel(self.list, text="No announcements yet. They are read from every course page with each sync.",
                         font=F(LG), text_color=C["dim"]).pack(pady=50)
            return
        box = surface(self.list)
        box.pack(fill="x")
        lazy = Lazy(self.list)
        for i, a in enumerate(rows):
            lazy.add(lambda i=i, a=a: self._ann_row(box, i, a))
        lazy.start()

    def _ann_row(self, box, i, a):
        if i:
            hairline(box)
        r = ctk.CTkFrame(box, fg_color="transparent")
        r.pack(fill="x", padx=20, pady=12)
        r.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(r, text=a.get("course", ""), font=F(SM, "semibold"), text_color=C["accent"], anchor="w").grid(
            row=0, column=0, sticky="w")
        posted = a.get("posted_at") or a.get("first_seen", "")
        ctk.CTkLabel(r, text=f"{rel_time(posted)}   ·   {a.get('posted', '')}", font=F(XS), text_color=C["dim"]).grid(
            row=0, column=1, sticky="e")
        line = 1
        if a.get("title") and a["title"].lower() not in ("all", "general"):
            ctk.CTkLabel(r, text=a["title"], font=F(MD, "semibold"), text_color=C["ink"], anchor="w", justify="left",
                         wraplength=820).grid(row=line, column=0, columnspan=2, sticky="w", pady=(4, 0))
            line += 1
        ctk.CTkLabel(r, text=a.get("text", ""), font=F(MD), text_color=C["ink"], anchor="w", justify="left",
                     wraplength=820).grid(row=line, column=0, columnspan=2, sticky="w", pady=(3, 0))


# ---------------------------------------------------------------------------- lectures
class LecturesView(ctk.CTkFrame):
    """Every course's lecture notes in one list with a checkbox per file; the selection downloads into
    <folder>/<course>/<Week NN - title>/ through the app's own signed-in session."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.course = "All courses"
        self.kind = "lecture"          # or "misc": the LMS Miscellaneous files, same list and downloader
        self.selected = set()          # (lecture id, file index)
        self.busy = False
        self.stop_flag = False

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(2, 8))
        self.kind_seg = ctk.CTkSegmentedButton(bar, values=["Lecture notes", "Miscellaneous"], font=F(SM, "semibold"), height=34,
                                               corner_radius=8, selected_color=C["accent"], selected_hover_color=C["accent_h"],
                                               unselected_color=C["surface"], unselected_hover_color=C["surface2"],
                                               text_color=C["ink"], fg_color=C["line"], command=self._set_kind)
        self.kind_seg.set("Lecture notes")
        self.kind_seg.pack(side="left")
        self.summary = ctk.CTkLabel(bar, text="", font=F(SM), text_color=C["muted"], anchor="w")
        self.summary.pack(side="left", padx=(14, 0))
        self.course_menu = ctk.CTkOptionMenu(bar, values=["All courses"], height=34, width=250, font=F(SM),
                                             fg_color=C["surface"], text_color=C["ink"], button_color=C["surface2"],
                                             button_hover_color=C["line2"], dropdown_font=F(SM), command=self._set_course)
        self.course_menu.pack(side="right")

        act = ctk.CTkFrame(self, fg_color="transparent")
        act.pack(fill="x", pady=(0, 8))
        self.dl_btn = primary_button(act, "Download selected", self._download, height=34, width=190)
        self.dl_btn.pack(side="left")
        self.sel_btn = soft_button(act, "Select all", lambda: self._select(True), width=90)
        self.sel_btn.pack(side="left", padx=(8, 0))
        self.clear_btn = soft_button(act, "Clear", lambda: self._select(False), width=70)
        self.clear_btn.pack(side="left", padx=(8, 0))
        self.stop_btn = soft_button(act, "Stop", self._stop, width=70)     # shown in their place while downloading
        soft_button(act, "Open folder", self._open_folder, width=100).pack(side="right")
        soft_button(act, "Change folder", self._change_folder, width=110).pack(side="right", padx=(0, 8))
        self.folder_lbl = ctk.CTkLabel(act, text="", font=F(XS), text_color=C["dim"], anchor="e")
        self.folder_lbl.pack(side="right", padx=(0, 12))
        self._act = act
        act.bind("<Configure>", lambda e: self._fit_folder_label())

        self.progress = ctk.CTkProgressBar(self, height=3, corner_radius=0, progress_color=C["accent"], fg_color=C["bg"])
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 6))
        self.progress.pack_forget()
        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.pack(fill="both", expand=True)

    # -- state helpers
    def _set_course(self, v):
        self.course = v
        self.refresh()

    def _set_kind(self, v):
        self.kind = "misc" if v == "Miscellaneous" else "lecture"
        if self.kind_seg.get() != v:
            self.kind_seg.set(v)
        self.refresh()

    def _visible(self):
        return [x for x in self.app.lectures if x.get("kind", "lecture") == self.kind
                and (self.course == "All courses" or x.get("course") == self.course)]

    def _select(self, on):
        keys = {(x["id"], i) for x in self._visible() for i in range(len(x.get("files", [])))}
        self.selected = (self.selected | keys) if on else (self.selected - keys)
        self.refresh()

    def _toggle(self, key, var):
        if var.get():
            self.selected.add(key)
        else:
            self.selected.discard(key)
        self._update_button()

    def _update_button(self):
        n = len(self.selected)
        self.dl_btn.configure(text=f"Download selected ({n})" if n else "Download selected",
                              state="normal" if n and not self.busy else "disabled")

    def _folder(self):
        return lectures_dir(self.app.env)

    def _fit_folder_label(self):
        """The folder path sits between the two button groups only when the bar has room for it (about 160 px);
        narrower windows drop it (Change folder shows the path, and the status line names it after a download)."""
        room = self._act.winfo_width() - 700
        shown = bool(self.folder_lbl.winfo_manager())
        if room < 160 and shown:
            self.folder_lbl.pack_forget()
        elif room >= 160 and not shown:
            self.folder_lbl.pack(side="right", padx=(0, 12))

    def _open_folder(self):
        d = self._folder()
        d.mkdir(parents=True, exist_ok=True)
        os.startfile(d)

    def _change_folder(self):
        chosen = filedialog.askdirectory(title="Save lecture files in…", initialdir=str(self._folder()))
        if not chosen:
            return
        env = dict(self.app.env)
        env["LECTURES_DIR"] = chosen
        save_env(env)
        self.app.env = load_env()
        self.refresh()

    # -- rendering
    def refresh(self):
        env = self.app.env
        items = self.app.lectures
        courses = ["All courses"] + sorted({x.get("course", "") for x in items if x.get("course")})
        self.course_menu.configure(values=courses)
        if self.course not in courses:
            self.course = "All courses"
            self.course_menu.set(self.course)
        self.folder_lbl.configure(text=short_path(self._folder()))
        for w in self.list.winfo_children():
            w.destroy()
        if not env.get("TRACK_LECTURES", True):
            self.summary.configure(text="Lecture notes are not being read (Settings → Campus tracking).")
            self._update_button()
            return
        if self.app.semester_empty:
            self.summary.configure(text="")
            self._update_button()
            empty_semester_box(self.list, self.app)
            return
        rows = self._visible()
        files = sum(len(x.get("files", [])) for x in rows)
        misc = self.kind == "misc"
        unit = f"{files} file{'s' if files != 1 else ''}" if misc else \
            f"{len(rows)} week{'s' if len(rows) != 1 else ''}  ·  {files} file{'s' if files != 1 else ''}"
        self.summary.configure(text=unit + ("" if self.course != "All courses" else f"  ·  {len(courses) - 1} courses"))
        self._update_button()
        if not rows:
            ctk.CTkLabel(self.list, text=("No miscellaneous files yet. Teachers put project briefs, templates and past papers "
                                          "here; they are read with each sync." if misc else
                                          "No lecture notes yet. They are read from every course page with each sync."),
                         font=F(LG), text_color=C["dim"], wraplength=700).pack(pady=50)
            return
        cutoff = datetime.now() - timedelta(days=3)
        by_course = {}
        for x in rows:
            by_course.setdefault(x["course"], []).append(x)
        lazy = Lazy(self.list)
        for course, lecs in by_course.items():
            def head(course=course, lecs=lecs):
                box = self._box = surface(self.list)
                box.pack(fill="x", pady=(0, 10))
                head = ctk.CTkFrame(box, fg_color="transparent")
                head.pack(fill="x", padx=20, pady=(16, 6))
                ctk.CTkLabel(head, text=course, font=F(LG, "semibold"), text_color=C["ink"], anchor="w").pack(side="left")
                nfiles = sum(len(x.get("files", [])) for x in lecs)
                ctk.CTkLabel(head, text=f"{nfiles} files" if misc else f"{len(lecs)} weeks  ·  {nfiles} files", font=F(SM),
                             text_color=C["muted"]).pack(side="right")
            lazy.add(head)
            for i, x in enumerate(lecs):
                def week(i=i, x=x):
                    if i:
                        hairline(self._box)
                    self._week(self._box, x, cutoff)
                lazy.add(week)
            lazy.add(lambda: ctk.CTkLabel(self._box, text="", height=6).pack())
        lazy.start()

    def _week(self, parent, x, cutoff):
        # one frame per week with a grid inside, instead of frames nested three deep: a page of ninety weeks has a
        # few hundred fewer widgets to lay out and repaint
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=20, pady=8)
        r.grid_columnconfigure(1, weight=1)
        is_new = False
        try:
            is_new = datetime.fromisoformat(x.get("first_seen", "")) >= cutoff
        except ValueError:
            pass
        label = x.get("title", "") if x.get("kind") == "misc" else f"Week {x.get('week', '')}   ·   {x.get('title', '')}"
        ctk.CTkLabel(r, text=label, font=F(MD, "semibold"), text_color=C["ink"], anchor="w").grid(row=0, column=0, sticky="w")
        if is_new:
            pill(r, "New", "week").grid(row=0, column=1, sticky="w", padx=(10, 0))
        line = 1
        files = x.get("files", [])
        for i, f in enumerate(files):
            key = (x["id"], i)
            var = ctk.BooleanVar(value=key in self.selected)
            label = f.get("filename") or f.get("label") or f"File {i + 1}"
            cb = ctk.CTkCheckBox(r, text=label, variable=var, font=F(SM), text_color=C["muted"], checkbox_width=18,
                                 checkbox_height=18, corner_radius=4, border_width=1, fg_color=C["accent"],
                                 hover_color=C["accent_h"], border_color=C["line2"],
                                 command=lambda k=key, v=var: self._toggle(k, v))
            cb.grid(row=line, column=0, columnspan=2, sticky="w", pady=(4, 0))
            line += 1
        if x.get("remarks"):
            ctk.CTkLabel(r, text=x["remarks"], font=F(XS), text_color=C["dim"], anchor="w", justify="left",
                         wraplength=700).grid(row=line, column=0, columnspan=2, sticky="w", pady=(3, 0))
            line += 1
        if x.get("videos"):
            vids = ctk.CTkFrame(r, fg_color="transparent")
            vids.grid(row=0, column=2, rowspan=line, sticky="ne", padx=(10, 0))
            for j, url in enumerate(x["videos"][:3]):
                soft_button(vids, "Video" if len(x["videos"]) == 1 else f"Video {j + 1}", lambda u=url: webbrowser.open(u),
                            width=70).pack(side="left", padx=(6, 0))

    # -- downloading
    def _download(self):
        if self.busy or not self.selected:
            return
        chosen = []
        for x in self.app.lectures:
            picked = [f for i, f in enumerate(x.get("files", [])) if (x["id"], i) in self.selected]
            if picked:
                y = dict(x)
                y["files"] = picked
                chosen.append(y)
        total = sum(len(y["files"]) for y in chosen)
        dest = self._folder()
        self.busy = True
        self.stop_flag = False
        self._update_button()
        self.sel_btn.pack_forget()
        self.clear_btn.pack_forget()
        self.stop_btn.pack(side="left", padx=(8, 0))
        self.progress.set(0)
        # a CTkScrollableFrame packs its outer frame, not itself, so that is the sibling to pack before
        self.progress.pack(fill="x", pady=(0, 6), before=self.list._parent_frame)
        self.app.set_status(f"Downloading {total} file{'s' if total != 1 else ''} to {dest}…")

        def prog(msg, done, tot):
            try:
                self.after(0, lambda: (self.progress.set(done / max(1, tot)), self.app.set_status(f"{done}/{tot}  ·  {msg}")))
            except RuntimeError:
                pass

        def work():
            try:
                res = download_lectures(chosen, dest, progress=prog, should_stop=lambda: self.stop_flag)
            except LoginError as e:
                res = {"saved": [], "skipped": 0, "failed": [("sign-in", str(e))]}
            except Exception as e:
                log.error("Lecture download failed: %s", e)
                res = {"saved": [], "skipped": 0, "failed": [("download", str(e)[:200])]}
            try:
                self.after(0, self._done, res, dest)
            except RuntimeError:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _stop(self):
        self.stop_flag = True
        self.app.set_status("Stopping after the current file…")

    def _done(self, res, dest):
        self.busy = False
        self.stop_btn.pack_forget()
        self.sel_btn.pack(side="left", padx=(8, 0), after=self.dl_btn)
        self.clear_btn.pack(side="left", padx=(8, 0), after=self.sel_btn)
        self.progress.pack_forget()
        saved, skipped, failed = len(res["saved"]), res["skipped"], res["failed"]
        bits = [f"{saved} file{'s' if saved != 1 else ''} saved"]
        if skipped:
            bits.append(f"{skipped} already there")
        if failed:
            bits.append(f"{len(failed)} failed")
        self.app.set_status("Lecture download: " + ", ".join(bits))
        if saved and not failed:
            self.selected = set()
        elif failed:
            keep = {k for k in self.selected}
            self.selected = keep
            messagebox.showwarning(APP_NAME, "Some files could not be downloaded:\n\n" +
                                   "\n".join(f"- {n}: {why}" for n, why in failed[:8]))
        self.refresh()
        if saved and not failed:
            try:
                os.startfile(dest)
            except OSError:
                pass


# ---------------------------------------------------------------------------- settings
class SettingsView(ctk.CTkScrollableFrame):
    EXAM_LEAD = {"the day before": 1, "2 days before": 2, "3 days before": 3, "a week before": 7}

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        env = app.env

        acc = self._section("Portal account", "Changing these re-verifies the sign-in when you save.")
        self.enroll = self._entry(acc, "Enrollment number", env.get("ENROLLMENT", ""))
        self.password = self._entry(acc, "Portal password", env.get("PASSWORD", ""), show="•")
        ctk.CTkLabel(acc, text="Campus", font=F(SM, "medium"), text_color=C["muted"]).pack(anchor="w", padx=20)
        self.campus = ctk.CTkOptionMenu(acc, values=CAMPUS_NAMES, height=38, font=F(MD), fg_color=C["field"],
                                        text_color=C["ink"], button_color=C["accent"], button_hover_color=C["accent_h"],
                                        dropdown_font=F(SM))
        self.campus.set(campus_name(env.get("INSTITUTE_ID", "1")))
        self.campus.pack(fill="x", padx=20, pady=(2, 12))
        row = ctk.CTkFrame(acc, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        primary_button(row, "Save and verify sign-in", self._save_account).pack(side="left")
        self.acc_msg = ctk.CTkLabel(row, text="", font=F(SM), text_color=C["muted"])
        self.acc_msg.pack(side="left", padx=14)
        soft_button(row, "Switch account", lambda: self.app.show_setup()).pack(side="right")

        look = self._section("Appearance", "Remembered across restarts.")
        theme_switch(look, self.app).pack(anchor="w", padx=20, pady=(0, 6))
        self.anim_sw = self._switch(look, "Animations (page transitions, counters, hover)", env.get("ANIMATIONS", True))
        ctk.CTkLabel(look, text="", height=8).pack()

        bg = self._section("Running in the background",
                           "Closing the window keeps the app in the system tray; right-click the icon to open, sync or quit.")
        self.tray_sw = self._switch(bg, "Keep running in the tray when the window is closed", env.get("CLOSE_TO_TRAY", True))
        self.updates_sw = self._switch(bg, "Check for updates when the app starts (asks api.github.com)",
                                       env.get("CHECK_UPDATES", True))
        self.startup_sw = ctk.CTkSwitch(bg, text="Start with Windows, minimized to the tray", font=F(MD),
                                        text_color=C["ink"], progress_color=C["accent"], command=self._toggle_startup)
        self.startup_sw.select() if automation.starts_with_windows() else self.startup_sw.deselect()
        self.startup_sw.pack(anchor="w", padx=20, pady=(4, 18))

        notif = self._section("Notifications", "How the app gets your attention after a sync or an hourly check.")
        self.voice = self._switch(notif, "Voice alerts through the speakers", env.get("ENABLE_VOICE", True))
        self.toast = self._switch(notif, "Windows desktop notifications", env.get("ENABLE_WINDOWS_TOAST", True))
        days_row = ctk.CTkFrame(notif, fg_color="transparent")
        days_row.pack(fill="x", padx=20, pady=(6, 4))
        ctk.CTkLabel(days_row, text="Mention assignments due within", font=F(MD), text_color=C["ink"]).pack(side="left")
        self.days = ctk.CTkOptionMenu(days_row, values=["1", "2", "3", "5", "7", "14"], width=80, height=32, font=F(SM),
                                      fg_color=C["field"], text_color=C["ink"], button_color=C["line2"],
                                      button_hover_color=C["dim"], command=lambda v: self._save_prefs())
        self.days.set(str(env.get("NOTIFY_DAYS_AHEAD", 3)))
        self.days.pack(side="left", padx=10)
        ctk.CTkLabel(days_row, text="days", font=F(MD), text_color=C["ink"]).pack(side="left")
        voice_row = ctk.CTkFrame(notif, fg_color="transparent")
        voice_row.pack(fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(voice_row, text="Voice", font=F(MD), text_color=C["ink"], width=60, anchor="w").pack(side="left")
        self.voice_menu = ctk.CTkOptionMenu(voice_row, values=["Default"], width=260, height=32, font=F(SM),
                                            fg_color=C["field"], text_color=C["ink"], button_color=C["line2"],
                                            button_hover_color=C["dim"], dropdown_font=F(SM), command=lambda v: self._save_prefs())
        self.voice_menu.set(env.get("VOICE_NAME") or "Default")
        self.voice_menu.pack(side="left", padx=(10, 0))
        self.after(400, lambda: threading.Thread(target=self._load_voices, daemon=True).start())

        vol_row = ctk.CTkFrame(notif, fg_color="transparent")
        vol_row.pack(fill="x", padx=20, pady=(6, 4))
        ctk.CTkLabel(vol_row, text="Volume", font=F(MD), text_color=C["ink"], width=60, anchor="w").pack(side="left")
        self.volume = ctk.CTkSlider(vol_row, from_=0, to=100, number_of_steps=20, width=260, height=16,
                                    progress_color=C["accent"], button_color=C["accent"], button_hover_color=C["accent_h"],
                                    fg_color=C["surface2"], command=self._volume_changed)
        self.volume.set(int(env.get("VOICE_VOLUME", 100)))
        self.volume.pack(side="left", padx=(10, 10))
        self.volume_lbl = ctk.CTkLabel(vol_row, text=f"{int(env.get('VOICE_VOLUME', 100))}%", font=F(SM),
                                       text_color=C["muted"], width=40, anchor="w")
        self.volume_lbl.pack(side="left")
        self.volume.bind("<ButtonRelease-1>", lambda e: self._save_prefs())

        rate_row = ctk.CTkFrame(notif, fg_color="transparent")
        rate_row.pack(fill="x", padx=20, pady=(6, 4))
        ctk.CTkLabel(rate_row, text="Speed", font=F(MD), text_color=C["ink"], width=60, anchor="w").pack(side="left")
        self.rate = ctk.CTkSegmentedButton(rate_row, values=["Slow", "Normal", "Fast"], font=F(SM, "semibold"), height=30,
                                           selected_color=C["accent"], selected_hover_color=C["accent_h"],
                                           unselected_color=C["surface"], unselected_hover_color=C["surface2"],
                                           text_color=C["ink"], fg_color=C["line"], command=lambda v: self._save_prefs())
        self.rate.set({-2: "Slow", 0: "Normal", 2: "Fast"}.get(int(env.get("VOICE_RATE", 0)), "Normal"))
        self.rate.pack(side="left", padx=(10, 0))

        btns = ctk.CTkFrame(notif, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(10, 18))
        soft_button(btns, "Preview voice", self._preview_voice).pack(side="left", padx=(0, 8))
        soft_button(btns, "Send a test alert", self._test_alert).pack(side="left")

        self._channels_section(env)

        camp = self._section("Campus tracking",
                             "Besides assignments, each sync can read these from the portal. "
                             "Alerts follow the notification settings above.")
        self.track_att = self._switch(camp, "Attendance per course, with an alert when an absence is recorded or a course "
                                            "drops under the minimum", env.get("TRACK_ATTENDANCE", True))
        self.track_exams = self._switch(camp, "Exam seating plan, with a reminder before each paper and on the morning of it",
                                        env.get("TRACK_EXAMS", True))
        self.track_results = self._switch(camp, "Results: every semester's grades, GPA and CGPA, with an alert the moment a result "
                                                "is posted", env.get("TRACK_RESULTS", True))
        self.track_ann = self._switch(camp, "Course announcements, with an alert for each new one", env.get("TRACK_ANNOUNCEMENTS", True))
        self.track_lec = self._switch(camp, "Lecture notes from every course, with an alert when new ones are uploaded "
                                            "(downloads happen only when you ask, from the Lectures page)", env.get("TRACK_LECTURES", True))
        self.track_tt = self._switch(camp, "Timetable from the CMS, drawn as a week grid you can save as PNG, JPG or PDF",
                                     env.get("TRACK_TIMETABLE", True))
        min_row = ctk.CTkFrame(camp, fg_color="transparent")
        min_row.pack(fill="x", padx=20, pady=(8, 4))
        ctk.CTkLabel(min_row, text="Minimum attendance", font=F(MD), text_color=C["ink"]).pack(side="left")
        self.att_min = ctk.CTkOptionMenu(min_row, values=["60", "65", "70", "75", "80", "85", "90"], width=80, height=32, font=F(SM),
                                         fg_color=C["field"], text_color=C["ink"], button_color=C["line2"],
                                         button_hover_color=C["dim"], command=lambda v: self._save_prefs())
        self.att_min.set(str(env.get("ATTENDANCE_MIN", 75)))
        self.att_min.pack(side="left", padx=10)
        ctk.CTkLabel(min_row, text="%  (your university's rule; margins on the Attendance page use it)", font=F(SM),
                     text_color=C["muted"]).pack(side="left")
        ex_row = ctk.CTkFrame(camp, fg_color="transparent")
        ex_row.pack(fill="x", padx=20, pady=(6, 18))
        ctk.CTkLabel(ex_row, text="Remind me about an exam", font=F(MD), text_color=C["ink"]).pack(side="left")
        self.exam_days = ctk.CTkOptionMenu(ex_row, values=list(self.EXAM_LEAD), width=150, height=32, font=F(SM),
                                           fg_color=C["field"], text_color=C["ink"], button_color=C["line2"],
                                           button_hover_color=C["dim"], dropdown_font=F(SM), command=lambda v: self._save_prefs())
        self.exam_days.set(next((k for k, v in self.EXAM_LEAD.items() if v == int(env.get("EXAM_REMIND_DAYS", 1))), "the day before"))
        self.exam_days.pack(side="left", padx=10)
        ctk.CTkLabel(ex_row, text="plus once on the morning of the paper", font=F(SM), text_color=C["muted"]).pack(side="left")

        auto = self._section("Automatic checks",
                             "Windows runs a check daily at 7:00 PM and two minutes after you sign in, plus an hourly "
                             "reminder while something is due today. These run even when the app is closed.")
        row = ctk.CTkFrame(auto, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        self.auto_status = ctk.CTkLabel(row, text="Checking…", font=F(MD, "semibold"), text_color=C["muted"])
        self.auto_status.pack(side="left")
        self.auto_btn = soft_button(row, "…", self._toggle_automation, width=140)
        self.auto_btn.configure(state="disabled")
        self.auto_btn.pack(side="right")
        self.after(300, lambda: threading.Thread(target=self._refresh_automation, daemon=True).start())

        self._cloud_section(env)

        data = self._section("Your data", f"Everything the app keeps is on this PC, in {BASE_DIR}. The activity log is what it "
                                          "did and when, including the background checks.")
        row = ctk.CTkFrame(data, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        soft_button(row, "Activity log", lambda: self.app.navigate("activity"), width=110).pack(side="left", padx=(0, 8))
        soft_button(row, "Open data folder", lambda: os.startfile(DATA_DIR)).pack(side="left", padx=(0, 8))
        soft_button(row, "Reset local data", self._clear_data).pack(side="right")

        about = self._section("About", f"{APP_NAME} {APP_VERSION} {TAGLINE}  ·  "
                              f"{'installed build' if FROZEN else 'running from source'}  ·  made by Nobody243  ·  MIT license")
        ctk.CTkLabel(about, text="Unofficial app. Not affiliated with, endorsed by, or supported by Bahria University.",
                     font=F(SM), text_color=C["dim"]).pack(anchor="w", padx=20, pady=(0, 10))
        urow = ctk.CTkFrame(about, fg_color="transparent")
        urow.pack(fill="x", padx=20, pady=(0, 10))
        soft_button(urow, "Check for updates", lambda: self.app.check_for_updates(quiet=False), width=140).pack(side="left")
        self.update_msg = ctk.CTkLabel(urow, text="", font=F(SM), text_color=C["muted"], cursor="hand2")
        self.update_msg.pack(side="left", padx=12)
        self.update_msg.bind("<Button-1>", lambda e: self.app.install_update())
        row = ctk.CTkFrame(about, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        docs = [("What's new", lambda: open_doc("CHANGELOG.md", f"{REPO_URL}/blob/main/CHANGELOG.md")),
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
        ctk.CTkLabel(parent, text=label, font=F(SM, "medium"), text_color=C["muted"]).pack(anchor="w", padx=20)
        e = ctk.CTkEntry(parent, height=38, font=F(MD), fg_color=C["field"], border_color=C["line2"],
                         text_color=C["ink"], show=show or "")
        e.insert(0, value)
        e.pack(fill="x", padx=20, pady=(2, 12))
        return e

    def _switch(self, parent, text, value):
        sw = ctk.CTkSwitch(parent, text=text, font=F(MD), text_color=C["ink"], progress_color=C["accent"],
                           command=self._save_prefs)
        sw.select() if value else sw.deselect()
        sw.pack(anchor="w", padx=20, pady=4)
        return sw

    # -- actions
    # ---- phone, email and calendar
    def _channels_section(self, env):
        box = self._section("Phone, email and calendar",
                            "The same alerts, delivered where you are. Email uses your own mailbox; phone pushes go "
                            "straight from this PC to your phone's browser. Nothing passes through a server of ours.")
        # email
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 2))
        self.email_sw = ctk.CTkSwitch(row, text="Email me each alert", font=F(MD), text_color=C["ink"],
                                      progress_color=C["accent"], command=self._save_channels)
        self.email_sw.select() if env.get("EMAIL_ENABLED") else self.email_sw.deselect()
        self.email_sw.pack(side="left")
        self.email_msg = ctk.CTkLabel(row, text="", font=F(SM), text_color=C["muted"])
        self.email_msg.pack(side="left", padx=14)
        grid = ctk.CTkFrame(box, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=(6, 4))
        grid.grid_columnconfigure((0, 1), weight=1, uniform="em")
        left = ctk.CTkFrame(grid, fg_color="transparent")
        left.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        right = ctk.CTkFrame(grid, fg_color="transparent")
        right.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(left, text="Your email address", font=F(SM, "medium"), text_color=C["muted"]).pack(anchor="w")
        self.email_to = ctk.CTkEntry(left, height=38, font=F(MD), fg_color=C["field"], border_color=C["line2"], text_color=C["ink"],
                                     placeholder_text="name@gmail.com")
        self.email_to.insert(0, env.get("EMAIL_TO", ""))
        self.email_to.pack(fill="x", pady=(2, 0))
        self.email_to.bind("<KeyRelease>", lambda e: self._email_hint())
        ctk.CTkLabel(right, text="App password (not your normal password)", font=F(SM, "medium"), text_color=C["muted"]).pack(anchor="w")
        self.email_pass = ctk.CTkEntry(right, height=38, font=F(MD), fg_color=C["field"], border_color=C["line2"], text_color=C["ink"],
                                       show="•", placeholder_text="16 characters from your mail provider")
        self.email_pass.insert(0, env.get("EMAIL_PASS", ""))
        self.email_pass.pack(fill="x", pady=(2, 0))
        self.email_hint = ctk.CTkLabel(box, text="", font=F(XS), text_color=C["dim"], anchor="w", justify="left", wraplength=820)
        self.email_hint.pack(fill="x", padx=20, pady=(6, 0))
        self._email_hint()
        act = ctk.CTkFrame(box, fg_color="transparent")
        act.pack(fill="x", padx=20, pady=(8, 14))
        primary_button(act, "Save and send a test email", self._test_email, height=34, width=220).pack(side="left")
        soft_button(act, "Advanced (SMTP server)", self._smtp_advanced, width=170).pack(side="left", padx=(8, 0))
        hairline(box)

        # phone
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(14, 4))
        self.push_sw = ctk.CTkSwitch(row, text="Push each alert to my phone", font=F(MD), text_color=C["ink"], progress_color=C["accent"],
                                     command=self._save_channels)
        self.push_sw.select() if env.get("PUSH_ENABLED") else self.push_sw.deselect()
        self.push_sw.pack(side="left")
        self.push_msg = ctk.CTkLabel(row, text="", font=F(SM), text_color=C["muted"])
        self.push_msg.pack(side="left", padx=14)
        ctk.CTkLabel(box, text="No app to install: scan a code with the phone's camera, tap Allow on the page that opens, done. "
                              "Works on Android (Chrome, Samsung Internet) and on iPhone with iOS 16.4 or newer after "
                              "adding the page to the Home Screen.",
                     font=F(XS), text_color=C["dim"], anchor="w", justify="left", wraplength=820).pack(fill="x", padx=20)
        act = ctk.CTkFrame(box, fg_color="transparent")
        act.pack(fill="x", padx=20, pady=(8, 14))
        primary_button(act, "Pair a phone", self._pair_phone, height=34, width=140).pack(side="left")
        soft_button(act, "Send a test push", self._test_push, width=140).pack(side="left", padx=(8, 0))
        soft_button(act, "Unpair", self._unpair, width=90).pack(side="left", padx=(8, 0))
        self._push_status()
        hairline(box)

        # calendar
        self.cal_sw = ctk.CTkSwitch(box, text="Keep a calendar file of deadlines and exams up to date (Documents \u203a "
                                              "Assignment Monitor \u203a Assignment Monitor.ics)",
                                    font=F(MD), text_color=C["ink"], progress_color=C["accent"], command=self._save_channels)
        self.cal_sw.select() if env.get("CALENDAR_ENABLED") else self.cal_sw.deselect()
        self.cal_sw.pack(anchor="w", padx=20, pady=(14, 4))
        self.cal_inv_sw = ctk.CTkSwitch(box, text="Also email me a calendar invite for each new deadline and exam "
                                                  "(they appear in Google Calendar or Outlook on the phone)",
                                        font=F(MD), text_color=C["ink"], progress_color=C["accent"], command=self._save_channels)
        self.cal_inv_sw.select() if env.get("CALENDAR_INVITES") else self.cal_inv_sw.deselect()
        self.cal_inv_sw.pack(anchor="w", padx=20, pady=(0, 6))
        act = ctk.CTkFrame(box, fg_color="transparent")
        act.pack(fill="x", padx=20, pady=(4, 18))
        soft_button(act, "Open calendar file", self._open_calendar, width=150).pack(side="left")
        ctk.CTkLabel(act, text="Import it once into Google Calendar or Outlook; it is rewritten after every sync.",
                     font=F(XS), text_color=C["dim"]).pack(side="left", padx=12)

    # ---- cloud checks
    def _cloud_section(self, env):
        box = self._section("Cloud checks (PC off)",
                            "GitHub runs the same check twice a day, at 8 AM and 7 PM, from a private repository in "
                            "your own GitHub account, so phone and email alerts arrive even when this PC is off. Free. "
                            "While it is on, this PC keeps its desktop and voice alerts and leaves phone and email to "
                            "the cloud, so nothing arrives twice.")
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        self.cloud_status = ctk.CTkLabel(row, text="Checking…", font=F(MD, "semibold"), text_color=C["muted"],
                                         anchor="w", justify="left", wraplength=420)
        self.cloud_status.pack(side="left", fill="x", expand=True)
        self.cloud_btn = soft_button(row, "…", self._toggle_cloud, width=140)
        self.cloud_btn.configure(state="disabled")
        self.cloud_btn.pack(side="right")
        self.cloud_more = ctk.CTkFrame(row, fg_color="transparent")
        self.cloud_more.pack(side="right", padx=(0, 8))
        soft_button(self.cloud_more, "Run now", self._cloud_run_now, width=100).pack(side="left", padx=(0, 8))
        soft_button(self.cloud_more, "Open on GitHub",
                    lambda: webbrowser.open(f"https://github.com/{self.app.env.get('CLOUD_REPO', '')}/actions"),
                    width=130).pack(side="left")
        self._cloud_sync_job = None
        self.after(400, lambda: threading.Thread(target=self._refresh_cloud, daemon=True).start())

    def _refresh_cloud(self):
        env = load_env()
        if not GITHUB_CLIENT_ID:
            self.after(0, self._show_cloud, False, "Not available in this build.", None)
            return
        if not cloud.enabled(env):
            self.after(0, self._show_cloud, False, "Off. Alerts come from this PC only.", None)
            return
        text = f"On, as {env.get('CLOUD_LOGIN', '')} on GitHub."
        try:
            run = cloud.last_run(env)
            if run:
                when = run["when"]
                day = "today" if when.date() == datetime.now().date() else when.strftime("%d %b")
                if run["status"] != "completed":
                    text += f"  A check is running now (started {day} {when:%I:%M %p})."
                else:
                    words = {"success": "passed", "failure": "failed", "cancelled": "was cancelled"}
                    word = words.get(run["conclusion"], run["conclusion"] or "")
                    text += f"  Last check {day} {when:%I:%M %p} {word}."
            else:
                text += "  No check has run yet."
        except Exception as e:
            text += f"  (GitHub could not be reached: {str(e)[:80]})"
        self.after(0, self._show_cloud, True, text, env)

    def _show_cloud(self, on, text, env):
        if not self.winfo_exists():
            return
        self.cloud_status.configure(text=text, text_color=C["green"] if on else C["muted"])
        self.cloud_btn.configure(text="Turn off" if on else "Set up", state="normal" if GITHUB_CLIENT_ID else "disabled",
                                 fg_color=C["surface2"] if on else C["accent"],
                                 text_color=C["ink"] if on else C["on_accent"],
                                 hover_color=C["line2"] if on else C["accent_h"])
        if on:
            self.cloud_more.pack(side="right", padx=(0, 8))
        else:
            self.cloud_more.pack_forget()
        self._cloud_on = on

    def _cloud_sync_later(self):
        """Pushes changed settings to the cloud a few seconds after the last change, off the main thread."""
        if not cloud.enabled(self.app.env):
            return
        if getattr(self, "_cloud_sync_job", None):
            self.after_cancel(self._cloud_sync_job)
        self._cloud_sync_job = self.after(3000, lambda: threading.Thread(
            target=lambda: cloud.sync_secrets(load_env()), daemon=True).start())

    def _cloud_run_now(self):
        def work():
            try:
                cloud.run_now(load_env())
                self.after(0, lambda: self.app.set_status("Cloud check started. Results in a few minutes on GitHub and on your phone."))
                self.after(15000, lambda: threading.Thread(target=self._refresh_cloud, daemon=True).start())
            except Exception as e:
                err = str(e)[:160]
                self.after(0, lambda: self.app.set_status(f"Could not start the cloud check: {err}"))
        threading.Thread(target=work, daemon=True).start()

    def _toggle_cloud(self):
        if getattr(self, "_cloud_on", False):
            if not messagebox.askyesno(APP_NAME, "Turn off cloud checks?\n\nThe secrets and the workflow are removed from "
                                                 "your GitHub repository and this PC forgets the GitHub sign-in. The "
                                                 "empty repository stays; you can delete it on GitHub afterwards.",
                                       parent=self.app):
                return
            self.cloud_btn.configure(state="disabled", text="Working…")

            def work():
                url = cloud.teardown(load_env())
                self.app.env = load_env()
                self.after(0, lambda: self.app.set_status("Cloud checks are off."))
                self.after(0, lambda: threading.Thread(target=self._refresh_cloud, daemon=True).start())
                if url and messagebox.askyesno(APP_NAME, "Open the repository's settings on GitHub so you can delete it?",
                                               parent=self.app):
                    webbrowser.open(url)
            threading.Thread(target=work, daemon=True).start()
            return
        self._cloud_setup_dialog()

    def _cloud_setup_dialog(self, demo_done=None):
        dlg = ctk.CTkToplevel(self.app)
        dlg.title("Cloud checks")
        dlg.geometry("560x540")
        dlg.resizable(False, False)
        dlg.transient(self.app)
        dlg.configure(fg_color=C["bg"])
        body = ctk.CTkFrame(dlg, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=32, pady=24)
        state = {"flow": None, "token": None, "cancel": False}
        dlg.protocol("WM_DELETE_WINDOW", lambda: (state.__setitem__("cancel", True), dlg.destroy()))

        def clear():
            for w in body.winfo_children():
                w.destroy()

        def text(parent, t, size=SM, color="ink", weight="normal", pady=(0, 10), wrap=490, justify="left"):
            lbl = ctk.CTkLabel(parent, text=t, font=F(size, weight), text_color=C[color], justify=justify,
                               anchor="w" if justify == "left" else "center", wraplength=wrap)
            lbl.pack(anchor="w" if justify == "left" else "center", pady=pady, fill="x")
            return lbl

        def stage_consent():
            clear()
            text(body, "Before you continue", H3, weight="semibold", pady=(0, 12))
            text(body, "GitHub will run the check for you. To set that up, this app will do the following in your "
                       "GitHub account, with your permission:")
            for line in ("Create a private repository named assignment-monitor-cloud.",
                         "Store your enrollment number, portal password and the phone and email keys there as GitHub "
                         "Actions secrets: encrypted by GitHub, readable only by the check while it runs, never shown "
                         "in logs.",
                         "Copy what this PC has seen so far (assignments, attendance, exams, announcements, timetable) "
                         "into it and keep that cache updated there."):
                ctk.CTkLabel(body, text="•  " + line, font=F(SM), text_color=C["ink"], justify="left", anchor="w",
                             wraplength=480).pack(fill="x", padx=(12, 0), pady=2)
            text(body, "GitHub's machines then sign in to the portal twice a day, at 8 AM and 7 PM. Until now your "
                       "password never left this PC; with cloud checks it also lives in GitHub's encrypted secrets. "
                       "Turning cloud checks off removes the secrets and the workflow.", pady=(12, 10))
            text(body, "You need a free GitHub account. GitHub will ask you to grant the \"repo\" and \"workflow\" "
                       "permissions; they cover every repository in your account, and the app touches only the one "
                       "above. You can revoke the grant any time at github.com/settings/applications.",
                 color="muted", pady=(0, 18))
            btns = ctk.CTkFrame(body, fg_color="transparent")
            btns.pack(fill="x")
            primary_button(btns, "Continue with GitHub", stage_code, width=200).pack(side="left")
            soft_button(btns, "Cancel", dlg.destroy, width=100).pack(side="left", padx=10)

        def stage_code():
            clear()
            text(body, "Sign in on GitHub", H3, weight="semibold", pady=(0, 12))
            status = text(body, "Asking GitHub for a code…", color="muted")
            code_lbl = ctk.CTkLabel(body, text="", font=F(34, "semibold", display=True), text_color=C["ink"])
            code_lbl.pack(pady=(8, 4))
            hint = text(body, "", color="muted", justify="center", pady=(0, 14))
            btns = ctk.CTkFrame(body, fg_color="transparent")
            btns.pack()

            def begin():
                try:
                    flow = cloud.device_start()
                except Exception as e:
                    err = str(e)[:200]
                    self.after(0, lambda: status.configure(text=err, text_color=C["red"]))
                    return
                state["flow"] = flow

                def show():
                    code_lbl.configure(text=flow["user_code"])
                    self.app.clipboard_clear()
                    self.app.clipboard_append(flow["user_code"])
                    status.configure(text="1.  Press Open GitHub (the code is already copied).\n"
                                          "2.  Paste the code there and press Continue.\n"
                                          "3.  Press Authorize. Come back here; this window moves on by itself.",
                                     text_color=C["ink"])
                    hint.configure(text=f"Or open {flow['verification_uri']} on any device and type the code. "
                                        f"It is valid for {int(flow.get('expires_in', 900)) // 60} minutes.")
                    primary_button(btns, "Open GitHub", lambda: webbrowser.open(flow["verification_uri"]), width=160).pack(side="left")
                    soft_button(btns, "Cancel", lambda: (state.__setitem__("cancel", True), dlg.destroy()),
                                width=100).pack(side="left", padx=10)
                self.after(0, show)
                poll()

            def poll():
                if state["cancel"] or not dlg.winfo_exists():
                    return
                flow = state["flow"]
                try:
                    token = cloud.device_poll(flow)
                except Exception as e:
                    err = str(e)[:200]
                    self.after(0, lambda: status.configure(text=err, text_color=C["red"]))
                    return
                if token:
                    state["token"] = token
                    self.after(0, stage_setup)
                    return
                time.sleep(int(flow.get("interval", 5)))
                poll()
            threading.Thread(target=begin, daemon=True).start()

        def stage_setup():
            clear()
            text(body, "Setting up", H3, weight="semibold", pady=(0, 12))
            status = text(body, "Starting…", color="muted")
            lines = []

            def progress(msg):
                lines.append(msg)
                self.after(0, lambda: status.configure(text="\n".join(lines)))

            def work():
                try:
                    info = cloud.setup(state["token"], load_env(), progress)
                except Exception as e:
                    err = str(e)[:300]
                    self.after(0, lambda: status.configure(text="\n".join(lines + ["", "Failed: " + err]), text_color=C["red"]))
                    self.after(0, lambda: soft_button(body, "Close", dlg.destroy, width=100).pack(anchor="w", pady=(16, 0)))
                    return
                self.app.env = load_env()
                self.after(0, lambda: stage_done(info))
            threading.Thread(target=work, daemon=True).start()

        def stage_done(info):
            clear()
            text(body, "Cloud checks are on", H3, weight="semibold", pady=(0, 12))
            text(body, f"GitHub ({info['login']}) now checks the portal for you at 8 AM and 7 PM, PC on or off. "
                       "A first check is running right now; within a few minutes it sends a test alert to your "
                       "phone and mailbox (whichever are set up) and the result shows in Settings.")
            text(body, "From now on this PC keeps its desktop and voice alerts and leaves phone and email to the "
                       "cloud. Changes you make here (password, phone, email, what to track) are sent to the cloud "
                       "automatically.", color="muted", pady=(0, 18))
            btns = ctk.CTkFrame(body, fg_color="transparent")
            btns.pack(fill="x")
            if info.get("run_url"):
                soft_button(btns, "Watch it on GitHub", lambda: webbrowser.open(info["run_url"]), width=160).pack(side="left")
            primary_button(btns, "Done", dlg.destroy, width=100).pack(side="left", padx=10)
            threading.Thread(target=self._refresh_cloud, daemon=True).start()

        if demo_done:
            stage_done(demo_done)
        else:
            stage_consent()

    def _email_hint(self):
        addr = self.email_to.get().strip()
        smtp_env = {"EMAIL_HOST": self.app.env.get("EMAIL_HOST", ""), "EMAIL_PORT": self.app.env.get("EMAIL_PORT", 587)}
        host, port = channels.smtp_for(addr, smtp_env) if "@" in addr else ("", 587)
        tip = channels.APP_PASSWORD_HELP.get(host, "")
        self.email_hint.configure(text=(f"Sends through {host}:{port}.  " if host else "") + tip)

    def _save_channels(self, quiet=False):
        env = dict(self.app.env)
        env["EMAIL_ENABLED"] = bool(self.email_sw.get())
        env["EMAIL_TO"] = self.email_to.get().strip()
        env["EMAIL_USER"] = env["EMAIL_TO"]
        env["EMAIL_PASS"] = self.email_pass.get().strip()
        env["PUSH_ENABLED"] = bool(self.push_sw.get()) and bool(env.get("PUSH_SUB"))
        env["CALENDAR_ENABLED"] = bool(self.cal_sw.get())
        env["CALENDAR_INVITES"] = bool(self.cal_inv_sw.get())
        save_env(env)
        self.app.env = load_env()
        self._cloud_sync_later()
        if self.push_sw.get() and not env.get("PUSH_SUB"):
            self.push_sw.deselect()
            self.push_msg.configure(text="Pair a phone first.")
        if env["CALENDAR_ENABLED"]:
            self._refresh_calendar()

    def _refresh_calendar(self):
        try:
            from calendar_export import events_from, write_calendar
            write_calendar(events_from(self.app.data.values(), self.app.exams))
        except Exception as e:
            log.warning("Calendar file: %s", e)

    def _test_email(self):
        self._save_channels()
        env = self.app.env
        if not env.get("EMAIL_TO") or not env.get("EMAIL_PASS"):
            self.email_msg.configure(text="Enter your address and an app password first.", text_color=C["red"])
            return
        self.email_msg.configure(text="Sending…", text_color=C["muted"])

        def work():
            try:
                channels.send_email(f"{APP_NAME} is connected",
                                    "This is the test email. Alerts from the app will arrive like this.", env)
                self.after(0, lambda: self.email_msg.configure(text="Sent. Check your inbox.", text_color=C["green"]))
            except Exception as e:
                msg = str(e)[:140]
                self.after(0, lambda: self.email_msg.configure(text=f"Failed: {msg}", text_color=C["red"]))
        threading.Thread(target=work, daemon=True).start()

    def _smtp_advanced(self):
        env = self.app.env
        host = simpledialog.askstring(APP_NAME, "SMTP server (leave empty to pick it from your address):",
                                      initialvalue=env.get("EMAIL_HOST", ""), parent=self.app)
        if host is None:
            return
        port = simpledialog.askinteger(APP_NAME, "Port (587 for STARTTLS, 465 for SSL):",
                                       initialvalue=int(env.get("EMAIL_PORT") or 587), parent=self.app, minvalue=1, maxvalue=65535)
        env = dict(env)
        env["EMAIL_HOST"] = host.strip()
        env["EMAIL_PORT"] = int(port or 587)
        save_env(env)
        self.app.env = load_env()
        self._email_hint()

    def _push_status(self):
        env = self.app.env
        if env.get("PUSH_SUB"):
            self.push_msg.configure(text=f"Paired: {channels.push_device(env)}", text_color=C["green"])
        else:
            self.push_msg.configure(text="No phone paired yet.", text_color=C["muted"])

    def _pair_phone(self):
        pairing = channels.pairing_start(self.app.env)
        self.app.env = load_env()
        dlg = ctk.CTkToplevel(self.app)
        dlg.title("Pair a phone")
        dlg.geometry("500x680")
        dlg.resizable(False, False)
        dlg.transient(self.app)
        dlg.configure(fg_color=C["bg"])
        ctk.CTkLabel(dlg, text="Pair your phone in three taps", font=F(H3, "semibold", display=True),
                     text_color=C["ink"]).pack(pady=(22, 10))
        steps = ctk.CTkFrame(dlg, fg_color="transparent")
        steps.pack(padx=36, fill="x")
        for n, line in enumerate(("Open the Camera app on your phone (the ordinary camera, not Settings).",
                                  "Point it at this code and tap the link that pops up.",
                                  "On the page that opens, tap \"Allow notifications and pair\"."), start=1):
            row = ctk.CTkFrame(steps, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{n}", font=F(SM, "semibold"), text_color=C["on_accent"], fg_color=C["accent"],
                         corner_radius=11, width=22, height=22).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(row, text=line, font=F(SM), text_color=C["ink"], anchor="w", justify="left",
                         wraplength=380).pack(side="left", fill="x")
        import qrcode
        qr = qrcode.QRCode(border=1, box_size=8)
        qr.add_data(pairing["url"])
        qr.make(fit=True)
        pil = qr.make_image(fill_color="#14161b", back_color="#ffffff").convert("RGB")
        img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(260, 260))
        holder = ctk.CTkFrame(dlg, fg_color="#ffffff", corner_radius=14)
        holder.pack(pady=(14, 8))
        ctk.CTkLabel(holder, text="", image=img).pack(padx=12, pady=12)
        status = ctk.CTkLabel(dlg, text="Waiting for the phone to open the link…", font=F(MD, "semibold"), text_color=C["muted"])
        status.pack(pady=(4, 0))
        ctk.CTkLabel(dlg, text=f"Code {pairing['code']}  ·  the page shows the same code", font=F(XS),
                     text_color=C["dim"]).pack(pady=(2, 0))
        hint = ("Camera not offering a link?  Press Copy link and send it to the phone any way you like (a WhatsApp message "
                "to yourself works), then open it there.\niPhone: in Safari tap Share, Add to Home Screen, open it from there, then pair.")
        ctk.CTkLabel(dlg, text=hint, font=F(XS), text_color=C["muted"], justify="center", wraplength=430).pack(pady=(12, 0))
        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=(12, 0))

        def copy_link():
            self.app.clipboard_clear()
            self.app.clipboard_append(pairing["url"])
            status.configure(text="Link copied. Paste it to your phone and open it there.", text_color=C["ink"])

        def email_link():
            status.configure(text="Emailing the link…", text_color=C["ink"])

            def work():
                try:
                    channels.send_email(f"{APP_NAME}: pair your phone",
                                        "Open this link on your phone and tap Allow notifications and pair:\n\n" + pairing["url"]
                                        + "\n\nThe link works for ten minutes and only once.", env=self.app.env)
                    self.after(0, lambda: status.configure(text="Sent. Open the email on your phone and tap the link.",
                                                           text_color=C["ink"]))
                except Exception as e:
                    err = str(e)[:90]
                    self.after(0, lambda: status.configure(text=f"Email failed: {err}", text_color=C["red"]))
            threading.Thread(target=work, daemon=True).start()
        soft_button(btns, "Copy link", copy_link, width=130).pack(side="left", padx=6)
        if channels.email_ready(self.app.env):
            soft_button(btns, "Email me the link", email_link, width=150).pack(side="left", padx=6)
        state = {"done": False}

        def poll():
            if state["done"] or not dlg.winfo_exists():
                return
            if time.time() - pairing["started"] > 600:
                status.configure(text="The code expired. Close this and try again.", text_color=C["red"])
                return

            def work():
                sub = channels.pairing_poll(pairing)
                if pairing.get("opened") and not sub and not state["done"] and dlg.winfo_exists():
                    self.after(0, lambda: status.configure(text="Your phone opened the page. Tap \"Allow notifications and pair\" there.",
                                                           text_color=C["accent"]))
                if sub and not state["done"]:
                    state["done"] = True
                    channels.save_subscription(sub, self.app.env)
                    self.app.env = load_env()
                    self.after(0, self._cloud_sync_later)

                    def ok():
                        self.push_sw.select()
                        self._push_status()
                        status.configure(text="Paired. Sending a test…", text_color=C["green"])
                        dlg.after(1800, dlg.destroy)
                    self.after(0, ok)
                    try:
                        channels.send_push(f"{APP_NAME} is connected", "Alerts from your PC will arrive here.", env=self.app.env)
                    except Exception as e:
                        log.warning("Test push failed: %s", e)
                elif dlg.winfo_exists():
                    dlg.after(4000, poll)
            threading.Thread(target=work, daemon=True).start()
        dlg.after(1500, poll)

    def _test_push(self):
        if not self.app.env.get("PUSH_SUB"):
            self.push_msg.configure(text="Pair a phone first.", text_color=C["red"])
            return
        self.push_msg.configure(text="Sending…", text_color=C["muted"])

        def work():
            try:
                channels.send_push(f"{APP_NAME} test", "If you can read this on your phone, pushes work.", env=self.app.env)
                self.after(0, lambda: self.push_msg.configure(text="Sent.", text_color=C["green"]))
            except Exception as e:
                msg = str(e)[:140]
                self.after(0, lambda: self.push_msg.configure(text=f"Failed: {msg}", text_color=C["red"]))
        threading.Thread(target=work, daemon=True).start()

    def _unpair(self):
        channels.save_subscription(None, self.app.env)
        self.app.env = load_env()
        self.push_sw.deselect()
        self._push_status()
        self._cloud_sync_later()

    def _open_calendar(self):
        self._save_channels()
        self._refresh_calendar()
        path = calendar_path()
        if path.exists():
            os.startfile(path.parent)
        else:
            messagebox.showinfo(APP_NAME, "Turn the calendar file on first; it is written after the next sync.")

    def _save_prefs(self):
        env = dict(self.app.env)
        env["ENABLE_VOICE"] = bool(self.voice.get())
        env["ENABLE_WINDOWS_TOAST"] = bool(self.toast.get())
        env["NOTIFY_DAYS_AHEAD"] = int(self.days.get())
        env["CLOSE_TO_TRAY"] = bool(self.tray_sw.get())
        env["CHECK_UPDATES"] = bool(self.updates_sw.get())
        if hasattr(self, "anim_sw"):
            env["ANIMATIONS"] = bool(self.anim_sw.get())
            ANIMATE["on"] = env["ANIMATIONS"]
        if hasattr(self, "track_att"):
            env["TRACK_ATTENDANCE"] = bool(self.track_att.get())
            env["TRACK_EXAMS"] = bool(self.track_exams.get())
            env["TRACK_RESULTS"] = bool(self.track_results.get())
            env["TRACK_ANNOUNCEMENTS"] = bool(self.track_ann.get())
            env["ATTENDANCE_MIN"] = int(self.att_min.get())
            env["EXAM_REMIND_DAYS"] = self.EXAM_LEAD.get(self.exam_days.get(), 1)
            env["TRACK_LECTURES"] = bool(self.track_lec.get())
            env["TRACK_TIMETABLE"] = bool(self.track_tt.get())
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
        self._cloud_sync_later()
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
        if messagebox.askyesno(APP_NAME, "Delete the locally saved assignments, attendance, exam plan, announcements and lecture list? "
                                          "The next sync will rebuild them."):
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
                     font=F(SM), text_color=C["muted"]).pack(side="left")
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
    NAV = [("dashboard", "Dashboard"), ("assignments", "Assignments"), ("attendance", "Attendance"), ("exams", "Exams"),
           ("results", "Results"), ("timetable", "Timetable"), ("announcements", "Announcements"), ("lectures", "Lectures"),
           ("settings", "Settings")]
    # pages reachable without a sidebar button (the activity log opens from Settings and from the Dashboard's
    # failed-checks line); the sidebar keeps Settings lit while one of them is shown
    TITLES = dict(NAV + [("activity", "Activity log")])
    UNDER_SETTINGS = {"activity"}
    CONTENT_MAX = 1120

    def __init__(self, start_view="dashboard", force_setup=False, start_hidden=False):
        self.env = load_env()
        self.theme = self.env.get("THEME", "dark")
        ctk.set_appearance_mode(self.theme)
        load_fonts()
        super().__init__(fg_color=C["bg"])
        pick_fonts()
        self.title(APP_NAME)
        ANIMATE["on"] = bool(self.env.get("ANIMATIONS", True))
        self._place_window()
        if ANIMATE["on"]:
            try:
                self.attributes("-alpha", 0.0)
                self.after(60, lambda: animate(self, 0.28, lambda t: self.attributes("-alpha", t)))
            except Exception:
                pass
        self.logo = self._load_logo()
        icon = ASSETS_DIR / "icon.ico"
        if icon.exists():
            try:
                self.iconbitmap(str(icon))
            except Exception:
                pass

        self.meta = load_meta()
        self.data = {}
        self.attendance = {}
        self.exams = []
        self.results = None
        self.announcements = []
        self.lectures = []
        self.timetable = {"semester": "", "sessions": []}
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
        # tasks registered by an older version lack the battery / wake settings; re-register them once, quietly
        self.after(8000, lambda: threading.Thread(target=automation.refresh_if_outdated, daemon=True).start())
        # cloud checks follow the installed version and the current settings
        self.after(9000, lambda: threading.Thread(target=self._cloud_housekeeping, daemon=True).start())

    def _cloud_housekeeping(self):
        try:
            if cloud.enabled(self.env):
                cloud.sync_secrets(load_env())
                cloud.warn_if_failing(load_env())
        except Exception as e:
            log.warning("Cloud housekeeping: %s", str(e)[:200])
            if "no longer accepts" in str(e):
                # the saved GitHub sign-in is dead: the scheduled runs continue on the repository's secrets, but
                # nothing from this PC reaches the cloud any more; say so once, not at every start
                from tracker import mark_reminder, reminder_sent
                if not reminder_sent("cloud-reauth"):
                    send_toast(f"{APP_NAME}: Cloud checks need a new sign-in",
                               "GitHub no longer accepts the saved sign-in. Open Settings → Cloud checks → Set up "
                               "to connect again. Scheduled cloud checks keep running meanwhile.")
                    mark_reminder("cloud-reauth")

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
        sv = self.views.get("settings") if self.views else None
        if sv is not None and "update_msg" in sv.__dict__:
            if info and info.get("newer"):
                sv.update_msg.configure(text=f"Version {info['version']} is available  ·  Install", text_color=C["accent"])
            elif info is None:
                sv.update_msg.configure(text="Could not reach GitHub. Try again in a while.", text_color=C["amber"])
            else:
                sv.update_msg.configure(text=f"Up to date ({APP_VERSION}).", text_color=C["green"])
        if info and info.get("newer"):
            text = f"Update {info['version']} available  ·  Install"
            if "update_lbl" in self.__dict__:
                self.update_lbl.configure(text=text)
            self.set_status(f"Version {info['version']} is available. Click Install at the top to update.")
            if self.tray:
                self.tray.set_tooltip(f"{APP_NAME} · update {info['version']} available")
        elif not quiet:
            if info is None:
                # stay in the app: a browser page is not an update, and offline it would not load either
                self.set_status("Could not reach GitHub to check for updates. Try again in a while.")
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
        w, h = min(1280, sw - 60), min(840, sh - 80)
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 20)}")
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

    # ---- resizing: a backdrop while the window changes size, then one clean reveal
    def _on_resize(self, e):
        """Tk paints every widget in its own time and has no double buffering, so after a maximize, a restore or a
        drag the old and the new layout show on top of each other for a tenth of a second. While the size is
        changing the window sits behind a plain backdrop; once it has been still for a moment the backdrop fades
        out over the finished page (the same window-alpha fade the page transitions use)."""
        if e.widget is not self or e.width < 50 or e.height < 50:
            return
        size = (e.width, e.height)
        if size == getattr(self, "_last_size", None):
            return
        first = not hasattr(self, "_last_size")
        self._last_size = size
        if first or "body" not in self.__dict__:
            return
        if getattr(self, "_backdrop", None) is None:
            bd = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
            bd.place(relx=0, rely=0, relwidth=1, relheight=1)
            bd.lift()
            self._backdrop = bd
        if getattr(self, "_resize_job", None):
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(140, self._resize_settled)

    def _resize_settled(self):
        self._resize_job = None
        bd, self._backdrop = getattr(self, "_backdrop", None), None
        if bd is None:
            return
        cover = None
        if ANIMATE["on"]:
            try:
                from PIL import Image
                dark = ctk.get_appearance_mode().lower() == "dark"
                colour = C["bg"][1] if dark else C["bg"][0]
                cover = cover_over(self, self, Image.new("RGB", (self.winfo_width(), self.winfo_height()), colour))
            except Exception:
                cover = None
        try:
            bd.destroy()
        except Exception:
            pass
        self.update_idletasks()                      # the page paints under the cover, unseen
        if cover is not None:
            fade_cover(cover, 0.18)

    def _bind_shortcuts(self):
        self.bind("<Configure>", self._on_resize, add="+")
        self.bind_all("<MouseWheel>", note_scroll, add="+")
        self.bind("<F5>", lambda e: self.start_sync())
        keys = (("<Prior>", ("page", -1)), ("<Next>", ("page", 1)), ("<Control-Home>", ("edge", 0)), ("<Control-End>", ("edge", 1)))
        for seq, what in keys:
            self.bind(seq, lambda e, w=what: self._key_scroll(w))
        for i, (key, _) in enumerate(self.NAV, start=1):
            self.bind(f"<Control-Key-{i}>", lambda e, k=key: self.navigate(k))
        self.bind("<Control-f>", lambda e: (self.navigate("assignments"), self.views["assignments"].focus_search()))

    def _key_scroll(self, what):
        focus = self.focus_get()
        if isinstance(focus, (tk_text_cls, tk_entry_cls)):
            return
        if self.current:
            page_scroll(self.views[self.current], what)

    # ---- theme
    def set_theme(self, theme):
        self.theme = theme
        env = dict(self.env)
        env["THEME"] = theme
        save_env(env)
        self.env = load_env()

        def switch():
            ctk.set_appearance_mode(theme)
            animate(self, 0.22, lambda t: self.attributes("-alpha", 0.55 + 0.45 * t))
        if ANIMATE["on"]:
            animate(self, 0.12, lambda t: self.attributes("-alpha", 1 - 0.45 * t), done=switch)
        else:
            ctk.set_appearance_mode(theme)

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

        side = ctk.CTkFrame(self.container, fg_color=C["side"], corner_radius=0, width=224)
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
        ctk.CTkLabel(bt, text=APP_NAME, font=F(LG, "semibold", display=True), text_color=C["ink"]).pack(anchor="w")
        ctk.CTkLabel(bt, text="Bahria University LMS", font=F(XS), text_color=C["muted"]).pack(anchor="w")

        self.nav_buttons = {}
        for key, label in self.NAV:
            item = ctk.CTkFrame(side, fg_color="transparent")
            item.pack(fill="x", padx=(0, 12), pady=1)
            bar = ctk.CTkFrame(item, fg_color="transparent", width=3, height=2, corner_radius=2)
            bar.pack(side="left", fill="y", pady=8)
            b = ctk.CTkButton(item, text=label, font=F(LG), height=40, anchor="w", corner_radius=10,
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
        ctk.CTkLabel(user, text=initials, font=F(SM, "semibold"), width=34, height=34, fg_color=C["accent"],
                     text_color=C["on_accent"], corner_radius=17).pack(side="left", padx=10, pady=10)
        ut = ctk.CTkFrame(user, fg_color="transparent")
        ut.pack(side="left", pady=10)
        ctk.CTkLabel(ut, text=name, font=F(SM, "semibold"), text_color=C["ink"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(ut, text=self.env.get("ENROLLMENT", ""), font=F(XS), text_color=C["muted"]).pack(anchor="w")

        content = ctk.CTkFrame(self.container, fg_color="transparent")
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(2, weight=1)
        content.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(content, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=32, pady=(20, 6))
        tt = ctk.CTkFrame(top, fg_color="transparent")
        tt.pack(side="left")
        self.page_title = ctk.CTkLabel(tt, text="", font=F(H2, "semibold", display=True), text_color=C["ink"])
        self.page_title.pack(anchor="w")
        self.last_sync_lbl = ctk.CTkLabel(tt, text="", font=F(SM), text_color=C["muted"])
        self.last_sync_lbl.pack(anchor="w")
        self._fail_streak = 0
        self.last_sync_lbl.bind("<Button-1>", lambda e: self.navigate("activity") if self._fail_streak else None)
        self.sync_btn = primary_button(top, "Sync now", self.start_sync, width=120)
        self.sync_btn.pack(side="right")
        self.update_lbl = ctk.CTkLabel(top, text="", font=F(SM, "semibold"), text_color=C["accent"], cursor="hand2")
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

        status = ctk.CTkFrame(content, fg_color=C["side"], corner_radius=0, height=28)
        status.grid(row=3, column=0, sticky="ew")
        ctk.CTkFrame(status, fg_color=C["line"], height=1, corner_radius=0).pack(fill="x", side="top")
        self.status_lbl = ctk.CTkLabel(status, text="Ready.", font=F(XS), text_color=C["muted"], anchor="w")
        self.status_lbl.pack(side="left", padx=32, pady=4)
        ctk.CTkLabel(status, text=f"F5 sync  ·  Ctrl+1–9 pages  ·  v{APP_VERSION}", font=F(XS),
                     text_color=C["dim"]).pack(side="right", padx=32)

        self.views = {
            "dashboard": DashboardView(self.body, self),
            "assignments": AssignmentsView(self.body, self),
            "attendance": AttendanceView(self.body, self),
            "exams": ExamsView(self.body, self),
            "results": ResultsView(self.body, self),
            "timetable": TimetableView(self.body, self),
            "announcements": AnnouncementsView(self.body, self),
            "lectures": LecturesView(self.body, self),
            "settings": SettingsView(self.body, self),
            "activity": ActivityView(self.body, self),
        }
        def lists_in(w, depth=0):
            # a scrollable frame sits two levels under its outer frame (outer frame > canvas > the frame itself)
            found = []
            for c in w.winfo_children():
                if isinstance(c, ctk.CTkScrollableFrame):
                    found.append(c)
                elif depth < 3:
                    found += lists_in(c, depth + 1)
            return found
        for view in self.views.values():
            # a page that holds exactly one list scrolls it with the wheel anywhere on the page (toolbar included)
            lists = lists_in(view)
            if not isinstance(view, ctk.CTkScrollableFrame) and len(lists) == 1:
                view._page_scroller = lists[0]
        self.reload_data()
        self.navigate("dashboard")
        if self.syncing:
            self._show_syncing(True)

    def navigate(self, key, **kwargs):
        if not self.views or getattr(self, "_navigating", False):
            return
        self._navigating = True            # the fade pumps the event loop; a second click meanwhile is ignored
        try:
            self._navigate(key, **kwargs)
        finally:
            self._navigating = False

    def _navigate(self, key, **kwargs):
        for k, (b, bar) in self.nav_buttons.items():
            active = k == key or (key in self.UNDER_SETTINGS and k == "settings")
            b.configure(fg_color=C["surface2"] if active else "transparent",
                        text_color=C["ink"] if active else C["muted"],
                        font=F(LG, "semibold" if active else "normal"))
            bar.configure(fg_color=C["accent"] if active else "transparent")
        leaving = self.views.get(self.current) if self.current else None
        view = self.views[key]
        # Pages cross-fade: the page being left is photographed and the picture shown in a borderless window over
        # the page area; the pages swap and the new one paints underneath; the picture then fades out. One picture
        # fading is the only transition Tk can do smoothly; fading hundreds of widgets is not possible.
        cover = None
        if ANIMATE["on"] and leaving is not None and leaving is not view:
            before = snapshot(getattr(leaving, "_parent_frame", leaving))
            if before is not None:
                cover = cover_over(self, self.body, before)
        if leaving is not None:
            leaving.pack_forget()
        self.current = key
        self.page_title.configure(text=self.TITLES[key])
        # a page is rebuilt only when the data or the settings behind it changed since it was last drawn (the
        # dashboard also every minute for its countdowns and "now" markers, the activity log every time), and it is
        # rebuilt before it is packed, so it appears in one piece instead of assembling itself on screen
        stamp = (self.data_version, id(self.env))
        stale = (getattr(view, "_drawn_for", None) != stamp or key == "activity"
                 or (key == "dashboard" and time.monotonic() - getattr(view, "_drawn_at", 0) > 60))
        if key == "assignments" and kwargs:
            view.apply(kwargs.get("filter_name"), kwargs.get("course"))
            view._drawn_for, view._drawn_at = stamp, time.monotonic()
        elif hasattr(view, "refresh") and stale:
            view.refresh()
            view._drawn_for, view._drawn_at = stamp, time.monotonic()
        view.pack(fill="both", expand=True)
        if cover is not None:
            self.update()                  # the new page lays out and paints under the cover
            fade_cover(cover)

    # ---- data
    @property
    def semester_empty(self):
        """True after a check that found no courses on the portal: between semesters, before registration."""
        return bool(self.meta.get("last_sync")) and "courses" in self.meta and not self.meta.get("courses")

    def empty_semester_text(self):
        sem = (self.meta.get("semester") or "").strip()
        return ((f"The portal lists no courses for {sem}." if sem else "The portal lists no courses yet.")
                + " There is nothing to track until registration goes through; checks keep running in the "
                  "background and this page fills in on its own.")

    def show_crash(self, details):
        """One dialog for an error inside the window: what happened, a Copy button, the log, a pre-filled issue."""
        try:
            dlg = ctk.CTkToplevel(self)
            dlg.title("Something went wrong")
            dlg.geometry("620x468")
            dlg.resizable(False, False)
            dlg.transient(self)
            dlg.configure(fg_color=C["bg"])
            body = ctk.CTkFrame(dlg, fg_color="transparent")
            body.pack(fill="both", expand=True, padx=28, pady=22)
            ctk.CTkLabel(body, text="Something went wrong", font=F(H3, "semibold", display=True), text_color=C["ink"],
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(body, text="A part of the app hit an error and stopped what it was doing. The rest keeps running; "
                                    "if things look off, close and reopen the app. Nothing of yours was lost.",
                         font=F(SM), text_color=C["muted"], wraplength=560, justify="left", anchor="w").pack(fill="x", pady=(6, 12))
            box = ctk.CTkTextbox(body, height=150, font=F(XS), fg_color=C["surface2"], text_color=C["ink"], wrap="word",
                                 corner_radius=10)
            box.pack(fill="x")
            box.insert("1.0", details)
            box.configure(state="disabled")
            ctk.CTkLabel(body, text="Report on GitHub opens a pre-filled issue with the app version, your Windows version and "
                                    "the lines above, nothing else. Read it over before you post it.",
                         font=F(XS), text_color=C["dim"], wraplength=560, justify="left", anchor="w").pack(fill="x", pady=(10, 14))
            btns = ctk.CTkFrame(body, fg_color="transparent")
            btns.pack(fill="x", side="bottom")

            def copy():
                self.clipboard_clear()
                self.clipboard_append(details)
                copy_btn.configure(text="Copied")
                dlg.after(1500, lambda: copy_btn.configure(text="Copy details"))
            copy_btn = soft_button(btns, "Copy details", copy, width=120)
            copy_btn.pack(side="left")
            soft_button(btns, "Open log", lambda: os.startfile(LOG_PATH), width=100).pack(side="left", padx=8)
            soft_button(btns, "Report on GitHub", lambda: webbrowser.open(crash.report_url(details)), width=150).pack(side="left")
            primary_button(btns, "Close", dlg.destroy, width=100).pack(side="right")
            dlg.after(50, dlg.lift)
        except Exception:
            log.exception("The crash dialog itself failed")

    def reload_data(self):
        self.data_version = getattr(self, "data_version", 0) + 1
        self.data = load_stored_assignments()
        self.attendance = load_attendance()
        self.exams = load_exams()
        self.results = load_results()
        self.announcements = load_announcements()
        self.lectures = load_lectures()
        self.timetable = load_timetable()
        self.meta = load_meta()
        if "last_sync_lbl" in self.__dict__:
            ls = self.meta.get("last_sync")
            if ls:
                try:
                    ls = datetime.fromisoformat(ls).strftime("%d %b, %I:%M %p").replace(" 0", " ")
                except ValueError:
                    pass
            text = f"Last sync {ls}" if ls else "Not synced yet"
            streak = int(self.meta.get("fail_streak") or 0)
            self._fail_streak = streak
            if streak:
                text += f"  ·  {streak} check{'s' if streak != 1 else ''} failed since. Click for the activity log."
            self.last_sync_lbl.configure(text=text, text_color=C["amber"] if streak else C["muted"], cursor="hand2" if streak else "")
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
            env = load_env()
            data = run_sync(headless=True, collect=collectors_for(env), previous_attendance=load_attendance(),
                            progress=lambda m: self.after(0, self.set_status, m))
            s = process_sync(data, env, notify=True)
            bits = [f"Synced {s['assignments']} assignments · {s['pending']} pending"]
            if s.get("new"):
                bits.append(f"{s['new']} new")
            if s.get("below"):
                bits.append(f"{s['below']} course{'s' if s['below'] != 1 else ''} under {int(env.get('ATTENDANCE_MIN', 75))}% attendance")
            if s.get("new_announcements"):
                bits.append(f"{s['new_announcements']} new announcement{'s' if s['new_announcements'] != 1 else ''}")
            if s.get("new_lectures"):
                bits.append(f"{s['new_lectures']} new lecture week{'s' if s['new_lectures'] != 1 else ''}")
            if data.get("errors"):
                bits.append("some pages could not be read (see Activity)")
            result = (True, " · ".join(bits))
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
