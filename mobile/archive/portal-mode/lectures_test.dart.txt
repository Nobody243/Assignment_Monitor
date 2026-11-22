import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/screens/lectures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';

Summary withLectures(List<Map<String, dynamic>> l) => Summary({'schema': 1, 'student': {'name': 'Alex'}, 'lectures': l});

Map<String, dynamic> week(String course, int w, String title, List<String> files, {String kind = 'lecture'}) => {
      'id': '$course$w', 'course': course, 'week': w, 'title': title, 'kind': kind,
      'files': [for (final f in files) {'label': 'Download Lecture', 'filename': f}],
    };

void main() {
  Future<AppModel> model({bool portal = true, bool demo = false, List<String> skipped = const []}) async {
    SharedPreferences.setMockInitialValues({});
    final m = AppModel(Prefs(), store: MemoryStore());
    m.hasLogin = portal; m.demo = demo; m.syncSkipped = skipped;
    return m;
  }

  Future<void> show(WidgetTester tester, Widget w, {double scale = 1, Size size = const Size(360, 740)}) async {
    tester.view.devicePixelRatio = 1; tester.view.physicalSize = size;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(
      builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(textScaler: TextScaler.linear(scale)), child: child!),
      home: Scaffold(body: w),
    ));
    await tester.pump(const Duration(milliseconds: 600));
  }

  testWidgets('lectures are grouped by course with a download button per file', (tester) async {
    final m = await model();
    final s = withLectures([
      week('Cyber Security', 1, 'Introduction', ['intro.pptx']),
      week('Cyber Security', 2, 'Threats', ['threats.pdf', 'threats-notes.pdf']),
      week('Databases', 1, 'Relational model', ['rm.pdf']),
      week('Databases', 0, 'Course outline', ['outline.pdf'], kind: 'misc'),
    ]);
    await show(tester, LecturesScreen(summary: s, model: m));
    expect(find.text('Cyber Security'), findsOneWidget);
    expect(find.text('Databases'), findsOneWidget);
    await tester.tap(find.text('Cyber Security'));
    await tester.pumpAndSettle();
    expect(find.text('Week 1: Introduction'), findsOneWidget);
    expect(find.text('intro.pptx'), findsOneWidget);
    expect(find.text('threats-notes.pdf'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('long course and file names and a large text size do not overflow on a small phone', (tester) async {
    final m = await model();
    final long = 'A very long course name that goes on and on: Advanced Topics in Distributed Systems and Parallel Computing';
    final s = withLectures([week(long, 12, 'An equally long week title about consensus protocols and their failure modes in practice', ['a-really-long-file-name-for-lecture-twelve-final-version-2.pptx'])]);
    await show(tester, LecturesScreen(summary: s, model: m), scale: 2, size: const Size(320, 568));
    await tester.tap(find.textContaining('A very long course name'));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('with no lectures the screen says why: not signed in, demo, could not be read, or nothing yet', (tester) async {
    final s = withLectures([]);
    await show(tester, LecturesScreen(summary: s, model: await model(portal: false)));
    expect(find.textContaining('Lectures need your university login'), findsOneWidget);
    expect(find.textContaining('University login'), findsWidgets);
    await show(tester, LecturesScreen(summary: s, model: await model(portal: false, demo: true)));
    expect(find.text('Lectures are not in the demo'), findsOneWidget);
    await show(tester, LecturesScreen(summary: s, model: await model(skipped: ['lectures'])));
    expect(find.text('The lecture notes could not be read'), findsOneWidget);
    await show(tester, LecturesScreen(summary: s, model: await model()));
    expect(find.text('No lecture notes yet'), findsOneWidget);
  });

  testWidgets('pulling down on an empty screen still refreshes it', (tester) async {
    var refreshed = 0;
    await show(tester, RefreshIndicator(onRefresh: () async { refreshed++; }, child: LecturesScreen(summary: withLectures([]), model: await model())));
    await tester.fling(find.text('No lecture notes yet'), const Offset(0, 400), 1000);
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
    expect(refreshed, 1);
  });
}
