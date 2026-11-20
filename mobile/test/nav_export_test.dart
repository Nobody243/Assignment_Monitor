import 'dart:typed_data';

import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/main.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/timetable_export.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('quick taps on the bar leave the title where it belongs and on the last tab chosen', (tester) async {
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = const Size(390 * 3, 800 * 3);
    addTearDown(tester.view.reset);
    final prefs = Prefs();
    final summary = (await tester.runAsync(Summary.load))!;
    final model = AppModel(prefs)..summary = summary..demo = true;
    await tester.pumpWidget(MaterialApp(home: Shell(model: model, prefs: prefs)));
    await tester.pumpAndSettle();

    final home = tester.getTopLeft(find.descendant(of: find.byType(AppBar), matching: find.text('Today'))).dx;   // where the title starts
    for (final order in [
      ['Assignments', 'Attendance', 'Exams'],
      ['Exams', 'Today', 'Attendance', 'Assignments', 'Exams'],
      ['Attendance', 'Exams', 'Attendance', 'Exams', 'Attendance'],
    ]) {
      for (final name in order) {
        await tester.tapAt(Offset(const {'Today': 65.0, 'Assignments': 151.0, 'Attendance': 238.0, 'Exams': 324.0}[name]!, 756));   // the four equal slots of the bar
        await tester.pump(const Duration(milliseconds: 40));
      }
      await tester.pumpAndSettle();
      final last = order.last;
      final titles = find.descendant(of: find.byType(AppBar), matching: find.text(last));
      expect(titles, findsOneWidget, reason: 'after $order the title should be "$last" and nothing else');
      expect(tester.getTopLeft(titles).dx, closeTo(home, 1), reason: 'the title "$last" is off its place');
    }
  });

  group('timetable files', () {
    late Summary s;
    setUpAll(() async {
      TestWidgetsFlutterBinding.ensureInitialized();
    });

    Future<Uint8List> make(WidgetTester tester, Future<Uint8List> Function(Summary) f) async {
      s = (await tester.runAsync(Summary.load))!;
      return (await tester.runAsync(() => f(s)))!;
    }

    testWidgets('PNG is a real picture', (tester) async {
      final b = await make(tester, (s) => TimetableExport.png(s));
      expect(b.sublist(0, 8), [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
      expect(b.length, greaterThan(5000));
    });

    testWidgets('JPG is a real picture', (tester) async {
      final b = await make(tester, (s) => TimetableExport.jpg(s, dark: true));
      expect(b.sublist(0, 2), [0xFF, 0xD8]);
    });

    testWidgets('PDF is a real document', (tester) async {
      final b = await make(tester, (s) => TimetableExport.pdfFile(s));
      expect(String.fromCharCodes(b.sublist(0, 5)), '%PDF-');
    });
  });
}
