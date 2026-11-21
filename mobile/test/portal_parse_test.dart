// The Dart parsers are checked against the same HTML snippets as the Python tests (tests/test_campus.py,
// test_results.py, test_deadlines.py, test_lectures.py, test_timetable.py, test_scraper_parsing.py, test_submit.py).
import 'dart:convert';

import 'package:assignment_monitor_mobile/portal_parse.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------- fixtures (synthetic, as in Python)
const attendanceHtml = '''
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
</table>''';

const detailHtml = '''
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
</table>''';

const examsHtml = '''
<table id="BodyPH_studentExamSeats_gvExamSeats" class="table">
 <tr><th>#</th><th>Title</th><th>Class</th><th>Date</th><th>Session</th><th>Start Time</th><th>Room</th>
     <th>Row</th><th>Column</th><th>Status</th><th>Fee Defaulter</th><th>Surveys</th></tr>
 <tr><td>1</td><td>Final Year Project</td><td>BS (IT)-7 (B)</td><td></td><td></td><td></td><td>N/A</td>
     <td>N/A</td><td>N/A</td><td>N/A</td><td>No</td><td>Completed</td></tr>
 <tr><td>2</td><td>Software Quality Assurance</td><td>BS (IT)-7 (B)</td><td>26/10/2026</td><td>Session - I</td>
     <td>09:00 AM</td><td>HL-18 (1st Floor)</td><td>1</td><td>1</td><td>N/A</td><td>No</td><td>Completed</td></tr>
 <tr><td>3</td><td>Operating Systems</td><td>BS (CS)-5 (S)</td><td>27/10/2026</td><td>Session - IV</td>
     <td>05:30 PM</td><td>HL-9</td><td>4</td><td>1</td><td>N/A</td><td>Yes</td><td>Pending</td></tr>
</table>''';

const announcementsHtml = '''
<table class="table table-hover">
 <tr><th>Sr.No.</th><th>Title</th><th>Announcements</th><th>Posted Date</th></tr>
 <tr><td>1</td><td>BSIT A&amp; B</td><td>Assignment date has been extended till 12 am tonight</td>
     <td>28-09-2026 11:27:40am</td></tr>
 <tr><td colspan="4">Please select a course to display the respective announcements.</td></tr>
</table>''';

const resultsHtml = '''
<table class="table tableCol4">
 <tr><td>Enrollment</td><td>01-000000-000</td><td>Registration No.</td><td>1</td></tr>
 <tr><td>Name</td><td>A STUDENT</td><td>Father Name</td><td>A PARENT</td></tr>
 <tr><td>Program</td><td>BS (IT)</td><td>Intake Semester</td><td>Fall-2023</td></tr>
</table>
<table class="table"><caption>Fall-2023</caption>
 <tr><th>#</th><th>Code</th><th>Title</th><th>Majors</th><th>Credit Hours</th><th>Grade</th><th>Grade Points</th><th>Product</th></tr>
 <tr><td>1</td><td>CSC 101</td><td>Programming</td><td>N/A</td><td>3</td><td>A</td><td>4</td><td>12</td></tr>
 <tr><td>2</td><td>CSL 101</td><td>Programming Lab</td><td>N/A</td><td>1</td><td>B+</td><td>3.33</td><td>3.33</td></tr>
 <tr><td>3</td><td>ISL 100</td><td>Tajweed</td><td>N/A</td><td>0</td><td>B</td><td>3</td><td>0</td></tr>
 <tr><td colspan="8" class="text-right"><strong>GPA:</strong> 3.83,
   <strong>CGPA:</strong> 3.83</td></tr>
</table>
<table class="table"><caption>Spring-2024</caption>
 <tr><th>#</th><th>Code</th><th>Title</th><th>Majors</th><th>Credit Hours</th><th>Grade</th><th>Grade Points</th><th>Product</th></tr>
 <tr><td>1</td><td>GSC 200</td><td>Calculus</td><td>N/A</td><td>3</td><td>C</td><td>2</td><td>6</td></tr>
 <tr><td>2</td><td>ENG 100</td><td>English</td><td>N/A</td><td>3</td><td>F</td><td>0</td><td>0</td></tr>
 <tr><td colspan="8" class="text-right"><strong>GPA:</strong> 1,
   <strong>CGPA:</strong> 2.13</td></tr>
</table>
<table class="table"><caption>Fall-2024</caption>
 <tr><th>#</th><th>Code</th><th>Title</th><th>Majors</th><th>Credit Hours</th><th>Grade</th><th>Grade Points</th><th>Product</th></tr>
 <tr><td>1</td><td>ENG 100</td><td>English</td><td>N/A</td><td>3</td><td>N/A</td><td>N/A</td><td>N/A</td></tr>
 <tr><td>2</td><td>SEN 300</td><td>Software Engineering</td><td>N/A</td><td>2</td><td>N/A</td><td>N/A</td><td>N/A</td></tr>
 <tr><td colspan="8" class="text-right"><strong>GPA:</strong> N/A,
   <strong>CGPA:</strong> N/A</td></tr>
</table>
''';

