import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/main.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Quality checks that go beyond single features:
///  - the contract: summary files that are empty, sparse or damaged still read and draw on every screen;
///  - layout: every screen fits a small phone at large text sizes, in light and dark, with a real font;
///  - contrast: the text and status colours stay readable in all four palettes.
const _sections = ['Today', 'Assignments', 'Attendance', 'Exams', 'Announcements', 'Timetable', 'Results & GPA', 'Settings'];

Directory? _fontDir() {
  final root = Platform.environment['FLUTTER_ROOT'] ?? 'C:/src/flutter';
  final dir = Directory('$root/bin/cache/artifacts/material_fonts');
  return dir.existsSync() ? dir : null;
}

/// The layout checks only mean something with the real font (the test default is a very wide stand-in), so they are
/// skipped, with a note, where the Flutter SDK's Roboto cannot be found.
final _roboto = _fontDir();

Future<void> _loadRoboto() async {
  final dir = _roboto;
  if (dir == null) return;
  final loader = FontLoader('Roboto');
  for (final f in ['Roboto-Regular.ttf', 'Roboto-Medium.ttf', 'Roboto-Bold.ttf']) {
    final file = File('${dir.path}/$f');
    if (file.existsSync()) loader.addFont(Future.value(ByteData.sublistView(file.readAsBytesSync())));
  }
  await loader.load();
}

/// Fails with what overflowed and where, not just that something did.
void _noException(WidgetTester tester, String reason) {
  final e = tester.takeException();
  if (e == null) return;
  final text = e is FlutterError ? (e.diagnostics.map((d) => d.toStringDeep()).join(' | ')) : '$e';
  final where = RegExp(r'[a-z_/]+\.dart:\d+:\d+').allMatches(Uri.decodeFull(text)).map((m) => m.group(0)).toSet().take(3).join(', ');
  fail('$reason: $text ($where)');
}

Summary _fixture(String name) => Summary(jsonDecode(File('test/fixtures/summary_$name.json').readAsStringSync()) as Map<String, dynamic>);

