"""The real window on throwaway data: every page draws, and the button paths that only exist in the GUI run without
a Tk error. The lecture download used to raise "window ... isn't packed" the moment Download was pressed, which no
unit test could see. One window per module, driven inside its own main loop (worker threads call `after`, which
needs the loop to be running). Skipped where no display is available."""
import time

import pytest

tk = pytest.importorskip("tkinter")

LECTURES = [
    {"id": "Cybe1", "course": "Cyber Security", "week": "1", "title": "Cyber Security Concepts",
     "files": [{"label": "Download Lecture", "href": "Download.php?k=Cyb10", "filename": "Lec-1-Cyber-Security-Concepts.pptx"}],
     "videos": [], "remarks": "", "first_seen": "2026-09-13T01:20:25"},
    {"id": "Cybe2", "course": "Cyber Security", "week": "2", "title": "Threat Models",
     "files": [{"label": "Download Lecture", "href": "Download.php?k=Cyb11", "filename": "Lec-2-Threat-Models.pdf"},
               {"label": "Lab", "href": "Download.php?k=Cyb12", "filename": "Lab-2.pdf"}],
     "videos": [], "remarks": "", "first_seen": "2026-09-20T01:20:25"},
]


def run_steps(win, steps, settle_ms=120):
    """Runs (delay_ms, fn) pairs inside the window's main loop; returns the exceptions the functions raised."""
    errors = []

    def go(i):
        if i >= len(steps):
            win.after(settle_ms, win.quit)
            return
        delay, fn = steps[i]

        def call():
            try:
                fn()
            except Exception as e:                       # noqa: BLE001 - every failure is reported after the loop
                errors.append(e)
            go(i + 1)
        win.after(delay, call)
    go(0)
    win.mainloop()
    return errors


@pytest.fixture(scope="module")
def gui(tmp_path_factory):
    try:
        probe = tk.Tk()
        probe.destroy()
    except tk.TclError:
        pytest.skip("no display")
    mp = pytest.MonkeyPatch()
    tmp_path = tmp_path_factory.mktemp("gui")
    import config
    import tracker
    import app as m
    for name in ("DB_PATH", "ATTENDANCE_PATH", "EXAMS_PATH", "ANNOUNCEMENTS_PATH", "REMINDERS_PATH", "LECTURES_PATH", "TIMETABLE_PATH"):
        mp.setattr(tracker, name, tmp_path / f"{name.lower()}.json")
    mp.setattr(config, "META_PATH", tmp_path / "meta.json")
    mp.setenv("AM_ENROLLMENT", "01-111111-111")
    mp.setenv("AM_PASSWORD", "x")
    mp.setattr(m, "save_env", lambda env: None)              # nothing of the test lands in settings
    tracker._save_json(tracker.LECTURES_PATH, LECTURES)
    config.save_meta({"student_name": "Test Student", "semester": "Fall-2026", "courses": ["Cyber Security"],
                      "last_sync": "2026-10-23T19:00:00", "last_result": "ok"})
    win = m.App(start_view="lectures")
    win.geometry("1100x700+10+10")
    yield win, m
    try:
        win.quit_app()                                        # stops the tray thread too; destroy() alone leaves it running
    except tk.TclError:
        pass
    mp.undo()


def test_every_page_draws(gui):
    win, m = gui
    seen = []
    pages = ("dashboard", "assignments", "attendance", "exams", "timetable", "announcements", "lectures", "settings", "activity")
    steps = [(300, lambda key=key: (win.navigate(key), seen.append(win.current))) for key in pages]
    errors = run_steps(win, steps, settle_ms=400)
    assert errors == []
    assert seen == list(pages)


def test_lecture_download_shows_progress_and_finishes(gui, monkeypatch):
    win, m = gui
    view = win.views["lectures"]
    seen, state = {}, {}

    def fake_download(chosen, dest, progress=None, should_stop=None):
        seen["chosen"] = chosen
        if progress:
            progress("Lec-1-Cyber-Security-Concepts.pptx", 1, 2)
        time.sleep(0.2)
        return {"saved": ["Lec-1-Cyber-Security-Concepts.pptx", "Lab-2.pdf"], "skipped": 0, "failed": []}
    monkeypatch.setattr(m, "download_lectures", fake_download)
    monkeypatch.setattr(m.os, "startfile", lambda p: None)

    def start():
        win.navigate("lectures")
        view.selected.add(("Cybe1", 0))
        view.selected.add(("Cybe2", 1))
        view._download()                                  # raised TclError ("isn't packed") before the fix
        state["busy"] = view.busy
        state["progress_shown"] = view.progress.winfo_manager()

    def finished():
        state["busy_after"] = view.busy
        state["progress_after"] = view.progress.winfo_manager()
        state["selected_after"] = set(view.selected)
    errors = run_steps(win, [(200, start), (1500, finished)])
    assert errors == []
    assert state["busy"] is True and state["progress_shown"] == "pack"
    assert state["busy_after"] is False and state["progress_after"] == ""
    files = sorted(f["filename"] for x in seen["chosen"] for f in x["files"])
    assert files == ["Lab-2.pdf", "Lec-1-Cyber-Security-Concepts.pptx"]
    assert state["selected_after"] == set()               # a clean result clears the selection
