import 'dart:convert';

import 'package:assignment_monitor_mobile/alerts.dart';
import 'package:assignment_monitor_mobile/background.dart';
import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/reminders.dart';
import 'package:assignment_monitor_mobile/source.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';

Map<String, dynamic> work(String id, String due, {String course = 'Databases', bool submitted = false, bool open = true, String urgency = 'ok', bool extended = false, String? marks}) =>
    {'id': id, 'course': course, 'title': 'Task $id', 'number': '1', 'due_at': due, 'submitted': submitted, 'open': open, 'urgency': urgency, 'extended': extended, 'marks': marks};

Summary make({List<Map<String, dynamic>> assignments = const [], List<Map<String, dynamic>> exams = const [], List<Map<String, dynamic>> notes = const [],
        List<Map<String, dynamic>> attendance = const [], List<Map<String, dynamic>> timetable = const [], List<Map<String, dynamic>> semesters = const []}) =>
    Summary({
      'schema': 1, 'generated_at': '2026-11-20T10:00:00', 'student': {'name': 'Alex Morgan', 'semester': 'Fall-2026'}, 'minimum_attendance': 75,
      'assignments': assignments, 'exams': exams, 'announcements': notes, 'attendance': attendance, 'timetable': timetable,
      'results': {'cgpa': 3.5, 'semesters': semesters},
    });

