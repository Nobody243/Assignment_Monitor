import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/main.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Flutter's own accessibility guidelines on every section (and every Settings page), with the sample summary:
/// every tap target is at least 48 by 48 dp, every one has a label a screen reader can speak, and the text has enough
/// contrast. These are the phone's counterpart of the desktop layout audit: small or unlabeled controls are found
/// by a test instead of by a thumb.
const _sections = ['Today', 'Assignments', 'Attendance', 'Exams', 'Announcements', 'Timetable', 'Results & GPA', 'Settings'];
const _settingsPages = ['Reminders', 'Appearance', 'Calendar', 'Security', 'Account and data', 'About and privacy'];

void main() {
  Future<void> boot(WidgetTester tester, Summary s, Brightness brightness) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = const Size(360 * 3, 740 * 3);
    addTearDown(tester.view.reset);
    final prefs = Prefs();
    final model = AppModel(prefs)..summary = s..demo = true;
    await tester.pumpWidget(MaterialApp(theme: buildTheme(palettes.first, brightness), home: Shell(model: model, prefs: prefs)));
    await tester.pump(const Duration(milliseconds: 600));
  }

  Future<void> open(WidgetTester tester, String section) async {
    if (section == 'Today') return;
    await tester.tap(find.byTooltip('Menu'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text(section).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text(section).first);
    await tester.pumpAndSettle();
  }

  // every problem on every screen is collected, so one run lists them all instead of stopping at the first
  final problems = <String>[];
  Future<void> guidelines(WidgetTester tester, String where) async {
    for (final g in [androidTapTargetGuideline, labeledTapTargetGuideline]) {
      final e = await g.evaluate(tester);
      if (!e.passed) {
        // the raw reason is a long semantics dump; keep what it is and how big it is
        final r = (e.reason ?? '').replaceAll(RegExp(r'\s+'), ' ');
        final what = RegExp(r'(?:label|tooltip): "([^"]*)"').firstMatch(r)?.group(1) ?? r.substring(0, r.length.clamp(0, 80));
        final size = RegExp(r'found (Size\([^)]*\))').firstMatch(r)?.group(1) ?? '';
        problems.add('$where: "$what" $size ${g == labeledTapTargetGuideline ? '(no label)' : ''}'.trim());
      }
    }
  }

  for (final b in [Brightness.light]) {
    testWidgets('tap targets and labels on every section, ${b.name}', (tester) async {
      final handle = tester.ensureSemantics();
      final s = (await tester.runAsync(Summary.load))!;
      await boot(tester, s, b);
      for (final section in _sections) {
        await open(tester, section);
        await guidelines(tester, section);
        if (section == 'Settings') {
          for (final page in _settingsPages) {
            await tester.ensureVisible(find.text(page));
            await tester.tap(find.text(page));
            await tester.pumpAndSettle();
            await guidelines(tester, 'Settings, $page');
            await tester.pageBack();
            await tester.pumpAndSettle();
          }
        }
        if (section == 'Results & GPA') {
          await tester.tap(find.text('Calculator'));
          await tester.pumpAndSettle();
          await guidelines(tester, 'the GPA calculator');
        }
      }
      handle.dispose();
      expect(problems.toSet().toList(), isEmpty, reason: 'accessibility guidelines');
    });
  }
}
