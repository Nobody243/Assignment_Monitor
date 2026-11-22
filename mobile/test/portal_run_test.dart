import 'dart:typed_data';

import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/main.dart' show sectionOfTab;
import 'package:assignment_monitor_mobile/portal.dart';
import 'package:assignment_monitor_mobile/portal_sync.dart';
import 'package:flutter_test/flutter_test.dart';

import 'portal_parse_test.dart';

/// A browser that only answers the two small scripts the whole-portal read runs itself.
class _B implements PortalBrowser {
  @override Future<dynamic> js(String s) async => s.contains('semesterId') ? '{"name":"MUHAMMAD SAAD","semester":"Fall 2026"}' : '[]';
  @override Future<void> open(String url, {Duration timeout = const Duration(seconds: 40)}) async {}
  @override Future<String> url() async => '';
  @override Future<String> html() async => courseTableHtml;
  @override Future<void> jsThenSettle(String source, {Duration timeout = const Duration(seconds: 20)}) async {}
  @override Future<FetchedFile> fetchFile(String url, {int maxBytes = maxDownloadBytes}) async => throw UnimplementedError();
  @override Future<void> attachFile(String selector, String name, String mime, Uint8List bytes) async {}
  @override Future<void> close() async {}
}

/// A portal that serves the parser fixtures, with chosen pages or courses failing.
class _Portal extends Portal {
  _Portal({this.failPages = const {}, this.failCourse, this.emptyTimes = const {}}) : super(_B(), pause: Duration.zero);

  /// How many times each CMS page answers with an empty shell before it fills in (a page read too early).
  final Map<String, int> emptyTimes;
  final seen = <String, int>{};
  final Set<String> failPages;
  final String? failCourse;
  final order = <String>[];

  @override Future<List<PortalCourse>> courses() async => const [PortalCourse('1', 'Cyber Security'), PortalCourse('2', 'Databases')];
  @override Future<String> cmsPage(String url, {String? ready, int readySeconds = 8}) async {
    order.add(url);
    if (failPages.contains(url)) throw StateError('page failed');
    final n = seen[url] = (seen[url] ?? 0) + 1;
    if (n <= (emptyTimes[url] ?? 0)) return '<html><body></body></html>';
    return switch (url) {
      attendanceUrl => attendanceHtml, resultsUrl => resultsHtml, examsUrl => examsHtml, timetableUrl => ttHtml, _ => detailHtml,
    };
  }
  @override Future<String> lmsPage(String url) async { order.add(url); if (failPages.contains(url)) throw StateError('page failed'); return ''; }
  @override Future<String> selectCourse(String name) async {
    if (name == failCourse) throw StateError('course failed');
    return courseTableHtml;
  }
}