void main() {
  setUp(() { SharedPreferences.setMockInitialValues({}); Reminders.forceSupported = false; });
  final sunday = DateTime(2026, 11, 22, 12);   // a Sunday

  group('Sunday summary', () {
    test('lists what is due in the coming week, exams and attendance to watch', () {
      final s = make(
        assignments: [work('a', '2026-11-24T23:59:00'), work('b', '2026-11-26T10:00:00', course: 'OS'), work('far', '2026-12-20T10:00:00')],
        exams: [{'title': 'Final DB', 'scheduled': true, 'date': '28/11/2026'}],
        attendance: [{'title': 'Networks', 'present': 6, 'absent': 4, 'percent': 60, 'ok': false}, {'title': 'Maths', 'present': 9, 'absent': 1, 'percent': 90, 'ok': true, 'can_miss': 1}],
      );
      final m = weeklySummary(s, sunday)!;
      expect(m.title, 'Your week ahead: 2 due, 1 exam, 2 attendance');
      expect(m.body, contains('Due next week (2):'));
      expect(m.body, contains('Task a'));
      expect(m.body, isNot(contains('Task far')));
      expect(m.body, contains('Exams (1): Final DB'));
      expect(m.body, contains('Networks: 60%, below 75%'));
      expect(m.body, contains('Maths: 90%, can miss only 1 h'));
    });

    test('says nothing when there is nothing to say', () {
      expect(weeklySummary(make(), sunday), isNull);
      expect(weeklySummary(make(assignments: [work('done', '2026-11-24T10:00:00', submitted: true)]), sunday), isNull);
    });

    test('caps the list at six and says how many more', () {
      final many = [for (var i = 0; i < 9; i++) work('w$i', '2026-11-25T${(8 + i).toString().padLeft(2, '0')}:00:00')];
      expect(weeklySummary(make(assignments: many), sunday)!.body, contains('... and 3 more'));
    });
  });

  group('morning digest', () {
    final friday = DateTime(2026, 11, 20, 7, 30);
    test('due today, the classes, and an exam in the next three days', () {
      final s = make(
        assignments: [work('a', '2026-11-20T23:59:00'), work('later', '2026-11-25T10:00:00')],
        timetable: [{'day': 'Fri', 'start': '10:00', 'end': '13:00', 'course': 'Data Structures Lab'}, {'day': 'Mon', 'start': '09:00', 'end': '10:00', 'course': 'Other'}],
        exams: [{'title': 'HCI paper', 'scheduled': true, 'date': '22/11/2026', 'time': '09:00 AM'}],
      );
      final m = dailyDigest(s, friday)!;
      expect(m.title, 'Today: 1 due, 1 class, exam soon');
      expect(m.body, contains('Due today: Task a'));
      expect(m.body, contains('Classes: 10:00 Data Structures Lab'));
      expect(m.body, isNot(contains('Other')));
      expect(m.body, contains('Exam soon: HCI paper'));
    });
    test('nothing to say means no digest', () => expect(dailyDigest(make(), friday), isNull));
  });

  group('when they are scheduled', () {
    final s = make(assignments: [work('a', '2026-11-25T10:00:00'), work('b', '2026-12-02T10:00:00')],
        timetable: [{'day': 'Fri', 'start': '10:00', 'end': '11:00', 'course': 'Lab'}, {'day': 'Sat', 'start': '10:00', 'end': '11:00', 'course': 'Lab'}]);
    test('the Sunday summary is the coming Sunday at 18:00, or tonight if it is Sunday morning', () {
      expect(Reminders.planMessages(s, weekly: true, digest: false, now: DateTime(2026, 11, 20, 9)).single.at, DateTime(2026, 11, 22, 18));
      expect(Reminders.planMessages(s, weekly: true, digest: false, now: DateTime(2026, 11, 22, 9)).single.at, DateTime(2026, 11, 22, 18));
      expect(Reminders.planMessages(s, weekly: true, digest: false, now: DateTime(2026, 11, 22, 19)).single.at, DateTime(2026, 11, 29, 18));
    });
    test('the digest is the next 07:30', () {
      expect(Reminders.planMessages(s, weekly: false, digest: true, now: DateTime(2026, 11, 20, 6)).single.at, DateTime(2026, 11, 20, 7, 30));
      expect(Reminders.planMessages(s, weekly: false, digest: true, now: DateTime(2026, 11, 20, 8)).single.at, DateTime(2026, 11, 21, 7, 30));
    });
    test('switched off means none', () => expect(Reminders.planMessages(s, weekly: false, digest: false, now: DateTime(2026, 11, 20)), isEmpty));
  });

  group('what changed', () {
    final before = make(
      assignments: [work('a', '2026-11-25T10:00:00'), work('b', '2026-11-26T10:00:00')],
      notes: [{'id': 'n1', 'title': 'Old notice', 'course': 'C'}],
      exams: [{'title': 'Final DB', 'scheduled': false}],
      semesters: [{'name': 'Fall-2026', 'courses': [{'code': 'DB', 'title': 'Databases', 'credits': 3, 'grade': null}]}],
    );
    test('new announcement, new assignment, extension, marks, exam date and result', () {
      final after = make(
        assignments: [work('a', '2026-11-27T10:00:00', extended: true), work('b', '2026-11-26T10:00:00', marks: '8/10'), work('c', '2026-12-01T10:00:00')],
        notes: [{'id': 'n1', 'title': 'Old notice', 'course': 'C'}, {'id': 'n2', 'title': 'Quiz moved', 'course': 'Databases'}],
        exams: [{'title': 'Final DB', 'scheduled': true, 'date': '02/12/2026', 'time': '09:00 AM', 'room': 'HL-12', 'row': '2', 'seat': '5'}],
        semesters: [{'name': 'Fall-2026', 'courses': [{'code': 'DB', 'title': 'Databases', 'credits': 3, 'grade': 'A-'}]}],
      );
      final titles = changesBetween(before, after).map((c) => c.title).toList();
      expect(titles, containsAll(['New announcement: Quiz moved', 'New assignment: Task c', 'Deadline extended: Task a', 'Marks posted: Task b', 'Exam date posted: Final DB', 'Result posted: Databases']));
      expect(titles.length, 6);
    });
    test('an unchanged summary has no changes', () => expect(changesBetween(before, before), isEmpty));
    test('a new assignment that is already submitted is not announced', () {
      expect(changesBetween(before, make(assignments: [work('a', '2026-11-25T10:00:00'), work('b', '2026-11-26T10:00:00'), work('z', '2026-11-20T10:00:00', submitted: true)], notes: [{'id': 'n1', 'title': 'Old notice', 'course': 'C'}],
          exams: [{'title': 'Final DB', 'scheduled': false}], semesters: [{'name': 'Fall-2026', 'courses': [{'code': 'DB', 'title': 'Databases', 'credits': 3, 'grade': null}]}])), isEmpty);
    });
    test('a flood is folded into one last notification', () {
      final flood = [for (var i = 0; i < 9; i++) Change('k$i', 'Title $i', 'body')];
      final out = messagesFor(flood);
      expect(out.length, 4);
      expect(out.last.title, '6 more updates');
    });
  });

  group('calendar file', () {
    final now = DateTime(2026, 11, 20, 12);
    test('is a valid calendar with deadlines and exams, escaped and with CRLF line ends', () {
      final s = make(
        assignments: [work('a', '2026-11-24T23:59:00', course: 'Data, Structures; Lab'), work('done', '2026-11-24T10:00:00', submitted: true)],
        exams: [{'title': 'Final DB', 'scheduled': true, 'date': '02/12/2026', 'time': '02:30 PM', 'room': 'HL-12', 'row': '2', 'seat': '5'}, {'title': 'No time', 'scheduled': true, 'date': '03/12/2026'}],
      );
      final ics = calendarIcs(s, now);
      expect(ics, startsWith('BEGIN:VCALENDAR\r\n'));
      expect(ics, endsWith('END:VCALENDAR\r\n'));
      expect('BEGIN:VEVENT'.allMatches(ics).length, 3);                    // one deadline (the submitted one is left out) and two exams
      expect(ics, contains('DTSTART:20261124T232900'));                   // 30 minutes before the deadline
      expect(ics, contains('DTEND:20261124T235900'));
      expect(ics, contains('DESCRIPTION:Data\\, Structures\\; Lab'));     // commas and semicolons escaped
      expect(ics, contains('DTSTART:20261202T143000'));                   // 2:30 PM exam
      expect(ics, contains('DTSTART;VALUE=DATE:20261203'));               // an exam with no time is an all-day entry
      expect(ics, contains('TRIGGER:-PT1H'));
      expect(RegExp(r'(?<!\r)\n').hasMatch(ics), isFalse, reason: 'every line ends in CRLF');
    });
    test('long lines are folded at 75 characters', () {
      final long = make(assignments: [work('a', '2026-11-24T23:59:00', course: 'x' * 200)]);
      for (final line in calendarIcs(long, now).split('\r\n')) { expect(line.length, lessThanOrEqualTo(75)); }
    });
    test('unique ids are stable between runs', () {
      final s = make(assignments: [work('a', '2026-11-24T23:59:00')]);
      expect(calendarIcs(s, now).split('\r\n').firstWhere((l) => l.startsWith('UID:')), calendarIcs(s, now.add(const Duration(days: 1))).split('\r\n').firstWhere((l) => l.startsWith('UID:')));
    });
  });

  test('support info carries versions and counts but nothing personal', () {
    final s = make(assignments: [work('a', '2026-11-24T10:00:00')], notes: [{'id': 'n', 'title': 'Private notice', 'course': 'Secret Course'}]);
    final text = supportInfo(s, platform: 'android', lastRead: DateTime(2026, 11, 20, 9), now: DateTime(2026, 11, 20, 12), error: 'No connection.', reminders: 4);
    expect(text, contains('Assignment Monitor for phones $appVersion'));
    expect(text, contains('1 assignments'));
    expect(text, contains('Last read from GitHub: 3 h ago'));
    expect(text, contains('Last problem: No connection.'));
    for (final private in ['Alex', 'Morgan', 'Private notice', 'Secret Course', 'Databases', 'Task a']) { expect(text, isNot(contains(private))); }
  });

  group('the background check', () {
    String json(Summary s) => jsonEncode(s.raw);
    final old = make(notes: [{'id': 'n1', 'title': 'Old notice', 'course': 'C'}]);
    final fresh = make(notes: [{'id': 'n1', 'title': 'Old notice', 'course': 'C'}, {'id': 'n2', 'title': 'Quiz moved', 'course': 'C'}]);

    MemoryStore store() => MemoryStore()..tokenV = 't'..loginV = 'alex'..summaryV = old..etagV = 'e1';

    test('shows a notification for what is new and saves the new summary', () async {
      final st = store();
      final shown = <AlertText>[];
      final n = await BackgroundCheck.run(store: st, source: SummarySource(MockClient((_) async => http.Response(json(fresh), 200, headers: {'etag': 'e2'}))), notify: (m, id) async => shown.add(m));
      expect(n, 1);
      expect(shown.single.title, 'New announcement: Quiz moved');
      expect((await st.cached()).etag, 'e2');
      expect((await st.cached()).summary!.announcements.length, 2);
    });

    test('nothing new, nothing shown', () async {
      final st = store();
      final n = await BackgroundCheck.run(store: st, source: SummarySource(MockClient((_) async => http.Response('', 304))), notify: (m, id) async => fail('no notification expected'));
      expect(n, 0);
    });

    test('with alerts switched off it saves the data but stays quiet', () async {
      SharedPreferences.setMockInitialValues({'alerts': false});
      final st = store();
      final n = await BackgroundCheck.run(store: st, source: SummarySource(MockClient((_) async => http.Response(json(fresh), 200, headers: {'etag': 'e2'}))), notify: (m, id) async => fail('alerts are off'));
      expect(n, 0);
      expect((await st.cached()).summary!.announcements.length, 2);
    });

    test('the first ever summary is not announced as a pile of news', () async {
      final st = MemoryStore()..tokenV = 't'..loginV = 'alex';
      final n = await BackgroundCheck.run(store: st, source: SummarySource(MockClient((_) async => http.Response(json(fresh), 200))), notify: (m, id) async => fail('nothing to compare with'));
      expect(n, 0);
      expect((await st.cached()).summary, isNotNull);
    });

    test('signed out: does nothing', () async {
      expect(await BackgroundCheck.run(store: MemoryStore(), source: SummarySource(MockClient((_) async => throw StateError('must not call')))), 0);
    });

    test('offline: throws, so Android retries later, and the saved data is untouched', () async {
      final st = store();
      await expectLater(BackgroundCheck.run(store: st, source: SummarySource(MockClient((_) async => throw http.ClientException('down')))), throwsA(isA<SourceError>()));
      expect((await st.cached()).summary!.announcements.length, 1);
    });
  });
}
