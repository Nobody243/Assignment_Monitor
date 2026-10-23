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
