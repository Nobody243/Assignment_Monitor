import 'dart:io';
import 'dart:typed_data';

import 'package:assignment_monitor_mobile/portal.dart';
import 'package:assignment_monitor_mobile/portal_files.dart';
import 'package:assignment_monitor_mobile/portal_parse.dart';
import 'package:flutter_test/flutter_test.dart';

import 'portal_parse_test.dart' show lecturesHtml;

/// A browser that is already signed in to the LMS and serves one lectures page and one file.
class Lms implements PortalBrowser {
  Lms({this.fileType = 'application/vnd.ms-powerpoint', this.status = 200, this.disposition = ''});
  final String fileType, disposition;
  final int status;
  String current = 'https://$lmsHost/Student/Home.php';
  final opened = <String>[];
  final fetched = <String>[];

  @override Future<void> open(String url, {Duration timeout = const Duration(seconds: 40)}) async { opened.add(url); current = url; }
  @override Future<String> url() async => current;
  @override Future<String> html() async => lecturesHtml;
  @override Future<dynamic> js(String s) async => s.contains("s.options") ? 'ok' : null;
  @override Future<void> jsThenSettle(String source, {Duration timeout = const Duration(seconds: 20)}) async {}
  @override Future<FetchedFile> fetchFile(String url, {int maxBytes = maxDownloadBytes}) async {
    fetched.add(url);
    return FetchedFile(status, fileType, disposition, Uint8List.fromList([1, 2, 3, 4]));
  }
  @override Future<void> attachFile(String selector, String name, String mime, Uint8List bytes) async {}
  @override Future<void> close() async {}
}

void main() {
  late Directory dir;
  setUp(() => dir = Directory.systemTemp.createTempSync('files_test'));
  tearDown(() => dir.deleteSync(recursive: true));

  PortalFiles make(Lms b) => PortalFiles(_Ready(b), dir, pause: Duration.zero);

  test('a lecture file is found in the live listing and saved under course / week', () async {
    final b = Lms();
    final first = parseLectures(lecturesHtml, 'Cyber Security')[0];
    final f = (first['files'] as List)[0] as Map;
    final saved = await make(b).lectureFile(course: 'Cyber Security', week: first['week'], title: first['title'] as String, kind: 'lecture',
        filename: f['filename'] as String, label: f['label'] as String);
    expect(File(saved.path).existsSync(), isTrue);
    expect(saved.bytes, 4);
    expect(saved.path, contains('Cyber Security'));
    expect(saved.path, contains('Week 01'));
    expect(b.fetched.single, startsWith('https://$lmsHost/'));
  });

  test('a file that is no longer listed says so instead of guessing', () async {
    expect(
      () => make(Lms()).lectureFile(course: 'Cyber Security', week: '1', title: 'No such week', kind: 'lecture', filename: 'x.pdf', label: 'Download'),
      throwsA(isA<FileProblem>()),
    );
  });

  test('a web page where a file should be (an expired session) is refused, not saved as the file', () async {
    final first = parseLectures(lecturesHtml, 'Cyber Security')[0];
    final f = (first['files'] as List)[0] as Map;
    expect(
      () => make(Lms(fileType: 'text/html; charset=utf-8')).lectureFile(course: 'Cyber Security', week: first['week'], title: first['title'] as String,
          kind: 'lecture', filename: f['filename'] as String, label: f['label'] as String),
      throwsA(isA<FileProblem>()),
    );
  });

  test('a submission of the wrong kind or size is refused before the portal is touched', () async {
    final b = Lms();
    final files = make(b);
    final exe = await files.submit(course: 'C', id: 'i', title: 't', number: '1', path: '/x/virus.exe', bytes: Uint8List(10));
    expect(exe.ok, isFalse);
    expect(exe.message, contains('.pdf'));
    final big = await files.submit(course: 'C', id: 'i', title: 't', number: '1', path: '/x/a.pdf', bytes: Uint8List(16 * 1024 * 1024));
    expect(big.message, contains('15 MB'));
    final empty = await files.submit(course: 'C', id: 'i', title: 't', number: '1', path: '/x/a.pdf', bytes: Uint8List(0));
    expect(empty.message, contains('empty'));
    expect(b.opened, isEmpty);
  });
}

/// A Portal that is already in the LMS, so the tests only exercise the file code.
class _Ready extends Portal {
  _Ready(super.browser) : super(pause: Duration.zero);
  @override Future<bool> enterLms() async => true;
  @override Future<String> lmsPage(String url) async { await browser.open(url); return browser.html(); }
  @override Future<String> selectCourse(String name) async => browser.html();
}
