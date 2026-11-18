"""Uploading and deleting a submission, end to end against a fake LMS: a real headless browser is pointed at a stand-in
for the portal's assignments page (the same table, the same Bootstrap-style modals and multipart form), and the
scraper's own functions drive it. What is checked is what reaches the portal and in what order, and what the
student is told when the portal says no."""
from contextlib import contextmanager

import pytest

import lms_scraper as L

TITLE = "Software Test Plan and Test Case Design"
COURSE = "Software Quality Assurance"


def _page_html(st: dict) -> str:
    """The assignments page the way the portal draws it for the current state of the fake."""
    if st["deadline_passed"]:
        action = "Deadline Exceeded"
        sub = '<a href="Download.php?k=abc">Submission</a>' if st["submitted"] else "No Submission"
    elif st["submitted"]:
        action = '<a href="#" data-toggle="modal" data-target="#modal-delete-assignment-submission-2">Delete</a>'
        sub = '<a href="Download.php?k=abc">Submission</a>'
    else:
        action = '<a href="#" data-toggle="modal" data-target="#modal-assignment-solution-4">Submit</a>'
        sub = "No Submission"
    alert = f'<div class="alert alert-success">{st["flash"]}</div>' if st.get("flash") else ""
    return f"""<html><body>{alert}
<script>window.jQuery = function (sel) {{
  return {{ modal: function () {{ document.querySelector(sel).style.display = 'block'; }} }}; }};</script>
<table>
 <tr><th>No</th><th>Title</th><th>Assignment</th><th>Added</th><th>Marks</th><th>Returned</th><th>Action</th><th>Deadline</th></tr>
 <tr><td>3</td><td>{TITLE}</td><td>Assignment Not available.</td><td>{sub}</td><td>Not marked yet</td><td>---</td>
     <td>{action}</td><td>21 November 2026-11:55 pm</td></tr>
 <tr><td>4</td><td>Another one</td><td>Assignment</td><td>No Submission</td><td>-</td><td>---</td>
     <td>Deadline Exceeded</td><td>1 November 2026-11:55 pm</td></tr>
</table>
<div id="modal-assignment-solution-4" style="display:none">
 <form action="/includes/studentprocess.php?s=assignmentSubmissionAdd" method="post" enctype="multipart/form-data">
  <input type="text" name="assignmentTitle" value="{st['form_title']}" disabled>
  <input type="file" name="assignmentSubmissionFile" required>
  <button type="submit" class="btn">Submit Assignment</button></form></div>
<div id="modal-delete-assignment-submission-2" style="display:none">
  <a class="btn" href="/includes/studentprocess.php?s=assignmentSubmissionDelete&aSubId=zzz">Delete</a></div>
</body></html>"""


def _record(st: dict) -> dict:
    return L._parse_course_table(_page_html(st), COURSE)[0]


@pytest.fixture()
def portal(monkeypatch, tmp_path):
    """A browser page wired to the fake LMS, with the scraper's sign-in step replaced by a stub that hands it over."""
    sync_api = pytest.importorskip("playwright.sync_api")
    pw = sync_api.sync_playwright().start()
    browser = None
    for kw in ({}, {"channel": "chrome"}, {"channel": "msedge"}):
        try:
            browser = pw.chromium.launch(**kw)
            break
        except Exception:
            continue
    if browser is None:
        pw.stop()
        pytest.skip("no browser available")
    st = {"submitted": False, "deadline_passed": False, "form_title": TITLE, "accept": True, "flash": "",
          "log": [], "bodies": []}
    ctx = browser.new_context()
    page = ctx.new_page()

    def handle(route, request):
        url = request.url
        if "assignmentSubmissionAdd" in url:
            st["log"].append("add")
            st["bodies"].append(request.post_data_buffer or b"")
            if st["accept"]:
                st["submitted"], st["flash"] = True, "Submission uploaded successfully."
            else:
                st["flash"] = "Error: file type not allowed"
        elif "assignmentSubmissionDelete" in url:
            st["log"].append("delete")
            st["submitted"], st["flash"] = False, "Submission deleted successfully.."
        else:
            st["log"].append("get")
            st["flash"] = ""
        route.fulfill(status=200, content_type="text/html; charset=utf-8", body=_page_html(st))

    page.route("https://lms.test/**", handle)
    page.goto("https://lms.test/Student/Assignments.php")

    class FakeSession:
        def select_course(self, name):
            page.goto("https://lms.test/Student/Assignments.php")

    @contextmanager
    def fake_assignment_page(a, say):
        page.goto("https://lms.test/Student/Assignments.php")        # the real one signs in and selects the course: a fresh read
        yield page, FakeSession()

    monkeypatch.setattr(L, "_assignment_page", fake_assignment_page)
    st["log"].clear()
    st["record"] = _record(st)
    file = tmp_path / "My#Report $final.PDF"
    file.write_bytes(b"%PDF-1.4 hello")
    st["file"] = file
    try:
        yield st
    finally:
        ctx.close()
        browser.close()
        pw.stop()