void main() {
  setUpAll(_loadRoboto);

  Future<void> boot(WidgetTester tester, Summary s, {double textScale = 1, Brightness brightness = Brightness.dark, Size size = const Size(360, 740)}) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = Size(size.width * 3, size.height * 3);
    addTearDown(tester.view.reset);
    final prefs = Prefs();
    final model = AppModel(prefs)..summary = s..demo = true;
    await tester.pumpWidget(MaterialApp(
      theme: buildTheme(palettes.first, brightness),
      builder: (context, child) => MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(textScale)), child: child!),
      home: Shell(model: model, prefs: prefs),
    ));
    await tester.pump(const Duration(milliseconds: 600));
  }

  Future<void> open(WidgetTester tester, String section) async {
    if (section == 'Today') return;
    await tester.tap(find.byTooltip('Menu'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text(section).first);   // at a large text size the menu scrolls
    await tester.pumpAndSettle();
    await tester.tap(find.text(section).first);
    await tester.pumpAndSettle();
    expect(find.descendant(of: find.byType(AppBar), matching: find.text(section)), findsOneWidget, reason: '$section did not open');
  }

  group('contract: awkward summary files', () {
    for (final name in ['empty', 'sparse']) {
      test('$name: every reader returns instead of throwing', () {
        final s = _fixture(name);
        expect(() {
          s.generatedAt; s.lastCheck; s.studentName; s.firstName; s.semester; s.minimum; s.cgpa;
          for (final w in s.work) { w.id; w.title; w.course; w.due; w.todo; w.overdue; w.marks; w.wasDue; }
          for (final c in s.attendance) { c.percent; c.present; c.absent; c.canMiss; c.need; c.ok; c.recorded; c.classHours; c.classes; c.credit; }
          for (final e in s.exams) { e.day; e.title; e.room; e.row; e.seat; e.time; }
          for (final c in s.timetable) { c.day; c.start; c.end; c.course; }
          for (final n in s.announcements) { n.id; n.title; n.text; n.postedAt; }
          for (final t in s.terms) { t.name; t.gpa; t.cgpa; t.complete; for (final c in t.courses) { c.code; c.title; c.credits; c.grade; } }
        }, returnsNormally);
      });

      for (final section in _sections) {
        testWidgets('$name: $section draws', (tester) async {
          await boot(tester, _fixture(name));
          await open(tester, section);
          _noException(tester, 'drawing');
        });
      }
    }
    test('classes without a weekday or readable times are left off the timetable', () {
      final s = _fixture('sparse');
      expect(s.timetable.map((c) => c.course), ['Fine']);
    });
  });

  group('layout: a small phone, large text, light and dark', skip: _roboto == null ? 'the SDK Roboto font was not found' : null, () {
    for (final scale in [1.0, 1.5, 2.0]) {
      for (final b in [Brightness.light, Brightness.dark]) {
        testWidgets('all sections at ${(scale * 100).round()}% text, ${b.name}', (tester) async {
          final s = (await tester.runAsync(Summary.load))!;
          await boot(tester, s, textScale: scale, brightness: b);
          for (final section in _sections) {
            await open(tester, section);
            _noException(tester, '$section overflowed at ${(scale * 100).round()}% text in ${b.name}');
            if (section == 'Settings') {
              for (final page in ['Reminders', 'Appearance', 'Calendar', 'Account and data', 'About and privacy']) {
                await tester.ensureVisible(find.text(page));
                await tester.tap(find.text(page));
                await tester.pumpAndSettle();
                _noException(tester, 'Settings, $page overflowed at ${(scale * 100).round()}% text in ${b.name}');
                await tester.pageBack();
                await tester.pumpAndSettle();
              }
            }
            if (section == 'Results & GPA') {
              await tester.tap(find.text('Calculator'));
              await tester.pumpAndSettle();
              _noException(tester, 'the calculator overflowed at ${(scale * 100).round()}% text in ${b.name}');
            }
          }
        });
      }
    }
  });

  group('contrast: WCAG ratios', () {
    double lum(Color c) {
      double ch(double v) => v <= 0.03928 ? v / 12.92 : math.pow((v + 0.055) / 1.055, 2.4).toDouble();
      return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
    }
    double ratio(Color a, Color b) {
      final x = lum(a), y = lum(b);
      return (math.max(x, y) + 0.05) / (math.min(x, y) + 0.05);
    }

    for (final p in palettes) {
      for (final b in [Brightness.light, Brightness.dark]) {
        test('${p.label} ${b.name}: body text, secondary text, accent and status colours', () {
          final c = buildTheme(p, b).colorScheme;
          final pairs = <String, (Color, Color)>{
            'text on page': (c.onSurface, c.surface),
            'text on card': (c.onSurface, c.surfaceContainer),
            'secondary text on page': (c.onSurfaceVariant, c.surface),
            'secondary text on card': (c.onSurfaceVariant, c.surfaceContainer),
            'secondary text on tile': (c.onSurfaceVariant, c.surfaceContainerHigh),
            'text on the hero': (c.onPrimaryContainer, c.primaryContainer),
            'text on the accent button': (c.onPrimary, c.primary),
            'good on card': (Status.good(b), c.surfaceContainer),
            'warning on card': (Status.warn(b), c.surfaceContainer),
            'bad on card': (Status.bad(b), c.surfaceContainer),
            'good on page': (Status.good(b), c.surface),
            'bad on page': (Status.bad(b), c.surface),
          };
          final failures = [for (final e in pairs.entries) if (ratio(e.value.$1, e.value.$2) < 4.5) '${e.key}: ${ratio(e.value.$1, e.value.$2).toStringAsFixed(2)}'];
          expect(failures, isEmpty, reason: '${p.label} ${b.name} below 4.5:1');
        });
      }
    }
  });
}
