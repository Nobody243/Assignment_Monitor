"""Screenshots of the phone prototype (mobile/build/web) at phone size:  python tools/shoot_mobile.py <output folder>

Needs `flutter build web --release` in mobile/ first. Flutter draws to a canvas, so screens are reached by tapping
at positions, not by selectors."""
import functools
import http.server
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W, H = 390, 844


def main(out: Path):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "mobile" / "build" / "web"))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 5199), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
            for scheme in ("light", "dark"):
                ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2, color_scheme=scheme)
                pg = ctx.new_page()
                pg.goto("http://127.0.0.1:5199/")
                pg.wait_for_timeout(9000)
                tabs = {"today": 49, "work": 146, "attendance": 244, "more": 341}      # bottom bar, x positions
                for name, x in tabs.items():
                    pg.mouse.click(x, H - 32)
                    pg.wait_for_timeout(900)
                    pg.screenshot(path=str(out / f"mobile-{name}-{scheme}.png"))
                    print("wrote", name, scheme)
                if scheme == "light":
                    pg.mouse.click(146, H - 32)                                           # Work: open the first card
                    pg.wait_for_timeout(700)
                    pg.mouse.click(195, 215)
                    pg.wait_for_timeout(900)
                    pg.screenshot(path=str(out / "mobile-work-detail-light.png"))
                    pg.keyboard.press("Escape")
                    pg.mouse.click(195, 100)
                    pg.wait_for_timeout(500)
                    pg.mouse.click(341, H - 32)                                           # More: each page
                    pg.wait_for_timeout(700)
                    for name, y in (("exams", 90), ("timetable", 164), ("results", 238), ("settings", 312)):
                        pg.mouse.click(195, y)
                        pg.wait_for_timeout(1000)
                        pg.screenshot(path=str(out / f"mobile-{name}-light.png"))
                        pg.keyboard.press("Escape")
                        pg.go_back() if False else pg.mouse.click(28, 36)                 # the app bar's back arrow
                        pg.wait_for_timeout(700)
                ctx.close()
            b.close()
    finally:
        srv.shutdown()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
