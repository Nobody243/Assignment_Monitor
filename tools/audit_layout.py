"""Layout audit for the desktop interface (ui/): opens every page (and Settings section) at several window sizes and reports
the layout faults that are easy to miss by eye:

  * sideways page scroll
  * dead space: a card sitting beside a much taller one with a visible empty block under it
  * fixed elements that scroll with the page (trapped by a transformed ancestor)
  * click targets under 24 px
  * text clipped inside a box that cannot show it (and has no tooltip)
  * console errors

    cd ui && npm run dev -- --port 5173 --strictPort      (and, for real data, python engine.py --dev)
    python tools/audit_layout.py [http://localhost:5173] [--shots=dir]

Without the engine the built-in sample data is used. Exit code 1 when anything is reported.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opts = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
URL = args[0] if args else "http://localhost:5173"
SHOTS = Path(opts["shots"]) if "shots" in opts else None
if SHOTS:
    SHOTS.mkdir(parents=True, exist_ok=True)

ROUTES = ["home", "assignments", "attendance", "exams", "timetable", "results", "lectures", "announcements",
          "settings/profile", "settings/appearance", "settings/notifications", "settings/tracking", "settings/background",
          "settings/data", "settings/activity", "settings/about"]
SIZES = [(1920, 1000), (1366, 820), (1100, 760), (900, 700)]

PROBE = r"""
() => {
  const out = [];
  const vw = document.documentElement.clientWidth;
  const label = (e) => (e.tagName.toLowerCase() + (e.getAttribute('aria-label') ? '[' + e.getAttribute('aria-label') + ']' : '') + '.' + String(e.className || '').split(' ').filter(Boolean).slice(0, 3).join('.')).slice(0, 70);
  const text = (e) => (e.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  const root = document.querySelector('main') || document.body;

  // 1. sideways scroll
  const over = document.documentElement.scrollWidth - vw;
  if (over > 1) out.push(['overflow-x', over + 'px sideways scroll']);

  // 2. dead space: siblings in one row where the shorter, visibly boxed one is far shorter than the row
  const boxed = (e) => { const c = getComputedStyle(e); return (c.borderTopWidth !== '0px' && c.borderTopStyle !== 'none') || (c.backgroundColor !== 'rgba(0, 0, 0, 0)' && c.backgroundColor !== 'transparent'); };
  root.querySelectorAll('*').forEach(parent => {
    const cs = getComputedStyle(parent);
    if (!(cs.display === 'grid' || (cs.display === 'flex' && cs.flexDirection.startsWith('row') && cs.flexWrap !== 'nowrap'))) return;
    const kids = [...parent.children].filter(k => k.getBoundingClientRect().height > 40 && getComputedStyle(k).position !== 'absolute');
    if (kids.length < 2) return;
    const rows = {};
    kids.forEach(k => { const r = k.getBoundingClientRect(); const key = Math.round(r.top / 8); (rows[key] ||= []).push(k); });
    Object.values(rows).forEach(row => {
      if (row.length < 2) return;
      const hs = row.map(k => k.getBoundingClientRect().height);
      const tall = Math.max(...hs);
      row.forEach((k, i) => {
        const gap = tall - hs[i];
        if (gap > 150 && hs[i] < tall * 0.88 && boxed(k) && getComputedStyle(k).position !== "sticky") out.push(['dead-space', `${label(k)} "${text(k)}" is ${Math.round(hs[i])}px beside a ${Math.round(tall)}px card (${Math.round(gap)}px empty)`]);
        // stretched empty block: a boxed card whose content stops far above its bottom
        if (boxed(k) && k.children.length) {
          const last = [...k.children].reverse().find(c => c.getBoundingClientRect().height > 0);
          if (last) { const space = k.getBoundingClientRect().bottom - last.getBoundingClientRect().bottom; if (space > 140) out.push(['stretched', `${label(k)} "${text(k)}" has ${Math.round(space)}px empty at the bottom`]); }
        }
      });
    });
  });

  // 3. fixed elements trapped by a transformed ancestor
  document.querySelectorAll('*').forEach(e => {
    if (getComputedStyle(e).position !== 'fixed') return;
    for (let a = e.parentElement; a && a !== document.documentElement; a = a.parentElement) {
      const c = getComputedStyle(a);
      if (c.transform !== 'none' || c.filter !== 'none' || c.perspective !== 'none' || /transform|filter|perspective/.test(c.willChange) || /paint|layout/.test(c.contain))
        { out.push(['trapped-fixed', `${label(e)} sits inside ${label(a)}, which makes it scroll with the page`]); break; }
    }
  });

  // 4. small click targets
  root.querySelectorAll('button, a[href], [role=tab], [role=checkbox], [role=switch], input[type=checkbox]').forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.pointerEvents === 'none') return;
    if (e.closest('[inert], [aria-hidden=true]')) return;
    const inline = e.tagName === 'A' && cs.display === 'inline';
    if (inline) return;
    // a pseudo-element can widen the hit area (checkboxes and switches do)
    const pa = getComputedStyle(e, '::after'); const pw = parseFloat(pa.width) || 0, ph = parseFloat(pa.height) || 0;
    const w = pa.position === 'absolute' ? Math.max(r.width, pw) : r.width, h = pa.position === 'absolute' ? Math.max(r.height, ph) : r.height;
    if (h < 24 || w < 24) out.push(['small-target', `${label(e)} "${text(e) || e.getAttribute('aria-label') || ''}" is ${Math.round(r.width)}x${Math.round(r.height)}`]);
  });

  // 5. clipped text with no way to read it
  root.querySelectorAll('*').forEach(e => {
    if (!e.children.length && e.textContent.trim().length > 3 && !e.classList.contains('sr-only')) {
      e.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));   // the app adds a tooltip to clipped text on hover
      const cs = getComputedStyle(e);
      if ((cs.overflow === 'hidden' || cs.textOverflow === 'ellipsis') && e.scrollWidth > e.clientWidth + 2 && !e.title && !e.closest('[title]') && !e.closest('[data-slot=tooltip-trigger]'))
        out.push(['clipped-text', `${label(e)} "${text(e)}" is cut off (${e.scrollWidth}px of ${e.clientWidth}px) with no tooltip`]);
    }
  });
  return out;
}
"""

findings: dict[tuple[str, str, str], set[str]] = {}
errors: list[str] = []

with sync_playwright() as p:
    for channel in ("chrome", "msedge", None):
        try:
            browser = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
            break
        except Exception as e:  # noqa: BLE001
            last = e
    else:
        raise SystemExit(f"no browser to drive: {last}")
    pg = browser.new_page(viewport={"width": 1366, "height": 820})
    pg.on("console", lambda m: errors.append(m.text[:160]) if m.type == "error" and "Failed to load" not in m.text else None)
    pg.on("pageerror", lambda e: errors.append(str(e)[:160]))
    pg.goto(URL)
    pg.wait_for_timeout(2500)
    if pg.get_by_role("button", name="View sample data").count():
        pg.get_by_role("button", name="View sample data").click()
        print("(sample data)")
    else:
        print("(real data from the engine)")
    pg.wait_for_timeout(800)
    for w, h in SIZES:
        pg.set_viewport_size({"width": w, "height": h})
        for route in ROUTES:
            pg.evaluate("r => { location.hash = '/' + r }", route)
            pg.wait_for_timeout(900)
            for kind, what in pg.evaluate(PROBE):
                findings.setdefault((route, kind, what), set()).add(f"{w}")
            if SHOTS and w in (1366, 900):
                pg.screenshot(path=str(SHOTS / f"{route.replace('/', '_')}_{w}.png"), full_page=True)
    browser.close()

print()
for (route, kind, what), widths in sorted(findings.items()):
    print(f"[{kind}] #/{route} @ {','.join(sorted(widths))}: {what}")
for e in sorted(set(errors))[:8]:
    print("[console]", e)
print(f"\n{len(findings)} finding(s), {len(set(errors))} console error(s)")
sys.exit(1 if findings or errors else 0)
