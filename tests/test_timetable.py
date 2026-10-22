# ruff: noqa: E501
"""Timetable and Miscellaneous parsing, plus a render smoke test. Fixtures mirror the portal's markup with made-up data."""
from pathlib import Path

from campus import parse_misc, parse_timetable, sessions_on
from timetable_render import render_timetable, save_timetable


def _cell(title, room, abbr, who, cls, span):
    return (f'<td data-type="Slot" class="event class Overall" colspan="{span}"><div title="{title}" class="Color1">'
            f'<div class="room"><span>{room}</span></div><div class="title"><span>{abbr}</span></div>'
            f'<div class="facultyMember"><span>{who}</span></div><div class="class"><span>{cls}</span></div></div></td>')


TT_HTML = f"""
<html><body><div>Fall-2026</div>
<table id="timeTable" class="timeTable">
<tr><th>Day</th><th class="hour" colspan="4" data-hour="08">8am</th><th>Day</th></tr>
<tr><td>Mon</td><td></td>{_cell("Operating Systems&#10;JANE DOE&#10;BS (CS)-5 (A) Morning&#10;HL-1&#10;08:30 AM - 10:00 AM", "HL-1", "OS", "JD", "BS (CS)-5A-M", 6)}
{_cell("Operating Systems&#10;JANE DOE&#10;BS (CS)-5 (A) Morning&#10;HL-1&#10;10:00 AM - 11:00 AM", "HL-1", "OS", "JD", "BS (CS)-5A-M", 4)}<td>Mon</td></tr>
<tr><td>Tue</td>{_cell("Data Science Lab&#10;ALI KHAN&#10;BS (CS)-5 (A) Morning&#10;LAB-3&#10;02:30 PM - 05:30 PM", "LAB-3", "DSL", "AK", "BS (CS)-5A-M", 12)}<td>Tue</td></tr>
<tr><td>Wed</td><td></td><td>Wed</td></tr>
</table></body></html>
"""

MISC_HTML = """
<table><tr><th>Sr.No.</th><th>Miscellaneous Type</th><th>Miscellaneous File</th><th>Remarks</th></tr>
<tr><td>1</td><td>Project</td><td><a href="Download.php?k=MTA4OTM1LDIwMjYtMTAtMjIsTWlzY2VsbGFuZW91cywwLFByb2plY3QtR3VpZGVsaW5lcy5kb2N4LGxtcw%3D%3D" target="_blank">Download Miscellaneous File</a></td><td>Read before week 5</td></tr>
<tr><td>2</td><td>Past Paper</td><td><a href="Download.php?k=MTA4OTM2LDIwMjYtMTAtMjIsTWlzY2VsbGFuZW91cywwLE1pZC0yMDI1LnBkZixsbXM%3D" target="_blank">Download Miscellaneous File</a></td><td></td></tr>
</table>
"""


def test_parse_timetable_merges_contiguous_blocks():
    data = parse_timetable(TT_HTML)
    assert data["semester"] == "Fall-2026"
    mon = sessions_on(data["sessions"], "Mon")
    assert len(mon) == 1, "the two back-to-back Operating Systems slots become one class"
    assert (mon[0]["start"], mon[0]["end"]) == ("08:30", "11:00")
    assert mon[0]["course"] == "Operating Systems" and mon[0]["teacher"] == "Jane Doe" and mon[0]["room"] == "HL-1"
    tue = sessions_on(data["sessions"], "Tue")
    assert (tue[0]["start"], tue[0]["end"], tue[0]["abbr"]) == ("14:30", "17:30", "DSL")
    assert sessions_on(data["sessions"], "Wed") == []


def test_parse_misc_records_look_like_lectures():
    items = parse_misc(MISC_HTML, "Cyber Security")
    assert len(items) == 2
    first = items[0]
    assert first["kind"] == "misc" and first["course"] == "Cyber Security" and first["title"] == "Project"
    assert first["files"][0]["filename"] == "Project-Guidelines.docx" and first["remarks"] == "Read before week 5"
    assert items[1]["files"][0]["filename"] == "Mid-2025.pdf"
    assert first["id"] != items[1]["id"]


def test_render_and_save(tmp_path: Path):
    data = parse_timetable(TT_HTML)
    img = render_timetable(data, "dark", scale=1)
    assert img.width > 800 and img.height > 400
    for name in ("week.png", "week.jpg", "week.pdf"):
        out = save_timetable(data, tmp_path / name, "light")
        assert out.exists() and out.stat().st_size > 1000
    empty = render_timetable({"semester": "", "sessions": []}, "light", scale=1)
    assert empty.width > 0
