"""Prints the details of one axe rule on every page (for fixing): python tools/axe_detail.py <axe.min.js> <rule> [palette] [theme]"""
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
from tools.audit_a11y import PAGES  # noqa: E402


def main(axe_path, rule, palette="royal", theme="light"):
    from playwright.sync_api import sync_playwright
    axe = Path(axe_path).read_text(encoding="utf-8")
    home = Path(tempfile.mkdtemp(prefix="am-axe-"))
    seed.seed(home)
    engine = subprocess.Popen([sys.executable, str(ROOT / "engine.py"), "--dev"], cwd=ROOT, env=dict(os.environ, ASSIGNMENT_MONITOR_HOME=str(home)),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "ui" / "dist"))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 5173), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8765/api/state", headers={"Authorization": "Bearer dev"}), timeout=2)  # nosec B310 - a fixed loopback address
                break
            except Exception:
                time.sleep(0.5)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            ctx = browser.new_context(viewport={"width": 1280, "height": 840}, color_scheme=theme)
            ctx.add_init_script(f"localStorage.setItem('am-theme','{theme}');localStorage.setItem('am-palette','{palette}');localStorage.setItem('am-motion','off');")
            page = ctx.new_page()
            for h in PAGES:
                page.goto(f"http://127.0.0.1:5173/{h}")
                page.wait_for_selector("h1", timeout=20000)
                page.wait_for_timeout(400)
                page.evaluate(axe)
                res = page.evaluate(f"axe.run(document, {{runOnly: {{type: 'rule', values: ['{rule}']}}}})")
                for v in res["violations"]:
                    for n in v["nodes"]:
                        d = (n["any"] + n["all"] + n["none"])[0]
                        print(h, "|", n["html"][:110].replace("\n", " "), "|", d["message"][:170])
            browser.close()
    finally:
        srv.shutdown()
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(engine.pid)], capture_output=True) if os.name == "nt" else engine.terminate()   # the whole tree: the launcher spawns the real engine


if __name__ == "__main__":
    main(*sys.argv[1:5])