final lectureKey = base64Encode(utf8.encode(
    '108935,2026-10-21,Lecture,0,Lec-1-Cyber-Security-Concepts-28092026-012454pm.pptx,'
    'lms.bahria.edu.pk/Student/LectureNotes.php?s=MjAyNjM%3D&oc=MTUyNzUw'));

final lecturesHtml = '''
<table class="table table-hover">
 <tr><th>Week #</th><th>Lecture Title</th><th>Lecture File(s)</th><th>Video Link(s)</th><th>Video Link</th><th>Remarks</th></tr>
 <tr><td>1</td><td>Cyber Security Concepts</td><td>1. <a href="Download.php?k=$lectureKey" target="_blank">Download Lecture</a></td>
     <td></td><td></td><td></td></tr>
 <tr><td>2</td><td>Two files</td><td>1. <a href="Download.php?k=abc">Download Lecture</a>
     2. <a href="Download.php?k=def">Download Lecture</a></td>
     <td><a href="https://youtu.be/x">Watch</a></td><td></td><td>Read chapter 3</td></tr>
 <tr><td>3</td><td>Empty week</td><td></td><td></td><td></td><td></td></tr>
 <tr><td colspan="6">Please select a course to display the respective lectures.</td></tr>
</table>''';

String ttCell(String title, String room, String abbr, String who, String cls, int span) =>
    '<td data-type="Slot" class="event class Overall" colspan="$span"><div title="$title" class="Color1">'
    '<div class="room"><span>$room</span></div><div class="title"><span>$abbr</span></div>'
    '<div class="facultyMember"><span>$who</span></div><div class="class"><span>$cls</span></div></div></td>';

final ttHtml = '''
<html><body><div>Fall-2026</div>
<table id="timeTable" class="timeTable">
<tr><th>Day</th><th class="hour" colspan="4" data-hour="08">8am</th><th>Day</th></tr>
<tr><td>Mon</td><td></td>${ttCell("Operating Systems&#10;JANE DOE&#10;BS (CS)-5 (A) Morning&#10;HL-1&#10;08:30 AM - 10:00 AM", "HL-1", "OS", "JD", "BS (CS)-5A-M", 6)}
${ttCell("Operating Systems&#10;JANE DOE&#10;BS (CS)-5 (A) Morning&#10;HL-1&#10;10:00 AM - 11:00 AM", "HL-1", "OS", "JD", "BS (CS)-5A-M", 4)}<td>Mon</td></tr>
<tr><td>Tue</td>${ttCell("Data Science Lab&#10;ALI KHAN&#10;BS (CS)-5 (A) Morning&#10;LAB-3&#10;02:30 PM - 05:30 PM", "LAB-3", "DSL", "AK", "BS (CS)-5A-M", 12)}<td>Tue</td></tr>
<tr><td>Wed</td><td></td><td>Wed</td></tr>
</table></body></html>
''';

const miscHtml = '''
<table><tr><th>Sr.No.</th><th>Miscellaneous Type</th><th>Miscellaneous File</th><th>Remarks</th></tr>
<tr><td>1</td><td>Project</td><td><a href="Download.php?k=MTA4OTM1LDIwMjYtMTAtMjIsTWlzY2VsbGFuZW91cywwLFByb2plY3QtR3VpZGVsaW5lcy5kb2N4LGxtcw%3D%3D" target="_blank">Download Miscellaneous File</a></td><td>Read before week 5</td></tr>
<tr><td>2</td><td>Past Paper</td><td><a href="Download.php?k=MTA4OTM2LDIwMjYtMTAtMjIsTWlzY2VsbGFuZW91cywwLE1pZC0yMDI1LnBkZixsbXM%3D" target="_blank">Download Miscellaneous File</a></td><td></td></tr>
</table>''';

const courseTableHtml = '''
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
</table>''';

