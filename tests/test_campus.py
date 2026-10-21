from datetime import datetime

import campus

# Trimmed copies of the CMS/LMS table layouts (synthetic data).
ATTENDANCE = """
<table class="table">
 <tr><th>#</th><th>Code</th><th>Registered Course Title</th><th>Credit Hours</th><th>Majors</th>
     <th>Offered Course Title</th><th>Class</th><th>Teacher Name</th><th>Fee Status</th><th>Present Hours</th>
     <th>Absent Hours</th><th>Total Hours</th><th>Actions</th></tr>
 <tr><td>1</td><td>CSL 341</td><td>Mobile App Lab</td><td>1</td><td>N/A</td><td>Mobile App Lab</td>
     <td>BS (IT)-6 (A) Morning</td><td>JANE TEACHER</td><td>Paid</td><td>15.0 :71.43%</td><td>6.0</td><td>21.0</td>
     <td><a href="AttendanceSummary.aspx?v=abc">Detail</a></td></tr>
 <tr><td>2</td><td>ITC 411</td><td>Cyber Security</td><td>3</td><td>N/A</td><td>Cyber Security</td>
     <td>BS (IT)-7 (B) Morning</td><td>John Smith</td><td>Paid</td><td>16.5 :91.67%</td><td>1.5</td><td>18.0</td>
     <td><a href="AttendanceSummary.aspx?v=def">Detail</a></td></tr>
</table>"""

DETAIL = """
<table class="table table-bordered table-condensed tab">
 <tr><td>Title</td><td>Database Lab</td><td>Teacher Name</td><td>A TEACHER</td></tr>
 <tr><td>Credit Hours</td><td>1</td><td>Contact Hours</td><td>3</td></tr>
</table>
<table id="BodyPH_gvAttendanceDetails" class="table">
 <tr><th>#</th><th>Class Date</th><th>Class Type</th><th>Room</th><th>Remarks / Topics Covered</th>
     <th>Total Hours</th><th>Present Hours</th><th>Absent Hours</th></tr>
 <tr><td>1</td><td>Monday, 31 August 2026</td><td>Class</td><td>NC-LAB3</td>
     <td>Remarks: 089,015 Topics Covered: Recap</td><td>3</td><td>0</td><td>3</td></tr>
 <tr><td>2</td><td>Monday, 7 September 2026</td><td>Lab</td><td>NC-LAB3</td>
     <td>Remarks: N/A Topics Covered: SQL server</td><td>3</td><td>3</td><td>0</td></tr>
 <tr><td></td><td></td><td></td><td></td><td></td><td>6</td><td>3 : 50%</td><td>3</td></tr>
</table>"""

EXAMS = """
<table id="BodyPH_studentExamSeats_gvExamSeats" class="table">
 <tr><th>#</th><th>Title</th><th>Class</th><th>Date</th><th>Session</th><th>Start Time</th><th>Room</th>
     <th>Row</th><th>Column</th><th>Status</th><th>Fee Defaulter</th><th>Surveys</th></tr>
 <tr><td>1</td><td>Final Year Project</td><td>BS (IT)-7 (B)</td><td></td><td></td><td></td><td>N/A</td>
     <td>N/A</td><td>N/A</td><td>N/A</td><td>No</td><td>Completed</td></tr>
 <tr><td>2</td><td>Software Quality Assurance</td><td>BS (IT)-7 (B)</td><td>26/10/2026</td><td>Session - I</td>
     <td>09:00 AM</td><td>HL-18 (1st Floor)</td><td>1</td><td>1</td><td>N/A</td><td>No</td><td>Completed</td></tr>
 <tr><td>3</td><td>Operating Systems</td><td>BS (CS)-5 (S)</td><td>27/10/2026</td><td>Session - IV</td>
     <td>05:30 PM</td><td>HL-9</td><td>4</td><td>1</td><td>N/A</td><td>Yes</td><td>Pending</td></tr>
</table>"""

