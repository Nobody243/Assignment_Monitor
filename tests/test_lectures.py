import base64

import campus
import tracker

K = base64.b64encode(b"108935,2026-10-21,Lecture,0,Lec-1-Cyber-Security-Concepts-28092026-012454pm.pptx,"
                     b"lms.bahria.edu.pk/Student/LectureNotes.php?s=MjAyNjM%3D&oc=MTUyNzUw").decode()
HTML = f"""
<table class="table table-hover">
 <tr><th>Week #</th><th>Lecture Title</th><th>Lecture File(s)</th><th>Video Link(s)</th><th>Video Link</th><th>Remarks</th></tr>
 <tr><td>1</td><td>Cyber Security Concepts</td><td>1. <a href="Download.php?k={K}" target="_blank">Download Lecture</a></td>
     <td></td><td></td><td></td></tr>
 <tr><td>2</td><td>Two files</td><td>1. <a href="Download.php?k=abc">Download Lecture</a>
     2. <a href="Download.php?k=def">Download Lecture</a></td>
     <td><a href="https://youtu.be/x">Watch</a></td><td></td><td>Read chapter 3</td></tr>
 <tr><td>3</td><td>Empty week</td><td></td><td></td><td></td><td></td></tr>
 <tr><td colspan="6">Please select a course to display the respective lectures.</td></tr>
</table>"""


def test_filename_from_link_decodes_the_token():
    assert campus.filename_from_link(f"Download.php?k={K}") == "Lec-1-Cyber-Security-Concepts-28092026-012454pm.pptx"
    assert campus.filename_from_link("Download.php?k=%%%") == ""
    assert campus.filename_from_link("nothing") == ""


def test_parse_lectures():
    rows = campus.parse_lectures(HTML, "Cyber Security")
    assert [r["week"] for r in rows] == ["1", "2"]          # the empty week and the hint row are skipped
    first = rows[0]
    assert first["files"][0]["filename"].endswith(".pptx") and first["files"][0]["label"] == "Download Lecture"
    two = rows[1]
    assert len(two["files"]) == 2 and two["videos"] == ["https://youtu.be/x"] and two["remarks"] == "Read chapter 3"
    assert two["files"][1]["filename"] == "Two files (2)"    # no name in the token: title + index
    assert len(first["id"]) == 12


def test_safe_name():
    assert campus.safe_name('Lab: "Intro" <v2>?') == "Lab Intro v2"
    assert campus.safe_name("") == "untitled"


def test_compare_lectures(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "LECTURES_PATH", tmp_path / "lectures.json")
    rows = campus.parse_lectures(HTML, "Cyber Security")
    assert tracker.compare_lectures(rows) == []                     # first read is silent
    assert len(tracker.load_lectures()) == 2
    more = rows + campus.parse_lectures(HTML.replace("Cyber Security Concepts", "Week four"), "Other")
    new = tracker.compare_lectures(more)
    assert {x["course"] for x in new} == {"Other"}
    assert tracker.compare_lectures(more) == []


def test_live_file_matches_each_file_of_a_week_by_name_not_by_label():
    from lms_scraper import live_file
    stored = {"week": "2", "title": "Threat Models"}
    a = {"label": "Download Lecture", "filename": "Lecture-2a.pptx", "href": "Download.php?k=old-a"}
    b = {"label": "Download Lecture", "filename": "Lecture-2b.pptx", "href": "Download.php?k=old-b"}
    live = [{"week": "2", "title": "Threat Models", "files": [
        {"label": "Download Lecture", "filename": "Lecture-2a.pptx", "href": "Download.php?k=new-a"},
        {"label": "Download Lecture", "filename": "Lecture-2b.pptx", "href": "Download.php?k=new-b"}]}]
    assert live_file(stored, a, live)["href"] == "Download.php?k=new-a"
    assert live_file(stored, b, live)["href"] == "Download.php?k=new-b"


def test_live_file_falls_back_to_link_then_unique_label_then_itself():
    from lms_scraper import live_file
    stored = {"week": 3, "title": "T"}
    live = [{"week": "3", "title": "T", "files": [{"label": "Slides", "href": "x"}, {"label": "Lab", "href": "y"}]}]
    assert live_file(stored, {"label": "Lab", "href": "stale"}, live)["href"] == "y"          # unique label
    assert live_file(stored, {"label": "?", "href": "x"}, live)["href"] == "x"                 # same link
    me = {"label": "Download Lecture", "href": "mine"}
    assert live_file(stored, me, [{"week": "3", "title": "T", "files": [
        {"label": "Download Lecture", "href": "p"}, {"label": "Download Lecture", "href": "q"}]}]) is me   # ambiguous