def _writes(st):
    return [x for x in st["log"] if x != "get"]


def test_upload_goes_through_the_portal_form(portal):
    res = L.submit_assignment(portal["record"], portal["file"])
    assert res["ok"] and not res["deleted"], res
    assert res["row"]["is_submitted"] is True
    assert _writes(portal) == ["add"]
    body = portal["bodies"][0]
    assert b'filename="MyReport final.pdf"' in body and b"%PDF-1.4 hello" in body   # the cleaned name, the real bytes


def test_replace_deletes_first_then_uploads(portal):
    portal["submitted"] = True
    portal["record"] = _record(portal)
    res = L.submit_assignment(portal["record"], portal["file"], replace=True)
    assert res["ok"] and res["deleted"], res
    assert _writes(portal) == ["delete", "add"]


def test_replace_without_a_delete_offered_touches_nothing(portal):
    res = L.submit_assignment(portal["record"], portal["file"], replace=True)      # nothing submitted: no Delete button
    assert not res["ok"] and not res["deleted"]
    assert "delete" in res["message"].lower()
    assert _writes(portal) == []


def test_no_upload_when_the_portal_offers_no_submit(portal):
    portal["deadline_passed"] = True
    res = L.submit_assignment(portal["record"], portal["file"])
    assert not res["ok"] and "not accepting" in res["message"]
    assert _writes(portal) == []


def test_nothing_is_sent_if_the_form_is_for_another_assignment(portal):
    portal["form_title"] = "Some other assignment"
    res = L.submit_assignment(portal["record"], portal["file"])
    assert not res["ok"] and "different assignment" in res["message"]
    assert _writes(portal) == []


def test_a_rejected_upload_reports_the_portals_message(portal):
    portal["accept"] = False
    res = L.submit_assignment(portal["record"], portal["file"])
    assert not res["ok"] and not res["deleted"]
    assert "file type not allowed" in res["message"]


def test_a_rejected_replace_says_the_old_submission_is_gone(portal):
    portal["submitted"], portal["accept"] = True, False
    portal["record"] = _record(portal)
    res = L.submit_assignment(portal["record"], portal["file"], replace=True)
    assert not res["ok"] and res["deleted"]
    assert "old submission was removed" in res["message"]


def test_delete_submission(portal):
    portal["submitted"] = True
    portal["record"] = _record(portal)
    res = L.delete_submission(portal["record"])
    assert res["ok"] and res["deleted"] and res["row"]["is_submitted"] is False
    assert _writes(portal) == ["delete"]


def test_delete_when_there_is_nothing_to_delete(portal):
    res = L.delete_submission(portal["record"])
    assert not res["ok"] and not res["deleted"] and "delete" in res["message"].lower()
    assert _writes(portal) == []


def test_a_bad_file_never_opens_the_portal(monkeypatch, tmp_path):
    def boom(a, say):
        raise AssertionError("the portal must not be touched")
    monkeypatch.setattr(L, "_assignment_page", boom)
    exe = tmp_path / "x.exe"
    exe.write_bytes(b"x")
    res = L.submit_assignment({"course": "c", "id": "i", "title": "t", "assign_no": "1"}, exe)
    assert not res["ok"] and "accepts only" in res["message"]


def test_button_states_follow_the_portals_action_cell():
    assert L.submission_actions("Submit") == (True, False)
    assert L.submission_actions("Delete") == (False, True)
    assert L.submission_actions("Deadline Exceeded") == (False, False)
    assert L.submission_actions("") == (False, False) and L.submission_actions(None) == (False, False)


def test_a_finished_upload_updates_just_that_stored_record(monkeypatch, tmp_path):
    import tracker
    monkeypatch.setattr(tracker, "DB_PATH", tmp_path / "assignments.json")
    tracker.save_assignments({"k1": {"id": "k1", "title": "A", "action": "Submit", "is_submitted": False, "due_date": "x"},
                              "k2": {"id": "k2", "title": "B", "action": "Submit", "is_submitted": False}})
    assert tracker.update_assignment_row("k1", {"action": "Delete", "is_submitted": True, "status": "Submitted",
                                                "submission_status": "Submission", "marks": "Not marked yet", "files": {}})
    data = tracker.load_stored_assignments()
    assert data["k1"]["is_submitted"] is True and data["k1"]["action"] == "Delete" and data["k1"]["due_date"] == "x"
    assert data["k2"]["is_submitted"] is False                                           # nothing else touched
    assert tracker.update_assignment_row("missing", {"action": "x"}) is False
