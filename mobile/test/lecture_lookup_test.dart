import 'dart:io';
import 'dart:typed_data';

import 'package:assignment_monitor_mobile/portal.dart';
import 'package:assignment_monitor_mobile/portal_files.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';
import 'package:assignment_monitor_mobile/portal_parse.dart' show parseLectures;

import 'portal_parse_test.dart' show lecturesHtml;

/// A signed-in LMS whose lecture table is empty on the first read(s) and fills in later, as the portal does.
class Slow implements PortalBrowser {
  Slow(this.emptyReads);
  int emptyReads;
  final fetched = <String>[];
  @override Future<void> open(String url, {Duration timeout = const Duration(seconds: 40)}) async {}
  @override Future<String> url() async => 'https://$lmsHost/Student/LectureNotes.php';
  @override Future<String> html() async => emptyReads-- > 0 ? '<html><body></body></html>' : lecturesHtml;
  @override Future<dynamic> js(String s) async => null;
  @override Future<void> jsThenSettle(String source, {Duration timeout = const Duration(seconds: 20)}) async {}
  @override Future<FetchedFile> fetchFile(String url, {int maxBytes = maxDownloadBytes}) async {
    fetched.add(url);
    return FetchedFile(200, 'application/pdf', '', Uint8List.fromList([1, 2, 3]));
  }
  @override Future<void> attachFile(String selector, String name, String mime, Uint8List bytes) async {}
  @override Future<void> close() async {}
}

class Ready extends Portal {
  Ready(super.b) : super(pause: Duration.zero);
  @override Future<bool> enterLms() async => true;
  @override Future<String> lmsPage(String url) async => browser.html();
  @override Future<String> selectCourse(String name) async => browser.html();
}

void main() {
  late Directory dir;
  setUp(() => dir = Directory.systemTemp.createTempSync('lookup_test'));
  tearDown(() => dir.deleteSync(recursive: true));

  Future<SavedFile> get(Slow b, {String title = 'Introduction to indexing', Object week = '1', String filename = '', String label = 'Download Lecture', int index = 0}) =>
      PortalFiles(Ready(b), dir, pause: Duration.zero).lectureFile(course: 'Cyber Security', week: week, title: title, kind: 'lecture', filename: filename, label: label, index: index);

  test('a lecture table that fills in late is waited for instead of reported missing, and the file is saved', () async {
    final first = parseLectures(lecturesHtml, 'Cyber Security').first;
    final f = (first['files'] as List).first as Map;
    final b = Slow(2);   // the first two reads are an empty shell
    final saved = await get(b, title: first['title'] as String, week: first['week'] as Object, filename: f['filename'] as String, label: f['label'] as String);
    expect(File(saved.path).existsSync(), isTrue);
    expect(b.fetched.length, 1);
  });

  test('a table that never fills in is reported with the course name after the retries', () async {
    final first = parseLectures(lecturesHtml, 'Cyber Security').first;
    final f = (first['files'] as List).first as Map;
    final b = Slow(99);
    await expectLater(
      get(b, title: first['title'] as String, week: first['week'] as Object, filename: f['filename'] as String, label: f['label'] as String),
      throwsA(isA<FileProblem>().having((e) => e.message, 'message', contains('Cyber Security'))),
    );
    expect(b.fetched, isEmpty);
  });

  test('a missing file says which course and what to do, after looking again', () async {
    final b = Slow(0);
    expect(() => get(b, title: 'No such week', week: '99', filename: 'nope.pdf', label: 'Other'), throwsA(isA<FileProblem>().having((e) => e.message, 'message', contains('Cyber Security'))));
  });

  test('the loose matching finds a file by position when its name and label are not unique', () {
    final live = [
      {'week': '2', 'title': 'Two files', 'files': [{'label': 'Download Lecture', 'filename': 'a.pdf', 'href': 'h0'}, {'label': 'Download Lecture', 'filename': 'b.pdf', 'href': 'h1'}]},
    ];
    // exact name wins
    expect(PortalFiles.findForTest(live, week: '2', title: 'Two files', filename: 'b.pdf', label: 'Download Lecture', index: 0)!['href'], 'h1');
    // a renamed file, the same label twice: the position decides
    expect(PortalFiles.findForTest(live, week: '2', title: 'Two files', filename: 'renamed.pdf', label: 'Download Lecture', index: 1)!['href'], 'h1');
    // title with different case and spacing
    expect(PortalFiles.findForTest(live, week: '2', title: '  TWO   files ', filename: 'a.pdf', label: 'x', index: 0)!['href'], 'h0');
    // the week renumbered, the title the same
    expect(PortalFiles.findForTest(live, week: '5', title: 'Two files', filename: 'a.pdf', label: 'x', index: 0)!['href'], 'h0');
    // the title edited, the week the same: only the exact file name is trusted
    expect(PortalFiles.findForTest(live, week: '2', title: 'Two files (updated)', filename: 'b.pdf', label: 'x', index: 0)!['href'], 'h1');
    expect(PortalFiles.findForTest(live, week: '2', title: 'Two files (updated)', filename: 'zzz.pdf', label: 'Download Lecture', index: 0), isNull, reason: 'no guessing by position across an edited title');
    // nothing alike
    expect(PortalFiles.findForTest(live, week: '9', title: 'Elsewhere', filename: 'q.pdf', label: 'x', index: 0), isNull);
  });

  test('portal jobs run one after another, and a failure in one does not stop the next', () async {
    final m = AppModel(Prefs(), store: MemoryStore());
    final order = <String>[];
    final a = m.serialForTest(() async { order.add('a start'); await Future<void>.delayed(const Duration(milliseconds: 30)); order.add('a end'); });
    final failing = m.serialForTest(() async { order.add('b start'); throw StateError('b failed'); });
    final c = m.serialForTest(() async { order.add('c'); });
    await a;
    await expectLater(failing, throwsA(isA<StateError>()));
    await c;
    expect(order, ['a start', 'a end', 'b start', 'c']);
  });

  test('the reason for a failure is short and says what it was', () {
    expect(AppModel.why(StateError('The portal did not list your courses this time.')), 'The portal did not list your courses this time.');
    expect(AppModel.why(ArgumentError('Not a portal address.')), 'Not a portal address.');
    final long = AppModel.why(Exception('x' * 500));
    expect(long.length, lessThanOrEqualTo(90));
    expect(long, startsWith('_Exception'));
  });
}
