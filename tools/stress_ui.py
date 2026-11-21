# ruff: noqa: E702, B007
"""Stress test for the desktop interface (ui/): hammers the sidebar, the settings sections, tab strips, menus, the command
palette, the collapsing sidebar and window resizing, then checks that the interface is still in one consistent state.

    cd ui && npm run dev -- --port 5173 --strictPort     (in another terminal)
    python tools/stress_ui.py [http://localhost:5173] [--rounds N] [--seed N]

It uses the built-in sample data (the engine does not need to run). After every storm it waits for the animations to
settle and asserts: the sliding marker sits exactly on the chosen item, the URL and the highlighted item agree, no menu or
overlay is left open, nothing blocks the pointer, there is no horizontal overflow, and no console error or uncaught
exception happened. Exit code 0 means every check held.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opts = dict(a.lstrip("-").split("=", 1) if "=" in a else (a.lstrip("-"), "1") for a in sys.argv[1:] if a.startswith("--"))
URL = args[0] if args else "http://localhost:5173"
ROUNDS = int(opts.get("rounds", 150))
SEED = int(opts.get("seed", random.randrange(10_000)))
rng = random.Random(SEED)

PAGES = ["Home", "Assignments", "Attendance", "Exams", "Timetable", "Results", "Lectures", "Announcements", "Settings"]
SECTIONS = ["Profile", "Appearance", "Notifications", "Tracking", "Background and cloud", "Data and files", "Activity", "About"]
problems: list[str] = []
errors: list[str] = []
checks = 0


def check(ok: bool, what: str) -> None:
    global checks
    checks += 1
    if not ok:
        problems.append(what)
        print("  FAIL:", what)


def settle(pg: Page, ms: int = 700) -> None:
    pg.wait_for_timeout(ms)


def marker_matches(pg: Page, host_sel: str, active_sel: str, what: str, tol: float = 1.5) -> None:
    """The sliding marker must sit exactly on the chosen item (after settling)."""
    r = pg.evaluate(
        """([h, a]) => {
          const host = document.querySelector(h); const act = host && host.querySelector(a);
          const mk = host && host.querySelector(':scope > [data-slot=slide-marker], [data-slot=slide-marker]');
          if (!host || !act || !mk) return {missing: !host ? 'host' : !act ? 'active' : 'marker'};
          const m = mk.getBoundingClientRect(), b = act.getBoundingClientRect();
          return {dx: Math.abs(m.left - b.left), dy: Math.abs(m.top - b.top), dw: Math.abs(m.width - b.width), dh: Math.abs(m.height - b.height), op: getComputedStyle(mk).opacity};
        }""",
        [host_sel, active_sel],
    )
    if "missing" in r:
        check(False, f"{what}: {r['missing']} not found")
        return
    check(max(r["dx"], r["dy"], r["dw"], r["dh"]) <= tol and float(r["op"]) > 0.99, f"{what}: marker off by {r}")


def clean_state(pg: Page, what: str) -> None:
    r = pg.evaluate(
        """() => ({
          menus: document.querySelectorAll('[role=menu], [role=listbox], [data-slot=dropdown-menu-content], [data-slot=select-content]').length,
          dialogs: document.querySelectorAll('[role=dialog][data-state=open], [role=alertdialog][data-state=open]').length,
          bodyPE: getComputedStyle(document.body).pointerEvents,
          scrollLock: document.body.hasAttribute('data-scroll-locked'),
          hOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          pages: document.querySelectorAll('.page-enter').length,
          palette: document.documentElement.dataset.palette,
        })"""
    )
    check(r["menus"] == 0, f"{what}: {r['menus']} menu(s) left open")
    check(r["dialogs"] == 0, f"{what}: {r['dialogs']} dialog(s) left open")
    check(r["bodyPE"] != "none", f"{what}: body pointer-events is none (a closed menu left the page dead)")
    check(not r["scrollLock"], f"{what}: scroll lock left on")
    check(r["hOverflow"] <= 1, f"{what}: horizontal overflow {r['hOverflow']}px")
    check(r["pages"] == 1, f"{what}: {r['pages']} page wrappers (expected exactly 1)")
    check(r["palette"] in ("royal", "ink", "forest", "ember"), f"{what}: palette is {r['palette']!r}")


def nav(pg: Page, name: str) -> None:
    pg.locator("[data-sidebar=content] [data-sidebar=menu-button]", has_text=name).first.click(timeout=3000, delay=0)


def active_page(pg: Page) -> str:
    return pg.evaluate("() => document.querySelector(\"[data-sidebar=content] [data-sidebar=menu-button][data-active=true]\")?.textContent?.trim() ?? ''")


def hash_page(pg: Page) -> str:
    h = pg.evaluate("() => location.hash").lstrip("#/").split("/")[0] or "home"
    return {"home": "Home"}.get(h, h.capitalize())


with sync_playwright() as p:
    # the PC's own Chrome (or Edge) is used, so nothing has to be downloaded
    for channel in ("chrome", "msedge", None):
        try:
            browser = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
            break
        except Exception as e:  # noqa: BLE001
            last = e
    else:
        raise SystemExit(f"no browser to drive: {last}")
    ctx = browser.new_context(viewport={"width": 1366, "height": 820})
    pg = ctx.new_page()
    pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text[:200]}") if m.type == "error" and "ERR_CONNECTION_REFUSED" not in m.text and "Failed to load resource" not in m.text else None)
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {str(e)[:200]}"))

    try:
        print(f"stress_ui  url={URL}  rounds={ROUNDS}  seed={SEED}")
        pg.goto(URL)
        pg.get_by_role("button", name="View sample data").click(timeout=15000)
        settle(pg, 900)
        check(active_page(pg) == "Home", "starts on Home")
        marker_matches(pg, "[data-sidebar=content]", "[data-sidebar=menu-button][data-active=true]", "sidebar at start")

        # ---- 1. the sidebar, clicked as fast as a hand can
        print("1. rapid sidebar navigation")
        last = "Home"
        for _ in range(ROUNDS * 2):
            last = rng.choice(PAGES)
            nav(pg, last)
            pg.wait_for_timeout(rng.choice([0, 0, 5, 15, 30, 80]))
        settle(pg)
        check(active_page(pg) == last, f"sidebar shows {active_page(pg)!r}, last click was {last!r}")
        check(hash_page(pg).lower().startswith(last.lower()[:5]) or last == "Home", f"url page {hash_page(pg)!r} vs {last!r}")
        marker_matches(pg, "[data-sidebar=content]", "[data-sidebar=menu-button][data-active=true]", "sidebar after rapid clicks")
        clean_state(pg, "after rapid navigation")

        # ---- 2. the page entrance runs in the right direction and always finishes
        print("2. page entrance direction")
        nav(pg, "Home"); settle(pg, 400)
        nav(pg, "Results"); pg.wait_for_timeout(30)
        check(pg.evaluate("() => document.querySelector('.page-enter')?.dataset.dir") == "1", "going down the list enters from below (dir 1)")
        settle(pg, 500)
        nav(pg, "Exams"); pg.wait_for_timeout(30)
        check(pg.evaluate("() => document.querySelector('.page-enter')?.dataset.dir") == "-1", "going up the list enters from above (dir -1)")
        settle(pg, 500)
        check(float(pg.evaluate("() => getComputedStyle(document.querySelector('.page-enter')).opacity")) > 0.99, "page is fully visible after the entrance")

        # ---- 3. keyboard: arrows walk the sidebar, Enter opens
        print("3. keyboard in the sidebar")
        nav(pg, "Home"); settle(pg, 300)
        pg.locator("[data-sidebar=content] [data-sidebar=menu-button]").first.focus()
        for _ in range(60):
            pg.keyboard.press(rng.choice(["ArrowDown", "ArrowDown", "ArrowUp", "Home", "End"]))
        pg.keyboard.press("Home")
        pg.keyboard.press("ArrowDown")
        pg.keyboard.press("Enter")
        settle(pg)
        check(active_page(pg) == "Assignments", f"Home, Down, Enter opens Assignments (got {active_page(pg)!r})")
        pg.keyboard.press("End")
        pg.keyboard.press("Enter")
        settle(pg)
        check(active_page(pg) == "Settings", f"End, Enter opens Settings (got {active_page(pg)!r})")
        for n in range(1, 10):
            pg.keyboard.press(f"Control+{n}")
            pg.wait_for_timeout(rng.choice([0, 10, 40]))
        settle(pg)
        check(active_page(pg) == "Settings", f"Ctrl+1..9 ends on page 9 (Settings), got {active_page(pg)!r}")
        marker_matches(pg, "[data-sidebar=content]", "[data-sidebar=menu-button][data-active=true]", "sidebar after keyboard storm")

        # ---- 4. settings sections
        print("4. settings sections")
        nav(pg, "Settings"); settle(pg, 400)
        sec = "Profile"
        for _ in range(ROUNDS * 2):
            sec = rng.choice(SECTIONS)
            pg.locator("nav[aria-label='Settings sections'] button", has_text=sec).first.click(timeout=3000, delay=0)
            pg.wait_for_timeout(rng.choice([0, 0, 10, 40]))
        settle(pg)
        cur = pg.evaluate("() => document.querySelector(\"nav[aria-label='Settings sections'] [aria-current=page]\")?.textContent?.trim()")
        check(cur == sec, f"settings section {cur!r} vs last click {sec!r}")
        marker_matches(pg, "nav[aria-label='Settings sections']", "[aria-current=page]", "settings sections marker")
        pg.locator("nav[aria-label='Settings sections'] button").first.focus()
        for _ in range(40):
            pg.keyboard.press(rng.choice(["ArrowDown", "ArrowUp", "Home", "End"]))
        pg.keyboard.press("Enter")
        settle(pg)
        marker_matches(pg, "nav[aria-label='Settings sections']", "[aria-current=page]", "settings sections marker after keys")
        clean_state(pg, "after settings storm")

        # ---- 5. tab strips
        print("5. tab strips")
        nav(pg, "Assignments"); settle(pg, 500)
        tabs = pg.locator("[data-slot=tabs-trigger]")
        n = tabs.count()
        check(n >= 3, f"assignment filter tabs present ({n})")
        for _ in range(ROUNDS * 2):
            tabs.nth(rng.randrange(n)).click(timeout=3000, delay=0)
            pg.wait_for_timeout(rng.choice([0, 0, 10, 50]))
        settle(pg)
        marker_matches(pg, "[data-slot=tabs-list]", "[data-state=active]", "tab strip marker")
        check(pg.locator("[data-slot=tabs-trigger][data-state=active]").count() == 1, "exactly one active tab")

        # ---- 6. the account menu and its submenus
        print("6. account menu and submenus")
        trigger = pg.locator("[data-sidebar=footer] [data-sidebar=menu-button]").first
        def close_any_menu() -> None:
            """A person would press Escape on a menu still open; it must then really close (within its closing animation)."""
            for _ in range(3):
                if trigger.get_attribute("aria-expanded") != "true":
                    return
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(250)
            check(trigger.get_attribute("aria-expanded") != "true", "the account menu would not close with Escape")

        def wait_for_page_to_listen() -> None:
            """While a menu is closing the page ignores the pointer for a moment; it must always start listening again."""
            for _ in range(30):
                if pg.evaluate("() => getComputedStyle(document.body).pointerEvents !== 'none' && !document.querySelector('[role=menu]')"):
                    return
                pg.wait_for_timeout(50)
            check(False, "the page kept ignoring the pointer, or a menu stayed in the page, after a menu closed")

        for i in range(ROUNDS):
            close_any_menu()
            wait_for_page_to_listen()
            trigger.click(timeout=3000, delay=0)
            pg.wait_for_timeout(rng.choice([0, 15, 60]))
            how = rng.choice(["escape", "toggle", "outside", "submenu"])
            if how == "escape":
                pg.keyboard.press("Escape")
            elif how == "toggle":
                # a modal menu makes the page ignore the pointer, so this click is "outside" and closes it, like for a real hand
                trigger.click(timeout=3000, delay=0, force=True)
            elif how == "outside":
                pg.mouse.click(700, 400)
            else:
                pg.keyboard.press("ArrowDown"); pg.keyboard.press("ArrowRight")
                pg.wait_for_timeout(rng.choice([0, 30, 120]))
                pg.keyboard.press("ArrowLeft"); pg.keyboard.press("Escape")
            pg.wait_for_timeout(rng.choice([0, 10, 40]))
            if pg.locator("[role=menu]").count():
                pg.keyboard.press("Escape"); pg.keyboard.press("Escape")
        settle(pg)
        clean_state(pg, "after menu storm")

        print("   palette and theme from the submenus, quickly")
        for i in range(30):
            close_any_menu()
            wait_for_page_to_listen()
            pg.wait_for_timeout(350)   # about the time a person needs to pick a menu item and reach for the trigger again
            trigger.click(timeout=3000)
            pg.get_by_role("menuitem", name="Palette").click(timeout=3000)
            pg.get_by_role("menuitemradio", name=rng.choice(["Royal", "Ink", "Forest", "Ember"])).click(timeout=3000)
            pg.wait_for_timeout(rng.choice([0, 30]))
            close_any_menu()
            wait_for_page_to_listen()
            pg.wait_for_timeout(350)   # about the time a person needs to pick a menu item and reach for the trigger again
            trigger.click(timeout=3000)
            pg.get_by_role("menuitem", name="Theme").click(timeout=3000)
            pg.get_by_role("menuitemradio", name=rng.choice(["Light", "Dark"])).click(timeout=3000)
            pg.wait_for_timeout(rng.choice([0, 30]))
        settle(pg)
        clean_state(pg, "after palette and theme storm")
        marker_matches(pg, "[data-sidebar=content]", "[data-sidebar=menu-button][data-active=true]", "sidebar after theme changes")

        # ---- 7. collapse and expand the sidebar
        print("7. collapsing the sidebar")
        for _ in range(ROUNDS // 2 + 20):
            pg.keyboard.press("Control+b")
            pg.wait_for_timeout(rng.choice([0, 20, 90, 250]))
        settle(pg, 900)
        state = pg.evaluate("() => document.querySelector('[data-slot=sidebar]')?.dataset.state")
        check(state in ("expanded", "collapsed"), f"sidebar state is {state!r}")
        marker_matches(pg, "[data-sidebar=content]", "[data-sidebar=menu-button][data-active=true]", f"sidebar marker while {state}")
        if state == "collapsed":
            pg.keyboard.press("Control+b"); settle(pg, 900)
        marker_matches(pg, "[data-sidebar=content]", "[data-sidebar=menu-button][data-active=true]", "sidebar marker expanded again")

        # ---- 8. the command palette and the help dialog
        print("8. command palette")
        for _ in range(ROUNDS // 2):
            pg.keyboard.press("Control+k")
            pg.wait_for_timeout(rng.choice([0, 20, 80]))
            if rng.random() < 0.5:
                pg.keyboard.type(rng.choice(["att", "set", "zzz", "home"]), delay=0)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(rng.choice([0, 20]))
        settle(pg)
        clean_state(pg, "after command palette storm")

        # ---- 9. resize the window while it all moves
        print("9. resizing")
        for w, h in [(800, 600), (1100, 700), (1920, 1000), (640, 800), (1366, 820), (900, 500), (1600, 900)]:
            pg.set_viewport_size({"width": w, "height": h})
            nav(pg, rng.choice(PAGES)) if w >= 1024 else None
            settle(pg, 600)
            r = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(r <= 1, f"horizontal overflow {r}px at {w}x{h}")
        pg.set_viewport_size({"width": 1366, "height": 820})
        settle(pg)
        marker_matches(pg, "[data-sidebar=content]", "[data-sidebar=menu-button][data-active=true]", "sidebar marker after resizing")

        # ---- 10. reduced motion: everything must still land in the right place
        print("10. reduced motion")
        pg.emulate_media(reduced_motion="reduce")
        for _ in range(40):
            nav(pg, rng.choice(PAGES))
        settle(pg, 300)
        marker_matches(pg, "[data-sidebar=content]", "[data-sidebar=menu-button][data-active=true]", "sidebar marker with reduced motion")
        clean_state(pg, "reduced motion")

    except Exception as exc:  # noqa: BLE001
        # say what the window looked like when it stopped answering
        shot = Path(__file__).with_name("stress_ui_failure.png")
        try:
            pg.screenshot(path=str(shot))
            text = pg.evaluate("() => document.body.innerText").replace(chr(10), " | ")[:400]
            print(chr(10) + "STOPPED:", str(exc).splitlines()[0][:160], chr(10) + "  page text:", text, chr(10) + "  screenshot:", shot)
        except Exception:  # noqa: BLE001
            pass
        import traceback
        print("  at:", [ln.strip() for ln in traceback.format_exc().splitlines() if "stress_ui.py" in ln][-1:], str(exc).splitlines()[1:12])
        problems.append(f"stopped: {str(exc).splitlines()[0][:120]}")
    check(not errors, f"{len(errors)} console/page error(s): {errors[:5]}")
    pg.screenshot(path=str(Path(__file__).with_name("stress_ui_last.png")))
    browser.close()

print(f"\n{checks} checks, {len(problems)} problem(s), {len(errors)} error(s)  (seed {SEED})")
for e in errors[:8]:
    print("  ", e)
sys.exit(1 if problems or errors else 0)
