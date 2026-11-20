"""Accessibility and layout audit of the built interface on fictional data: axe-core on every page, in light and dark, in all
four palettes, plus a narrow-window check for horizontal scrolling.

    python tools/audit_a11y.py <path to axe.min.js>

Needs `npm run build` in ui/ and Playwright's Chrome. Exits 1 when axe reports a violation or a page scrolls sideways.
"""
import functools
import http.server
import json
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

PAGES = ["#/", "#/assignments", "#/attendance", "#/exams", "#/timetable", "#/results", "#/lectures", "#/announcements",
         "#/settings/profile", "#/settings/appearance", "#/settings/notifications", "#/settings/tracking", "#/settings/background",
         "#/settings/data", "#/settings/activity", "#/settings/about"]
PALETTES = ["royal", "ink", "forest", "ember"]


def main(axe_path: Path) -> int:
    from playwright.sync_api import sync_playwright
    axe = axe_path.read_text(encoding="utf-8")
    home = Path(tempfile.mkdtemp(prefix="am-a11y-"))
    seed.seed(home)
    engine = subprocess.Popen([sys.executable, str(ROOT / "engine.py"), "--dev"], cwd=ROOT, env=dict(os.environ, ASSIGNMENT_MONITOR_HOME=str(home)),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "ui" / "dist"))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 5173), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    problems = []
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
                for palette in PALETTES:
                    ctx = browser.new_context(viewport={"width": 1280, "height": 840}, color_scheme=theme)
                    ctx.add_init_script(f"localStorage.setItem('am-theme','{theme}');localStorage.setItem('am-palette','{palette}');localStorage.setItem('am-motion','off');")
                    page = ctx.new_page()
                    for h in PAGES:
                        page.goto(f"http://127.0.0.1:5173/{h}")
                        page.wait_for_selector("h1", timeout=20000)
                        page.wait_for_timeout(500)
                        page.evaluate(axe)
                        res = page.evaluate("axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21aa','best-practice']})")
                        for v in res["violations"]:
                            problems.append(f"{theme}/{palette} {h}: {v['id']} ({v['impact']}) x{len(v['nodes'])}: {v['nodes'][0]['target']}")
                    ctx.close()
            for width in (360, 600):
                ctx = browser.new_context(viewport={"width": width, "height": 800})
                ctx.add_init_script("localStorage.setItem('am-motion','off');")
                page = ctx.new_page()
                for h in PAGES:
                    page.goto(f"http://127.0.0.1:5173/{h}")
                    page.wait_for_selector("h1", timeout=20000)
                    page.wait_for_timeout(400)
                    over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                    if over > 1:
                        problems.append(f"{width}px {h}: scrolls sideways by {over}px")
                ctx.close()
            browser.close()
    finally:
        srv.shutdown()
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(engine.pid)], capture_output=True) if os.name == "nt" else engine.terminate()   # the whole tree: the launcher spawns the real engine
    seen = sorted(set(problems))
    print(json.dumps(seen, indent=1) if seen else "No violations")
    print(f"{len(problems)} findings, {len(seen)} distinct")
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1])))