String dlKey(String kind, String name) {
  final raw = '108935,2026-10-24,$kind,0,$name,lms.bahria.edu.pk/Student/Assignments.php';
  return 'Download.php?k=${Uri.encodeComponent(base64Encode(utf8.encode(raw))).replaceAll('%2F', '/')}';
}

final rowWithFiles = '''<table><tr>
<td>3</td><td>Lab Journal 3</td>
<td><a href="${dlKey('Assignment', 'Lab-Journal-1-11092026-090600am.docx')}" class="label"> Assignment </a><br/>
    <a href="${dlKey('AssignmentSolution', 'Solution-3.pdf')}"> Solution File </a><br/><span>Remarks</span></td>
<td><a href="${dlKey('AssignmentSubmissions', '01-123456-789-152746108935.pdf')}"> Submission </a></td>
<td>Not Marked Yet</td>
<td><a href="${dlKey('Returned', 'checked.pdf')}"> Returned </a></td>
<td>Deadline Exceeded</td><td>23 October 2026-11:55 pm</td>
</tr><tr>
<td>4</td><td>Lab Journal 4</td><td><span>Not available.</span></td><td>No Submission</td>
<td>Not Marked Yet</td><td>---</td><td>Submit</td><td>30 October 2026-11:55 pm</td>
</tr></table>''';

final now = DateTime(2026, 10, 19, 20, 0);

