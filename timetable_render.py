"""Draws the week timetable the app's own way: a clean grid, one row per day, rounded colour-coded blocks per course,
a legend underneath. Saves as PNG, JPG or PDF. Pure Pillow, no browser involved."""
from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

from campus import DAY_ORDER, minutes
from config import APP_NAME, ASSETS_DIR

THEMES = {
    "light": dict(bg="#f3f4f7", surface="#ffffff", line="#e3e6ec", line2="#cfd4de", ink="#14161b", muted="#5b6170",
                  dim="#9096a3", accent="#2f5bea"),
    "dark": dict(bg="#0d0f13", surface="#15181d", line="#252a32", line2="#343a45", ink="#eef0f4", muted="#9aa1ad",
                 dim="#666d79", accent="#8aa7ff"),
}
# course colours: (block fill, block text) per theme, six hues spaced round the wheel
COURSE_COLOURS = {
    "light": [("#dbe4ff", "#1f3fae"), ("#dcf5f0", "#0b5e57"), ("#fdeee6", "#9a3412"), ("#fbf3dc", "#6e4a00"),
              ("#f3e8fb", "#63308f"), ("#e0f2fe", "#075985"), ("#e8e9ee", "#2b2f38")],
    "dark": [("#1f2a4d", "#b7c7ff"), ("#10302b", "#7fe3cf"), ("#3a2219", "#ffb79a"), ("#302a12", "#ecd27a"),
             ("#2e2136", "#e2b6f6"), ("#122a3a", "#8fd3fa"), ("#23272f", "#c9ced8")],
}


def _font(name: str, size: int):
    path = ASSETS_DIR / "fonts" / name
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:
        try:
            return ImageFont.truetype("segoeui.ttf", size)
        except Exception:
            return ImageFont.load_default()


