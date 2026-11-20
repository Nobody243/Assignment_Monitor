"""Draws the phone app's icon and launch mark: the countdown ring. A ring that is nearly closed (time running out) with a
tick inside (the deadline met) and a small dot where the ring is still open. White on the Ember orange.

    python tools/make_mobile_icon.py            writes mobile/assets/icon/icon.png, mark.png and mark_splash.png

The same geometry is drawn in Flutter by `BrandLogo` in mobile/lib/screens/intro.dart (all numbers are in a 512-unit
square), so the icon, the launch screen and the in-app mark are one drawing. Change both together.

icon.png is the full launcher icon (orange square); mark.png is the mark alone on a transparent background, scaled into
Android's adaptive-icon safe circle; mark_splash.png is the same, larger, for the Android 12 launch screen.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "mobile" / "assets" / "icon"
ORANGE = (232, 85, 43, 255)
WHITE = (255, 250, 246, 255)
SAND = (255, 224, 205, 255)

# geometry, in a 512-unit square (keep in step with BrandLogo in intro.dart)
CENTER = (256, 256)
RING_R = 138          # radius of the ring's centre line
STROKE = 44
ARC = (-60, 210)      # degrees, clockwise from 3 o'clock: a 270 degree ring with the gap at the top right
TICK = [(196, 262), (240, 306), (322, 214)]
DOT = (220, 123, 20)  # x, y, radius: the middle of the ring's gap


def mark(size: int = 1024, safe: float = 1.0) -> Image.Image:
    """The ring, tick and dot on a transparent canvas; `safe` < 1 shrinks it toward the centre."""
    k = 4
    big = size * k
    u = big / 512 * safe
    off = (big - 512 * u) / 2
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def p(x, y):
        return (off + x * u, off + y * u)

    def cap(x, y, fill):
        r = STROKE * u / 2
        cx, cy = p(x, y)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)

    cx, cy = p(*CENTER)
    outer = (RING_R + STROKE / 2) * u
    d.arc([cx - outer, cy - outer, cx + outer, cy + outer], ARC[0], ARC[1], fill=WHITE, width=int(STROKE * u))
    for a in ARC:
        cap(CENTER[0] + RING_R * math.cos(math.radians(a)), CENTER[1] + RING_R * math.sin(math.radians(a)), WHITE)
    d.line([p(*q) for q in TICK], fill=WHITE, width=int(STROKE * u), joint="curve")
    for q in (TICK[0], TICK[-1]):
        cap(*q, WHITE)
    x, y, r = DOT
    d.ellipse([*p(x - r, y - r), *p(x + r, y + r)], fill=SAND)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = 1024
    icon = Image.new("RGBA", (s, s), ORANGE)
    icon.alpha_composite(mark(s, 0.86))
    icon.save(OUT / "icon.png")
    mark(s, 0.60).save(OUT / "mark.png")         # inside the adaptive icon's safe circle
    mark(s, 0.86).save(OUT / "mark_splash.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
