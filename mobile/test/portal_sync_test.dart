import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/portal_sync.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final now = DateTime(2026, 11, 21, 9);

  Map<String, dynamic> build({List<Map<String, dynamic>>? assignments, List<Map<String, dynamic>>? attendance}) => buildSummary(
        meta: {'student_name': 'Muhammad Saad', 'semester': 'Fall 2026', 'campus': 'Islamabad E-8 Campus', 'last_sync': '2026-11-21T08:59:00'},
        assignments: assignments ?? [], attendance: attendance ?? [], exams: [], timetable: null, results: null,
        announcements: [], lectures: [], minimum: 75, now: now);

  test('an assignment gets its urgency, due time and what the portal lets you do', () {
    final s = build(assignments: [
      {'id': 'DS#1#Lab', 'course': 'DS', 'assign_no': '1', 'title': 'Lab', 'due_date': '23 November 2026 - 11:59 pm', 'raw_deadline': '23 November 2026 - 11:59 pm',
       'is_extended': false, 'original_due_date': '', 'action': 'Submit', 'marks': '', 'status': 'Pending', 'is_submitted': false, 'files': {'brief': 'x'}},
      {'id': 'DS#2#Quiz', 'course': 'DS', 'assign_no': '2', 'title': 'Quiz', 'due_date': 'Deadline Exceeded', 'raw_deadline': 'Deadline Exceeded',
       'is_extended': false, 'original_due_date': '', 'action': 'Deadline Exceeded', 'marks': '', 'status': 'Missed (Exceeded)', 'is_submitted': false, 'files': {}},
    ]);
    final a = (s['assignments'] as List).cast<Map<String, dynamic>>();
    expect(a[0]['urgency'], 'soon');
    expect(a[0]['can_submit'], isTrue);
    expect(a[0]['has_brief'], isTrue);
    expect(a[0]['due_at'], startsWith('2026-11-23T23:59'));
    expect(a[1]['urgency'], 'missed');
    expect(a[1]['can_submit'], isFalse);
  });

  test('attendance margins are worked out on the phone, with the same rule as the desktop', () {
    final s = build(attendance: [
      {'code': 'CS101', 'title': 'DS', 'credit_hours': '3', 'teacher': '', 'present': 30.0, 'absent': 5.0, 'sessions': []},
      {'code': 'CS102', 'title': 'OS', 'credit_hours': '3', 'teacher': 'Ali', 'present': 20.0, 'absent': 10.0, 'sessions': [for (var i = 0; i < 20; i++) {'date': '$i', 'hours': 1, 'present': 1, 'absent': 0}]},
    ]);
    final c = (s['attendance'] as List).cast<Map<String, dynamic>>();
    expect(c[0]['ok'], isTrue);
    expect(c[0]['percent'], 85.71);
    expect(c[0]['can_miss'], 5.0);   // 30 / 0.75 - 35
    expect(c[1]['ok'], isFalse);
    expect(c[1]['need'], 10.0);      // (0.75 * 30 - 20) / 0.25
    expect((c[1]['classes'] as List).length, 12, reason: 'the last twelve classes only, like the desktop file');
    expect(c[0]['teacher'], isNull);
  });

  test('the result is a summary every screen can read, even when parts are missing', () {
    final s = Summary(build());
    expect(s.work, isEmpty);
    expect(s.studentName, 'Muhammad Saad');
  });

  test('all-capitals names are title-cased like the desktop does', () {
    expect(titleCase('MUHAMMAD SAAD'), 'Muhammad Saad');
    expect(titleCase("O'BRIEN KHAN"), "O'Brien Khan");
  });
}