def _hour_range(sessions: List[dict]) -> tuple:
    if not sessions:
        return 8, 17
    lo = min(minutes(x["start"]) for x in sessions) // 60
    hi = -(-max(minutes(x["end"]) for x in sessions) // 60)
    return min(lo, 8), max(hi, 17)


def course_index(sessions: List[dict]) -> dict:
    """Stable colour slot per course, in first-appearance order across the week."""
    order = {}
    for x in sessions:
        order.setdefault(x.get("course", ""), len(order))
    return order


def _rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _ellipsize(draw, text, font, max_w):
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…"


def render_timetable(data: dict, theme: str = "light", scale: int = 2, student: str = "") -> Image.Image:
    """Returns a PIL image of the week. `scale` 2 gives a crisp 2x image for screens and print."""
    t = THEMES["dark" if theme == "dark" else "light"]
    palette = COURSE_COLOURS["dark" if theme == "dark" else "light"]
    sessions = data.get("sessions", [])
    days = [d for d in DAY_ORDER if d in ("Mon", "Tue", "Wed", "Thu", "Fri") or any(x["day"] == d for x in sessions)]
    h0, h1 = _hour_range(sessions)
    hours = h1 - h0
    colours = course_index(sessions)

    S = scale
    pad, label_w, hour_w, row_h, head_h = 36 * S, 74 * S, 128 * S, 108 * S, 112 * S
    axis_h = 30 * S
    grid_w = hours * hour_w
    legend_rows = max(1, len(colours))
    legend_h = (24 * S) + legend_rows * (26 * S) + 20 * S
    W = pad * 2 + label_w + grid_w
    H = pad + head_h + axis_h + len(days) * row_h + 26 * S + legend_h + pad
    img = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(img)
    f_title = _font("InterDisplay-SemiBold.ttf", 30 * S)
    f_sub = _font("Inter-Regular.ttf", 14 * S)
    f_axis = _font("Inter-Medium.ttf", 12 * S)
    f_day = _font("Inter-SemiBold.ttf", 14 * S)
    f_block = _font("Inter-SemiBold.ttf", 14 * S)
    f_small = _font("Inter-Regular.ttf", 12 * S)
    f_legend = _font("Inter-Medium.ttf", 13 * S)

    # header
    d.text((pad, pad), "Timetable", font=f_title, fill=t["ink"])
    sub = "  ·  ".join(b for b in (data.get("semester", ""), student, f"{len(sessions)} classes a week") if b)
    d.text((pad, pad + 42 * S), sub, font=f_sub, fill=t["muted"])

    # grid card
    gx, gy = pad + label_w, pad + head_h + axis_h
    card = (pad, pad + head_h, W - pad, gy + len(days) * row_h)
    _rounded(d, card, 16 * S, t["surface"], t["line"], S)
    # hour axis
    for h in range(hours + 1):
        x = gx + h * hour_w
        lbl = f"{(h0 + h - 1) % 12 + 1}{'am' if (h0 + h) % 24 < 12 else 'pm'}"
        if h < hours:
            d.text((x + 8 * S, pad + head_h + 8 * S), lbl, font=f_axis, fill=t["dim"])
        if 0 < h < hours:
            d.line([(x, gy), (x, gy + len(days) * row_h)], fill=t["line"], width=S)
        if h < hours:   # half-hour tick
            xm = x + hour_w // 2
            d.line([(xm, gy), (xm, gy + len(days) * row_h)], fill=t["line"], width=1)
    # day rows
    for i, day in enumerate(days):
        y = gy + i * row_h
        if i:
            d.line([(pad + S, y), (W - pad - S, y)], fill=t["line"], width=S)
        d.text((pad + 20 * S, y + row_h // 2 - 9 * S), day, font=f_day, fill=t["ink"])
        todays = [x for x in sessions if x["day"] == day]
        for x in todays:
            a, b = minutes(x["start"]) - h0 * 60, minutes(x["end"]) - h0 * 60
            x0 = gx + a * hour_w // 60 + 3 * S
            x1 = gx + b * hour_w // 60 - 3 * S
            y0, y1 = y + 8 * S, y + row_h - 8 * S
            fill, ink = palette[colours.get(x["course"], 0) % len(palette)]
            _rounded(d, (x0, y0, x1, y1), 10 * S, fill)
            d.rectangle((x0, y0 + 10 * S, x0 + 3 * S, y1 - 10 * S), fill=ink)
            tx, max_w = x0 + 12 * S, (x1 - x0) - 20 * S
            name = x.get("abbr") or x.get("course", "")
            if d.textlength(x.get("course", ""), font=f_block) <= max_w:
                name = x.get("course", "")
            d.text((tx, y0 + 10 * S), _ellipsize(d, name, f_block, max_w), font=f_block, fill=ink)
            d.text((tx, y0 + 32 * S), _ellipsize(d, f"{x['start']} – {x['end']}", f_small, max_w), font=f_small, fill=ink)
            where = "  ·  ".join(b for b in (x.get("room", ""), x.get("teacher", "") or x.get("initials", "")) if b)
            d.text((tx, y0 + 50 * S), _ellipsize(d, where, f_small, max_w), font=f_small, fill=ink)
            if (y1 - y0) > 86 * S and x.get("class"):
                d.text((tx, y0 + 68 * S), _ellipsize(d, x["class"], f_small, max_w), font=f_small, fill=ink)

    # legend
    ly = card[3] + 26 * S
    d.text((pad, ly), "Courses", font=f_day, fill=t["ink"])
    ly += 24 * S
    for course, idx in colours.items():
        fill, ink = palette[idx % len(palette)]
        _rounded(d, (pad, ly + 5 * S, pad + 14 * S, ly + 19 * S), 4 * S, fill, ink, S)
        teacher = next((x.get("teacher") for x in sessions if x.get("course") == course and x.get("teacher")), "")
        line = course + (f"   ·   {teacher}" if teacher else "")
        d.text((pad + 24 * S, ly), _ellipsize(d, line, f_legend, W - 2 * pad - 24 * S), font=f_legend, fill=t["muted"])
        ly += 26 * S
    d.text((W - pad - d.textlength(f"Made with {APP_NAME}", font=f_small), H - pad - 14 * S), f"Made with {APP_NAME}",
           font=f_small, fill=t["dim"])
    return img


def save_timetable(data: dict, path, theme: str = "light", student: str = "") -> Path:
    """Writes the rendered week to `path`; the suffix picks PNG, JPG or PDF."""
    path = Path(path)
    img = render_timetable(data, theme, student=student)
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix in (".jpg", ".jpeg"):
        img.save(path, "JPEG", quality=92, optimize=True)
    elif suffix == ".pdf":
        img.save(path, "PDF", resolution=192)
    else:
        img.save(path, "PNG", optimize=True)
    return path
