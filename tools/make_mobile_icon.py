"""Draws the phone app's icon and launch mark: a clipboard with a tick, white on the Ember orange.

    python tools/make_mobile_icon.py            writes mobile/assets/icon/icon.png and mark.png

icon.png is the full launcher icon (orange square); mark.png is the white mark alone on a transparent background, used
as the launch screen image and as the foreground of Android's adaptive icon.
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "mobile" / "assets" / "icon"
ORANGE = (232, 85, 43, 255)
WHITE = (255, 250, 246, 255)
S = 1024


def mark(size: int = S, safe: float = 1.0) -> Image.Image:
    """The clipboard-and-tick on a transparent canvas; `safe` shrinks it into the adaptive-icon safe zone."""
    big = size * 4
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = big / 1024 * safe
    ox = oy = (big - 1024 * u) / 2

    def p(x, y):
        return (ox + x * u, oy + y * u)

    # board
    d.rounded_rectangle([*p(262, 250), *p(762, 830)], radius=90 * u, outline=WHITE, width=int(56 * u))
    # clip at the top
    d.rounded_rectangle([*p(392, 190), *p(632, 320)], radius=56 * u, fill=WHITE)
    # tick
    d.line([p(380, 560), p(468, 650), p(650, 450)], fill=WHITE, width=int(60 * u), joint="curve")
    for x, y in ((380, 560), (650, 450)):
        d.ellipse([*p(x - 30, y - 30), *p(x + 30, y + 30)], fill=WHITE)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icon = Image.new("RGBA", (S, S), ORANGE)
    icon.alpha_composite(mark(S, 0.92))
    icon.save(OUT / "icon.png")
    mark(S, 0.62).save(OUT / "mark.png")        # smaller: it sits inside the adaptive icon's safe circle
    mark(S, 0.9).save(OUT / "mark_splash.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
