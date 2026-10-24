from lms_scraper import _parse_course_table

# A trimmed copy of the LMS assignments table layout (synthetic data).
HTML = """
<table class="table">
  <tr><th>Assign. No.</th><th>Title</th><th>Assignment</th><th>Added Submission</th><th>Marks Obtained</th>
      <th>Returned Submission</th><th>Action</th><th>Deadline</th></tr>
  <tr><td>1</td><td>Lab Journal 1</td><td>Assignment  Not available.</td><td>Submission</td><td>Not marked yet</td>
      <td>---</td><td>Deadline Exceeded</td><td>4 October 2026 - 11:50 am13 September 2026-11:55 am</td></tr>
  <tr><td>2</td><td>Widgets</td><td>Assignment</td><td>No Submission</td><td>Not marked yet</td>
      <td>---</td><td>Deadline Exceeded</td><td>4 October 2026-11:55 am</td></tr>
  <tr><td>3</td><td>Cursors</td><td>Assignment</td><td>No Submission</td><td>Not marked yet</td>
      <td>---</td><td>Submit</td><td>19 October 2026-10:30 pm</td></tr>
  <tr><td>4</td><td>Graded one</td><td>Assignment</td><td>Submission</td><td>8 / 10</td>
      <td>Good</td><td>Deadline Exceeded</td><td>1 October 2026-11:55 pm</td></tr>
  <tr><td colspan="8">No record found</td></tr>
</table>
"""


def test_parse_course_table():
    items = _parse_course_table(HTML, "Mobile App Lab")
    assert [i["title"] for i in items] == ["Lab Journal 1", "Widgets", "Cursors", "Graded one"]

    extended = items[0]
    assert extended["is_extended"] is True
    assert extended["due_date"] == "4 October 2026 - 11:50 am"
    assert extended["original_due_date"] == "13 September 2026-11:55 am"
    assert extended["is_submitted"] is True and extended["status"] == "Submitted"

    missed = items[1]
    assert missed["is_submitted"] is False and missed["status"] == "Missed (Exceeded)"

    pending = items[2]
    assert pending["is_submitted"] is False and pending["status"] == "Pending"
    assert pending["id"] == "Mobile_App_Lab#3#Cursors"

    graded = items[3]
    assert graded["marks"] == "8 / 10"


def test_rows_with_too_few_cells_are_ignored():
    assert _parse_course_table("<table><tr><td>a</td><td>b</td></tr></table>", "X") == []


def test_enrollment_is_masked_in_the_log_line():
    from lms_scraper import mask_enrollment
    assert mask_enrollment("01-134212-034") == "•" * 10 + "034"
    assert mask_enrollment("ab") == "••"
    assert mask_enrollment("") == ""


def test_login_error_text_ignores_hidden_messages():
    from lms_scraper import _login_error_text

    class El:
        def __init__(self, text, visible):
            self.text, self.visible = text, visible
        def is_visible(self):
            return self.visible
        def inner_text(self):
            return self.text

    class Loc:
        def __init__(self, els):
            self.els = els
        def count(self):
            return len(self.els)
        def nth(self, i):
            return self.els[i]

    class Page:
        def locator(self, sel):
            if sel == "[id*='Message']":
                return Loc([El("This LinkedIn profile is already associated with another student.", False),
                            El("Invalid enrollment or password.", True), El("Invalid enrollment or password.", True)])
            return Loc([])
    assert _login_error_text(Page()) == "Invalid enrollment or password."


def _key(kind, name):
    import base64
    from urllib.parse import quote
    raw = f"108935,2026-10-24,{kind},0,{name},lms.bahria.edu.pk/Student/Assignments.php"
    return "Download.php?k=" + quote(base64.b64encode(raw.encode()).decode())


ROW_WITH_FILES = f"""<table><tr>
<td>3</td><td>Lab Journal 3</td>
<td><a href="{_key('Assignment', 'Lab-Journal-1-11092026-090600am.docx')}" class="label"> Assignment </a><br/>
    <a href="{_key('AssignmentSolution', 'Solution-3.pdf')}"> Solution File </a><br/><span>Remarks</span></td>
<td><a href="{_key('AssignmentSubmissions', '01-135232-062-152746108935.pdf')}"> Submission </a></td>
<td>Not Marked Yet</td>
<td><a href="{_key('Returned', 'checked.pdf')}"> Returned </a></td>
<td>Deadline Exceeded</td><td>23 October 2026-11:55 pm</td>
</tr><tr>
<td>4</td><td>Lab Journal 4</td><td><span>Not available.</span></td><td>No Submission</td>
<td>Not Marked Yet</td><td>---</td><td>Submit</td><td>30 October 2026-11:55 pm</td>
</tr></table>"""


def test_assignment_rows_carry_their_files_with_names_from_the_link_key():
    items = _parse_course_table(ROW_WITH_FILES, "Course")
    files = items[0]["files"]
    assert set(files) == {"brief", "solution", "submission", "returned"}
    assert files["brief"]["filename"] == "Lab-Journal-1-11092026-090600am.docx"
    assert files["submission"]["filename"] == "01-135232-062-152746108935.pdf"
    assert files["solution"]["filename"] == "Solution-3.pdf"
    assert files["returned"]["filename"] == "checked.pdf"
    assert items[1]["files"] == {}


def test_decode_download_key_tolerates_other_links():
    from lms_scraper import decode_download_key
    assert decode_download_key("Assignments.php?s=1") == {}
    assert decode_download_key("Download.php?k=%%%") == {}