void main() {
  group('malformed input never throws', () {
    const junk = ['', '   ', '<', '<<<>>>', '<table><tr><td>', '<tr><td>1</td></tr>', 'plain text', '<table><caption>', '\u0000<td>'];
    test('every parser returns empty results', () {
      for (final h in junk) {
        expect(parseAttendance(h), isEmpty, reason: h);
        expect(parseAttendanceDetail(h), {'title': '', 'teacher': '', 'contact_hours': '', 'sessions': isEmpty});
        expect(parseExamSeats(h, 'Mid'), isEmpty);
        expect(parseAnnouncements(h, 'C'), isEmpty);
        expect(parseLectures(h, 'C'), isEmpty);
        expect(parseMisc(h, 'C'), isEmpty);
        expect(parseCourseTable(h, 'C'), isEmpty);
        expect(parseTimetable(h), {'semester': '', 'sessions': isEmpty});
        expect(parseResults(h), {'student': isEmpty, 'semesters': isEmpty});
      }
    });
    test('helpers accept null-ish and odd input', () {
      expect(parseDeadlineDatetime('31 February 2026'), isNull);
      expect(sessionDate('31 Febuary 2026'), isNull);
      expect(filenameFromLink(null), '');
      expect(decodeDownloadKey(null), isEmpty);
      expect(postedIso('31-02-2026'), '');
      expect(assignmentFiles([]), isEmpty);
      expect(gpaOf([]), isNull);
      expect(totals([]), {'credits': 0.0, 'earned': 0.0, 'points': 0.0, 'cgpa': null});
      expect(currentSemester([]), isNull);
      expect(gradedCount({}), 0);
    });
  });

  group('helpers', () {
    test('cleanText, firstNumber', () {
      expect(cleanText('  a \n\t b\u00a0 c '), 'a b c');
      expect(cleanText(null), '');
      expect(firstNumber('15.0 :71.43%'), 15.0);
      expect(firstNumber('-2.5 x'), -2.5);
      expect(firstNumber('none'), 0.0);
      expect(firstNumber('none', 7), 7.0);
    });
    test('cellTexts reads only direct td cells', () {
      final doc = parseAttendance('<table><tr><td> a  b </td><td><table><tr><td>inner</td></tr></table></td></tr></table>');
      expect(doc, isEmpty); // fewer than 12 cells
    });
    test('sha1Hex matches hashlib', () {
      expect(sha1Hex('abc'), 'a9993e364706816aba3e25717850c26c9cd0d89d');
      expect(sha1Hex('${'x' * 200}\u00e9'), '985a0e90f61569af6e9673f772d606dc060a1d48');
    });
    test('to24h and minutes', () {
      expect(to24h('12:05', 'AM'), '00:05');
      expect(to24h('12:05', 'pm'), '12:05');
      expect(to24h('1:30', 'PM'), '13:30');
      expect(minutes('13:30'), 810);
    });
  });

  group('campus: attendance', () {
    test('parseAttendance', () {
      final rows = parseAttendance(attendanceHtml);
      expect(rows.map((r) => r['code']), ['CSL 341', 'ITC 411']);
      final a = rows[0];
      expect([a['present'], a['absent'], a['total']], [15.0, 6.0, 21.0]);
      expect(a['percent'], 71.43);
      expect(a['teacher'], 'Jane Teacher');
      expect(a['detail_url'], 'AttendanceSummary.aspx?v=abc');
      expect(a['credit_hours'], '1');
      expect(a['class'], 'BS (IT)-6 (A) Morning');
      expect(a['fee_status'], 'Paid');
      expect(rows[1]['teacher'], 'John Smith');
    });

    test('percent is computed when the cell has none; header row skipped', () {
      final h = attendanceHtml.replaceFirst('15.0 :71.43%', '15.0');
      expect(parseAttendance(h)[0]['percent'], 71.43);
      expect(parseAttendance(attendanceHtml.replaceFirst('15.0 :71.43%', '0').replaceFirst('<td>21.0</td>', '<td>0</td>'))[0]['percent'], 0.0);
    });

    test('parseAttendanceDetail', () {
      final d = parseAttendanceDetail(detailHtml);
      expect(d['title'], 'Database Lab');
      expect(d['teacher'], 'A TEACHER');
      expect(d['contact_hours'], '3');
      final sessions = (d['sessions'] as List).cast<Map<String, dynamic>>();
      expect(sessions.length, 2); // the totals row is skipped
      final s = sessions[0];
      expect(s['date'], 'Monday, 31 August 2026');
      expect(s['absent'], 3.0);
      expect(s['topics'], 'Recap');
      expect(s['remarks'], '089,015');
      expect(sessions[1]['remarks'], '');
      expect(sessions[1]['topics'], 'SQL server');
      expect(sessionDate(s['date'] as String), DateTime(2026, 8, 31));
    });

    test('attendanceMargin', () {
      final ok = attendanceMargin(18, 20, 75);
      expect(ok['ok'], isTrue);
      expect(ok['percent'], 90.0);
      expect(ok['can_miss'], 4.0); // 18/24 = 75%
      final low = attendanceMargin(11, 18, 75);
      expect(low['ok'], isFalse);
      expect(low['need'], 10.0); // (11+10)/(18+10) = 75%
      expect(attendanceMargin(0, 0, 75)['ok'], isTrue);
      expect(attendanceMargin(5, 10, 0)['can_miss'], double.infinity);
      expect(attendanceMargin(25, 100, 100)['need'], double.infinity);
    });

    test('sessionDate', () {
      expect(sessionDate('Monday, 7 Sep 2026'), DateTime(2026, 9, 7));
      expect(sessionDate('Monday, 7 September 2026'), DateTime(2026, 9, 7));
      expect(sessionDate('nothing'), isNull);
      expect(sessionDate(null), isNull);
    });
  });

  group('campus: exams', () {
    test('parseExamSeats, examDatetime, seatText', () {
      final rows = parseExamSeats(examsHtml, 'Mid-Term');
      expect(rows.map((r) => r['scheduled']), [false, true, true]);
      final sqa = rows[1];
      expect(sqa['room'], 'HL-18 (1st Floor)');
      expect(sqa['row'], '1');
      expect(sqa['column'], '1');
      expect(sqa['id'], 'Mid-Term#Software_Quality_Assurance');
      expect(examDatetime(sqa), DateTime(2026, 10, 26, 9, 0));
      expect(examDatetime(rows[2]), DateTime(2026, 10, 27, 17, 30));
      expect(examDatetime(rows[0]), isNull);
      expect(rows[2]['fee_defaulter'], isTrue);
      expect(rows[0]['room'], '');
      expect(seatText(sqa), 'Room HL-18 (1st Floor) \u00b7 row 1, seat 1');
      expect(seatText(rows[0]), '');
    });

    test('examDatetime formats', () {
      expect(examDatetime({'date': '26/10/2026', 'start_time': '17:30'}), DateTime(2026, 10, 26, 17, 30));
      expect(examDatetime({'date': '26/10/2026', 'start_time': ''}), DateTime(2026, 10, 26));
      expect(examDatetime({'date': '26/10/2026', 'start_time': '12:00 am'}), DateTime(2026, 10, 26, 0, 0));
      expect(examDatetime({'date': '31/02/2026', 'start_time': ''}), isNull);
      expect(examDatetime({'date': 'soon'}), isNull);
    });

    test('upcomingExams sorted with days', () {
      final rows = parseExamSeats(examsHtml, 'Mid-Term');
      final up = upcomingExams(rows, DateTime(2026, 10, 25, 20, 0));
      expect(up.map((e) => e['title']), ['Software Quality Assurance', 'Operating Systems']);
      expect([up[0]['days'], up[1]['days']], [1, 2]);
      expect(up[0]['when'], DateTime(2026, 10, 26, 9, 0));
      expect(upcomingExams(rows, DateTime(2026, 11, 5)), isEmpty);
    });
  });

  group('campus: announcements', () {
    test('parseAnnouncements', () {
      final items = parseAnnouncements(announcementsHtml, 'Cyber Security');
      expect(items.length, 1);
      final a = items[0];
      expect(a['course'], 'Cyber Security');
      expect(a['title'], 'BSIT A& B');
      expect(a['text'], startsWith('Assignment date has been extended'));
      expect(a['posted_at'], '2026-09-28T11:27:40');
      expect((a['id'] as String).length, 12);
      expect(a['id'], 'a5192be184cc'); // the id Python produces for the same row
      expect(parseAnnouncements(announcementsHtml, 'Other')[0]['id'], isNot(a['id']));
    });

    test('postedIso', () {
      expect(postedIso('28-09-2026 11:27:40am'), '2026-09-28T11:27:40');
      expect(postedIso('28-09-2026 12:05pm'), '2026-09-28T12:05:00');
      expect(postedIso('28-09-2026 12:05 AM'), '2026-09-28T00:05:00');
      expect(postedIso('28-09-2026'), '2026-09-28T00:00:00');
      expect(postedIso('garbage'), '');
      expect(postedIso(''), '');
    });
  });

  group('campus: lecture notes', () {
    test('filenameFromLink decodes the token', () {
      expect(filenameFromLink('Download.php?k=$lectureKey'), 'Lec-1-Cyber-Security-Concepts-28092026-012454pm.pptx');
      expect(filenameFromLink('Download.php?k=%%%'), '');
      expect(filenameFromLink('nothing'), '');
    });

    test('parseLectures', () {
      final rows = parseLectures(lecturesHtml, 'Cyber Security');
      expect(rows.map((r) => r['week']), ['1', '2']); // the empty week and the hint row are skipped
      final first = rows[0];
      final f0 = (first['files'] as List)[0] as Map;
      expect(f0['filename'], endsWith('.pptx'));
      expect(f0['label'], 'Download Lecture');
      final two = rows[1];
      expect((two['files'] as List).length, 2);
      expect(two['videos'], ['https://youtu.be/x']);
      expect(two['remarks'], 'Read chapter 3');
      expect(((two['files'] as List)[1] as Map)['filename'], 'Two files (2)'); // no name in the token: title + index
      expect((first['id'] as String).length, 12);
      expect(rows.map((r) => r['id']), ['a3867ab309ce', '99f3f24cab7d']);
    });

    test('safeName', () {
      expect(safeName('Lab: "Intro" <v2>?'), 'Lab Intro v2');
      expect(safeName(''), 'untitled');
      expect(safeName('...'), 'untitled');
      expect(safeName('a' * 100).length, 80);
    });
  });

  group('campus: timetable and miscellaneous', () {
    test('parseTimetable merges contiguous blocks', () {
      final data = parseTimetable(ttHtml);
      expect(data['semester'], 'Fall-2026');
      final all = (data['sessions'] as List).cast<Map<String, dynamic>>();
      final mon = sessionsOn(all, 'Mon');
      expect(mon.length, 1, reason: 'the two back-to-back Operating Systems slots become one class');
      expect([mon[0]['start'], mon[0]['end']], ['08:30', '11:00']);
      expect(mon[0]['course'], 'Operating Systems');
      expect(mon[0]['teacher'], 'Jane Doe');
      expect(mon[0]['room'], 'HL-1');
      expect(mon[0]['class'], 'BS (CS)-5 (A) Morning');
      expect(mon[0]['initials'], 'JD');
      final tue = sessionsOn(all, 'Tue');
      expect([tue[0]['start'], tue[0]['end'], tue[0]['abbr']], ['14:30', '17:30', 'DSL']);
      expect(sessionsOn(all, 'Wed'), isEmpty);
    });

    test('parseTimetable sorts by day then start', () {
      final h = ttHtml.replaceFirst('<tr><td>Mon</td>', '<tr><td>Fri</td>');
      final all = (parseTimetable(h)['sessions'] as List).cast<Map<String, dynamic>>();
      expect(all.map((s) => s['day']), ['Tue', 'Fri']);
    });

    test('parseMisc records look like lectures', () {
      final items = parseMisc(miscHtml, 'Cyber Security');
      expect(items.length, 2);
      final first = items[0];
      expect(first['kind'], 'misc');
      expect(first['course'], 'Cyber Security');
      expect(first['title'], 'Project');
      expect(first['week'], 0);
      expect(((first['files'] as List)[0] as Map)['filename'], 'Project-Guidelines.docx');
      expect(first['remarks'], 'Read before week 5');
      expect(((items[1]['files'] as List)[0] as Map)['filename'], 'Mid-2025.pdf');
      expect(first['id'], isNot(items[1]['id']));
      expect(items.map((i) => i['id']), ['1c72e6af381143c2', 'a280f5bd94c1c2fc']);
    });
  });

  group('results', () {
    List<Map<String, dynamic>> sems() => (parseResults(resultsHtml)['semesters'] as List).cast<Map<String, dynamic>>();

    test('parseResults reads student, semesters and footers', () {
      final d = parseResults(resultsHtml);
      final student = d['student'] as Map;
      expect(student['program'], 'BS (IT)');
      expect(student['intake_semester'], 'Fall-2023');
      expect(student['name'], 'A STUDENT');
      final s = sems();
      expect(s.map((x) => x['name']), ['Fall-2023', 'Spring-2024', 'Fall-2024']);
      final first = s[0];
      expect(first['gpa'], 3.83);
      expect(first['cgpa'], 3.83);
      expect(first['complete'], isTrue);
      expect((first['courses'] as List)[1],
          {'code': 'CSL 101', 'title': 'Programming Lab', 'credits': 1.0, 'grade': 'B+', 'points': 3.33, 'product': 3.33});
      final running = s[2];
      expect(running['gpa'], isNull);
      expect(running['cgpa'], isNull);
      expect(running['complete'], isFalse);
      final c0 = (running['courses'] as List)[0] as Map;
      expect(c0['grade'], '');
      expect(c0['points'], isNull);
    });

    test('gpaOf, totals, currentSemester, gradedCount match the portal', () {
      final s = sems();
      List<Map<String, dynamic>> courses(Map<String, dynamic> x) => (x['courses'] as List).cast<Map<String, dynamic>>();
      expect(gpaOf(courses(s[0])), 3.83); // (12 + 3.33) / 4; the zero-credit course weighs nothing
      expect(gpaOf(courses(s[1])), 1.0);
      final t = totals([s[0], s[1]]);
      expect([t['credits'], t['earned'], t['cgpa']], [10.0, 7.0, 2.13]);
      expect(gpaOf(courses(s[2])), isNull);
      expect(currentSemester(s)!['name'], 'Fall-2024');
      expect(currentSemester([s[0], s[1]]), isNull);
      expect(gradedCount(s[0]), 3);
      expect(gradedCount(s[2]), 0);
      final later = (parseResults(resultsHtml.replaceFirst('<td>3</td><td>N/A</td><td>N/A</td><td>N/A</td>', '<td>3</td><td>A-</td><td>3.67</td><td>11.01</td>'))['semesters'] as List).cast<Map<String, dynamic>>();
      expect(gradedCount(later[2]), 1);
      expect(later[2]['complete'], isFalse);
    });

    test('a grade without printed points falls back to the scale', () {
      final h = resultsHtml.replaceFirst('<td>B+</td><td>3.33</td><td>3.33</td>', '<td>B+</td><td>N/A</td><td>3.33</td>');
      expect(((parseResults(h)['semesters'] as List)[0]['courses'] as List)[1]['points'], 3.33);
    });
  });

  group('deadlines', () {
    test('parseDeadline splits extended from original', () {
      expect(parseDeadline('4 October 2026 - 11:50 am13 September 2026-11:55 am'), ('4 October 2026 - 11:50 am', true, '13 September 2026-11:55 am'));
      expect(parseDeadline('28 September 2026 - 12:00 am22 September 2026-12:00 am'), ('28 September 2026 - 12:00 am', true, '22 September 2026-12:00 am'));
      expect(parseDeadline('19 October 2026-10:30 pm'), ('19 October 2026-10:30 pm', false, ''));
      expect(parseDeadline(''), ('N/A', false, ''));
      expect(parseDeadline('   '), ('N/A', false, ''));
      expect(parseDeadline(null), ('N/A', false, ''));
    });

    test('parseDeadlineDatetime', () {
      expect(parseDeadlineDatetime('19 October 2026-10:30 pm'), DateTime(2026, 10, 19, 22, 30));
      expect(parseDeadlineDatetime('19 October 2026 - 10:30 am'), DateTime(2026, 10, 19, 10, 30));
      expect(parseDeadlineDatetime('28 September 2026 - 12:00 am'), DateTime(2026, 9, 28, 0, 0));
      expect(parseDeadlineDatetime('13 October 2026 - 12:00 pm'), DateTime(2026, 10, 13, 12, 0));
      expect(parseDeadlineDatetime('5 Nov 2026-11:55 pm'), DateTime(2026, 11, 5, 23, 55));
      expect(parseDeadlineDatetime('5 November 2026'), DateTime(2026, 11, 5, 23, 59));
      expect(parseDeadlineDatetime('N/A'), isNull);
      expect(parseDeadlineDatetime(''), isNull);
      expect(parseDeadlineDatetime('Deadline Exceeded'), isNull);
    });

    test('deadlineOf and daysUntil', () {
      expect(deadlineOf({'due_date': '19 October 2026-10:30 pm'}), DateTime(2026, 10, 19, 22, 30));
      expect(deadlineOf({}), isNull);
      expect(daysUntil(DateTime(2026, 10, 22, 1, 0), now), 3);
      expect(daysUntil(DateTime(2026, 10, 19, 23, 59), now), 0);
      expect(daysUntil(null, now), isNull);
    });

    test('classify', () {
      const cases = <(Map<String, dynamic>, String)>[
        ({'due_date': '19 October 2026-10:30 pm'}, 'today'),
        ({'due_date': '19 October 2026-10:30 am'}, 'missed'),
        ({'due_date': '20 October 2026-11:55 pm'}, 'soon'),
        ({'due_date': '22 October 2026-11:55 pm'}, 'soon'),
        ({'due_date': '25 October 2026-11:55 pm'}, 'week'),
        ({'due_date': '5 November 2026-11:55 pm'}, 'later'),
        ({'due_date': '4 October 2026 - 11:50 am', 'is_submitted': true}, 'submitted'),
        ({'due_date': '4 October 2026-11:55 am', 'status': 'Missed (Exceeded)'}, 'missed'),
        ({'due_date': '30 October 2026-11:55 am', 'status': 'Missed (Exceeded)'}, 'missed'),
        ({'due_date': 'N/A'}, 'unknown'),
      ];
      for (final (item, key) in cases) {
        expect(classify(item, now)['key'], key, reason: '$item');
      }
      expect(classify({'due_date': 'N/A'}, now), {'key': 'unknown', 'label': 'No deadline', 'days': null});
    });

    test('classify labels mention the time for today and tomorrow', () {
      expect(classify({'due_date': '19 October 2026-10:30 pm'}, now)['label'], 'Due today at 10:30 pm');
      expect(classify({'due_date': '20 October 2026-08:00 am'}, now)['label'], 'Due tomorrow at 8:00 am');
      expect(classify({'due_date': '20 October 2026-12:15 am'}, now)['label'], 'Due tomorrow at 12:15 am');
      expect(classify({'due_date': '22 October 2026-11:55 pm'}, now)['label'], 'Due in 3 days');
    });

    test('isOpenPending', () {
      expect(isOpenPending({'is_submitted': false, 'status': 'Pending'}), isTrue);
      expect(isOpenPending({'is_submitted': true, 'status': 'Submitted'}), isFalse);
      expect(isOpenPending({'is_submitted': false, 'status': 'Missed (Exceeded)'}), isFalse);
    });

    test('sortKey puts open work first by nearest deadline', () {
      final items = <Map<String, dynamic>>[
        {'title': 'submitted-late', 'due_date': '30 October 2026-11:55 pm', 'is_submitted': true, 'status': 'Submitted'},
        {'title': 'open-far', 'due_date': '28 October 2026-11:55 pm', 'is_submitted': false, 'status': 'Pending'},
        {'title': 'open-near', 'due_date': '21 October 2026-11:55 pm', 'is_submitted': false, 'status': 'Pending'},
        {'title': 'submitted-early', 'due_date': '1 October 2026-11:55 pm', 'is_submitted': true, 'status': 'Submitted'},
      ];
      items.sort((a, b) => compareSortKeys(sortKey(a), sortKey(b)));
      expect(items.map((i) => i['title']), ['open-near', 'open-far', 'submitted-late', 'submitted-early']);
      expect(sortKey({'status': 'Pending'}), (0, double.infinity));
    });
  });

  group('assignments (lms_scraper)', () {
    test('parseCourseTable', () {
      final items = parseCourseTable(courseTableHtml, 'Mobile App Lab');
      expect(items.map((i) => i['title']), ['Lab Journal 1', 'Widgets', 'Cursors', 'Graded one']);
      final extended = items[0];
      expect(extended['is_extended'], isTrue);
      expect(extended['due_date'], '4 October 2026 - 11:50 am');
      expect(extended['original_due_date'], '13 September 2026-11:55 am');
      expect(extended['is_submitted'], isTrue);
      expect(extended['status'], 'Submitted');
      expect(extended['raw_deadline'], '4 October 2026 - 11:50 am13 September 2026-11:55 am');
      expect(extended['submission_status'], 'Submission');
      expect(extended['action'], 'Deadline Exceeded');
      expect(items[1]['is_submitted'], isFalse);
      expect(items[1]['status'], 'Missed (Exceeded)');
      expect(items[2]['is_submitted'], isFalse);
      expect(items[2]['status'], 'Pending');
      expect(items[2]['id'], 'Mobile_App_Lab#3#Cursors');
      expect(items[2]['assign_no'], '3');
      expect(items[3]['marks'], '8 / 10');
    });

    test('rows with too few cells are ignored', () {
      expect(parseCourseTable('<table><tr><td>a</td><td>b</td></tr></table>', 'X'), isEmpty);
    });

    test('assignment rows carry their files, named from the link key', () {
      final items = parseCourseTable(rowWithFiles, 'Course');
      final files = items[0]['files'] as Map;
      expect(files.keys.toSet(), {'brief', 'solution', 'submission', 'returned'});
      expect(files['brief']['filename'], 'Lab-Journal-1-11092026-090600am.docx');
      expect(files['brief']['label'], 'Assignment');
      expect(files['submission']['filename'], '01-123456-789-152746108935.pdf');
      expect(files['solution']['filename'], 'Solution-3.pdf');
      expect(files['returned']['filename'], 'checked.pdf');
      expect(items[1]['files'], isEmpty);
    });

    test('assignmentFiles reads the td list directly', () {
      // a row built by hand: only a brief link in column three
      final items = parseCourseTable(
          '<table><tr><td>1</td><td>T</td><td><a href="Download.php?k=zzz">Assignment</a><a href="x.php">other</a></td><td></td><td></td><td></td><td>Submit</td><td>1 October 2026-11:55 pm</td></tr></table>',
          'C');
      final files = items[0]['files'] as Map;
      expect(files.keys, ['brief']);
      expect(files['brief']['filename'], '');
    });

    test('decodeDownloadKey', () {
      expect(decodeDownloadKey(dlKey('Assignment', 'a.docx')), {'date': '2026-10-24', 'kind': 'Assignment', 'filename': 'a.docx'});
      expect(decodeDownloadKey('Assignments.php?s=1'), isEmpty);
      expect(decodeDownloadKey('Download.php?k=%%%'), isEmpty);
      expect(decodeDownloadKey('Download.php?k=${base64Encode(utf8.encode('a,b,c'))}'), isEmpty);
    });
  });

  group('submitting work', () {
    test('submissionUploadName drops special symbols and lowercases the extension', () {
      expect(submissionUploadName(r'C:\x\My#Report $final (v2).PDF'), 'MyReport final (v2).pdf');
      expect(submissionUploadName('/tmp/My#Report \$final (v2).PDF'), 'MyReport final (v2).pdf');
      expect(submissionUploadName('###.zip'), 'submission.zip');
      expect(submissionUploadName('.hidden'), 'hidden');
      expect(submissionUploadName('noext'), 'noext');
    });

    test('checkSubmissionFileBytes', () {
      expect(checkSubmissionFileBytes('a.pdf', 10), '');
      expect(checkSubmissionFileBytes('a.PDF', 10), '');
      expect(checkSubmissionFileBytes('a.exe', 1), contains('accepts only'));
      expect(checkSubmissionFileBytes('a', 1), contains('accepts only'));
      expect(checkSubmissionFileBytes('e.docx', 0), contains('empty'));
      expect(checkSubmissionFileBytes('b.zip', submitMaxBytes + 1), contains('15 MB'));
      expect(checkSubmissionFileBytes('c.zip', submitMaxBytes), '');
    });

    test('submissionActions', () {
      expect(submissionActions('Submit'), (true, false));
      expect(submissionActions('Delete'), (false, true));
      expect(submissionActions('Submit Delete'), (true, true));
      expect(submissionActions('Deadline Exceeded'), (false, false));
      expect(submissionActions(''), (false, false));
      expect(submissionActions(null), (false, false));
    });
  });
}