void main() {
  test('everything is read, and the summary has every section', () async {
    final out = await PortalSync(_Portal(), now: () => DateTime(2026, 11, 21, 9), retryPause: Duration.zero).run(campus: 'Islamabad E-8 Campus');
    expect(out.skipped, isEmpty);
    final s = out.summary;
    expect(s.studentName, 'Muhammad Saad');
    expect(s.semester, 'Fall 2026');
    expect(s.attendance, isNotEmpty);
    expect(s.terms, isNotEmpty);
    expect(out.report.any((l) => l.startsWith('lectures:')), isTrue);
    expect(out.report.every((l) => !l.contains('could not')), isTrue);
  });

  test('each part fills the screens as soon as it is read, and unread parts keep the last full read', () async {
    final previous = {'schema': 1, 'attendance': [{'code': 'OLD101', 'title': 'Old', 'present': 1, 'absent': 0, 'percent': 100, 'ok': true}], 'lectures': [{'id': 'x', 'course': 'C', 'week': 1, 'title': 'Old week', 'files': []}]};
    final partials = <Summary>[];
    await PortalSync(_Portal(), now: () => DateTime(2026, 11, 21, 9)).run(previous: previous, onPartial: (s) async => partials.add(s));
    expect(partials.length, greaterThanOrEqualTo(6), reason: 'one per part');
    expect(partials.first.work, isNotEmpty, reason: 'assignments come first');
    expect(partials.first.attendance.single.code, 'OLD101', reason: 'attendance is still the old copy until it is read');
    expect(partials.first.raw['lectures'], isNotEmpty);
    expect(partials.last.attendance.any((c) => c.code == 'OLD101'), isFalse, reason: 'replaced once read');
  });

  test('a page that fails is skipped and named; the rest is still read', () async {
    final out = await PortalSync(_Portal(failPages: {examsUrl, lecturesUrl})).run();
    expect(out.skipped, containsAll(['exams', 'lectures']));
    expect(out.summary.attendance, isNotEmpty);
    expect(out.summary.terms, isNotEmpty);
    expect(out.report.where((l) => l.contains('could not be read')).length, 2);
  });

  test('one course failing is noted and the other courses still come through', () async {
    final out = await PortalSync(_Portal(failCourse: 'Databases')).run();
    expect(out.skipped, isEmpty, reason: 'the part as a whole worked');
    expect(out.report.any((l) => l.contains('1 of 2 courses could not be read')), isTrue);
    expect(out.summary.work, isNotEmpty);
  });

  test('a section refresh reads only its own page and leaves the rest as it was', () async {
    final previous = {'schema': 1, 'exams': [{'title': 'Old exam', 'scheduled': false}], 'lectures': [{'id': 'x', 'course': 'C', 'week': 1, 'title': 'Old week', 'files': []}]};
    final p = _Portal();
    final out = await PortalSync(p).run(only: {'attendance'}, previous: previous);
    expect(p.order, [attendanceUrl, ...p.order.where((u) => u.contains('Attendance') && u != attendanceUrl)], reason: 'attendance and its detail pages only');
    expect(p.order.contains(examsUrl), isFalse);
    expect(p.order.contains(lecturesUrl), isFalse);
    expect(out.summary.attendance, isNotEmpty);
    expect(out.summary.exams.single.title, 'Old exam', reason: 'untouched sections keep the last read');
    expect(out.summary.raw['lectures'], isNotEmpty);
    expect(out.report.length, 1);
  });

  test('refreshing the lectures looks up the courses but reads nothing else', () async {
    final p = _Portal();
    final out = await PortalSync(p).run(only: {'lectures'});
    expect(p.order.where((u) => u == lecturesUrl || u == miscUrl).length, 2);
    expect(p.order.contains(attendanceUrl), isFalse);
    expect(p.order.contains(announcementsUrl), isFalse);
    expect(out.report.last, startsWith('lectures:'));
  });

  test('each screen refreshes its own section and Today refreshes everything', () {
    expect(sectionOfTab[1], 'assignments');
    expect(sectionOfTab[2], 'attendance');
    expect(sectionOfTab[3], 'exams');
    expect(sectionOfTab[4], 'announcements');
    expect(sectionOfTab[5], 'timetable');
    expect(sectionOfTab[6], 'results');
    expect(sectionOfTab[7], 'lectures');
    expect(sectionOfTab[0], isNull, reason: 'Today is the full check');
    expect(sectionOfTab[8], isNull, reason: 'Settings has no data of its own');
  });

  test('progress is reported part by part: seven for everything, one for a single screen', () async {
    final full = <(int, int)>[];
    await PortalSync(_Portal()).run(onProgress: (d, n) => full.add((d, n)));
    expect(full.first, (0, 7));
    expect(full.last, (7, 7));
    final one = <(int, int)>[];
    await PortalSync(_Portal()).run(only: {'results'}, onProgress: (d, n) => one.add((d, n)));
    expect(one.first, (0, 1));
    expect(one.last, (1, 1));
  });

  test('when the lecture page shows nothing the report says what the page looked like', () async {
    final out = await PortalSync(_Portal()).run(only: {'lectures'});
    expect(out.report.any((l) => l.startsWith('lecture page for Cyber Security:')), isTrue);
  });

  test('no courses at all stops with a message instead of an empty summary', () async {
    final p = _NoCourses();
    expect(() => PortalSync(p).run(), throwsA(isA<StateError>()));
  });
  test('a page read before it filled in is read again, so attendance, exams and the timetable arrive the first time', () async {
    final p = _Portal(emptyTimes: {attendanceUrl: 1, examsUrl: 1, timetableUrl: 1});
    final out = await PortalSync(p, retryPause: Duration.zero).run();
    expect(out.summary.attendance, isNotEmpty);
    expect(out.summary.exams, isNotEmpty);
    expect(out.summary.timetable, isNotEmpty);
    expect(out.skipped, isEmpty);
    expect(out.report.every((l) => !l.contains('came back empty')), isTrue);
  });

  test('a page that stays empty keeps the earlier data instead of wiping it, and says so', () async {
    final previous = {
      'schema': 1,
      'attendance': [{'code': 'OLD101', 'title': 'Old', 'present': 3.0, 'absent': 1.0, 'percent': 75, 'ok': true}],
      'timetable': [{'day': 'Mon', 'start': '09:00', 'end': '10:00', 'course': 'Old class'}],
    };
    final p = _Portal(emptyTimes: {attendanceUrl: 99, timetableUrl: 99});
    final out = await PortalSync(p, retryPause: Duration.zero).run(previous: previous);
    expect(out.summary.attendance.single.code, 'OLD101');
    expect(out.summary.timetable.single.course, 'Old class');
    expect(out.report.where((l) => l.contains('came back empty')).length, 2);
    expect(out.skipped, isEmpty, reason: 'an empty page is not a failure');
  });

  test('with nothing earlier to keep, an empty page is simply empty', () async {
    final out = await PortalSync(_Portal(emptyTimes: {examsUrl: 99}), retryPause: Duration.zero).run();
    expect(out.summary.exams, isEmpty);
    expect(out.report.any((l) => l.startsWith('exams: 0 rows')), isTrue);
  });

  test('the everyday check leaves the lecture notes out once there are some, and reads them when there are none', () async {
    final known = {'schema': 1, 'lectures': [{'id': 'x', 'course': 'C', 'week': 1, 'title': 'W', 'files': []}]};
    final a = _Portal();
    final withLectures = await PortalSync(a, retryPause: Duration.zero).run(previous: known);
    expect(a.order.contains(lecturesUrl), isFalse);
    expect(withLectures.summary.raw['lectures'], isNotEmpty, reason: 'the earlier list stays');
    final b = _Portal();
    await PortalSync(b, retryPause: Duration.zero).run();
    expect(b.order.contains(lecturesUrl), isTrue, reason: 'first time: read them');
    final c = _Portal();
    await PortalSync(c, retryPause: Duration.zero).run(previous: known, only: {'lectures'});
    expect(c.order.contains(lecturesUrl), isTrue, reason: 'the Lectures screen refresh always reads them');
  });

  test('attendance whose hours have not changed does not load the class-by-class pages again', () async {
    final first = _Portal();
    final out1 = await PortalSync(first, retryPause: Duration.zero).run(only: {'attendance'});
    final details1 = first.order.where((u) => u != attendanceUrl && u.contains('Attendance')).length;
    final again = _Portal();
    final out2 = await PortalSync(again, retryPause: Duration.zero).run(only: {'attendance'}, previous: out1.summary.raw);
    final details2 = again.order.where((u) => u != attendanceUrl && u.contains('Attendance')).length;
    expect(details1, greaterThan(0));
    expect(details2, lessThan(details1), reason: 'unchanged courses reuse their class list');
    expect(out2.summary.attendance.length, out1.summary.attendance.length);
  });

}

class _NoCourses extends _Portal {
  @override Future<List<PortalCourse>> courses() async => const [];
}