ANNOUNCEMENTS = """
<table class="table table-hover">
 <tr><th>Sr.No.</th><th>Title</th><th>Announcements</th><th>Posted Date</th></tr>
 <tr><td>1</td><td>BSIT A&amp; B</td><td>Assignment date has been extended till 12 am tonight</td>
     <td>28-09-2026 11:27:40am</td></tr>
 <tr><td colspan="4">Please select a course to display the respective announcements.</td></tr>
</table>"""


def test_parse_attendance():
    rows = campus.parse_attendance(ATTENDANCE)
    assert [r["code"] for r in rows] == ["CSL 341", "ITC 411"]
    a = rows[0]
    assert a["present"] == 15.0 and a["absent"] == 6.0 and a["total"] == 21.0
    assert a["percent"] == 71.43
    assert a["teacher"] == "Jane Teacher" and a["detail_url"] == "AttendanceSummary.aspx?v=abc"
    assert rows[1]["teacher"] == "John Smith"


def test_parse_attendance_detail():
    d = campus.parse_attendance_detail(DETAIL)
    assert d["title"] == "Database Lab" and d["contact_hours"] == "3"
    assert len(d["sessions"]) == 2          # the totals row is skipped
    s = d["sessions"][0]
    assert s["date"] == "Monday, 31 August 2026" and s["absent"] == 3 and s["topics"] == "Recap" and s["remarks"] == "089,015"
    assert d["sessions"][1]["remarks"] == "" and d["sessions"][1]["topics"] == "SQL server"
    assert campus.session_date(s["date"]) == datetime(2026, 8, 31)


def test_attendance_margin():
    ok = campus.attendance_margin(18, 20, 75)
    assert ok["ok"] and ok["percent"] == 90.0 and ok["can_miss"] == 4.0        # 18/24 = 75%
    low = campus.attendance_margin(11, 18, 75)
    assert not low["ok"] and low["need"] == 10.0                               # (11+10)/(18+10) = 75%
    assert campus.attendance_margin(0, 0, 75)["ok"]


def test_parse_exam_seats_and_datetime():
    rows = campus.parse_exam_seats(EXAMS, "Mid-Term")
    assert [r["scheduled"] for r in rows] == [False, True, True]
    sqa = rows[1]
    assert sqa["room"] == "HL-18 (1st Floor)" and sqa["row"] == "1" and sqa["column"] == "1"
    assert campus.exam_datetime(sqa) == datetime(2026, 10, 26, 9, 0)
    assert campus.exam_datetime(rows[2]) == datetime(2026, 10, 27, 17, 30)
    assert campus.exam_datetime(rows[0]) is None
    assert rows[2]["fee_defaulter"] is True and rows[0]["room"] == ""
    assert campus.seat_text(sqa) == "Room HL-18 (1st Floor) · row 1, seat 1"


def test_upcoming_exams_sorted_with_days():
    rows = campus.parse_exam_seats(EXAMS, "Mid-Term")
    up = campus.upcoming_exams(rows, now=datetime(2026, 10, 25, 20, 0))
    assert [e["title"] for e in up] == ["Software Quality Assurance", "Operating Systems"]
    assert up[0]["days"] == 1 and up[1]["days"] == 2
    assert campus.upcoming_exams(rows, now=datetime(2026, 11, 5)) == []


def test_parse_announcements():
    items = campus.parse_announcements(ANNOUNCEMENTS, "Cyber Security")
    assert len(items) == 1
    a = items[0]
    assert a["course"] == "Cyber Security" and a["title"] == "BSIT A& B"
    assert a["text"].startswith("Assignment date has been extended")
    assert a["posted_at"] == "2026-09-28T11:27:40"
    assert len(a["id"]) == 12
    assert campus.parse_announcements(ANNOUNCEMENTS, "Other")[0]["id"] != a["id"]
