"""Takes the website's screenshots of the real interface on FICTIONAL data (tools/seed_demo_data.py).

    python tools/capture_screens.py <output folder> [palette]

Starts the engine on a throw-away data folder, serves ui/dist, opens each page at 1280x840 in light and dark, and writes
shot-<page>-<theme>.png files. Needs `npm run build` in ui/ first and Playwright's Chrome (already a dependency).
"""
import functools
import http.server
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tools.seed_demo_data as seed  # noqa: E402

PAGES = {"dashboard": "#/", "assignments": "#/assignments", "attendance": "#/attendance", "exams": "#/exams", "results": "#/results",
         "timetable": "#/timetable", "lectures": "#/lectures", "announcements": "#/announcements", "settings": "#/settings/profile"}


def main(out: Path, palette: str = "ember"):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    home = Path(tempfile.mkdtemp(prefix="am-shots-"))
    seed.seed(home)
    env = dict(os.environ, ASSIGNMENT_MONITOR_HOME=str(home))
    engine = subprocess.Popen([sys.executable, str(ROOT / "engine.py"), "--dev"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "ui" / "dist"))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 5173), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8765/api/state", headers={"Authorization": "Bearer dev"}), timeout=2)
                break
            except Exception:
                time.sleep(0.5)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            for theme in ("light", "dark"):
                ctx = browser.new_context(viewport={"width": 1280, "height": 840}, device_scale_factor=1, color_scheme=theme)
                ctx.add_init_script(f"localStorage.setItem('am-theme','{theme}');localStorage.setItem('am-palette','{palette}');localStorage.setItem('am-motion','off');")
                page = ctx.new_page()
                for name, hash_ in PAGES.items():
                    page.goto(f"http://127.0.0.1:5173/{hash_}")
                    page.wait_for_selector("h1", timeout=20000)
                    page.wait_for_timeout(900)
                    page.screenshot(path=str(out / f"shot-{name}-{theme}.png"))
                    print("wrote", name, theme)
                ctx.close()
            browser.close()
    finally:
        srv.shutdown()
        engine.terminate()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), *(sys.argv[2:3]))
